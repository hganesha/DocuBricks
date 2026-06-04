"""
apps/lib/components/status_tracker.py
--------------------------------------
Real-time document status tracker component.

``status_tracker`` polls the Lakebase ``document_registry`` table at a
configurable interval and renders status metric cards inside a ``st.empty()``
container.  It blocks (loops) until the document reaches a terminal state, then
returns the final status string so the caller can decide what to do next.

Terminal states
~~~~~~~~~~~~~~~
``COMPLETE``, ``QUARANTINE``, ``FAILED``, ``REVIEW``
"""
from __future__ import annotations

import time

import streamlit as st

from ..lakebase import lb_query

# ---------------------------------------------------------------------------
# Status configuration
# ---------------------------------------------------------------------------

#: Maps each document status to display properties.
#: ``done: True`` means the polling loop should stop when this status is reached.
STATUS_CONFIG: dict[str, dict] = {
    "RECEIVED":    {"emoji": "📥", "color": "#5F5E5A", "label": "Received",    "done": False},
    "PARSING":     {"emoji": "⚙️",  "color": "#185FA5", "label": "Parsing",     "done": False},
    "PARSED":      {"emoji": "📄", "color": "#185FA5", "label": "Parsed",      "done": False},
    "CLASSIFYING": {"emoji": "🔍", "color": "#185FA5", "label": "Classifying", "done": False},
    "CLASSIFIED":  {"emoji": "🏷️",  "color": "#185FA5", "label": "Classified",  "done": False},
    "EXTRACTING":  {"emoji": "⚙️",  "color": "#185FA5", "label": "Extracting",  "done": False},
    "EXTRACTED":   {"emoji": "📋", "color": "#185FA5", "label": "Extracted",   "done": False},
    "VALIDATED":   {"emoji": "✔️",  "color": "#0F6E56", "label": "Validated",   "done": False},
    "COMPLETE":    {"emoji": "🎉", "color": "#0F6E56", "label": "Complete",    "done": True},
    "REVIEW":      {"emoji": "👁️",  "color": "#854F0B", "label": "Needs Review","done": True},
    "QUARANTINE":  {"emoji": "⚠️",  "color": "#993C1D", "label": "Quarantine",  "done": True},
    "FAILED":      {"emoji": "❌", "color": "#A32D2D", "label": "Failed",      "done": True},
}

_TERMINAL_STATES = {k for k, v in STATUS_CONFIG.items() if v["done"]}

_POLL_SQL = """
    SELECT status, document_type, extraction_conf, classification_conf, failure_reason
    FROM document_registry
    WHERE document_id = %s
"""


# ---------------------------------------------------------------------------
# Component
# ---------------------------------------------------------------------------

def status_tracker(document_id: str, poll_interval: float = 2.0) -> str:
    """
    Block and poll Lakebase until the document reaches a terminal state,
    rendering live status cards on every update.

    The component renders inside a single ``st.empty()`` container so it
    does not accumulate DOM nodes across poll iterations.

    Parameters
    ----------
    document_id:    hex SHA-256 document identifier
    poll_interval:  seconds to sleep between polls (default: 2.0)

    Returns
    -------
    str
        The final terminal status string, e.g. ``'COMPLETE'``, ``'REVIEW'``.
    """
    placeholder = st.empty()

    while True:
        rows = lb_query(_POLL_SQL, (document_id,))

        if not rows:
            with placeholder.container():
                st.info(f"Waiting for document `{document_id[:16]}…` to appear in registry…")
            time.sleep(poll_interval)
            continue

        info = rows[0]
        status = info.get("status", "RECEIVED")
        cfg = STATUS_CONFIG.get(status, {"emoji": "?", "color": "#000000", "label": status, "done": False})

        with placeholder.container():
            # Status headline
            st.markdown(
                f'<div style="border-left:4px solid {cfg["color"]};'
                f'padding:8px 12px;border-radius:0 6px 6px 0;'
                f'background:rgba(0,0,0,0.03);margin-bottom:12px;">'
                f'<span style="font-size:1.3em">{cfg["emoji"]}</span> '
                f'<strong style="font-size:1.1em;color:{cfg["color"]}">{cfg["label"]}</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Metric cards
            col1, col2, col3 = st.columns(3)
            col1.metric("Status", f"{cfg['emoji']}  {status}")

            doc_type = info.get("document_type") or "—"
            col2.metric("Document Type", doc_type)

            ext_conf = info.get("extraction_conf")
            if ext_conf is not None:
                col3.metric("Extraction Confidence", f"{float(ext_conf):.0%}")
            else:
                cls_conf = info.get("classification_conf")
                if cls_conf is not None:
                    col3.metric("Classification Confidence", f"{float(cls_conf):.0%}")
                else:
                    col3.metric("Confidence", "—")

            # Failure reason
            if status == "FAILED" and info.get("failure_reason"):
                st.error(f"Failure: {info['failure_reason']}")

            # Review hint
            if status == "REVIEW":
                st.warning(
                    "This document has been flagged for human review.  "
                    "Open the Review app to inspect and resolve."
                )

        if cfg.get("done") or status in _TERMINAL_STATES:
            return status

        time.sleep(poll_interval)
