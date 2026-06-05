"""
apps/portal/pages/genie_chat.py
--------------------------------
Genie Chat page — conversational interface to the Databricks AI/BI Genie
spaces configured per vertical.

Features
~~~~~~~~
- Vertical-aware: resolves correct Genie space_id for the user's vertical
- Full conversation history persisted in st.session_state.messages
- st.chat_input widget for question submission
- OTel timing on every Genie call (genie_latency histogram)
- Five seed-question pills shown below the chat input
- Graceful GenieError handling with retry suggestion
- Genie space name displayed in the page header
"""
from __future__ import annotations

import time

import streamlit as st

from lib.auth import get_session
from lib.lakebase import lb_query
from lib.genie import ask_genie, GenieError
from lib.components.vertical_selector import vertical_selector, genie_space_for
from lib.otel import genie_latency, tracer

# ---------------------------------------------------------------------------
# Seed questions per vertical
# ---------------------------------------------------------------------------
_SEED_QUESTIONS: dict[str, list[str]] = {
    "fs": [
        "What is the average LTV ratio across all mortgage applications this month?",
        "How many KYC forms are pending review right now?",
        "Show me the top 5 applicants by loan amount.",
        "What is the extraction confidence trend over the last 7 days?",
        "Which document types have the highest re-review rate?",
    ],
    "healthcare": [
        "How many patient intake forms were processed this week?",
        "What is the average confidence score for clinical notes?",
        "Show me the breakdown of document types by department.",
        "Which documents are flagged for review in the last 24 hours?",
        "What is the average processing time per document type?",
    ],
    "legal": [
        "How many contract documents were processed this quarter?",
        "What clauses are most frequently extracted from NDAs?",
        "Show me documents with the lowest extraction confidence.",
        "Which legal document types have the most review flags?",
        "What is the volume of documents processed by week?",
    ],
}

_DEFAULT_SEEDS = [
    "How many documents were processed today?",
    "What is the average extraction confidence across all document types?",
    "Show me documents that need review.",
    "What are the most common document types processed?",
    "What is the processing time trend over the last 30 days?",
]

_VERTICAL_LABELS = {
    "fs": "Financial Services",
    "healthcare": "Healthcare & Life Sciences",
    "legal": "Legal & Compliance",
    "manufacturing": "Manufacturing / Supply Chain",
    "insurance": "Insurance",
    "real_estate": "Real Estate",
}


# ---------------------------------------------------------------------------
# Page render
# ---------------------------------------------------------------------------

def render(session: dict) -> None:
    tenant_id = session["tenant_id"]

    st.title("Ask DocuBricks")

    # ── Vertical / space resolution ────────────────────────────────────────
    vertical = vertical_selector(tenant_id)
    vertical_label = _VERTICAL_LABELS.get(vertical, vertical.upper())

    try:
        space_id = genie_space_for(vertical)
    except ValueError as exc:
        st.error(
            f"Genie is not configured for the **{vertical_label}** vertical.  \n"
            f"Details: {exc}"
        )
        st.stop()

    st.markdown(
        f"Chatting with **Genie space:** `{space_id}` &nbsp;·&nbsp; "
        f"Vertical: **{vertical_label}**"
    )
    st.divider()

    # ── Conversation history init ──────────────────────────────────────────
    msg_key = f"genie_messages_{vertical}"
    if msg_key not in st.session_state:
        st.session_state[msg_key] = []

    messages: list[dict] = st.session_state[msg_key]

    # ── Render conversation history ────────────────────────────────────────
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Seed question pills ────────────────────────────────────────────────
    seeds = _SEED_QUESTIONS.get(vertical, _DEFAULT_SEEDS)

    # Show seed pills only when conversation is empty or fewer than 3 messages
    if len(messages) < 3:
        st.markdown("**Try asking:**")
        seed_cols = st.columns(len(seeds))
        for i, (col, question) in enumerate(zip(seed_cols, seeds)):
            with col:
                if st.button(
                    question,
                    key=f"seed_{vertical}_{i}",
                    help=question,
                    use_container_width=True,
                ):
                    st.session_state[f"genie_pending_{vertical}"] = question
                    st.rerun()

        st.divider()

    # ── Chat input ─────────────────────────────────────────────────────────
    pending = st.session_state.pop(f"genie_pending_{vertical}", None)
    user_input = st.chat_input(
        f"Ask anything about your {vertical_label} documents…",
        key=f"genie_input_{vertical}",
    )

    question = pending or user_input
    if question:
        # Add user message
        messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Call Genie with OTel timing
        with st.chat_message("assistant"):
            with st.spinner("Genie is thinking…"):
                t0 = time.monotonic()
                try:
                    with tracer.start_as_current_span("genie.ask"):
                        answer = ask_genie(space_id, question, timeout=90)
                    elapsed = time.monotonic() - t0
                    genie_latency.record(elapsed, {"vertical": vertical, "space_id": space_id})
                    st.markdown(answer)
                    messages.append({"role": "assistant", "content": answer})
                except GenieError as exc:
                    elapsed = time.monotonic() - t0
                    genie_latency.record(elapsed, {"vertical": vertical, "space_id": space_id, "error": "true"})
                    error_msg = (
                        f"Genie could not answer your question right now.  \n\n"
                        f"**Reason:** {exc.message}  \n\n"
                        "Please rephrase your question or try again in a moment."
                    )
                    st.warning(error_msg)
                    messages.append({"role": "assistant", "content": error_msg})
                except Exception as exc:
                    elapsed = time.monotonic() - t0
                    genie_latency.record(elapsed, {"vertical": vertical, "space_id": space_id, "error": "true"})
                    error_msg = (
                        f"An unexpected error occurred: `{type(exc).__name__}: {exc}`  \n\n"
                        "Please try again."
                    )
                    st.error(error_msg)
                    messages.append({"role": "assistant", "content": error_msg})

        # Persist updated messages
        st.session_state[msg_key] = messages

    # ── Clear conversation button ──────────────────────────────────────────
    if messages:
        st.divider()
        if st.button("Clear conversation", key=f"genie_clear_{vertical}"):
            st.session_state[msg_key] = []
            st.rerun()
