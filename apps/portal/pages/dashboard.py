"""
apps/portal/pages/dashboard.py
--------------------------------
Analytics Dashboard page.

Reads from Gold views via SQL Warehouse (wh_query / wh_query_df):
  - docubricks_prod.gold.fs_mortgage_portfolio
  - docubricks_prod.gold.extraction_metrics_daily

Features
~~~~~~~~
- Date range filter (default: last 30 days)
- Top metrics row: total documents processed, avg confidence, review rate,
  processing time trend (as delta on avg processing seconds)
- Line chart: documents processed per day by document_type
- Bar chart: avg extraction confidence by document_type
- Bar chart: review queue depth by day
- All queries filtered by tenant_id
- Uses only st.metric, st.line_chart, st.bar_chart (no external chart libs)
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from lib.auth import get_session
from lib.sql_warehouse import wh_query, wh_query_df

# ---------------------------------------------------------------------------
# SQL queries
# ---------------------------------------------------------------------------

_METRICS_DAILY_SQL = """
SELECT
    metric_date,
    document_type,
    docs_processed,
    avg_confidence,
    review_count,
    avg_processing_seconds
FROM docubricks_prod.gold.extraction_metrics_daily
WHERE tenant_id = %s
  AND metric_date >= %s
  AND metric_date <= %s
ORDER BY metric_date ASC
"""

_MORTGAGE_PORTFOLIO_SQL = """
SELECT
    application_date,
    loan_amount,
    ltv_ratio,
    extraction_conf
FROM docubricks_prod.gold.fs_mortgage_portfolio
WHERE tenant_id = %s
  AND application_date >= %s
  AND application_date <= %s
ORDER BY application_date ASC
"""

_SUMMARY_SQL = """
SELECT
    COUNT(*)                             AS total_docs,
    AVG(avg_confidence)                  AS overall_avg_conf,
    SUM(review_count)                    AS total_review,
    SUM(docs_processed)                  AS total_processed,
    AVG(avg_processing_seconds)          AS avg_proc_seconds
FROM docubricks_prod.gold.extraction_metrics_daily
WHERE tenant_id = %s
  AND metric_date >= %s
  AND metric_date <= %s
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1%}"


def _num(value, fmt=",") -> str:
    if value is None:
        return "—"
    try:
        return f"{int(value):{fmt}}"
    except Exception:
        return str(value)


def _sec_fmt(value: float | None) -> str:
    if value is None:
        return "—"
    if value < 60:
        return f"{value:.1f}s"
    return f"{value/60:.1f}m"


# ---------------------------------------------------------------------------
# Page render
# ---------------------------------------------------------------------------

