"""
apps/review/pages/field_editor_page.py
---------------------------------------
History view: resolved review items for this tenant in the last 7 days.

Shows a table of resolved documents; clicking a row expands a field diff
that shows what the reviewer changed vs the original AI extraction.
"""
from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd

from lib.lakebase import lb_query
from lib.sql_warehouse import wh_query
from lib.components.field_editor import field_diff_view

_HISTORY_QUERY = """
    SELECT
        r.review_id,
        r.document_id,
        d.document_type,
        r.resolution,
        r.resolved_at,
        r.resolved_by        AS reviewer,
        r.corrected_json,
        d.source_path,
        d.extraction_conf
    FROM  review_queue      r
    JOIN  document_registry d USING (document_id)
    WHERE r.tenant_id    = %s
      AND r.resolved_at >= NOW() - INTERVAL '7 days'
      AND r.resolved_at IS NOT NULL
    ORDER BY r.resolved_at DESC
    LIMIT 200
"""

_SILVER_TABLE: dict[str, str] = {
    "mortgage_application": "docubricks_prod.silver.mortgage_applications",
    "kyc_cdd_form":         "docubricks_prod.silver.kyc_cdd_forms",
    "aml_sar":              "docubricks_prod.silver.aml_sars",
    "invoice":              "docubricks_prod.silver.invoices",
}

_RESOLUTION_COLOR: dict[str, str] = {
    "APPROVED":   "#16a34a",
    "REPROCESS":  "#2563eb",
    "QUARANTINE": "#dc2626",
}


def _resolution_badge(resolution: str) -> str:
    color = _RESOLUTION_COLOR.get(resolution, "#6b7280")
    return (
        f'<span style="background:{color}22;color:{color};'
        f'border-radius:4px;font-size:11px;font-weight:700;'
        f'padding:2px 7px;">{resolution}</span>'
    )


def _load_original_fields(document_id: str, document_type: str) -> dict:
    table = _SILVER_TABLE.get(document_type)
    if not table:
        return {}
    rows = wh_query(
        f"SELECT * FROM {table} WHERE document_id = %(doc_id)s LIMIT 1",
        {"doc_id": document_id},
    )
    if not rows:
        return {}
    row = rows[0]
    row.pop("field_confidences", None)
    return row


def render(session: dict) -> None:
    tenant_id: str = session["tenant_id"]

    st.title("Review History")
    st.caption("Resolved items from the last 7 days")

    rows = lb_query(_HISTORY_QUERY, (tenant_id,))

    if not rows:
        st.info("No resolved reviews in the last 7 days.")
        return

    # ── Summary metrics ────────────────────────────────────────────────────────
    total   = len(rows)
    approved    = sum(1 for r in rows if r["resolution"] == "APPROVED")
    reprocessed = sum(1 for r in rows if r["resolution"] == "REPROCESS")
    quarantined = sum(1 for r in rows if r["resolution"] == "QUARANTINE")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total resolved", total)
    m2.metric("Approved",    approved,    delta=None)
    m3.metric("Reprocessed", reprocessed, delta=None)
    m4.metric("Quarantined", quarantined, delta=None)

    st.markdown("---")

    # ── Filter controls ────────────────────────────────────────────────────────
    filter_col1, filter_col2 = st.columns([2, 2])
    with filter_col1:
        resolution_filter = st.multiselect(
            "Filter by resolution",
            options=["APPROVED", "REPROCESS", "QUARANTINE"],
            default=[],
            placeholder="All resolutions",
        )
    with filter_col2:
        type_options = sorted({r["document_type"] for r in rows})
        type_filter = st.multiselect(
            "Filter by document type",
            options=type_options,
            default=[],
            placeholder="All types",
        )

    # Apply filters
    filtered = rows
    if resolution_filter:
        filtered = [r for r in filtered if r["resolution"] in resolution_filter]
    if type_filter:
        filtered = [r for r in filtered if r["document_type"] in type_filter]

    if not filtered:
        st.warning("No items match your filters.")
        return

    # ── Table ──────────────────────────────────────────────────────────────────
    st.markdown(f"**{len(filtered)} item{'s' if len(filtered) != 1 else ''}**")

    header = st.columns([2, 2, 1.5, 2, 2])
    header[0].markdown("**Document ID**")
    header[1].markdown("**Document Type**")
    header[2].markdown("**Resolution**")
    header[3].markdown("**Resolved At**")
    header[4].markdown("**Reviewer**")

    st.markdown(
        '<hr style="margin:4px 0 8px 0;border-color:#e5e7eb;">',
        unsafe_allow_html=True,
    )

    for item in filtered:
        review_id   = item["review_id"]
        document_id = item["document_id"]
        doc_type    = item["document_type"]
        resolution  = item["resolution"]
        resolved_at = item["resolved_at"]
        reviewer    = item["reviewer"] or "—"
        corrected_json = item["corrected_json"]

        resolved_str = (
            resolved_at.strftime("%Y-%m-%d %H:%M UTC")
            if hasattr(resolved_at, "strftime")
            else str(resolved_at)
        )

        row_cols = st.columns([2, 2, 1.5, 2, 2])
        row_cols[0].markdown(f"`{document_id[:20]}…`" if len(document_id) > 20 else f"`{document_id}`")
        row_cols[1].markdown(doc_type.replace("_", " ").title())
        row_cols[2].markdown(_resolution_badge(resolution), unsafe_allow_html=True)
        row_cols[3].markdown(f'<span style="font-size:12px">{resolved_str}</span>', unsafe_allow_html=True)
        row_cols[4].markdown(f'<span style="font-size:12px">{reviewer}</span>', unsafe_allow_html=True)

        # Expandable diff view
        with st.expander(f"View diff — {document_id}", expanded=False):
            if corrected_json is None:
                st.info("No corrections recorded (approved as-is or quarantined without edits).")
            else:
                # Load original fields from Silver for comparison
                try:
                    corrected: dict = (
                        json.loads(corrected_json)
                        if isinstance(corrected_json, str)
                        else corrected_json
                    )
                except (json.JSONDecodeError, TypeError):
                    corrected = {}

                with st.spinner("Loading original extraction…"):
                    original = _load_original_fields(document_id, doc_type)

                if not original:
                    st.warning(
                        "Original extracted fields not found in Silver — "
                        "the Silver record may have been overwritten or deleted."
                    )
                    st.json(corrected)
                else:
                    field_diff_view(original=original, corrected=corrected)

        st.markdown(
            '<hr style="margin:2px 0;border-color:#f3f4f6;">',
            unsafe_allow_html=True,
        )
