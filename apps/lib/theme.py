"""
apps/lib/theme.py
-----------------
DocuBricks shared Streamlit theme.

Call ``apply_docubricks_theme()`` once at the top of every app entry-point
(``app.py``) before any other Streamlit call.  The function is idempotent —
calling it more than once on the same page run is safe (Streamlit ignores
duplicate ``set_page_config`` calls after the first).

Design system tokens
~~~~~~~~~~~~~~~~~~~~
Primary blue   #0C447C   – sidebar background, primary buttons
Teal accent    #0F6E56   – success states, high-confidence badges
Amber          #B06000   – warnings, medium-confidence badges
Red alert      #A32D2D   – errors, low-confidence badges, quarantine
Surface light  #F0F4F9   – page background tint
Text primary   #1A1A2E   – body copy
"""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Color palette (exported for components that need raw hex values)
# ---------------------------------------------------------------------------

COLORS = {
    "sidebar_bg": "#0C447C",
    "sidebar_fg": "#E6F1FB",
    "primary": "#185FA5",
    "teal": "#0F6E56",
    "teal_light": "#E6F4F0",
    "amber": "#B06000",
    "amber_light": "#FEF7E0",
    "red": "#A32D2D",
    "red_light": "#FCE8E6",
    "gray": "#5F5E5A",
    "gray_light": "#F0F4F9",
    "surface": "#FFFFFF",
    "border": "#D1D9E6",
    "text_primary": "#1A1A2E",
    "text_secondary": "#4A4A6A",
    "monospace_bg": "#F3F4F6",
}

# ---------------------------------------------------------------------------
# Theme entry-point
# ---------------------------------------------------------------------------

def apply_docubricks_theme() -> None:
    """
    Configure the Streamlit page and inject the DocuBricks CSS design system.

    Must be called before any other ``st.*`` call in each app page.
    """
    st.set_page_config(
        page_title="DocuBricks",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        f"""
        <style>
        /* ── Global body ─────────────────────────────────────────────────── */
        .stApp {{
            background-color: {COLORS['gray_light']};
            color: {COLORS['text_primary']};
            font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
        }}

        /* ── Sidebar ─────────────────────────────────────────────────────── */
        [data-testid="stSidebar"] {{
            background-color: {COLORS['sidebar_bg']} !important;
        }}
        [data-testid="stSidebar"] * {{
            color: {COLORS['sidebar_fg']} !important;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            background-color: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.25);
            color: {COLORS['sidebar_fg']} !important;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background-color: rgba(255,255,255,0.22);
        }}
        [data-testid="stSidebar"] hr {{
            border-color: rgba(255,255,255,0.2) !important;
        }}
        [data-testid="stSidebarNav"] a[data-active="true"] span {{
            color: #7EC8F5 !important;
            font-weight: 600;
        }}

        /* ── Metric widgets ──────────────────────────────────────────────── */
        [data-testid="stMetricLabel"] {{
            font-size: 10px !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            color: {COLORS['text_secondary']} !important;
            font-weight: 600 !important;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 1.6rem !important;
            font-weight: 700 !important;
            color: {COLORS['text_primary']} !important;
        }}

        /* ── Document / monospace IDs ────────────────────────────────────── */
        .docubricks-mono {{
            font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
            font-size: 12px;
            background: {COLORS['monospace_bg']};
            border-radius: 4px;
            padding: 2px 6px;
            color: {COLORS['text_primary']};
        }}
        code, .stCodeBlock {{
            font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace !important;
        }}

        /* ── Primary buttons ─────────────────────────────────────────────── */
        .stButton > button[kind="primary"] {{
            background-color: {COLORS['primary']};
            color: #ffffff;
            border: none;
            border-radius: 6px;
            font-weight: 600;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: {COLORS['sidebar_bg']};
        }}

        /* ── Alert / info boxes ──────────────────────────────────────────── */
        [data-testid="stAlert"] {{
            border-radius: 6px;
        }}

        /* ── Data tables ─────────────────────────────────────────────────── */
        [data-testid="stDataFrame"] table {{
            font-size: 13px;
        }}

        /* ── Expander headers ────────────────────────────────────────────── */
        [data-testid="stExpander"] summary {{
            font-weight: 600;
            color: {COLORS['primary']};
        }}

        /* ── Divider ─────────────────────────────────────────────────────── */
        hr {{
            border-color: {COLORS['border']};
        }}

        /* ── Confidence badge utility classes ────────────────────────────── */
        .db-badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }}
        .db-badge-green  {{ background:{COLORS['teal_light']};  color:{COLORS['teal']};  }}
        .db-badge-amber  {{ background:{COLORS['amber_light']}; color:{COLORS['amber']}; }}
        .db-badge-red    {{ background:{COLORS['red_light']};   color:{COLORS['red']};   }}
        .db-badge-gray   {{ background:{COLORS['gray_light']};  color:{COLORS['gray']};  }}

        /* ── Field highlight for low-confidence fields ───────────────────── */
        .db-field-amber {{
            background: {COLORS['amber_light']};
            border-left: 3px solid {COLORS['amber']};
            padding: 4px 8px;
            border-radius: 0 4px 4px 0;
            margin-bottom: 4px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
