"""
DocuBricks — Legal Contract Expiry Agent
Daily agent (08:00 UTC). Finds NDA/MSA contracts expiring within 90 days and
queues them for renewal review with an LLM-generated briefing.

The legal vertical Silver table (silver_extracted_nda_msa) is added in a later
wave. This agent guards against its absence with a try/except and exits cleanly
if the table does not yet exist.

Tables read  : docubricks_prod.silver.silver_extracted_nda_msa  (guarded)
               Lakebase review_queue (exclusion list)
Tables write : Lakebase review_queue
               docubricks_prod.gold.agent_activity
"""

from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from pyspark.sql import SparkSession
from pyspark.sql.utils import AnalysisException

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("contract_expiry")

AGENT_NAME = "contract_expiry"
VERTICAL = "legal"
RENEWAL_WINDOW_DAYS = 90


def get_spark() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def get_lakebase_conn(spark: SparkSession):
    secret_scope = spark.conf.get("secret_scope", "docubricks-prod")
    conn_str = dbutils.secrets.get(scope=secret_scope, key="LAKEBASE_CONN")  # noqa: F821
    return psycopg2.connect(conn_str)


# ---------------------------------------------------------------------------
# Step 1 — Query Silver for contracts expiring within 90 days
# ---------------------------------------------------------------------------

EXPIRING_CONTRACTS_SQL = """
SELECT
    document_id,
    tenant_id,
    contract_type,
    counterparty_name,
    effective_date,
    expiry_date,
    auto_renewal_clause,
    governing_law,
    extracted_at
FROM docubricks_prod.silver.silver_extracted_nda_msa
WHERE
    expiry_date BETWEEN current_date() AND current_date() + {window}
    AND document_id NOT IN (
        SELECT document_id
        FROM review_queue
        WHERE reason = 'CONTRACT_RENEWAL_DUE'
    )
"""


def fetch_expiring_contracts(spark: SparkSession) -> list[dict] | None:
    """
    Returns list of expiring contract rows, or None if the table doesn't exist.
    Exits cleanly (None) when the legal vertical is not yet deployed.
    """
    sql = EXPIRING_CONTRACTS_SQL.format(window=RENEWAL_WINDOW_DAYS)
    try:
        df = spark.sql(sql)
        rows = [row.asDict() for row in df.collect()]
        log.info(
            "Found %d contract(s) expiring within %d days.",
            len(rows),
            RENEWAL_WINDOW_DAYS,
        )
        return rows
    except AnalysisException as exc:
        if "Table or view not found" in str(exc) or "does not exist" in str(exc).lower():
            log.info(
                "Legal vertical not yet deployed — "
                "silver_extracted_nda_msa does not exist. Exiting cleanly."
            )
            return None
        raise


# ---------------------------------------------------------------------------
# Step 2 — LLM renewal briefing via ai_query()
# ---------------------------------------------------------------------------

