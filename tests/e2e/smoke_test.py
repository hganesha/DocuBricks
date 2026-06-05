"""
tests/e2e/smoke_test.py
------------------------
End-to-end smoke test run as a Databricks Job after bootstrap.

This script exercises the full DocuBricks pipeline:
  1. Upload tests/fixtures/sample_mortgage.pdf to UC Volume via Files API.
  2. Register the document in Lakebase.
  3. Trigger the DLT pipeline via the Jobs API.
  4. Poll Lakebase until status = COMPLETE or FAILED (timeout: 10 min).
  5. Assert status = COMPLETE.
  6. Assert docubricks_prod.silver.extracted_mortgage_application has a row.
  7. Assert avg_confidence >= 0.70.
  8. Ask Genie: "how many documents were processed today?" — assert non-empty.
  9. Print success or raise on failure.

Environment variables required:
    DATABRICKS_HOST        Workspace URL
    DATABRICKS_TOKEN       PAT or SP token
    LAKEBASE_CONN          PostgreSQL DSN for Lakebase
    SQL_WH_HTTP_PATH       Serverless SQL warehouse HTTP path
    PIPELINE_JOB_ID        DLT pipeline job ID
    GENIE_SPACE_ID_FS      Genie space ID for the FS vertical
    CATALOG_NAME           UC catalog (default: docubricks_prod)
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

DATABRICKS_HOST   = os.environ["DATABRICKS_HOST"].rstrip("/")
DATABRICKS_TOKEN  = os.environ["DATABRICKS_TOKEN"]
LAKEBASE_CONN     = os.environ["LAKEBASE_CONN"]
SQL_WH_HTTP_PATH  = os.environ["SQL_WH_HTTP_PATH"]
PIPELINE_JOB_ID   = os.environ["PIPELINE_JOB_ID"]
GENIE_SPACE_ID_FS = os.environ["GENIE_SPACE_ID_FS"]
CATALOG_NAME      = os.environ.get("CATALOG_NAME", "docubricks_prod")

# Test parameters
TENANT_ID          = "smoke-test-tenant"
VERTICAL           = "fs"
DOC_TYPE           = "mortgage_application"
POLL_TIMEOUT_SECS  = 600   # 10 minutes
POLL_INTERVAL_SECS = 10
MIN_CONFIDENCE     = 0.70

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_mortgage.pdf"

# ---------------------------------------------------------------------------
# Imports (installed in the Databricks Job environment)
# ---------------------------------------------------------------------------

import requests
import psycopg2
import psycopg2.extras

try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.sql import StatementState
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}


def _api(method: str, path: str, **kwargs) -> dict[str, Any]:
    """Make a Databricks REST API call and return the parsed JSON response."""
    url = f"{DATABRICKS_HOST}{path}"
    resp = requests.request(method, url, headers=_headers(), timeout=30, **kwargs)
    resp.raise_for_status()
    if resp.content:
        return resp.json()
    return {}


def compute_document_id(file_bytes: bytes) -> str:
    """SHA-256 of raw file bytes, hex-encoded (per wave0.json strategy)."""
    return hashlib.sha256(file_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Step 1: Upload fixture PDF to UC Volume
# ---------------------------------------------------------------------------

def upload_to_volume(file_bytes: bytes, document_id: str) -> str:
    """
    Upload file bytes to the UC Volume using the Files API.

    Target path: /Volumes/{catalog}/{vertical}/documents/{tenant_id}/{vertical}/
    Returns the volume path.
    """
    volume_path = (
        f"/Volumes/{CATALOG_NAME}/raw_landing/documents/"
        f"{TENANT_ID}/{VERTICAL}/{document_id}.pdf"
    )
    print(f"  Uploading to {volume_path} …")
    resp = requests.put(
        f"{DATABRICKS_HOST}/api/2.0/fs/files{volume_path}",
        headers={**_headers(), "Content-Type": "application/octet-stream"},
        data=file_bytes,
        timeout=60,
    )
    resp.raise_for_status()
    print(f"  Upload complete ({len(file_bytes)} bytes).")
    return volume_path


# ---------------------------------------------------------------------------
# Step 2: Register in Lakebase
# ---------------------------------------------------------------------------

def register_in_lakebase(document_id: str, source_path: str) -> None:
    """Insert the document into document_registry with status=RECEIVED."""
    sql = """
        INSERT INTO document_registry
            (document_id, tenant_id, vertical, doc_type, source_path, status)
        VALUES (%s, %s, %s, %s, %s, 'RECEIVED')
        ON CONFLICT (document_id) DO UPDATE
            SET status = 'RECEIVED',
                updated_at = NOW()
    """
    conn = psycopg2.connect(LAKEBASE_CONN)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (document_id, TENANT_ID, VERTICAL, DOC_TYPE, source_path))
        conn.commit()
        print(f"  Registered document_id={document_id[:16]}… in Lakebase.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Step 3: Trigger pipeline via Jobs API
# ---------------------------------------------------------------------------

def trigger_pipeline(document_id: str) -> str:
    """
    Trigger the DLT pipeline job and return the run_id.

    The job is parameterized with document_id and tenant_id so the pipeline
    can process just this document in smoke-test mode.
    """
    print(f"  Triggering pipeline job {PIPELINE_JOB_ID} …")
    body = {
        "job_id": int(PIPELINE_JOB_ID),
        "python_params": [
            f"--document_id={document_id}",
            f"--tenant_id={TENANT_ID}",
        ],
    }
    response = _api("POST", "/api/2.1/jobs/run-now", json=body)
    run_id = str(response["run_id"])
    print(f"  Pipeline run_id={run_id}.")
    return run_id


# ---------------------------------------------------------------------------
# Step 4: Poll Lakebase until status reaches a terminal state
# ---------------------------------------------------------------------------

TERMINAL_STATUSES = {"COMPLETE", "FAILED", "QUARANTINE"}


def poll_lakebase_until_terminal(document_id: str) -> str:
    """
    Poll document_registry every POLL_INTERVAL_SECS seconds until the document
    reaches a terminal status or the timeout is exceeded.

    Returns the final status string.
    Raises TimeoutError if timeout is exceeded.
    """
    deadline = time.monotonic() + POLL_TIMEOUT_SECS
    sql = "SELECT status, avg_confidence FROM document_registry WHERE document_id = %s"
    conn = psycopg2.connect(LAKEBASE_CONN)
    try:
        while time.monotonic() < deadline:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (document_id,))
                row = cur.fetchone()
            if row:
                status = row["status"]
                conf   = row["avg_confidence"]
                elapsed = int(POLL_TIMEOUT_SECS - (deadline - time.monotonic()))
                print(f"  [{elapsed:>3}s] status={status}  avg_confidence={conf}")
                if status in TERMINAL_STATUSES:
                    return status
            time.sleep(POLL_INTERVAL_SECS)
    finally:
        conn.close()

    raise TimeoutError(
        f"Document {document_id[:16]}… did not reach a terminal status "
        f"within {POLL_TIMEOUT_SECS}s."
    )


# ---------------------------------------------------------------------------
# Step 5 + 6 + 7: Assertions against UC Silver table
# ---------------------------------------------------------------------------

def assert_silver_row_exists(document_id: str) -> dict[str, Any]:
    """
    Query the Serverless SQL Warehouse to verify a row exists in the
    silver extracted_mortgage_application table for this document.

    Returns the row as a dict.
    """
    table = f"{CATALOG_NAME}.silver.extracted_mortgage_application"
    sql = f"""
        SELECT document_id, avg_confidence, status
        FROM {table}
        WHERE document_id = '{document_id}'
        LIMIT 1
    """
    print(f"  Querying {table} …")

    if HAS_SDK:
        wc = WorkspaceClient(host=DATABRICKS_HOST, token=DATABRICKS_TOKEN)
        response = wc.statement_execution.execute_statement(
            warehouse_id=_resolve_warehouse_id(),
            statement=sql,
            wait_timeout="120s",
        )
        if response.status.state != StatementState.SUCCEEDED:
            raise AssertionError(
                f"SQL query failed with state {response.status.state}: "
                f"{response.status.error}"
            )
        rows = response.result.data_array
        if not rows:
            raise AssertionError(
                f"No row found in {table} for document_id={document_id[:16]}…"
            )
        columns = [col.name for col in response.manifest.schema.columns]
        row_dict = dict(zip(columns, rows[0]))
    else:
        # Fallback: use the SQL statement API directly
        row_dict = _sql_query_via_api(sql)

    print(f"  Silver row: {row_dict}")
    return row_dict


def _resolve_warehouse_id() -> str:
    """Extract the warehouse ID from SQL_WH_HTTP_PATH."""
    # HTTP path format: /sql/1.0/warehouses/<warehouse_id>
    parts = SQL_WH_HTTP_PATH.strip("/").split("/")
    return parts[-1]


def _sql_query_via_api(sql: str) -> dict[str, Any]:
    """Execute a SQL statement via the Statement Execution REST API."""
    warehouse_id = _resolve_warehouse_id()
    body = {
        "warehouse_id": warehouse_id,
        "statement": sql,
        "wait_timeout": "120s",
    }
    resp = _api("POST", "/api/2.0/sql/statements", json=body)
    state = resp.get("status", {}).get("state")
    if state != "SUCCEEDED":
        error = resp.get("status", {}).get("error", {})
        raise AssertionError(f"SQL query failed [{state}]: {error}")

    columns = [col["name"] for col in resp.get("manifest", {}).get("schema", {}).get("columns", [])]
    rows = resp.get("result", {}).get("data_array", [])
    if not rows:
        raise AssertionError("No rows returned from silver table query.")
    return dict(zip(columns, rows[0]))


# ---------------------------------------------------------------------------
# Step 8: Genie question
# ---------------------------------------------------------------------------

def ask_genie_documents_today() -> str:
    """
    Ask the Genie space: "how many documents were processed today?"
    Returns the text response.
    Raises AssertionError if the response is empty.
    """
    question = "how many documents were processed today?"
    print(f"  Asking Genie: '{question}' …")

    # Start conversation
    body = {"content": question}
    resp = _api(
        "POST",
        f"/api/2.0/genie/spaces/{GENIE_SPACE_ID_FS}/start-conversation",
        json=body,
    )
    conversation_id = resp.get("conversation_id") or resp.get("id")
    message_id = resp.get("message_id") or (resp.get("messages") or [{}])[0].get("id")

    if not conversation_id:
        raise AssertionError(f"Genie did not return a conversation_id. Response: {resp}")

    # Poll for answer
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        msg_resp = _api(
            "GET",
            f"/api/2.0/genie/spaces/{GENIE_SPACE_ID_FS}/conversations/{conversation_id}/messages/{message_id}",
        )
        state = msg_resp.get("status", "")
        if state in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)

    # Extract answer text
    attachments = msg_resp.get("attachments", [])
    answer_text = ""
    for attachment in attachments:
        if attachment.get("type") == "TEXT":
            answer_text = attachment.get("content", "")
            break
    if not answer_text:
        answer_text = msg_resp.get("content", "")

    if not answer_text.strip():
        raise AssertionError(
            f"Genie returned an empty response for question: '{question}'"
        )

    print(f"  Genie answered: {answer_text[:200]!r}")
    return answer_text


# ---------------------------------------------------------------------------
# Main smoke test
# ---------------------------------------------------------------------------

def run_smoke_test() -> None:
    print("\n" + "=" * 60)
    print("DocuBricks E2E Smoke Test")
    print("=" * 60)

    # Validate fixture exists (may be empty placeholder in CI)
    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(
            f"Fixture not found: {FIXTURE_PATH}. "
            "Run: touch tests/fixtures/sample_mortgage.pdf"
        )

    file_bytes = FIXTURE_PATH.read_bytes()
    if not file_bytes:
        # Use a minimal PDF-like payload for the smoke test
        file_bytes = b"%PDF-1.4 smoke-test-placeholder"

    document_id = compute_document_id(file_bytes)
    print(f"\nDocument ID (SHA-256): {document_id}")

    # Step 1: Upload
    print("\n[1/8] Uploading fixture to UC Volume …")
    source_path = upload_to_volume(file_bytes, document_id)

    # Step 2: Register
    print("\n[2/8] Registering in Lakebase …")
    register_in_lakebase(document_id, source_path)

    # Step 3: Trigger pipeline
    print("\n[3/8] Triggering DLT pipeline …")
    run_id = trigger_pipeline(document_id)

    # Step 4: Poll until terminal
    print(f"\n[4/8] Polling Lakebase (timeout={POLL_TIMEOUT_SECS}s) …")
    final_status = poll_lakebase_until_terminal(document_id)

    # Step 5: Assert COMPLETE
    print("\n[5/8] Asserting status = COMPLETE …")
    if final_status != "COMPLETE":
        raise AssertionError(
            f"Expected status=COMPLETE, got status={final_status} "
            f"for document_id={document_id[:16]}…"
        )
    print(f"  status = {final_status} ✓")

    # Step 6: Assert silver row exists
    print("\n[6/8] Asserting silver table row exists …")
    silver_row = assert_silver_row_exists(document_id)
    print(f"  Silver row found for document_id={document_id[:16]}… ✓")

    # Step 7: Assert avg_confidence >= 0.70
    print(f"\n[7/8] Asserting avg_confidence >= {MIN_CONFIDENCE} …")
    avg_conf = silver_row.get("avg_confidence")
    if avg_conf is None:
        # Try from Lakebase as fallback
        conn = psycopg2.connect(LAKEBASE_CONN)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT avg_confidence FROM document_registry WHERE document_id = %s",
                    (document_id,),
                )
                row = cur.fetchone()
                avg_conf = row["avg_confidence"] if row else None
        finally:
            conn.close()

    if avg_conf is None:
        raise AssertionError("avg_confidence is NULL — pipeline may not have set confidence.")

    avg_conf_float = float(avg_conf)
    if avg_conf_float < MIN_CONFIDENCE:
        raise AssertionError(
            f"avg_confidence={avg_conf_float:.4f} is below minimum {MIN_CONFIDENCE}. "
            "Pipeline extraction quality is insufficient."
        )
    print(f"  avg_confidence={avg_conf_float:.4f} >= {MIN_CONFIDENCE} ✓")

    # Step 8: Ask Genie
    print("\n[8/8] Asking Genie a business question …")
    genie_answer = ask_genie_documents_today()
    if not genie_answer.strip():
        raise AssertionError("Genie returned an empty answer.")
    print(f"  Genie answer is non-empty ✓")

    # Final summary
    print("\n" + "=" * 60)
    print("✓ DocuBricks smoke test PASSED")
    print(f"  document_id    : {document_id}")
    print(f"  final_status   : {final_status}")
    print(f"  avg_confidence : {avg_conf_float:.4f}")
    print(f"  pipeline_run_id: {run_id}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        run_smoke_test()
    except Exception as exc:
        print(f"\n✗ DocuBricks smoke test FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
