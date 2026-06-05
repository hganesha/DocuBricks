"""
apps/lib/components/vertical_selector.py
------------------------------------------
Vertical and Genie space routing helpers.
"""
from __future__ import annotations

import os
import streamlit as st
from ..lakebase import lb_query

_VERTICAL_LABELS = {
    "fs":            "Financial Services",
    "healthcare":    "Healthcare & Life Sciences",
    "legal":         "Legal & Compliance",
    "manufacturing": "Manufacturing / Supply Chain",
    "insurance":     "Insurance",
    "real_estate":   "Real Estate",
}

_GENIE_ENV_KEYS = {
    "fs":         "GENIE_SPACE_ID_FS",
    "healthcare": "GENIE_SPACE_ID_HC",
    "legal":      "GENIE_SPACE_ID_LEGAL",
}


def vertical_selector(tenant_id: str) -> str:
    """
    Selectbox populated from the tenant's configured vertical(s) in Lakebase.

    Returns the selected vertical code ('fs', 'healthcare', 'legal', …).
    Falls back to 'fs' if the tenant has no vertical configured.
    """
    rows = lb_query(
        "SELECT vertical FROM tenant_registry WHERE tenant_id = %s",
        (tenant_id,),
    )
    if not rows:
        return "fs"

    tenant_vertical = rows[0]["vertical"]
    # For Enterprise tenants with multi-vertical access, expose a selector
    available = [v for v in _VERTICAL_LABELS if v == tenant_vertical]
    if not available:
        available = [tenant_vertical]

    if len(available) == 1:
        return available[0]

    labels = [_VERTICAL_LABELS.get(v, v) for v in available]
    chosen_label = st.selectbox("Vertical", labels, key="vertical_selector")
    idx = labels.index(chosen_label)
    return available[idx]


def genie_space_for(vertical: str) -> str:
    """
    Return the Genie space ID for a vertical from environment secrets.

    Raises ValueError if the space ID is not configured.
    """
    env_key = _GENIE_ENV_KEYS.get(vertical)
    if not env_key:
        raise ValueError(f"No Genie space configured for vertical '{vertical}'")
    space_id = os.environ.get(env_key, "")
    if not space_id:
        raise ValueError(
            f"Environment variable {env_key} is not set. "
            "Run the bootstrap setup_genie.py job first."
        )
    return space_id
