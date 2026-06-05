"""
apps/admin/pages/accuracy_trends.py
-------------------------------------
Extraction accuracy dashboard.

Sources:
  - docubricks_prod.gold.extraction_metrics_daily  (via wh_query)
  - docubricks_prod.gold.extraction_audit           (via wh_query)

Panels:
  1. Date range picker.
  2. Per document_type: avg_confidence trend, review_rate trend, total docs.
  3. Alert section: types where avg_confidence dropped >5% WoW.
  4. Low confidence fields table (confidence < 0.65, last 7 days).
  5. OTel note.
"""
from __future__ import annotations

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import pandas as pd

from lib.sql_warehouse import wh_query, wh_query_df

_METRICS_QUERY = """
    SELECT
        metric_date,
        document_type,
        avg_confidence,
        review_rate,
        total_docs
    FROM docubricks_prod.gold.extraction_metrics_daily
    WHERE metric_date BETWEEN %(start)s AND %(end)s
    ORDER BY metric_date ASC
"""

_WOW_QUERY = """
    SELECT
        document_type,
        AVG(CASE WHEN metric_date >= DATEADD(day, -7,  CURRENT_DATE) THEN avg_confidence END) AS this_week,
        AVG(CASE WHEN metric_date BETWEEN DATEADD(day, -14, CURRENT_DATE)
                                      AND DATEADD(day, -8,  CURRENT_DATE) THEN avg_confidence END) AS last_week
    FROM docubricks_prod.gold.extraction_metrics_daily
    WHERE metric_date >= DATEADD(day, -14, CURRENT_DATE)
    GROUP BY document_type
    HAVING last_week IS NOT NULL AND this_week IS NOT NULL
"""

_LOW_CONF_FIELDS_QUERY = """
    SELECT
        field_name,
        document_type,
        AVG(confidence_score)  AS avg_confidence,
        COUNT(*)               AS occurrence_count
    FROM docubricks_prod.gold.extraction_audit
    WHERE confidence_score < 0.65
      AND extracted_at >= DATEADD(day, -7, CURRENT_DATE)
    GROUP BY field_name, document_type
    ORDER BY avg_confidence ASC, occurrence_count DESC
    LIMIT 50
"""

_CONF_COLOR = {
    "high":   "#16a34a",
    "medium": "#f59e0b",
    "low":    "#ef4444",
}


def _conf_color(val: float) -> str:
    if val >= 0.85:
        return _CONF_COLOR["high"]
    if val >= 0.65:
        return _CONF_COLOR["medium"]
    return _CONF_COLOR["low"]


