"""
Ops Task — Stale document recovery.
Detects documents stuck in intermediate processing states for more than 30 minutes
and requeues them for reprocessing.
Intended to run every 15 minutes as a Databricks Workflow task.
"""

import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _conf(key: str, env_var: str, default: str = "") -> str:
    try:
        val = spark.conf.get(key, default)  # noqa: F821
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(env_var, default)


SECRET_SCOPE       = _conf("secret_scope",         "SECRET_SCOPE",         "docubricks-prod")
STALE_THRESHOLD_MIN = int(_conf("stale_threshold_minutes", "STALE_THRESHOLD_MINUTES", "30"))

STALE_STATUSES = ("PARSING", "CLASSIFYING", "EXTRACTING")

# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

def get_connection():
    try:
        conn_string = dbutils.secrets.get(SECRET_SCOPE, "lakebase-conn-string")  # noqa: F821
    except Exception:
        conn_string = os.environ.get("LAKEBASE_CONN", "")

    if not conn_string:
        raise RuntimeError(
            "LAKEBASE_CONN is not set. "
            f"Provide via dbutils.secrets (scope='{SECRET_SCOPE}', key='lakebase-conn-string') "
            "or LAKEBASE_CONN env var."
        )

    import psycopg2
    conn = psycopg2.connect(conn_string)
    conn.autocommit = False
    return conn


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def find_stale_documents(cursor) -> list[dict]:
    """
    Return all documents stuck in an intermediate status for longer than
    STALE_THRESHOLD_MIN minutes.
    """
    cursor.execute(
        """
        SELECT document_id, tenant_id, vertical, document_type, status, received_at
        FROM document_registry
        WHERE status = ANY(%s)
          AND received_at < NOW() - INTERVAL '1 minute' * %s
        ORDER BY received_at ASC
        """,
        (list(STALE_STATUSES), STALE_THRESHOLD_MIN),
    )
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def mark_failed(cursor, document_id: str) -> None:
    """Update document status to FAILED with a stale-timeout reason."""
    cursor.execute(
        """
        UPDATE document_registry
        SET    status         = 'FAILED',
               failure_reason = 'STALE_PROCESSING_TIMEOUT'
        WHERE  document_id    = %s
          AND  status = ANY(%s)
        """,
        (document_id, list(STALE_STATUSES)),
    )


def enqueue_for_reprocessing(cursor, document_id: str) -> None:
    """
    Insert into reprocessing_queue with reason MANUAL_TRIGGER.
    ON CONFLICT DO NOTHING prevents duplicate pending rows (the UNIQUE constraint
    on (document_id, status) in V004 guards this).
    """
    cursor.execute(
        """
        INSERT INTO reprocessing_queue (document_id, reason, status, queued_at)
        VALUES (%s, 'MANUAL_TRIGGER', 'PENDING', NOW())
        ON CONFLICT DO NOTHING
        """,
        (document_id,),
    )


def recover_stale_documents(conn) -> dict:
    """Main recovery loop. Returns summary dict."""
    cursor = conn.cursor()

    stale_docs = find_stale_documents(cursor)
    total_stale = len(stale_docs)

    if total_stale == 0:
        cursor.close()
        conn.rollback()
        return {"total_stale": 0, "recovered": 0, "errors": []}

    print(f"  Found {total_stale} stale document(s) to recover.")

    recovered = 0
    errors: list[str] = []

    for doc in stale_docs:
        doc_id   = doc["document_id"]
        status   = doc["status"]
        tenant   = doc["tenant_id"]
        received = doc["received_at"]

        try:
            mark_failed(cursor, doc_id)
            enqueue_for_reprocessing(cursor, doc_id)
            recovered += 1
            print(
                f"  [RECOVERED] {doc_id[:16]}... "
                f"tenant={tenant} status_was={status} received_at={received}"
            )
        except Exception as exc:
            errors.append(f"{doc_id}: {exc}")
            print(f"  [ERROR] {doc_id}: {exc}", file=sys.stderr)

    if errors:
        conn.rollback()
    else:
        conn.commit()

    cursor.close()
    return {"total_stale": total_stale, "recovered": recovered, "errors": errors}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    run_ts = datetime.now(timezone.utc).isoformat()
    print("=" * 60)
    print("Ops Task — Stale Document Recovery")
    print(f"  Run time           : {run_ts}")
    print(f"  Stale threshold    : {STALE_THRESHOLD_MIN} minutes")
    print(f"  Stale statuses     : {STALE_STATUSES}")
    print(f"  Secret scope       : {SECRET_SCOPE}")
    print("=" * 60)

    print("\nConnecting to Lakebase...")
    conn = get_connection()
    print("  Connected.")

    print("\nScanning for stale documents...")
    result = recover_stale_documents(conn)
    conn.close()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Stale documents found    : {result['total_stale']}")
    print(f"  Successfully recovered   : {result['recovered']}")
    print(f"  Errors                   : {len(result['errors'])}")
    if result["errors"]:
        for err in result["errors"]:
            print(f"    - {err}")
    print("=" * 60)

    if result["errors"]:
        raise RuntimeError(
            f"Stale doc recovery completed with {len(result['errors'])} error(s). "
            "Check logs above."
        )

    print("Stale document recovery complete.")


main()
