"""
apps/portal/app.py
------------------
DocuBricks Portal — entry point.

Sets up the theme, authenticates the session, renders the sidebar navigation,
and routes to the correct page module.
"""
from __future__ import annotations

import sys
import os

# ---------------------------------------------------------------------------
# Ensure apps/ is on sys.path so `from lib.X import Y` works everywhere
# ---------------------------------------------------------------------------
_APPS_DIR = os.path.join(os.path.dirname(__file__), "..")
if _APPS_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_APPS_DIR))

import streamlit as st

from lib.theme import apply_docubricks_theme
from lib.auth import get_session
from lib.lakebase import lb_query

# Apply theme FIRST — must precede any other st.* call
apply_docubricks_theme()

# ---------------------------------------------------------------------------
# Session / auth
# ---------------------------------------------------------------------------
session = get_session()
user_email = session["user_email"]
tenant_id = session["tenant_id"]
role = session["role"]

# ---------------------------------------------------------------------------
# Fetch tenant display info for the sidebar footer
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def _get_tenant_info(tid: str) -> dict:
    rows = lb_query(
        "SELECT tenant_name, vertical FROM tenant_registry WHERE tenant_id = %s LIMIT 1",
        (tid,),
    )
    if rows:
        return rows[0]
    return {"tenant_name": tid, "vertical": "—"}


tenant_info = _get_tenant_info(tenant_id)
tenant_name = tenant_info.get("tenant_name", tenant_id)
tenant_vertical = tenant_info.get("vertical", "—")

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
PAGES = {
    "Upload": "Upload Documents",
    "Status": "Document Status",
    "Ask DocuBricks": "Ask DocuBricks (Genie)",
    "Dashboard": "Analytics Dashboard",
}

with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:8px 0 16px;">'
        '<span style="font-size:2rem;">◈</span><br>'
        '<span style="font-size:1.15rem;font-weight:700;letter-spacing:0.04em;">DocuBricks</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    page = st.radio(
        "Navigate",
        list(PAGES.keys()),
        format_func=lambda k: PAGES[k],
        label_visibility="collapsed",
        key="nav_page",
    )

    st.divider()

    # Sidebar footer — tenant info
    st.markdown(
        f"""
        <div style="font-size:11px;opacity:0.75;line-height:1.6;">
            <strong>Tenant</strong><br>{tenant_name}<br>
            <strong>Vertical</strong><br>{tenant_vertical.upper()}<br>
            <strong>User</strong><br>{user_email}<br>
            <strong>Role</strong><br>{role.capitalize()}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------
if page == "Upload":
    from pages.upload import render
    render(session)

elif page == "Status":
    from pages.status import render
    render(session)

elif page == "Ask DocuBricks":
    from pages.genie_chat import render
    render(session)

elif page == "Dashboard":
    from pages.dashboard import render
    render(session)
