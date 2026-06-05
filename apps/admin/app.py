"""
apps/admin/app.py
-----------------
DocuBricks Admin & Schema Manager — entry point.

Requires role: admin.
Sidebar navigation:
  - Schema Manager
  - Accuracy Trends
  - Tenant Onboarding
  - Job Monitor
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

from lib.theme import apply_docubricks_theme
from lib.auth import get_session, require_role

st.set_page_config(
    page_title="DocuBricks Admin",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_docubricks_theme()

# ── Authentication ─────────────────────────────────────────────────────────────
session = get_session()
require_role(session["user_email"], session["tenant_id"], "admin")

# ── Sidebar navigation ─────────────────────────────────────────────────────────
PAGES = {
    "Schema Manager":    "schema_prompts",
    "Accuracy Trends":   "accuracy_trends",
    "Tenant Onboarding": "tenant_onboarding",
    "Job Monitor":       "job_monitor",
}

PAGE_ICONS = {
    "Schema Manager":    "📝",
    "Accuracy Trends":   "📈",
    "Tenant Onboarding": "🏢",
    "Job Monitor":       "🔍",
}

with st.sidebar:
    st.image("https://via.placeholder.com/160x40?text=DocuBricks", width=160)
    st.caption("Admin Portal")
    st.markdown("---")

    page_label = st.radio(
        "Navigation",
        options=list(PAGES.keys()),
        format_func=lambda p: f"{PAGE_ICONS[p]}  {p}",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption(f"Signed in as **{session['user_email']}**")
    st.caption(f"Role: `admin`")

# ── Route to page ──────────────────────────────────────────────────────────────
module_name = PAGES[page_label]

if module_name == "schema_prompts":
    from pages.schema_prompts import render
elif module_name == "accuracy_trends":
    from pages.accuracy_trends import render
elif module_name == "tenant_onboarding":
    from pages.tenant_onboarding import render
elif module_name == "job_monitor":
    from pages.job_monitor import render

render(session)
