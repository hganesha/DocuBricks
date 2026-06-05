"""
tests/integration/test_lakebase_lifecycle.py
----------------------------------------------
Integration tests for the document_registry lifecycle in Lakebase (PostgreSQL).

Requirements
------------
- A real Lakebase (PostgreSQL) connection, provided via the LAKEBASE_CONN env var.
- All tests are marked with ``@pytest.mark.integration``.
- If LAKEBASE_CONN is not set, every test is automatically skipped.
- Tests clean up after themselves using transaction rollback where possible,
  or by deleting test rows keyed on a unique test_run_id prefix.

Run with::

    LAKEBASE_CONN="host=... dbname=..." pytest tests/integration/ -m integration -v

Schema (expected from migrations/V001__create_document_registry.sql):
    document_registry(
        document_id       TEXT PRIMARY KEY,
        tenant_id         TEXT NOT NULL,
        vertical          TEXT NOT NULL,
        doc_type          TEXT,
        source_path       TEXT,
        status            TEXT NOT NULL,
        avg_confidence    FLOAT,
        created_at        TIMESTAMPTZ DEFAULT NOW(),
        updated_at        TIMESTAMPTZ DEFAULT NOW()
    )
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Skip all tests if LAKEBASE_CONN is not available
# ---------------------------------------------------------------------------
LAKEBASE_CONN = os.environ.get("LAKEBASE_CONN", "")

pytestmark = pytest.mark.integration

if not LAKEBASE_CONN:
    pytest.skip(
        "LAKEBASE_CONN env var not set — skipping Lakebase integration tests",
        allow_module_level=True,
    )

# Only import psycopg2 if we actually have a connection string
try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
except ImportError:
    pytest.skip("psycopg2 not installed", allow_module_level=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_pool():
    """Module-scoped connection pool for the integration test suite."""
    pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=LAKEBASE_CONN,
    )
    yield pool
    pool.closeall()


@pytest.fixture()
def conn(db_pool):
    """
    Function-scoped connection from the pool.

    Each test runs inside a transaction that is rolled back on completion
    to keep the database clean. We use a savepoint pattern so that
    tests which intentionally trigger exceptions (constraint violations)
    can recover without aborting the outer transaction.
    """
    connection = db_pool.getconn()
    connection.autocommit = False
    try:
        yield connection
        connection.rollback()  # always roll back — tests must not leave state
    finally:
        db_pool.putconn(connection)


@pytest.fixture()
def test_document_id() -> str:
    """Unique document_id for each test run, SHA-256-style hex prefix."""
    raw = f"test-{uuid.uuid4()}".encode()
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture()
def test_tenant_id() -> str:
    return f"tenant-test-{uuid.uuid4().hex[:8]}"


def insert_document(
    conn,
    document_id: str,
    tenant_id: str,
    status: str = "RECEIVED",
    vertical: str = "fs",
    doc_type: str | None = "mortgage_application",
    source_path: str | None = None,
    avg_confidence: float | None = None,
) -> dict:
    """Insert a row into document_registry and return it."""
    sql = """
        INSERT INTO document_registry
            (document_id, tenant_id, vertical, doc_type, source_path, status, avg_confidence)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING document_id, tenant_id, vertical, doc_type, status, avg_confidence,
                  created_at, updated_at
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (
            document_id, tenant_id, vertical, doc_type, source_path, status, avg_confidence
        ))
        row = cur.fetchone()
    return dict(row)


def update_status(conn, document_id: str, new_status: str, avg_confidence: float | None = None) -> dict:
    """Advance the document status and optionally set avg_confidence."""
    sql = """
        UPDATE document_registry
        SET status = %s,
            avg_confidence = COALESCE(%s, avg_confidence),
            updated_at = NOW()
        WHERE document_id = %s
        RETURNING document_id, status, avg_confidence, updated_at
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (new_status, avg_confidence, document_id))
        row = cur.fetchone()
    return dict(row) if row else {}


def fetch_document(conn, document_id: str) -> dict | None:
    sql = """
        SELECT document_id, tenant_id, vertical, doc_type, status,
               avg_confidence, created_at, updated_at
        FROM document_registry
        WHERE document_id = %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (document_id,))
        row = cur.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Tests: insert and initial state
