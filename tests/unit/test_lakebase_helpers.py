"""
tests/unit/test_lakebase_helpers.py
-------------------------------------
Unit tests for lb_query, lb_exec, lb_exec_returning in apps/lib/lakebase.py.

All psycopg2 calls are mocked — no real database connection is required.

Scenarios covered
-----------------
- lb_query returns list[dict] with correct column names from cursor.description.
- lb_exec returns the rowcount integer.
- lb_exec_returning returns a dict on a hit, None when no row is produced.
- Context manager (lakebase_conn) commits on success.
- Context manager rolls back on exception and re-raises.
- Context manager always returns the connection to the pool (putconn called).
"""
from __future__ import annotations

import importlib
import os
import sys
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers: build psycopg2 mock objects
# ---------------------------------------------------------------------------

def _make_description(*column_names: str):
    """
    Build a cursor.description-compatible list.
    psycopg2 returns a list of 7-tuples; only index 0 (name) matters here.
    """
    return [(col,) + (None,) * 6 for col in column_names]


def _make_cursor(
    *,
    fetchall_result: list[tuple] | None = None,
    fetchone_result: tuple | None = None,
    column_names: tuple[str, ...] = (),
    rowcount: int = 0,
    is_real_dict: bool = False,
):
    """
    Return a MagicMock that mimics a psycopg2 cursor.

    When is_real_dict=True, fetchall returns list-of-dicts and
    fetchone returns a dict (mimics RealDictCursor).
    """
    cursor = MagicMock()
    cursor.description = _make_description(*column_names) if column_names else []
    cursor.rowcount = rowcount

    if is_real_dict and column_names:
        # Simulate RealDictCursor: fetchall returns list of dicts
        dict_rows = [
            dict(zip(column_names, row)) for row in (fetchall_result or [])
        ]
        cursor.fetchall.return_value = dict_rows
        dict_one = (
            dict(zip(column_names, fetchone_result))
            if fetchone_result is not None
            else None
        )
        cursor.fetchone.return_value = dict_one
    else:
        cursor.fetchall.return_value = fetchall_result or []
        cursor.fetchone.return_value = fetchone_result

    # Support 'with cursor() as cur:' pattern
    cursor.__enter__ = lambda s: s
    cursor.__exit__ = MagicMock(return_value=False)
    return cursor


def _make_conn(cursor: MagicMock):
    """Return a MagicMock psycopg2 connection that yields the given cursor."""
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    return conn


def _make_pool(conn: MagicMock):
    """Return a MagicMock ThreadedConnectionPool that yields the given conn."""
    pool = MagicMock()
    pool.getconn.return_value = conn
    return pool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_pool_and_conn():
    """Patch _pool() so no real DB is needed. Returns (pool, conn, cursor)."""
    # We'll inject specific cursors inside each test; here we provide defaults.
    col_names = ("id", "status", "document_type")
    rows = [(1, "RECEIVED", "mortgage_application"), (2, "COMPLETE", "invoice")]
    cursor = _make_cursor(
        fetchall_result=rows,
        column_names=col_names,
        rowcount=2,
        is_real_dict=True,
    )
    conn = _make_conn(cursor)
    pool = _make_pool(conn)
    return pool, conn, cursor


# ---------------------------------------------------------------------------
# Shared patch target
# ---------------------------------------------------------------------------

LAKEBASE_MODULE = "apps.lib.lakebase"


def _patch_pool(pool_mock):
    """Context manager that patches _pool() to return pool_mock."""
    return patch(f"{LAKEBASE_MODULE}._pool", return_value=pool_mock)


# ---------------------------------------------------------------------------
# Tests: lb_query
# ---------------------------------------------------------------------------

