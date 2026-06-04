"""
apps/lib/sql_warehouse.py
-------------------------
Databricks SQL Warehouse connection and query helpers.

Uses the ``databricks-sql-connector`` package.  The connection object is
cached as a Streamlit resource so the expensive TCP+auth handshake happens at
most once per app process.

Environment variables required
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``DATABRICKS_HOST``      – workspace URL  (e.g. ``https://adb-xxx.azuredatabricks.net``)
``SQL_WH_HTTP_PATH``     – e.g. ``/sql/1.0/warehouses/<id>``
``DATABRICKS_TOKEN``     – PAT or service-principal OAuth token
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st
from databricks import sql as dbsql


# ---------------------------------------------------------------------------
# Cached connection
# ---------------------------------------------------------------------------

@st.cache_resource
def _wh_conn():
    """Return a cached Databricks SQL connection object."""
    host = os.environ["DATABRICKS_HOST"].replace("https://", "").rstrip("/")
    http_path = os.environ["SQL_WH_HTTP_PATH"]
    token = os.environ["DATABRICKS_TOKEN"]
    return dbsql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
        session_configuration={"spark.sql.ansi.enabled": "true"},
    )


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def wh_query(sql_text: str, params: tuple = ()) -> list[dict]:
    """
    Execute *sql_text* against the SQL Warehouse and return all rows as a
    list of dicts.

    Parameters are passed as a positional tuple (``?`` placeholders).
    """
    conn = _wh_conn()
    with conn.cursor() as cur:
        cur.execute(sql_text, params if params else None)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def wh_query_df(sql_text: str, params: tuple = ()) -> pd.DataFrame:
    """
    Execute *sql_text* against the SQL Warehouse and return results as a
    :class:`pandas.DataFrame`.

    Column names are taken from the cursor description; an empty DataFrame
    with correct columns is returned when the query produces no rows.
    """
    conn = _wh_conn()
    with conn.cursor() as cur:
        cur.execute(sql_text, params if params else None)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return pd.DataFrame(rows, columns=columns)