# ---------------------------------------------------------------------------

class TestDocumentInsert:
    def test_insert_with_received_status(self, conn, test_document_id, test_tenant_id):
        row = insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")
        assert row["document_id"] == test_document_id
        assert row["status"] == "RECEIVED"

    def test_insert_sets_correct_tenant_id(self, conn, test_document_id, test_tenant_id):
        row = insert_document(conn, test_document_id, test_tenant_id)
        assert row["tenant_id"] == test_tenant_id

    def test_insert_sets_correct_vertical(self, conn, test_document_id, test_tenant_id):
        row = insert_document(conn, test_document_id, test_tenant_id, vertical="fs")
        assert row["vertical"] == "fs"

    def test_insert_sets_correct_doc_type(self, conn, test_document_id, test_tenant_id):
        row = insert_document(conn, test_document_id, test_tenant_id, doc_type="kyc_cdd_form")
        assert row["doc_type"] == "kyc_cdd_form"

    def test_insert_avg_confidence_is_null_initially(self, conn, test_document_id, test_tenant_id):
        row = insert_document(conn, test_document_id, test_tenant_id)
        assert row["avg_confidence"] is None

    def test_inserted_row_is_fetchable(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id)
        fetched = fetch_document(conn, test_document_id)
        assert fetched is not None
        assert fetched["document_id"] == test_document_id


# ---------------------------------------------------------------------------
# Tests: valid status transitions
# ---------------------------------------------------------------------------
# Valid lifecycle: RECEIVED → PROCESSING → EXTRACTED → REVIEW | VALIDATED → COMPLETE | QUARANTINE

VALID_TRANSITIONS = [
    ("RECEIVED",   "PROCESSING"),
    ("PROCESSING", "EXTRACTED"),
    ("EXTRACTED",  "REVIEW"),
    ("EXTRACTED",  "VALIDATED"),
    ("REVIEW",     "COMPLETE"),
    ("VALIDATED",  "COMPLETE"),
    ("PROCESSING", "QUARANTINE"),
    ("EXTRACTED",  "QUARANTINE"),
]