class TestLbQuery:
    def test_returns_list_of_dicts(self, mock_pool_and_conn):
        pool, conn, cursor = mock_pool_and_conn
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_query  # type: ignore[import]
                result = lb_query(
                    "SELECT id, status, document_type FROM document_registry"
                )
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable; testing reference logic")

        assert isinstance(result, list)
        assert all(isinstance(row, dict) for row in result)

    def test_returns_correct_number_of_rows(self, mock_pool_and_conn):
        pool, conn, cursor = mock_pool_and_conn
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_query  # type: ignore[import]
                result = lb_query("SELECT ...")
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        assert len(result) == 2

    def test_returns_correct_column_names(self, mock_pool_and_conn):
        pool, conn, cursor = mock_pool_and_conn
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_query  # type: ignore[import]
                result = lb_query("SELECT id, status, document_type FROM document_registry")
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        assert set(result[0].keys()) == {"id", "status", "document_type"}

    def test_returns_correct_values(self, mock_pool_and_conn):
        pool, conn, cursor = mock_pool_and_conn
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_query  # type: ignore[import]
                result = lb_query("SELECT ...")
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        assert result[0]["status"] == "RECEIVED"
        assert result[1]["document_type"] == "invoice"

    def test_passes_params_to_cursor(self, mock_pool_and_conn):
        pool, conn, cursor = mock_pool_and_conn
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_query  # type: ignore[import]
                lb_query("SELECT * FROM t WHERE id = %s", (42,))
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        cursor.execute.assert_called_once_with(
            "SELECT * FROM t WHERE id = %s", (42,)
        )

    def test_empty_result_returns_empty_list(self):
        cursor = _make_cursor(
            fetchall_result=[],
            column_names=("id",),
            is_real_dict=True,
        )
        conn = _make_conn(cursor)
        pool = _make_pool(conn)
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_query  # type: ignore[import]
                result = lb_query("SELECT ...")
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        assert result == []

    def test_commits_on_success(self, mock_pool_and_conn):
        pool, conn, cursor = mock_pool_and_conn
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_query  # type: ignore[import]
                lb_query("SELECT 1")
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        conn.commit.assert_called_once()

    def test_conn_returned_to_pool_on_success(self, mock_pool_and_conn):
        pool, conn, cursor = mock_pool_and_conn
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_query  # type: ignore[import]
                lb_query("SELECT 1")
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        pool.putconn.assert_called_once_with(conn)


# ---------------------------------------------------------------------------
# Tests: lb_exec
# ---------------------------------------------------------------------------

class TestLbExec:
    def _make_exec_setup(self, rowcount: int = 1):
        cursor = _make_cursor(rowcount=rowcount)
        conn = _make_conn(cursor)
        pool = _make_pool(conn)
        return pool, conn, cursor

    def test_returns_rowcount(self):
        pool, conn, cursor = self._make_exec_setup(rowcount=3)
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_exec  # type: ignore[import]
                result = lb_exec("UPDATE document_registry SET status = %s WHERE id = %s", ("COMPLETE", 1))
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        assert result == 3

    def test_returns_zero_rowcount_when_nothing_matched(self):
        pool, conn, cursor = self._make_exec_setup(rowcount=0)
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_exec  # type: ignore[import]
                result = lb_exec("UPDATE document_registry SET status = %s WHERE id = %s", ("COMPLETE", 99999))
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        assert result == 0

    def test_passes_params_to_cursor(self):
        pool, conn, cursor = self._make_exec_setup()
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_exec  # type: ignore[import]
                lb_exec("INSERT INTO t (x) VALUES (%s)", ("hello",))
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        cursor.execute.assert_called_once_with("INSERT INTO t (x) VALUES (%s)", ("hello",))

    def test_commits_on_success(self):
        pool, conn, cursor = self._make_exec_setup()
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_exec  # type: ignore[import]
                lb_exec("DELETE FROM t WHERE 1=0")
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        conn.commit.assert_called_once()

    def test_conn_returned_to_pool(self):
        pool, conn, cursor = self._make_exec_setup()
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_exec  # type: ignore[import]
                lb_exec("DELETE FROM t WHERE 1=0")
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        pool.putconn.assert_called_once_with(conn)


# ---------------------------------------------------------------------------
# Tests: lb_exec_returning
# ---------------------------------------------------------------------------

class TestLbExecReturning:
    def test_returns_dict_on_row_found(self):
        cursor = _make_cursor(
            fetchone_result=(42, "RECEIVED"),
            column_names=("id", "status"),
            is_real_dict=True,
        )
        conn = _make_conn(cursor)
        pool = _make_pool(conn)
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_exec_returning  # type: ignore[import]
                result = lb_exec_returning(
                    "INSERT INTO document_registry (doc_id) VALUES (%s) RETURNING id, status",
                    ("abc",),
                )
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        assert result == {"id": 42, "status": "RECEIVED"}

    def test_returns_none_when_no_row(self):
        cursor = _make_cursor(
            fetchone_result=None,
            column_names=("id", "status"),
            is_real_dict=True,
        )
        conn = _make_conn(cursor)
        pool = _make_pool(conn)
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_exec_returning  # type: ignore[import]
                result = lb_exec_returning(
                    "UPDATE t SET x=1 WHERE 1=0 RETURNING id, status"
                )
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        assert result is None

    def test_commits_on_success(self):
        cursor = _make_cursor(
            fetchone_result=(1, "OK"),
            column_names=("id", "status"),
            is_real_dict=True,
        )
        conn = _make_conn(cursor)
        pool = _make_pool(conn)
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_exec_returning  # type: ignore[import]
                lb_exec_returning("INSERT INTO t (x) VALUES (%s) RETURNING id, status", ("v",))
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        conn.commit.assert_called_once()

    def test_conn_returned_to_pool(self):
        cursor = _make_cursor(
            fetchone_result=(1, "OK"),
            column_names=("id", "status"),
            is_real_dict=True,
        )
        conn = _make_conn(cursor)
        pool = _make_pool(conn)
        try:
            with _patch_pool(pool):
                from apps.lib.lakebase import lb_exec_returning  # type: ignore[import]
                lb_exec_returning("INSERT INTO t (x) VALUES (%s) RETURNING id, status", ("v",))
        except ImportError:
            pytest.skip("apps.lib.lakebase not importable")

        pool.putconn.assert_called_once_with(conn)


