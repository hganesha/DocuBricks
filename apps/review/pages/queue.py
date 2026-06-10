"""
apps/review/pages/queue.py
--------------------------
Core review queue page.

Flow:
  1. Load the highest-priority unresolved review item for this tenant.
  2. If queue is empty, celebrate.
  3. Show document inline (left) + editable field editor (right).
  4. Three resolution actions: Approve / Save & Reprocess / Quarantine.
  5. After resolution, rerun to load next item.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

from lib.lakebase import lb_query, lb_exec, lb_exec_returning
from lib.sql_warehouse import wh_query
from lib.components.field_editor import field_editor
from lib.components.document_viewer import document_viewer
from lib.components.confidence_badge import confidence_badge
from lib.schema_sections import get_schema_meta

# ── Constants ──────────────────────────────────────────────────────────────────
_SILVER_TABLE: dict[str, str] = {
    "mortgage_application": "docubricks_prod.silver.mortgage_applications",
    "kyc_cdd_form":         "docubricks_prod.silver.kyc_cdd_forms",
    "aml_sar":              "docubricks_prod.silver.aml_sars",
    "invoice":              "docubricks_prod.silver.invoices",
}

_QUEUE_QUERY = """
    SELECT
        r.review_id,
        r.document_id,
        r.review_reason,
        r.priority,
        r.sla_due_at,
        d.document_type,
        d.extraction_conf,
        d.source_path
    FROM  review_queue        r
    JOIN  document_registry   d USING (document_id)
    WHERE r.tenant_id   = %s
      AND r.resolved_at IS NULL
    ORDER BY r.priority ASC, r.created_at ASC
    LIMIT 1
"""

_STATS_QUERY = """
    SELECT
        COUNT(*)                                              AS total_pending,
        COUNT(*) FILTER (WHERE sla_due_at < NOW())           AS past_sla,
        AVG(d.extraction_conf)                               AS avg_conf
    FROM  review_queue      r
    JOIN  document_registry d USING (document_id)
    WHERE r.tenant_id   = %s
      AND r.resolved_at IS NULL
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_queue_item(tenant_id: str) -> dict | None:
    rows = lb_query(_QUEUE_QUERY, (tenant_id,))
    return rows[0] if rows else None


def _load_stats(tenant_id: str) -> dict:
    rows = lb_query(_STATS_QUERY, (tenant_id,))
    return rows[0] if rows else {"total_pending": 0, "past_sla": 0, "avg_conf": None}


def _load_silver_fields(document_id: str, document_type: str) -> tuple[dict, dict]:
    """
    Returns (fields_dict, confidence_scores_dict).
    Falls back to empty dicts if the Silver row is not found.
    """
    table = _SILVER_TABLE.get(document_type)
    if not table:
        return {}, {}

    rows = wh_query(
        f"SELECT * FROM {table} WHERE document_id = %(doc_id)s LIMIT 1",
        {"doc_id": document_id},
    )
    if not rows:
        return {}, {}

    row = rows[0]

    # field_confidences is stored as a JSON string in Silver
    raw_conf = row.pop("field_confidences", None)
    conf_scores: dict[str, float] = {}
    if raw_conf:
        try:
            conf_scores = json.loads(raw_conf) if isinstance(raw_conf, str) else raw_conf
        except (json.JSONDecodeError, TypeError):
            pass

    return row, conf_scores


def _resolve(
    review_id: str,
    document_id: str,
    resolution: str,
    corrected_fields: dict | None = None,
    reviewer: str = "",
) -> None:
    """Write resolution to Lakebase and update document_registry status."""

    new_doc_status = {
        "APPROVED":   "COMPLETE",
        "REPROCESS":  "REPROCESS",
        "QUARANTINE": "QUARANTINE",
    }[resolution]

    corrected_json = json.dumps(corrected_fields) if corrected_fields else None

    lb_exec(
        """
        UPDATE review_queue
           SET resolved_at    = NOW(),
               resolution     = %s,
               corrected_json = %s,
               resolved_by    = %s
         WHERE review_id = %s
        """,
        (resolution, corrected_json, reviewer, review_id),
    )

    lb_exec(
        "UPDATE document_registry SET status = %s WHERE document_id = %s",
        (new_doc_status, document_id),
    )

    if resolution == "REPROCESS":
        lb_exec(
            """
            INSERT INTO reprocessing_queue
                (document_id, corrected_json, queued_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (document_id) DO UPDATE
                SET corrected_json = EXCLUDED.corrected_json,
                    queued_at      = EXCLUDED.queued_at
            """,
            (document_id, corrected_json),
        )


