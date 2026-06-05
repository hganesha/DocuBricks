"""
apps/admin/pages/job_monitor.py
---------------------------------
Pipeline job monitor page.

Panels:
  1. Recent jobs table (last 50) with color-coded status.
  2. Summary metrics: success rate, avg docs/run, avg quarantine rate.
  3. Stale documents section (status IN PARSING|CLASSIFYING|EXTRACTING, > 30 min old).
  4. "Requeue stale" button per document.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd

from lib.lakebase import lb_query, lb_exec
from lib.databricks_api import trigger_pipeline

_JOBS_QUERY = """
    SELECT
        job_run_id,
        pipeline_id,
        started_at,
        completed_at,
        status,
        docs_ingested,
        docs_extracted,
        docs_quarantine,
        docs_failed
    FROM processing_jobs
    ORDER BY started_at DESC
    LIMIT 50
"""

_STALE_QUERY = """
    SELECT
        document_id,
        tenant_id,
        status,
        received_at
    FROM document_registry
    WHERE status IN ('PARSING', 'CLASSIFYING', 'EXTRACTING')
      AND received_at < NOW() - INTERVAL '30 minutes'
    ORDER BY received_at ASC
"""

_STATUS_COLORS: dict[str, str] = {
    "COMPLETE":  "#16a34a",
    "FAILED":    "#dc2626",
    "RUNNING":   "#d97706",
    "CANCELLED": "#6b7280",
    "PENDING":   "#3b82f6",
}

_STATUS_BG: dict[str, str] = {
    "COMPLETE":  "#dcfce7",
    "FAILED":    "#fee2e2",
    "RUNNING":   "#fef9c3",
    "CANCELLED": "#f3f4f6",
    "PENDING":   "#dbeafe",
}


def _status_badge(status: str) -> str:
    color = _STATUS_COLORS.get(status, "#374151")
    bg    = _STATUS_BG.get(status, "#f9fafb")
    return (
        f'<span style="background:{bg};color:{color};border-radius:4px;'
        f'font-size:11px;font-weight:700;padding:2px 8px;">{status}</span>'
    )


def _format_dt(dt) -> str:
    if dt is None:
        return "—"
    if hasattr(dt, "strftime"):
        return dt.strftime("%Y-%m-%d %H:%M")
    return str(dt)


def _duration_str(started, completed) -> str:
    if started is None or completed is None:
        return "—"
    try:
        delta = completed - started
        secs  = int(delta.total_seconds())
        if secs < 60:
            return f"{secs}s"
        return f"{secs // 60}m {secs % 60}s"
    except Exception:
        return "—"


def render(session: dict) -> None:
    st.title("Job Monitor")
    st.caption("Pipeline run history and stale document detection.")

    # ── Load jobs ──────────────────────────────────────────────────────────────
    with st.spinner("Loading recent jobs…"):
        try:
            job_rows = lb_query(_JOBS_QUERY)
        except Exception as exc:
            st.error(f"Failed to load processing_jobs: {exc}")
            job_rows = []

    if st.button("🔄 Refresh"):
        st.rerun()

    # ── Summary metrics ────────────────────────────────────────────────────────
    if job_rows:
        terminal_jobs = [r for r in job_rows if r["status"] in ("COMPLETE", "FAILED")]
        success_rate  = (
            sum(1 for r in terminal_jobs if r["status"] == "COMPLETE") / len(terminal_jobs)
            if terminal_jobs else 0.0
        )
        total_ingested = sum(r["docs_ingested"] or 0 for r in job_rows)
        total_quar     = sum(r["docs_quarantine"] or 0 for r in job_rows)
        avg_docs_run   = total_ingested / len(job_rows) if job_rows else 0
        avg_quar_rate  = total_quar / total_ingested if total_ingested else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Runs shown",    len(job_rows))
        m2.metric("Success rate",  f"{success_rate:.1%}")
        m3.metric("Avg docs/run",  f"{avg_docs_run:.1f}")
        m4.metric("Avg quarantine rate", f"{avg_quar_rate:.1%}")
    else:
        st.info("No job runs found.")

    st.markdown("---")

    # ── Jobs table ─────────────────────────────────────────────────────────────
    st.subheader("Recent Runs")

    if job_rows:
        # Filter controls
        fcol1, fcol2 = st.columns([2, 4])
        with fcol1:
            status_filter = st.multiselect(
                "Filter by status",
                options=["COMPLETE", "FAILED", "RUNNING", "PENDING", "CANCELLED"],
                default=[],
                placeholder="All statuses",
            )

        filtered_jobs = job_rows
        if status_filter:
            filtered_jobs = [r for r in job_rows if r["status"] in status_filter]

        # Header
        hcols = st.columns([2, 2, 2, 2, 1, 1, 1, 1, 1.5])
        headers = ["Run ID", "Pipeline", "Started", "Duration", "Ingested", "Extracted", "Quarantined", "Failed", "Status"]
        for col, h in zip(hcols, headers):
            col.markdown(f"**{h}**")
        st.markdown('<hr style="margin:4px 0 8px 0;">', unsafe_allow_html=True)

        for row in filtered_jobs:
            rcols = st.columns([2, 2, 2, 2, 1, 1, 1, 1, 1.5])
            run_id_short = str(row["job_run_id"])[:12] + "…" if len(str(row["job_run_id"])) > 12 else str(row["job_run_id"])
            pip_short    = str(row["pipeline_id"] or "—")[:14]

            rcols[0].markdown(f'<span style="font-size:11px;font-family:monospace">{run_id_short}</span>', unsafe_allow_html=True)
            rcols[1].markdown(f'<span style="font-size:12px">{pip_short}</span>', unsafe_allow_html=True)
            rcols[2].markdown(f'<span style="font-size:12px">{_format_dt(row["started_at"])}</span>', unsafe_allow_html=True)
            rcols[3].markdown(f'<span style="font-size:12px">{_duration_str(row["started_at"], row["completed_at"])}</span>', unsafe_allow_html=True)
            rcols[4].markdown(str(row["docs_ingested"] or 0))
            rcols[5].markdown(str(row["docs_extracted"] or 0))
            rcols[6].markdown(str(row["docs_quarantine"] or 0))
            rcols[7].markdown(str(row["docs_failed"] or 0))
            rcols[8].markdown(_status_badge(row["status"]), unsafe_allow_html=True)

            st.markdown('<hr style="margin:2px 0;border-color:#f3f4f6;">', unsafe_allow_html=True)

    st.markdown("---")

    # ── Stale documents ────────────────────────────────────────────────────────
    st.subheader("Stale Documents (>30 min in processing)")

    with st.spinner("Checking for stale documents…"):
        try:
            stale_rows = lb_query(_STALE_QUERY)
        except Exception as exc:
            st.error(f"Failed to query stale documents: {exc}")
            stale_rows = []

    if not stale_rows:
        st.success("No stale documents detected.")
    else:
        st.warning(f"{len(stale_rows)} stale document{'s' if len(stale_rows) != 1 else ''} detected.")

        shcols = st.columns([3, 2, 2, 2, 2])
        shcols[0].markdown("**Document ID**")
        shcols[1].markdown("**Tenant**")
        shcols[2].markdown("**Status**")
        shcols[3].markdown("**Received At**")
        shcols[4].markdown("**Action**")
        st.markdown('<hr style="margin:4px 0 8px 0;">', unsafe_allow_html=True)

        for stale in stale_rows:
            doc_id    = stale["document_id"]
            tenant_id = stale["tenant_id"]
            status    = stale["status"]
            rcvd_at   = _format_dt(stale["received_at"])

            scols = st.columns([3, 2, 2, 2, 2])
            scols[0].markdown(f'<span style="font-size:11px;font-family:monospace">{doc_id}</span>', unsafe_allow_html=True)
            scols[1].markdown(f'<span style="font-size:12px">{tenant_id}</span>', unsafe_allow_html=True)
            scols[2].markdown(_status_badge(status), unsafe_allow_html=True)
            scols[3].markdown(f'<span style="font-size:12px">{rcvd_at}</span>', unsafe_allow_html=True)

            with scols[4]:
                if st.button("↩ Requeue", key=f"requeue_{doc_id}"):
                    with st.spinner(f"Requeueing {doc_id}…"):
                        try:
                            # Reset status to RECEIVED so ingestion pipeline re-picks it up
                            lb_exec(
                                """
                                UPDATE document_registry
                                   SET status      = 'RECEIVED',
                                       received_at = NOW()
                                 WHERE document_id = %s
                                """,
                                (doc_id,),
                            )
                            run_id = trigger_pipeline(
                                document_id=doc_id,
                                tenant_id=tenant_id,
                            )
                            st.success(f"Requeued — run ID: `{run_id}`")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Requeue failed: {exc}")

            st.markdown('<hr style="margin:2px 0;border-color:#f3f4f6;">', unsafe_allow_html=True)