def render(session: dict) -> None:
    tenant_id = session["tenant_id"]

    st.title("Analytics Dashboard")
    st.caption("All metrics are scoped to your tenant and filtered by the selected date range.")

    # ── Date range filter ──────────────────────────────────────────────────
    col_from, col_to, col_apply = st.columns([2, 2, 1])
    today = date.today()
    default_start = today - timedelta(days=30)

    with col_from:
        date_from = st.date_input("From", value=default_start, max_value=today, key="dash_from")
    with col_to:
        date_to = st.date_input("To", value=today, max_value=today, key="dash_to")
    with col_apply:
        st.markdown("<br>", unsafe_allow_html=True)  # vertical align
        refresh = st.button("Refresh", type="primary", key="dash_refresh")

    if date_from > date_to:
        st.error("'From' date must be on or before 'To' date.")
        return

    date_from_str = date_from.isoformat()
    date_to_str = date_to.isoformat()

    # ── Load summary metrics ───────────────────────────────────────────────
    @st.cache_data(ttl=120, show_spinner=False)
    def _load_summary(tid: str, d_from: str, d_to: str) -> dict:
        rows = wh_query(_SUMMARY_SQL, (tid, d_from, d_to))
        return rows[0] if rows else {}

    @st.cache_data(ttl=120, show_spinner=False)
    def _load_metrics_df(tid: str, d_from: str, d_to: str) -> pd.DataFrame:
        return wh_query_df(_METRICS_DAILY_SQL, (tid, d_from, d_to))

    @st.cache_data(ttl=120, show_spinner=False)
    def _load_mortgage_df(tid: str, d_from: str, d_to: str) -> pd.DataFrame:
        return wh_query_df(_MORTGAGE_PORTFOLIO_SQL, (tid, d_from, d_to))

    with st.spinner("Loading dashboard data…"):
        try:
            summary = _load_summary(tenant_id, date_from_str, date_to_str)
            metrics_df = _load_metrics_df(tenant_id, date_from_str, date_to_str)
            mortgage_df = _load_mortgage_df(tenant_id, date_from_str, date_to_str)
        except Exception as exc:
            st.error(f"Failed to load dashboard data: {exc}")
            return

    # ── Top metrics row ────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Key Metrics")

    total_processed = summary.get("total_processed")
    overall_avg_conf = summary.get("overall_avg_conf")
    total_review = summary.get("total_review")
    avg_proc_seconds = summary.get("avg_proc_seconds")

    # Review rate = review_count / processed (guard division by zero)
    review_rate: float | None = None
    if total_processed and total_review is not None:
        try:
            review_rate = float(total_review) / float(total_processed)
        except ZeroDivisionError:
            review_rate = None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        label="Documents Processed",
        value=_num(total_processed),
        help=f"Total documents processed between {date_from_str} and {date_to_str}.",
    )
    col2.metric(
        label="Avg Extraction Confidence",
        value=_pct(float(overall_avg_conf) if overall_avg_conf is not None else None),
        help="Average extraction confidence score across all document types.",
    )
    col3.metric(
        label="Review Rate",
        value=_pct(review_rate),
        help="Fraction of processed documents flagged for human review.",
    )
    col4.metric(
        label="Avg Processing Time",
        value=_sec_fmt(float(avg_proc_seconds) if avg_proc_seconds is not None else None),
        help="Average end-to-end processing time from upload to terminal state.",
    )

    if metrics_df.empty:
        st.info("No data available for the selected date range. Try expanding the date window.")
        return

    # ── Line chart: documents processed per day by doc type ───────────────
    st.divider()
    st.markdown("### Documents Processed Per Day")

    # Pivot: index = metric_date, columns = document_type, values = docs_processed
    if "metric_date" in metrics_df.columns and "document_type" in metrics_df.columns:
        pivot_docs = (
            metrics_df
            .groupby(["metric_date", "document_type"])["docs_processed"]
            .sum()
            .unstack(fill_value=0)
        )
        pivot_docs.index = pd.to_datetime(pivot_docs.index)
        pivot_docs.sort_index(inplace=True)
        st.line_chart(pivot_docs, use_container_width=True)
    else:
        st.info("Daily document volume data not available.")

    # ── Bar chart: avg confidence by document type ─────────────────────────
    st.divider()
    st.markdown("### Avg Extraction Confidence by Document Type")

    if "document_type" in metrics_df.columns and "avg_confidence" in metrics_df.columns:
        conf_by_type = (
            metrics_df
            .groupby("document_type")["avg_confidence"]
            .mean()
            .reset_index()
            .rename(columns={"document_type": "Document Type", "avg_confidence": "Avg Confidence"})
            .set_index("Document Type")
        )
        conf_by_type["Avg Confidence"] = conf_by_type["Avg Confidence"].round(4)
        st.bar_chart(conf_by_type, use_container_width=True)
    else:
        st.info("Confidence by document type data not available.")

    # ── Bar chart: review queue depth by day ───────────────────────────────
    st.divider()
    st.markdown("### Review Queue Depth by Day")

    if "metric_date" in metrics_df.columns and "review_count" in metrics_df.columns:
        review_by_day = (
            metrics_df
            .groupby("metric_date")["review_count"]
            .sum()
            .reset_index()
            .rename(columns={"metric_date": "Date", "review_count": "Review Queue Depth"})
            .set_index("Date")
        )
        review_by_day.index = pd.to_datetime(review_by_day.index)
        review_by_day.sort_index(inplace=True)
        st.bar_chart(review_by_day, use_container_width=True)
    else:
        st.info("Review queue depth data not available.")

    # ── Mortgage portfolio section (only when data is present) ─────────────
    if not mortgage_df.empty:
        st.divider()
        st.markdown("### Mortgage Portfolio Overview")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if "loan_amount" in mortgage_df.columns:
                total_loan = mortgage_df["loan_amount"].sum()
                st.metric("Total Loan Volume", f"${total_loan:,.0f}")
        with col_m2:
            if "ltv_ratio" in mortgage_df.columns:
                avg_ltv = mortgage_df["ltv_ratio"].mean()
                st.metric("Avg LTV Ratio", f"{avg_ltv:.1%}" if pd.notna(avg_ltv) else "—")

        if "application_date" in mortgage_df.columns and "loan_amount" in mortgage_df.columns:
            loan_trend = (
                mortgage_df
                .groupby("application_date")["loan_amount"]
                .sum()
                .reset_index()
                .rename(columns={"application_date": "Date", "loan_amount": "Loan Volume ($)"})
                .set_index("Date")
            )
            loan_trend.index = pd.to_datetime(loan_trend.index)
            loan_trend.sort_index(inplace=True)
            st.markdown("**Loan Volume by Application Date**")
            st.line_chart(loan_trend, use_container_width=True)

    st.divider()
    st.caption(
        f"Data refreshed on each page load. Tenant: `{tenant_id}` · "
        f"Period: {date_from_str} to {date_to_str}"
    )
