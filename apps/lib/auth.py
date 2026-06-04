"""
apps/lib/auth.py
----------------
Authentication and authorisation helpers for DocuBricks Streamlit apps.

Databricks Apps injects the authenticated user's email in the ``X-Forwarded-User``
HTTP header.  No separate auth layer is needed — the Databricks workspace SSO
handles identity.  Tenant resolution and role checks are backed by the Lakebase
``tenant_users`` table.

Role hierarchy (lowest → highest privilege)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  viewer  <  reviewer  <  admin
"""
from __future__ import annotations

import streamlit as st

from .lakebase import lb_query

# Ordered role list used for ≥ comparisons
_ROLE_ORDER = ["viewer", "reviewer", "admin"]


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

def get_current_user() -> dict:
    """
    Return the currently authenticated user as ``{"email": <str>}``.

    Reads the ``X-Forwarded-User`` header injected by the Databricks Apps proxy.
    Calls ``st.stop()`` with an error message if the header is absent (i.e. the
    request did not come through Databricks Apps authentication).
    """
    user_email = st.context.headers.get("X-Forwarded-User", "").strip()
    if not user_email:
        st.error(
            "Could not determine user identity.  "
            "Please access this app through the Databricks Apps portal."
        )
        st.stop()
    return {"email": user_email}


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------

def resolve_tenant(user_email: str) -> str:
    """
    Look up the ``tenant_id`` for *user_email* in the Lakebase ``tenant_users``
    table.

    Calls ``st.stop()`` with an error message if the user is not associated with
    any active tenant.
    """
    rows = lb_query(
        "SELECT tenant_id FROM tenant_users "
        "WHERE user_email = %s AND is_active = TRUE "
        "LIMIT 1",
        (user_email,),
    )
    if not rows:
        st.error(
            f"The account **{user_email}** is not associated with any tenant.  "
            "Contact your administrator to be added."
        )
        st.stop()
    return rows[0]["tenant_id"]


# ---------------------------------------------------------------------------
# Role enforcement
# ---------------------------------------------------------------------------

def require_role(user_email: str, tenant_id: str, min_role: str) -> None:
    """
    Assert that *user_email* has at least *min_role* in *tenant_id*.

    Calls ``st.stop()`` with an error message if the user's role is below the
    required threshold or if no record exists.

    Parameters
    ----------
    user_email:  authenticated user's email
    tenant_id:   the tenant scope to check
    min_role:    minimum required role – one of ``'viewer'``, ``'reviewer'``, ``'admin'``
    """
    rows = lb_query(
        "SELECT role FROM tenant_users "
        "WHERE user_email = %s AND tenant_id = %s AND is_active = TRUE "
        "LIMIT 1",
        (user_email, tenant_id),
    )
    if not rows:
        st.error(
            f"Access denied: **{user_email}** has no active membership in this tenant."
        )
        st.stop()

    actual_role = rows[0]["role"]
    try:
        actual_idx = _ROLE_ORDER.index(actual_role)
        required_idx = _ROLE_ORDER.index(min_role)
    except ValueError:
        st.error(f"Unknown role value encountered: '{actual_role}' / '{min_role}'.")
        st.stop()

    if actual_idx < required_idx:
        st.error(
            f"This page requires the **{min_role}** role or higher.  "
            f"Your current role is **{actual_role}**."
        )
        st.stop()


# ---------------------------------------------------------------------------
# Convenience session helper
# ---------------------------------------------------------------------------

def get_session() -> dict:
    """
    Return a dict with ``{user_email, tenant_id, role}`` for the current
    Streamlit session.

    On the first call the values are resolved from the request header and
    Lakebase, then cached in ``st.session_state`` so subsequent page navigations
    do not repeat the database round-trip.
    """
    if "docubricks_session" not in st.session_state:
        user = get_current_user()
        user_email = user["email"]
        tenant_id = resolve_tenant(user_email)

        # Fetch the user's role while we are at it
        rows = lb_query(
            "SELECT role FROM tenant_users "
            "WHERE user_email = %s AND tenant_id = %s AND is_active = TRUE "
            "LIMIT 1",
            (user_email, tenant_id),
        )
        role = rows[0]["role"] if rows else "viewer"

        st.session_state["docubricks_session"] = {
            "user_email": user_email,
            "tenant_id": tenant_id,
            "role": role,
        }

    return st.session_state["docubricks_session"]
