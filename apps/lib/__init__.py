"""
apps/lib — DocuBricks shared application library.

All three Streamlit apps (portal, review, admin) import from this package.
"""
from .lakebase import lakebase_conn, lb_query, lb_exec, lb_exec_returning
from .sql_warehouse import wh_query, wh_query_df
from .auth import get_session, require_role
from .theme import apply_docubricks_theme

__all__ = [
    "lakebase_conn", "lb_query", "lb_exec", "lb_exec_returning",
    "wh_query", "wh_query_df",
    "get_session", "require_role",
    "apply_docubricks_theme",
]
