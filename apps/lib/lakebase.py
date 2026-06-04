"""
apps/lib/lakebase.py
--------------------
Lakebase (PostgreSQL) connection pool and typed query helpers.

The pool is cached as a Streamlit resource — one pool per app process, shared
across all threads/sessions.  Every public function opens a connection from the
pool, commits on success, rolls back on exception, and returns the connection
to the pool in the `finally` block.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras
import psycopg2.pool
import streamlit as st


# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

@st.cache_resource
def _pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Return the singleton ThreadedConnectionPool (cached per Streamlit process)."""
    dsn = os.environ["LAKEBASE_CONN"]
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=20,
        dsn=dsn,
    )


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

@contextmanager
def lakebase_conn():
    """
    Context manager that yields a psycopg2 connection from the pool.

    On exit:
      - commits if no exception was raised
      - rolls back on any exception (and re-raises)
      - always returns the connection to the pool
    """
    pool = _pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ---------------------------------------------------------------------------
# Typed query helpers
# ---------------------------------------------------------------------------

def lb_query(sql: str, params: tuple = ()) -> list[dict]:
    """
    Execute *sql* with *params* and return all rows as a list of dicts.

    Column names are taken from cursor.description so callers never need to
    maintain positional indexes.
    """
    with lakebase_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            # RealDictRow is not a plain dict — convert so callers get real dicts
            return [dict(row) for row in rows]


def lb_exec(sql: str, params: tuple = ()) -> int:
    """
    Execute a write statement (*sql* with *params*) and return rowcount.

    Suitable for INSERT / UPDATE / DELETE statements that do not return rows.
    """
    with lakebase_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


def lb_exec_returning(sql: str, params: tuple = ()) -> dict | None:
    """
    Execute a write statement that ends with ``RETURNING …`` and return the
    first row as a dict, or ``None`` if no row was returned.
    """
    with lakebase_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row is not None else None