def generate_renewal_briefing(spark: SparkSession, contract: dict) -> str:
    """Call Databricks ai_query() for a 2-sentence contract renewal briefing."""
    counterparty = (contract.get("counterparty_name") or "Unknown counterparty").replace("'", "''")
    contract_type = (contract.get("contract_type") or "Agreement").replace("'", "''")
    expiry_date = str(contract.get("expiry_date") or "unknown")
    auto_renewal = contract.get("auto_renewal_clause") or False
    governing_law = (contract.get("governing_law") or "unspecified").replace("'", "''")

    prompt = (
        f"Generate a 2-sentence contract renewal briefing for a {contract_type} "
        f"with {counterparty}, expiring on {expiry_date}. "
        f"Auto-renewal clause: {'yes' if auto_renewal else 'no'}. "
        f"Governing law: {governing_law}. "
        f"Summarise key renewal action items."
    )

    try:
        result_df = spark.sql(
            f"SELECT ai_query('databricks-claude-sonnet', '{prompt}') AS briefing"
        )
        briefing = result_df.collect()[0]["briefing"]
        return briefing or ""
    except Exception as exc:  # noqa: BLE001
        log.warning("ai_query failed (non-fatal): %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Step 3 — Lakebase write: review_queue
# ---------------------------------------------------------------------------

REVIEW_QUEUE_INSERT = """
INSERT INTO review_queue
    (document_id, tenant_id, reason, priority, notes, status, created_at)
VALUES
    (%(document_id)s, %(tenant_id)s, %(reason)s, %(priority)s,
     %(notes)s, 'PENDING', NOW())
ON CONFLICT (document_id)
DO UPDATE SET
    reason     = EXCLUDED.reason,
    priority   = EXCLUDED.priority,
    notes      = EXCLUDED.notes,
    updated_at = NOW()
"""


def _expiry_priority(contract: dict) -> int:
    """Priority 1 if expiring within 30 days, 2 within 60, 3 within 90."""
    expiry_date = contract.get("expiry_date")
    if expiry_date is None:
        return 3
    today = datetime.now(timezone.utc).date()
    if hasattr(expiry_date, "date"):
        expiry_dt = expiry_date.date()
    else:
        expiry_dt = expiry_date
    days_left = (expiry_dt - today).days
    if days_left <= 30:
        return 1
    if days_left <= 60:
        return 2
    return 3


def write_review_queue(conn, contract: dict, briefing: str) -> None:
    priority = _expiry_priority(contract)
    with conn.cursor() as cur:
        cur.execute(
            REVIEW_QUEUE_INSERT,
            {
                "document_id": contract["document_id"],
                "tenant_id": contract["tenant_id"],
                "reason": "CONTRACT_RENEWAL_DUE",
                "priority": priority,
                "notes": briefing[:2000] if briefing else None,  # truncate to column limit
            },
        )
    conn.commit()
    log.info(
        "review_queue updated: document_id=%s priority=%d expiry=%s",
        contract["document_id"],
        priority,
        contract.get("expiry_date"),
    )


# ---------------------------------------------------------------------------
# Step 4 — Write run summary to gold.agent_activity
# ---------------------------------------------------------------------------

AGENT_ACTIVITY_SQL = """
INSERT INTO docubricks_prod.gold.agent_activity
    (agent_name, vertical, tenant_id, items_scanned, items_actioned, run_date, status)
VALUES
    ('{agent_name}', '{vertical}', '{tenant_id}', {items_scanned},
     {items_actioned}, '{run_date}', '{status}')
"""


def write_agent_activity(
    spark: SparkSession,
    *,
    tenant_id: str,
    items_scanned: int,
    items_actioned: int,
    status: str,
) -> None:
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sql = AGENT_ACTIVITY_SQL.format(
        agent_name=AGENT_NAME,
        vertical=VERTICAL,
        tenant_id=tenant_id,
        items_scanned=items_scanned,
        items_actioned=items_actioned,
        run_date=run_date,
        status=status,
    )
    try:
        spark.sql(sql)
        log.info(
            "agent_activity written: tenant=%s scanned=%d actioned=%d status=%s",
            tenant_id,
            items_scanned,
            items_actioned,
            status,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not write agent_activity (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    spark = get_spark()
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log.info("=== %s starting — run_date=%s ===", AGENT_NAME, run_date)

    try:
        contracts = fetch_expiring_contracts(spark)
    except Exception:
        log.error("Failed to query Silver:\n%s", traceback.format_exc())
        write_agent_activity(
            spark,
            tenant_id="ALL",
            items_scanned=0,
            items_actioned=0,
            status="ERROR",
        )
        return 1

    # Legal vertical not yet deployed — clean exit
    if contracts is None:
        write_agent_activity(
            spark,
            tenant_id="ALL",
            items_scanned=0,
            items_actioned=0,
            status="SKIPPED",
        )
        return 0

    if not contracts:
        log.info(
            "No contracts expiring within %d days. Exiting cleanly.",
            RENEWAL_WINDOW_DAYS,
        )
        write_agent_activity(
            spark,
            tenant_id="ALL",
            items_scanned=0,
            items_actioned=0,
            status="SUCCESS",
        )
        return 0

    try:
        conn = get_lakebase_conn(spark)
    except Exception:
        log.error("Cannot connect to Lakebase:\n%s", traceback.format_exc())
        return 1

    items_actioned = 0
    tenant_counts: dict[str, dict] = {}

    try:
        for contract in contracts:
            tenant_id = contract["tenant_id"]

            if tenant_id not in tenant_counts:
                tenant_counts[tenant_id] = {"scanned": 0, "actioned": 0}
            tenant_counts[tenant_id]["scanned"] += 1

            briefing = generate_renewal_briefing(spark, contract)
            write_review_queue(conn, contract, briefing)
            items_actioned += 1
            tenant_counts[tenant_id]["actioned"] += 1
    except Exception:
        log.error("Error processing contracts:\n%s", traceback.format_exc())
        conn.close()
        return 1
    finally:
        conn.close()

    for tenant_id, counts in tenant_counts.items():
        write_agent_activity(
            spark,
            tenant_id=tenant_id,
            items_scanned=counts["scanned"],
            items_actioned=counts["actioned"],
            status="SUCCESS",
        )

    log.info(
        "=== %s complete — scanned=%d actioned=%d ===",
        AGENT_NAME,
        len(contracts),
        items_actioned,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
