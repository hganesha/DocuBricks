"""
apps/portal/pages/status.py
----------------------------
Document Status page.

Features
~~~~~~~~
- If session state contains ``tracking_doc``: show live status_tracker component
  for that document, then extracted fields from the relevant Silver table
- Otherwise: show a table of the last 20 documents for the current tenant with
  clickable rows to drill into any document
- "Needs review" documents highlighted in amber with link to Review app
- Extracted field detail fetched from SQL Warehouse (Silver tables)
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from lib.auth import get_session
from lib.lakebase import lb_query
from lib.sql_warehouse import wh_query
from lib.components.status_tracker import status_tracker
from lib.components.confidence_badge import confidence_badge

# ---------------------------------------------------------------------------
# Status display config (emoji + colour)
# ---------------------------------------------------------------------------
_STATUS_EMOJI = {
    "RECEIVED":    "📥",
    "PARSING":     "⚙️",
    "PARSED":      "📄",
    "CLASSIFYING": "🔍",
    "CLASSIFIED":  "🏷️",
    "EXTRACTING":  "⚙️",
    "EXTRACTED":   "📋",
    "VALIDATED":   "✔️",
    "COMPLETE":    "✅",
    "REVIEW":      "⚠️",
    "QUARANTINE":  "🚫",
    "FAILED":      "❌",
}

# Silver table per document_type
_SILVER_TABLE = {
    "mortgage_application": "docubricks_prod.silver.silver_route_mortgage_application",
    "kyc_cdd_form":         "docubricks_prod.silver.silver_route_kyc_cdd_form",
    "aml_sar":              "docubricks_prod.silver.silver_route_aml_sar",
    "invoice":              "docubricks_prod.silver.silver_route_invoice",
}

_RECENT_SQL = """
    SELECT
        document_id,
        original_filename,
        document_type,
        status,
        extraction_conf,
        created_at,
        updated_at
    FROM document_registry
    WHERE tenant_id = %s
    ORDER BY created_at DESC
    LIMIT 20
"""

_DETAIL_SQL = """
    SELECT
        document_id,
        status,
        document_type,
        extraction_conf,
        classification_conf,
        failure_reason,
        original_filename,
        vertical,
        created_at,
        updated_at
    FROM document_registry
    WHERE document_id = %s
    LIMIT 1
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_emoji(status: str) -> str:
    return _STATUS_EMOJI.get(status, "❓")


def _fmt_doc_id(doc_id: str) -> str:
    return doc_id[:16] + "…" if len(doc_id) > 16 else doc_id


def _fmt_ts(ts) -> str:
    if ts is None:
        return "—"
    if isinstance(ts, str):
        return ts[:19].replace("T", " ")
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M")
    return str(ts)


def _fetch_silver_fields(document_id: str, document_type: str) -> list[dict]:
    """Query the appropriate Silver table for extracted fields."""
    table = _SILVER_TABLE.get(document_type)
    if not table:
        return []
    try:
        rows = wh_query(
            f"SELECT * FROM {table} WHERE document_id = %s LIMIT 1",
            (document_id,),
        )
        return rows
    except Exception:
        return []


def _render_detail_view(document_id: str, tenant_id: str) -> None:
    """Render full detail for a tracked/clicked document."""
    rows = lb_query(_DETAIL_SQL, (document_id,))
    if not rows:
        st.info(f"Document `{document_id}` not found in registry yet.")
        return

    info = rows[0]
    status = info.get("status", "RECEIVED")
    emoji = _status_emoji(status)
    doc_type = info.get("document_type") or "—"
    ext_conf = info.get("extraction_conf")
    cls_conf = info.get("classification_conf")

    # Amber highlight for REVIEW docs
    if status == "REVIEW":
        st.warning(
            "This document requires human review.  \n"
            "[Open the Review app](/review) to inspect and resolve."
        )

    # Status card
    st.subheader(f"{emoji} {status}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Document Type", doc_type.replace("_", " ").title() if doc_type != "—" else "—")
    col2.metric("Vertical", (info.get("vertical") or "—").upper())
    col3.metric("Uploaded", _fmt_ts(info.get("created_at")))
    col4.metric("Updated", _fmt_ts(info.get("updated_at")))

    # Confidence
    if ext_conf is not None:
        confidence_badge(float(ext_conf), label="Extraction Confidence")
    elif cls_conf is not None:
        confidence_badge(float(cls_conf), label="Classification Confidence")

    if info.get("failure_reason"):
        st.error(f"Failure reason: {info['failure_reason']}")

    st.markdown(
        f"**Document ID:** `{document_id}`  \n"
        f"**Original File:** `{info.get('original_filename', '—')}`"
    )

    # Extracted fields from Silver table
    if doc_type != "—" and status not in ("RECEIVED", "PARSING", "CLASSIFYING"):
        st.divider()
        st.markdown("#### Extracted Fields")
        silver_rows = _fetch_silver_fields(document_id, doc_type)
        if silver_rows:
            row = silver_rows[0]
            # Filter out internal columns
            _skip = {"document_id", "tenant_id", "source_path", "_rescued_data",
                     "_commit_timestamp", "_change_type", "ingested_date"}
            display = {k: v for k, v in row.items() if k not in _skip and v is not None}
            if display:
                for field, value in display.items():
                    label = field.replace("_", " ").title()
                    st.text_input(label, value=str(value), disabled=True, key=f"field_{field}")
            else:
                st.info("No extracted fields available yet.")
        else:
            st.info("Extracted fields not yet available or document type not supported.")


