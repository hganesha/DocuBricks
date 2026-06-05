"""
Bootstrap Job 04 — Mosaic AI Vector Search provisioning.
Creates the Vector Search endpoint and Delta Sync Index on silver_parsed.
Triggers the first sync and prints index status.
"""

import os
import sys
import time

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


CATALOG      = _conf("catalog_name",  "CATALOG_NAME",  "docubricks_prod")
SECRET_SCOPE = _conf("secret_scope",  "SECRET_SCOPE",  "docubricks-prod")

ENDPOINT_NAME        = "docubricks-vector-search"
SOURCE_TABLE         = f"{CATALOG}.silver.silver_parsed"
INDEX_NAME           = f"{CATALOG}.silver.silver_parsed_vs_index"
PRIMARY_KEY          = "document_id"
EMBEDDING_SOURCE_COL = "parsed_text"
EMBEDDING_ENDPOINT   = "databricks-bge-large-en"
PIPELINE_TYPE        = "TRIGGERED"

# Columns beyond the embedding source to sync into the index
COLUMNS_TO_SYNC = [
    "document_id",
    "tenant_id",
    "vertical",
    "document_type",
    "ingested_date",
    "page_count",
]

# Polling config for endpoint readiness
ENDPOINT_POLL_INTERVAL_S = 15
ENDPOINT_POLL_TIMEOUT_S  = 600   # 10 minutes

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_endpoint(vsc, endpoint_name: str) -> None:
    """Poll until endpoint is ONLINE or timeout."""
    deadline = time.monotonic() + ENDPOINT_POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        ep = vsc.get_endpoint(endpoint_name)
        state = (
            ep.get("endpoint_status", {}).get("state")
            or ep.get("state")
            or "UNKNOWN"
        )
        print(f"  Endpoint state: {state}")
        if state == "ONLINE":
            return
        if state in ("FAILED", "DELETED"):
            raise RuntimeError(f"Endpoint entered terminal state: {state}")
        time.sleep(ENDPOINT_POLL_INTERVAL_S)
    raise TimeoutError(
        f"Endpoint did not reach ONLINE within {ENDPOINT_POLL_TIMEOUT_S}s."
    )


def _get_index_status(vsc, index_name: str) -> dict:
    try:
        return vsc.get_index(index_name=index_name)
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Bootstrap Job 04 — Vector Search Provisioning")
    print(f"  Catalog          : {CATALOG}")
    print(f"  Endpoint         : {ENDPOINT_NAME}")
    print(f"  Source table     : {SOURCE_TABLE}")
    print(f"  Index            : {INDEX_NAME}")
    print(f"  Embedding model  : {EMBEDDING_ENDPOINT}")
    print("=" * 60)

    from databricks.vector_search.client import VectorSearchClient

    vsc = VectorSearchClient(disable_notice=True)

    # ------------------------------------------------------------------
    # 1. Endpoint
    # ------------------------------------------------------------------
    print(f"\n[1/3] Vector Search endpoint '{ENDPOINT_NAME}'")
    existing_endpoints = []
    try:
        existing_endpoints = vsc.list_endpoints().get("endpoints", [])
    except Exception as exc:
        print(f"  [WARN] Could not list endpoints: {exc}")

    endpoint_exists = any(
        ep.get("name") == ENDPOINT_NAME for ep in existing_endpoints
    )

    if endpoint_exists:
        print(f"  Endpoint already exists — skipping creation.")
    else:
        print(f"  Creating endpoint '{ENDPOINT_NAME}'...")
        vsc.create_endpoint(
            name=ENDPOINT_NAME,
            endpoint_type="STANDARD",
        )
        print(f"  Endpoint creation requested. Waiting for ONLINE state...")
        _wait_for_endpoint(vsc, ENDPOINT_NAME)
        print(f"  [OK] Endpoint is ONLINE.")

    # ------------------------------------------------------------------
    # 2. Delta Sync Index
    # ------------------------------------------------------------------
    print(f"\n[2/3] Delta Sync Index '{INDEX_NAME}'")

    # Check if index already exists
    existing_indexes = []
    try:
        existing_indexes = vsc.list_indexes(ENDPOINT_NAME).get("vector_indexes", [])
    except Exception as exc:
        print(f"  [WARN] Could not list indexes: {exc}")

    index_exists = any(
        idx.get("name") == INDEX_NAME for idx in existing_indexes
    )

    if index_exists:
        print(f"  Index already exists — skipping creation.")
    else:
        print(f"  Creating Delta Sync Index...")
        print(f"    primary_key          : {PRIMARY_KEY}")
        print(f"    embedding_source_col : {EMBEDDING_SOURCE_COL}")
        print(f"    embedding_endpoint   : {EMBEDDING_ENDPOINT}")
        print(f"    pipeline_type        : {PIPELINE_TYPE}")
        print(f"    columns_to_sync      : {COLUMNS_TO_SYNC}")

        vsc.create_delta_sync_index(
            endpoint_name=ENDPOINT_NAME,
            index_name=INDEX_NAME,
            source_table_name=SOURCE_TABLE,
            pipeline_type=PIPELINE_TYPE,
            primary_key=PRIMARY_KEY,
            embedding_source_column=EMBEDDING_SOURCE_COL,
            embedding_model_endpoint_name=EMBEDDING_ENDPOINT,
            columns_to_sync=COLUMNS_TO_SYNC,
        )
        print(f"  [OK] Index created.")

    # ------------------------------------------------------------------
    # 3. Trigger first sync
    # ------------------------------------------------------------------
    print(f"\n[3/3] Triggering index sync...")
    index = vsc.get_index(endpoint_name=ENDPOINT_NAME, index_name=INDEX_NAME)
    try:
        index.sync()
        print(f"  [OK] Sync triggered.")
    except Exception as exc:
        # Non-fatal: may already be syncing or freshly created
        print(f"  [WARN] Sync trigger returned: {exc}")

    # Status
    status = _get_index_status(vsc, INDEX_NAME)
    index_state = (
        status.get("status", {}).get("ready_for_query")
        or status.get("status", {}).get("state")
        or "unknown"
    )
    print(f"  Index status: {index_state}")
    if status.get("error"):
        print(f"  [ERROR] {status['error']}", file=sys.stderr)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Endpoint         : {ENDPOINT_NAME} — {'existed' if endpoint_exists else 'created'}")
    print(f"  Index            : {INDEX_NAME} — {'existed' if index_exists else 'created'}")
    print(f"  Pipeline type    : {PIPELINE_TYPE}")
    print(f"  Embedding model  : {EMBEDDING_ENDPOINT}")
    print(f"  Index state      : {index_state}")
    print("=" * 60)
    print("Bootstrap Job 04 complete.")


main()