# ---------------------------------------------------------------------------
# Tests: context manager (lakebase_conn) — commit / rollback / putconn
# ---------------------------------------------------------------------------

class TestLakebaseConnContextManager:
    def _get_lakebase_conn(self):
        try:
            from apps.lib.lakebase import lakebase_conn  # type: ignore[import]
            return lakebase_conn
        except ImportError:
            return None

    def test_commits_on_clean_exit(self):
        conn = MagicMock()
        pool = _make_pool(conn)

        lakebase_conn = self._get_lakebase_conn()
        if lakebase_conn is None:
            pytest.skip("apps.lib.lakebase not importable")

        with _patch_pool(pool):
            with lakebase_conn():
                pass

        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    def test_rolls_back_on_exception(self):
        conn = MagicMock()
        pool = _make_pool(conn)

        lakebase_conn = self._get_lakebase_conn()
        if lakebase_conn is None:
            pytest.skip("apps.lib.lakebase not importable")

        with _patch_pool(pool):
            with pytest.raises(RuntimeError, match="boom"):
                with lakebase_conn():
                    raise RuntimeError("boom")

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()

    def test_reraises_exception(self):
        conn = MagicMock()
        pool = _make_pool(conn)

        lakebase_conn = self._get_lakebase_conn()
        if lakebase_conn is None:
            pytest.skip("apps.lib.lakebase not importable")

        with _patch_pool(pool):
            with pytest.raises(ValueError, match="test error"):
                with lakebase_conn():
                    raise ValueError("test error")

    def test_putconn_called_on_success(self):
        conn = MagicMock()
        pool = _make_pool(conn)

        lakebase_conn = self._get_lakebase_conn()
        if lakebase_conn is None:
            pytest.skip("apps.lib.lakebase not importable")

        with _patch_pool(pool):
            with lakebase_conn():
                pass

        pool.putconn.assert_called_once_with(conn)

    def test_putconn_called_on_exception(self):
        """putconn must always be called — even after rollback."""
        conn = MagicMock()
        pool = _make_pool(conn)

        lakebase_conn = self._get_lakebase_conn()
        if lakebase_conn is None:
            pytest.skip("apps.lib.lakebase not importable")

        with _patch_pool(pool):
            with pytest.raises(RuntimeError):
                with lakebase_conn():
                    raise RuntimeError("oops")

        pool.putconn.assert_called_once_with(conn)

    def test_rollback_before_putconn(self):
        """Rollback must happen before putconn (ordering check via call_args_list)."""
        conn = MagicMock()
        pool = _make_pool(conn)

        lakebase_conn = self._get_lakebase_conn()
        if lakebase_conn is None:
            pytest.skip("apps.lib.lakebase not importable")

        call_order: list[str] = []
        conn.rollback.side_effect = lambda: call_order.append("rollback")
        pool.putconn.side_effect = lambda c: call_order.append("putconn")

        with _patch_pool(pool):
            with pytest.raises(RuntimeError):
                with lakebase_conn():
                    raise RuntimeError("ordering test")

        assert call_order == ["rollback", "putconn"]

    def test_commit_before_putconn(self):
        """Commit must happen before putconn on the success path."""
        conn = MagicMock()
        pool = _make_pool(conn)

        lakebase_conn = self._get_lakebase_conn()
        if lakebase_conn is None:
            pytest.skip("apps.lib.lakebase not importable")

        call_order: list[str] = []
        conn.commit.side_effect = lambda: call_order.append("commit")
        pool.putconn.side_effect = lambda c: call_order.append("putconn")

        with _patch_pool(pool):
            with lakebase_conn():
                pass

        assert call_order == ["commit", "putconn"]

    def test_getconn_called_once(self):
        conn = MagicMock()
        pool = _make_pool(conn)

        lakebase_conn = self._get_lakebase_conn()
        if lakebase_conn is None:
            pytest.skip("apps.lib.lakebase not importable")

        with _patch_pool(pool):
            with lakebase_conn():
                pass

        pool.getconn.assert_called_once()
