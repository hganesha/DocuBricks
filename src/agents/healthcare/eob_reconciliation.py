"""
src/agents/healthcare/eob_reconciliation.py
---------------------------------------------
Daily agent: reconciles EOB/CMS-1500 extractions against corresponding
prior authorizations and flags amount discrepancies for billing team review.
Runs after each healthcare EOB batch.

Tables read  : docubricks_prod.silver.extracted_eob_cms1500
               docubricks_prod.silver.extracted_prior_auth
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
log = logging.getLogger("eob_reconciliation")

AGENT_NAME = "eob_reconciliation"
VERTICAL = "healthcare"

# Variance thresholds
VARIANCE_DOLLARS_MIN = 1.00      # flag if absolute variance > $1
VARIANCE_PERCENT_MIN = 0.01      # flag if relative variance > 1 %
PRIORITY_HIGH = 1                # variance > $100
PRIORITY_NORMAL = 2              # variance $1–$100 or unmatched claim


def get_spark() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def get_lakebase_conn(spark: SparkSession):
    """Return a psycopg2 connection using the secret stored in the secret scope."""
    secret_scope = spark.conf.get("secret_scope", "docubricks-prod")
    conn_str = dbutils.secrets.get(scope=secret_scope, key="LAKEBASE_CONN")  # noqa: F821
    return psycopg2.connect(conn_str)


# ---------------------------------------------------------------------------
# Step 1 — Query Silver EOB records extracted in the last 24 hours
# ---------------------------------------------------------------------------

EOB_QUERY = """
SELECT
    document_id,
    tenant_id,
    patient_member_id,
    procedure_codes,
    billed_amount,
    extracted_at
FROM docubricks_prod.silver.extracted_eob_cms1500
WHERE extracted_at > current_timestamp() - INTERVAL 24 HOURS
"""


def fetch_recent_eobs(spark: SparkSession) -> list[dict]:
    log.info("Querying Silver for EOB records extracted in the last 24 h…")
    df = spark.sql(EOB_QUERY)
    rows = [row.asDict() for row in df.collect()]
    log.info("Found %d EOB record(s) to reconcile.", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Step 2 — Look up prior auth for each EOB (last 90 days, code overlap)
# ---------------------------------------------------------------------------

PRIOR_AUTH_QUERY = """
SELECT
    document_id        AS auth_document_id,
    patient_member_id,
    procedure_codes    AS auth_procedure_codes,
    approved_units,
    allowed_unit_rate,
    extracted_at       AS auth_extracted_at
FROM docubricks_prod.silver.extracted_prior_auth
WHERE
    patient_member_id = '{member_id}'
    AND extracted_at  > current_timestamp() - INTERVAL 90 DAYS
ORDER BY extracted_at DESC
"""


def find_matching_auth(spark: SparkSession, member_id: str, eob_codes: list[str]) -> dict | None:
    """
    Return the most recent prior auth whose procedure_codes overlap with
    eob_codes, or None if no match is found.

    procedure_codes is stored as an array<string> column; we compare in Python
    after collecting the small candidate set filtered by member_id.
    """
    query = PRIOR_AUTH_QUERY.format(member_id=member_id.replace("'", "''"))
    df = spark.sql(query)
    candidates = [row.asDict() for row in df.collect()]

    eob_code_set = set(eob_codes or [])
    for candidate in candidates:
        auth_codes = candidate.get("auth_procedure_codes") or []
        # auth_procedure_codes may be a Python list (array column) or a
        # comma-separated string depending on how the extractor serialised it.
        if isinstance(auth_codes, str):
            auth_codes = [c.strip() for c in auth_codes.split(",") if c.strip()]
        if eob_code_set & set(auth_codes):
            return candidate

    return None


# ---------------------------------------------------------------------------
# Step 3 — Variance computation
# ---------------------------------------------------------------------------

def compute_variance(billed_amount: float, approved_units: float, allowed_unit_rate: float) -> float:
    """Return billed_amount minus (approved_units * allowed_unit_rate)."""
    authorised_amount = approved_units * allowed_unit_rate
    return billed_amount - authorised_amount


def variance_priority(variance: float) -> int:
    return PRIORITY_HIGH if abs(variance) > 100.00 else PRIORITY_NORMAL


# ---------------------------------------------------------------------------
# Step 4 — Lakebase writes
# ---------------------------------------------------------------------------

REVIEW_QUEUE_INSERT = """
INSERT INTO review_queue
    (document_id, tenant_id, reason, priority, sla_hours, status, created_at)
VALUES
    (%(document_id)s, %(tenant_id)s, %(reason)s, %(priority)s,
     %(sla_hours)s, 'PENDING', NOW())
ON CONFLICT (document_id)
DO UPDATE SET
    priority   = EXCLUDED.priority,
    reason     = EXCLUDED.reason,
    sla_hours  = EXCLUDED.sla_hours,
    updated_at = NOW()