# ---------------------------------------------------------------------------
# Page render
# ---------------------------------------------------------------------------

def render(session: dict) -> None:
    tenant_id = session["tenant_id"]

    st.title("Document Status")

    tracking_doc = st.session_state.get("tracking_doc")

    # ── Live tracker mode ──────────────────────────────────────────────────
    if tracking_doc:
        col_back, col_title = st.columns([1, 6])
        with col_back:
            if st.button("← Back to list"):
                del st.session_state["tracking_doc"]
                st.rerun()
        with col_title:
            st.markdown(
                f"**Tracking:** `{_fmt_doc_id(tracking_doc)}`"
            )

        st.divider()

        # Check if document is already in a terminal state — if so skip the
        # polling loop and jump straight to detail view.
        info_rows = lb_query(
            "SELECT status FROM document_registry WHERE document_id = %s LIMIT 1",
            (tracking_doc,),
        )
        existing_status = info_rows[0]["status"] if info_rows else None
        _TERMINAL = {"COMPLETE", "QUARANTINE", "FAILED", "REVIEW"}

        if existing_status in _TERMINAL:
            _render_detail_view(tracking_doc, tenant_id)
        else:
            st.markdown("#### Live Processing Status")
            final_status = status_tracker(tracking_doc, poll_interval=2.0)
            st.divider()
            _render_detail_view(tracking_doc, tenant_id)

        return

    # ── Recent documents table ─────────────────────────────────────────────
    st.markdown("### Recent Documents")
    st.caption("Showing the last 20 documents for your tenant. Click a row to view details.")

    rows = lb_query(_RECENT_SQL, (tenant_id,))

    if not rows:
        st.info("No documents found for your tenant. Upload your first document to get started.")
        return

    # Build display rows
    table_data = []
    for r in rows:
        status = r.get("status", "RECEIVED")
        emoji = _status_emoji(status)
        conf = r.get("extraction_conf")
        conf_str = f"{float(conf):.0%}" if conf is not None else "—"
        doc_type = r.get("document_type") or "—"
        table_data.append(
            {
                "Doc ID": _fmt_doc_id(r["document_id"]),
                "Filename": r.get("original_filename") or "—",
                "Type": doc_type.replace("_", " ").title() if doc_type != "—" else "—",
                "Status": f"{emoji} {status}",
                "Confidence": conf_str,
                "Uploaded": _fmt_ts(r.get("created_at")),
            }
        )

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.markdown("**Open a document**")
    st.caption("Paste or select a document ID to view its full status and extracted fields.")

    # Manual document ID entry
    manual_id = st.text_input(
        "Document ID",
        placeholder="Enter full document ID (SHA-256 hex)",
        key="status_manual_id",
    )

    # Quick-select from recent list
    quick_options = ["— select —"] + [r["document_id"] for r in rows]
    quick_select = st.selectbox(
        "Or select from recent list",
        quick_options,
        key="status_quick_select",
    )

    col_open, _ = st.columns([2, 6])
    with col_open:
        if st.button("Open Document", type="primary"):
            chosen_id = (
                quick_select if quick_select != "— select —"
                else manual_id.strip()
            )
            if not chosen_id:
                st.warning("Please enter or select a Document ID.")
            else:
                st.session_state["tracking_doc"] = chosen_id
                st.rerun()