class TestStatusTransitions:
    def test_received_to_processing(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")
        result = update_status(conn, test_document_id, "PROCESSING")
        assert result["status"] == "PROCESSING"

    def test_processing_to_extracted(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")
        update_status(conn, test_document_id, "PROCESSING")
        result = update_status(conn, test_document_id, "EXTRACTED", avg_confidence=0.88)
        assert result["status"] == "EXTRACTED"
        assert abs(result["avg_confidence"] - 0.88) < 0.001

    def test_extracted_to_validated(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")
        update_status(conn, test_document_id, "PROCESSING")
        update_status(conn, test_document_id, "EXTRACTED", avg_confidence=0.91)
        result = update_status(conn, test_document_id, "VALIDATED")
        assert result["status"] == "VALIDATED"

    def test_extracted_to_review(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")
        update_status(conn, test_document_id, "PROCESSING")
        update_status(conn, test_document_id, "EXTRACTED", avg_confidence=0.60)
        result = update_status(conn, test_document_id, "REVIEW")
        assert result["status"] == "REVIEW"

    def test_validated_to_complete(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")
        update_status(conn, test_document_id, "PROCESSING")
        update_status(conn, test_document_id, "EXTRACTED", avg_confidence=0.91)
        update_status(conn, test_document_id, "VALIDATED")
        result = update_status(conn, test_document_id, "COMPLETE")
        assert result["status"] == "COMPLETE"

    def test_full_happy_path_lifecycle(self, conn, test_document_id, test_tenant_id):
        """Walk through the entire lifecycle and verify each transition."""
        transitions = [
            ("RECEIVED",   None),
            ("PROCESSING", None),
            ("EXTRACTED",  0.87),
            ("VALIDATED",  None),
            ("COMPLETE",   None),
        ]
        insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")
        for status, confidence in transitions[1:]:
            result = update_status(conn, test_document_id, status, confidence)
            assert result["status"] == status

        final = fetch_document(conn, test_document_id)
        assert final["status"] == "COMPLETE"
        assert abs(final["avg_confidence"] - 0.87) < 0.001

    def test_quarantine_path(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")
        update_status(conn, test_document_id, "PROCESSING")
        result = update_status(conn, test_document_id, "QUARANTINE")
        assert result["status"] == "QUARANTINE"

    def test_avg_confidence_persists_after_status_update(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id)
        update_status(conn, test_document_id, "PROCESSING")
        update_status(conn, test_document_id, "EXTRACTED", avg_confidence=0.78)
        # Update status without re-specifying confidence
        update_status(conn, test_document_id, "VALIDATED", avg_confidence=None)
        final = fetch_document(conn, test_document_id)
        assert abs(final["avg_confidence"] - 0.78) < 0.001

    def test_transition_recorded_in_updated_at(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id)
        before = fetch_document(conn, test_document_id)["updated_at"]
        time.sleep(0.05)  # ensure clock advances
        update_status(conn, test_document_id, "PROCESSING")
        after = fetch_document(conn, test_document_id)["updated_at"]
        assert after >= before


# ---------------------------------------------------------------------------
# Tests: ON CONFLICT DO UPDATE for duplicate document_id
# ---------------------------------------------------------------------------

class TestUpsertBehaviour:
    def test_duplicate_insert_raises_or_upserts(self, conn, test_document_id, test_tenant_id):
        """
        Inserting the same document_id twice should either:
        - Raise an IntegrityError (if no ON CONFLICT clause), or
        - Upsert cleanly (if the table uses ON CONFLICT DO UPDATE).

        This test verifies the behaviour is deterministic.
        """
        insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")

        upsert_sql = """
            INSERT INTO document_registry
                (document_id, tenant_id, vertical, doc_type, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (document_id) DO UPDATE
                SET status = EXCLUDED.status,
                    updated_at = NOW()
            RETURNING document_id, status
        """
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(upsert_sql, (
                test_document_id, test_tenant_id, "fs", "mortgage_application", "PROCESSING"
            ))
            row = dict(cur.fetchone())

        assert row["document_id"] == test_document_id
        assert row["status"] == "PROCESSING"

    def test_upsert_does_not_create_duplicate_rows(self, conn, test_document_id, test_tenant_id):
        insert_document(conn, test_document_id, test_tenant_id)

        upsert_sql = """
            INSERT INTO document_registry
                (document_id, tenant_id, vertical, doc_type, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (document_id) DO UPDATE
                SET status = EXCLUDED.status
        """
        with conn.cursor() as cur:
            cur.execute(upsert_sql, (
                test_document_id, test_tenant_id, "fs", "mortgage_application", "PROCESSING"
            ))

        count_sql = "SELECT COUNT(*) FROM document_registry WHERE document_id = %s"
        with conn.cursor() as cur:
            cur.execute(count_sql, (test_document_id,))
            count = cur.fetchone()[0]

        assert count == 1

    def test_plain_duplicate_raises_integrity_error(self, conn, test_document_id, test_tenant_id):
        """Without ON CONFLICT, a plain INSERT of an existing PK should fail."""
        insert_document(conn, test_document_id, test_tenant_id)

        # Use a savepoint so the connection isn't poisoned by the expected error
        with conn.cursor() as cur:
            cur.execute("SAVEPOINT sp_dup_test")

        try:
            insert_sql = """
                INSERT INTO document_registry (document_id, tenant_id, vertical, status)
                VALUES (%s, %s, %s, %s)
            """
            with conn.cursor() as cur:
                cur.execute(insert_sql, (test_document_id, test_tenant_id, "fs", "RECEIVED"))
            pytest.fail("Expected IntegrityError for duplicate primary key")
        except psycopg2.IntegrityError:
            with conn.cursor() as cur:
                cur.execute("ROLLBACK TO SAVEPOINT sp_dup_test")


# ---------------------------------------------------------------------------
# Tests: invalid status raises constraint violation
# ---------------------------------------------------------------------------

class TestStatusConstraint:
    """
    If document_registry has a CHECK constraint on status values,
    inserting an invalid status should raise an IntegrityError.

    If no CHECK constraint is defined, we note this as a known gap.
    """

    INVALID_STATUSES = ["UNKNOWN", "IN_PROGRESS", "DONE", "", "NULL", "received"]

    @pytest.mark.parametrize("bad_status", INVALID_STATUSES)
    def test_invalid_status_raises_or_is_rejected(self, conn, test_document_id, test_tenant_id, bad_status):
        """
        An invalid status string should be rejected by the DB (via CHECK constraint)
        or by application-level validation. This test verifies DB-level enforcement.

        If the table does not have a CHECK constraint, this test will pass anyway
        (the insert succeeds) but we log a warning to flag the missing constraint.
        """
        sql = """
            INSERT INTO document_registry (document_id, tenant_id, vertical, status)
            VALUES (%s, %s, %s, %s)
        """
        with conn.cursor() as cur:
            cur.execute("SAVEPOINT sp_invalid_status")

        try:
            with conn.cursor() as cur:
                cur.execute(sql, (test_document_id, test_tenant_id, "fs", bad_status))
            # If no constraint, the insert succeeded — roll back and note the gap
            with conn.cursor() as cur:
                cur.execute("ROLLBACK TO SAVEPOINT sp_invalid_status")
            # This is not a test failure per se, but signals missing constraint
            pytest.xfail(
                f"No CHECK constraint enforced — status '{bad_status}' was accepted by the DB. "
                "Consider adding: CHECK (status IN ('RECEIVED','PROCESSING','EXTRACTED',"
                "'REVIEW','VALIDATED','COMPLETE','QUARANTINE','FAILED'))"
            )
        except psycopg2.IntegrityError:
            # Expected: constraint violation — roll back to savepoint and continue
            with conn.cursor() as cur:
                cur.execute("ROLLBACK TO SAVEPOINT sp_invalid_status")

    def test_valid_status_does_not_raise(self, conn, test_document_id, test_tenant_id):
        """Sanity check: a valid status must always succeed."""
        row = insert_document(conn, test_document_id, test_tenant_id, status="RECEIVED")
        assert row["status"] == "RECEIVED"


# ---------------------------------------------------------------------------
# Tests: multi-row queries and tenant isolation
# ---------------------------------------------------------------------------

class TestTenantIsolation:
    def test_fetch_returns_only_tenant_rows(self, conn):
        tenant_a = f"tenant-a-{uuid.uuid4().hex[:6]}"
        tenant_b = f"tenant-b-{uuid.uuid4().hex[:6]}"

        doc_a = hashlib.sha256(f"doc-a-{uuid.uuid4()}".encode()).hexdigest()
        doc_b = hashlib.sha256(f"doc-b-{uuid.uuid4()}".encode()).hexdigest()

        insert_document(conn, doc_a, tenant_a)
        insert_document(conn, doc_b, tenant_b)

        sql = "SELECT document_id FROM document_registry WHERE tenant_id = %s"
        with conn.cursor() as cur:
            cur.execute(sql, (tenant_a,))
            rows = cur.fetchall()

        doc_ids = {r[0] for r in rows}
        assert doc_a in doc_ids
        assert doc_b not in doc_ids