"""


def write_review_queue(conn, document_id: str, tenant_id: str, reason: str, priority: int) -> None:
    sla_hours = 4 if priority == PRIORITY_HIGH else 24
    with conn.cursor() as cur:
        cur.execute(
            REVIEW_QUEUE_INSERT,
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "reason": reason,
                "priority": priority,
                "sla_hours": sla_hours,
            },
        )
    conn.commit()
    log.info(
        "review_queue upserted: document_id=%s reason=%s priority=%d",
        document_id,
        reason,
        priority,
    )


# ---------------------------------------------------------------------------
# Step 5 — Write run summary to gold.agent_activity
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

    # ------------------------------------------------------------------
    # Guard: check that extracted_prior_auth exists before proceeding.
    # Healthcare vertical may not be deployed in all environments.
    # ------------------------------------------------------------------
    try:
        spark.sql(
            "SELECT 1 FROM docubricks_prod.silver.extracted_prior_auth LIMIT 0"
        )
    except AnalysisException:
        log.warning(
            "healthcare prior_auth vertical not yet deployed — "
            "table docubricks_prod.silver.extracted_prior_auth does not exist. "
            "Skipping EOB reconciliation run."
        )
        write_agent_activity(
            spark,
            tenant_id="ALL",
            items_scanned=0,
            items_actioned=0,
            status="SKIPPED",
        )
        return 0

    # ------------------------------------------------------------------
    # Step 1: Fetch EOBs from the last 24 hours.
    # ------------------------------------------------------------------
    try:
        eobs = fetch_recent_eobs(spark)
    except Exception:
        log.error("Failed to query Silver EOB table:\n%s", traceback.format_exc())
        return 1

    if not eobs:
        log.info("No EOB records found in the last 24 h. Exiting cleanly.")
        write_agent_activity(
            spark,
            tenant_id="ALL",
            items_scanned=0,
            items_actioned=0,
            status="SUCCESS",
        )
        return 0

    # ------------------------------------------------------------------
    # Open Lakebase connection once for the entire run.
    # ------------------------------------------------------------------
    try:
        conn = get_lakebase_conn(spark)
    except Exception:
        log.error("Cannot connect to Lakebase:\n%s", traceback.format_exc())
        return 1

    items_actioned = 0
    tenant_counts: dict[str, dict] = {}

    try:
        for eob in eobs:
            document_id = eob["document_id"]
            tenant_id = str(eob["tenant_id"])
            member_id = str(eob.get("patient_member_id") or "")
            billed_amount = float(eob.get("billed_amount") or 0.0)

            # procedure_codes may be an array column or serialised string
            raw_codes = eob.get("procedure_codes") or []
            if isinstance(raw_codes, str):
                eob_codes = [c.strip() for c in raw_codes.split(",") if c.strip()]
            else:
                eob_codes = list(raw_codes)

            if tenant_id not in tenant_counts:
                tenant_counts[tenant_id] = {"scanned": 0, "actioned": 0}
            tenant_counts[tenant_id]["scanned"] += 1

            # ----------------------------------------------------------
            # Step 2: Look up matching prior auth.
            # ----------------------------------------------------------
            try:
                auth = find_matching_auth(spark, member_id, eob_codes)
            except Exception:
                log.warning(
                    "Prior auth lookup failed for document_id=%s (non-fatal):\n%s",
                    document_id,
                    traceback.format_exc(),
                )
                auth = None

            # ----------------------------------------------------------
            # Step 3a: No matching auth — flag UNMATCHED_CLAIM (priority 2).
            # ----------------------------------------------------------
            if auth is None:
                log.info(
                    "No prior auth match for document_id=%s member_id=%s — "
                    "flagging as UNMATCHED_CLAIM.",
                    document_id,
                    member_id,
                )
                write_review_queue(
                    conn,
                    document_id=document_id,
                    tenant_id=tenant_id,
                    reason="EOB_DISCREPANCY",
                    priority=PRIORITY_NORMAL,
                )
                items_actioned += 1
                tenant_counts[tenant_id]["actioned"] += 1
                continue

            # ----------------------------------------------------------
            # Step 3b: Auth found — compute variance.
            # ----------------------------------------------------------
            approved_units = float(auth.get("approved_units") or 0.0)
            allowed_unit_rate = float(auth.get("allowed_unit_rate") or 0.0)
            variance = compute_variance(billed_amount, approved_units, allowed_unit_rate)
            authorised_amount = approved_units * allowed_unit_rate

            dollar_threshold_exceeded = abs(variance) > VARIANCE_DOLLARS_MIN
            percent_threshold_exceeded = (
                authorised_amount > 0
                and abs(variance) / authorised_amount > VARIANCE_PERCENT_MIN
            )

            if dollar_threshold_exceeded or percent_threshold_exceeded:
                priority = variance_priority(variance)
                log.info(
                    "Amount discrepancy for document_id=%s: "
                    "billed=%.2f authorised=%.2f variance=%.2f priority=%d",
                    document_id,
                    billed_amount,
                    authorised_amount,
                    variance,
                    priority,
                )
                write_review_queue(
                    conn,
                    document_id=document_id,
                    tenant_id=tenant_id,
                    reason="AMOUNT_DISCREPANCY",
                    priority=priority,
                )
                items_actioned += 1
                tenant_counts[tenant_id]["actioned"] += 1
            else:
                log.debug(
                    "EOB within tolerance for document_id=%s variance=%.2f",
                    document_id,
                    variance,
                )

    except Exception:
        log.error("Error during EOB reconciliation loop:\n%s", traceback.format_exc())
        conn.close()
        return 1
    finally:
        conn.close()

    # ------------------------------------------------------------------
    # Step 5: Write per-tenant run summary to gold.agent_activity.
    # ------------------------------------------------------------------
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
        len(eobs),
        items_actioned,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