def render(session: dict) -> None:
    st.title("Accuracy Trends")
    st.caption("Extraction confidence and review rate trends across document types.")

    # ── Date range ─────────────────────────────────────────────────────────────
    col_start, col_end, _ = st.columns([2, 2, 4])
    with col_start:
        start_date = st.date_input(
            "From",
            value=date.today() - timedelta(days=30),
            max_value=date.today(),
        )
    with col_end:
        end_date = st.date_input(
            "To",
            value=date.today(),
            min_value=start_date,
            max_value=date.today(),
        )

    if start_date > end_date:
        st.error("Start date must be before end date.")
        return

    st.markdown("---")

    # ── Load metrics ───────────────────────────────────────────────────────────
    with st.spinner("Loading metrics…"):
        try:
            df = wh_query_df(
                _METRICS_QUERY,
                {"start": str(start_date), "end": str(end_date)},
            )
        except Exception as exc:
            st.error(f"Failed to load extraction_metrics_daily: {exc}")
            return

    if df.empty:
        st.info("No data found for the selected date range.")
        return

    doc_types = sorted(df["document_type"].unique())

    # ── Summary cards ──────────────────────────────────────────────────────────
    st.subheader("Summary")
    summary_cols = st.columns(len(doc_types) if len(doc_types) <= 4 else 4)

    for idx, dt in enumerate(doc_types[:4]):
        sub = df[df["document_type"] == dt]
        avg_conf = sub["avg_confidence"].mean()
        total    = sub["total_docs"].sum()
        col = summary_cols[idx]
        col.metric(
            label=dt.replace("_", " ").title(),
            value=f"{avg_conf:.1%}" if pd.notna(avg_conf) else "—",
            help=f"{int(total):,} docs processed in date range",
        )

    st.markdown("---")

    # ── Per document_type charts ───────────────────────────────────────────────
    st.subheader("Per Document Type")

    doc_type_filter = st.multiselect(
        "Document types to display",
        options=doc_types,
        default=doc_types,
    )

    for dt in doc_type_filter:
        sub = df[df["document_type"] == dt].copy()
        sub["metric_date"] = pd.to_datetime(sub["metric_date"])
        sub = sub.sort_values("metric_date")

        with st.expander(f"**{dt.replace('_', ' ').title()}**", expanded=True):
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Avg confidence", f"{sub['avg_confidence'].mean():.1%}")
            kpi2.metric("Avg review rate", f"{sub['review_rate'].mean():.1%}")
            kpi3.metric("Total docs", f"{int(sub['total_docs'].sum()):,}")

            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.markdown("**Avg Confidence over time**")
                chart_data = sub.set_index("metric_date")[["avg_confidence"]]
                st.line_chart(chart_data, color="#2563eb")

            with chart_col2:
                st.markdown("**Review Rate over time**")
                chart_data = sub.set_index("metric_date")[["review_rate"]]
                st.line_chart(chart_data, color="#7c3aed")

    st.markdown("---")

    # ── WoW alert section ──────────────────────────────────────────────────────
    st.subheader("Week-over-Week Alerts")

    with st.spinner("Checking WoW confidence changes…"):
        try:
            wow_rows = wh_query(_WOW_QUERY)
        except Exception as exc:
            st.warning(f"Could not compute WoW comparison: {exc}")
            wow_rows = []

    alerts = [
        r for r in wow_rows
        if r["this_week"] is not None
        and r["last_week"] is not None
        and (r["last_week"] - r["this_week"]) / max(r["last_week"], 1e-6) > 0.05
    ]

    if not alerts:
        st.success("No document types with >5% WoW confidence drop.")
    else:
        for alert in alerts:
            drop_pct = (alert["last_week"] - alert["this_week"]) / alert["last_week"] * 100
            st.warning(
                f"**{alert['document_type'].replace('_',' ').title()}**: "
                f"avg confidence dropped {drop_pct:.1f}% WoW "
                f"({alert['last_week']:.1%} → {alert['this_week']:.1%})"
            )

    st.markdown("---")

    # ── Low confidence fields ──────────────────────────────────────────────────
    st.subheader("Low-Confidence Fields (last 7 days, < 65%)")

    with st.spinner("Loading field-level audit data…"):
        try:
            lc_rows = wh_query(_LOW_CONF_FIELDS_QUERY)
        except Exception as exc:
            st.warning(f"Could not load extraction_audit: {exc}")
            lc_rows = []

    if not lc_rows:
        st.success("No low-confidence fields found in the last 7 days.")
    else:
        lc_df = pd.DataFrame(lc_rows)
        lc_df["avg_confidence"] = lc_df["avg_confidence"].round(3)
        lc_df = lc_df.rename(columns={
            "field_name":       "Field",
            "document_type":    "Document Type",
            "avg_confidence":   "Avg Confidence",
            "occurrence_count": "Occurrences",
        })
        st.dataframe(
            lc_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Avg Confidence": st.column_config.ProgressColumn(
                    "Avg Confidence",
                    format="%.1%",
                    min_value=0.0,
                    max_value=1.0,
                ),
                "Occurrences": st.column_config.NumberColumn(
                    "Occurrences",
                    format="%d",
                ),
            },
        )

    st.markdown("---")

    # ── OTel note ──────────────────────────────────────────────────────────────
    st.info(
        "Confidence histograms available in your OTel backend at metric "
        "`docubricks.extraction.confidence`"
    )