def _sla_chip(sla_due_at) -> None:
    if sla_due_at is None:
        return
    now = datetime.now(timezone.utc)
    if hasattr(sla_due_at, "tzinfo") and sla_due_at.tzinfo is None:
        sla_due_at = sla_due_at.replace(tzinfo=timezone.utc)
    overdue = sla_due_at < now
    delta = abs((sla_due_at - now).total_seconds())
    hours = int(delta // 3600)
    mins  = int((delta % 3600) // 60)
    label = f"{'OVERDUE' if overdue else 'Due'} {hours}h {mins}m {'ago' if overdue else ''}"
    color = "#ef4444" if overdue else "#f59e0b"
    bg    = "#fee2e2" if overdue else "#fef3c7"
    st.markdown(
        f'<span style="background:{bg};color:{color};border-radius:4px;'
        f'font-size:11px;font-weight:700;padding:2px 8px;">{label}</span>',
        unsafe_allow_html=True,
    )


def _reason_chip(reason: str) -> None:
    st.markdown(
        f'<span style="background:#ede9fe;color:#6d28d9;border-radius:4px;'
        f'font-size:12px;font-weight:600;padding:3px 10px;">{reason}</span>',
        unsafe_allow_html=True,
    )


# ── Main render ────────────────────────────────────────────────────────────────

def render(session: dict) -> None:
    tenant_id: str = session["tenant_id"]
    user_email: str = session["user_email"]

    st.title("Review Queue")

    # ── Stats bar ──────────────────────────────────────────────────────────────
    stats = _load_stats(tenant_id)
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Pending items", stats["total_pending"])
    col_b.metric(
        "Past SLA",
        stats["past_sla"],
        delta=None,
        delta_color="inverse" if stats["past_sla"] > 0 else "normal",
    )
    avg_conf = stats["avg_conf"]
    col_c.metric(
        "Avg confidence",
        f"{avg_conf:.1%}" if avg_conf is not None else "—",
    )

    st.markdown("---")

    # ── Load next item ─────────────────────────────────────────────────────────
    item = _load_queue_item(tenant_id)

    if item is None:
        st.success("Queue is empty — all documents reviewed! ✓")
        st.balloons()
        return

    review_id   = item["review_id"]
    document_id = item["document_id"]
    doc_type    = item["document_type"]
    source_path = item["source_path"]
    conf_score  = item["extraction_conf"]

    # ── CSS: sticky document pane + clean tab styling ─────────────────────────
    st.markdown(
        """
        <style>
        [data-testid="column"]:nth-child(1) > div:first-child {
            position: sticky;
            top: 3.5rem;
        }
        [data-testid="stTabs"] [data-baseweb="tab"] {
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 500;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Two-column layout: doc 55% | fields 45% ───────────────────────────────
    left_col, right_col = st.columns([55, 45], gap="large")

    with left_col:
        st.subheader("Document")
        document_viewer(source_path, height=620)

    with right_col:
        st.subheader("Review Details")

        # Metadata chips
        meta_row = st.columns([2, 2, 2])
        with meta_row[0]:
            _reason_chip(item["review_reason"])
        with meta_row[1]:
            st.markdown(
                f'<span style="background:#dbeafe;color:#1d4ed8;border-radius:4px;'
                f'font-size:12px;font-weight:600;padding:3px 10px;">'
                f'{doc_type.replace("_"," ").title()}</span>',
                unsafe_allow_html=True,
            )
        with meta_row[2]:
            confidence_badge(conf_score, label="Extraction confidence")

        _sla_chip(item["sla_due_at"])
        st.markdown(f"**Document ID:** `{document_id}`")
        st.markdown("---")

        # ── Load Silver fields + schema metadata ───────────────────────────────
        fields, conf_scores = _load_silver_fields(document_id, doc_type)

        if not fields:
            st.warning(
                "Extracted fields not found in Silver layer for this document type. "
                "The document may still be processing."
            )
            fields = {}
            conf_scores = {}

        schema_meta = get_schema_meta(doc_type)

        # Low-conf summary: count fields needing attention
        low_count = sum(1 for v in conf_scores.values() if v < 0.65)
        if low_count:
            st.markdown(
                f'<div style="background:#FCE8E6;border-radius:6px;'
                f'padding:6px 12px;margin-bottom:8px;">'
                f'<span style="color:#A32D2D;font-size:12px;font-weight:600">'
                f'⚠ {low_count} field{"s" if low_count != 1 else ""} need attention '
                f'— check the ⚠ Needs Review tab first</span></div>',
                unsafe_allow_html=True,
            )

        # ── Scrollable field panel ──────────────────────────────────────────────
        with st.form(key=f"review_form_{review_id}"):
            with st.container(height=620, border=False):
                corrected = field_editor(
                    fields=fields,
                    confidence_scores=conf_scores,
                    editable=True,
                    schema_meta=schema_meta,
                )

            st.markdown("---")
            btn_col1, btn_col2, btn_col3 = st.columns(3)

            approve_clicked    = btn_col1.form_submit_button(
                "✓ Approve as-is",
                use_container_width=True,
                type="primary",
            )
            reprocess_clicked  = btn_col2.form_submit_button(
                "💾 Save & reprocess",
                use_container_width=True,
            )
            quarantine_clicked = btn_col3.form_submit_button(
                "🗑 Quarantine",
                use_container_width=True,
            )

        # ── Resolution handlers ────────────────────────────────────────────────
        if approve_clicked:
            with st.spinner("Approving…"):
                _resolve(review_id, document_id, "APPROVED", reviewer=user_email)
            st.toast("Document approved!", icon="✅")
            st.rerun()

        elif reprocess_clicked:
            with st.spinner("Saving corrections and queuing reprocess…"):
                _resolve(
                    review_id,
                    document_id,
                    "REPROCESS",
                    corrected_fields=corrected,
                    reviewer=user_email,
                )
            st.toast("Saved — document queued for reprocessing.", icon="💾")
            st.rerun()

        elif quarantine_clicked:
            with st.spinner("Quarantining…"):
                _resolve(review_id, document_id, "QUARANTINE", reviewer=user_email)
            st.toast("Document quarantined.", icon="🗑")
            st.rerun()
