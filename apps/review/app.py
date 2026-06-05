"""
apps/review/app.py
------------------
DocuBricks Review & Correction UI — entry point.

Requires role: reviewer (minimum).
Sidebar navigation: Queue (default) | History
"""
from __future__ import annotations

import sys
import os

# Ensure lib/ is importable regardless of working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

from lib.theme import apply_docubricks_theme
from lib.auth import get_session, require_role
from lib.lakebase import lb_query

# ── Page config must be first Streamlit call ──────────────────────────────────
st.set_page_config(
    page_title="DocuBricks Review",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_docubricks_theme()

# ── Authentication ─────────────────────────────────────────────────────────────
session = get_session()
require_role(session["user_email"], session["tenant_id"], "reviewer")

tenant_id: str = session["tenant_id"]
user_email: str = session["user_email"]

# ── Queue depth badge (sidebar) ────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _queue_count(tid: str) -> int:
    rows = lb_query(
        "SELECT COUNT(*) AS n FROM review_queue "
        "WHERE tenant_id = %s AND resolved_at IS NULL",
        (tid,),
    )
    return rows[0]["n"] if rows else 0


pending: int = _queue_count(tenant_id)

# ── Sidebar navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/160x40?text=DocuBricks", width=160)
    st.markdown("---")

    badge_html = (
        f'<span style="background:#ef4444;color:#fff;border-radius:9999px;'
        f'font-size:11px;font-weight:700;padding:1px 7px;margin-left:6px;">'
        f'{pending}</span>'
        if pending > 0
        else ""
    )

    page = st.radio(
        "Navigation",
        options=["Queue", "History"],
        format_func=lambda p: p if p != "Queue" else f"Queue {badge_html if pending else ''}",
        label_visibility="collapsed",
    )

    # Render badge inline next to Queue label via HTML injection
    if pending > 0 and page == "Queue":
        st.markdown(
            f'<p style="font-size:12px;color:#6b7280;margin-top:-12px;">'
            f'{pending} item{"s" if pending != 1 else ""} pending</p>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.caption(f"Signed in as **{user_email}**")
    st.caption(f"Tenant: `{tenant_id}`")

# ── Route to page ──────────────────────────────────────────────────────────────
if page == "Queue":
    from pages.queue import render
    render(session)
else:
    from pages.field_editor_page import render
    render(session)
