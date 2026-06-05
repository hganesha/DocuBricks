"""Shared application helpers for the DocuBricks Databricks Apps.

Submodules intentionally own their optional Databricks/runtime dependencies so
tests and lightweight scripts can import ``apps.lib`` without installing every
workspace connector.
"""

__all__ = [
    "auth",
    "components",
    "databricks_api",
    "genie",
    "lakebase",
    "otel",
    "sql_warehouse",
    "theme",
]
