"""
DocuBricks — FS AML Pattern Match Agent
Daily agent (runs after the AML SAR extraction batch). Cross-references SAR
subjects extracted today against SAR subjects from the last 90 days to surface
repeat offenders that may warrant enhanced investigation.

Tables read  : docubricks_prod.silver.extracted_aml_sar
Tables write : Lakebase monitoring_alerts, review_queue
               docubricks_prod.gold.agent_activity
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from pyspark.sql import SparkSession

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("aml_pattern")

AGENT_NAME = "aml_pattern"
VERTICAL = "fs"
ALERT_TYPE = "AML_PATTERN_MATCH"


def get_spark() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def get_lakebase_conn(spark: SparkSession):
    secret_scope = spark.conf.get("secret_scope", "docubricks-prod")
    conn_str = dbutils.secrets.get(scope=secret_scope, key="LAKEBASE_CONN")  # noqa: F821
    return psycopg2.connect(conn_str)


# ---------------------------------------------------------------------------
# Step 1 — Fetch today's SARs
# ---------------------------------------------------------------------------

TODAY_SARS_SQL = """
SELECT
    document_id,
    tenant_id,
    subject_name,
    subject_entity_type,
    transaction_amount,
    suspicious_activity_type,
    reporting_institution,
    extracted_at
FROM docubricks_prod.silver.extracted_aml_sar
WHERE DATE(extracted_at) = current_date()
"""


def fetch_todays_sars(spark: SparkSession) -> list[dict]:
    log.info("Querying Silver for today's AML SARs…")
    df = spark.sql(TODAY_SARS_SQL)
    rows = [row.asDict() for row in df.collect()]
    log.info("Found %d SAR(s) extracted today.", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Step 2 — Look for historical name matches (last 90 days, excluding today)
# ---------------------------------------------------------------------------

HISTORICAL_MATCH_SQL = """
SELECT
    document_id,
    tenant_id,
    subject_name,
    suspicious_activity_type,
    reporting_institution,
    extracted_at
FROM docubricks_prod.silver.extracted_aml_sar
WHERE
    DATE(extracted_at) BETWEEN current_date() - 90 AND current_date() - 1
    AND lower(trim(subject_name)) = lower(trim('{subject_name}'))
"""


def find_historical_matches(spark: SparkSession, subject_name: str) -> list[dict]:
    """Simple name match — exact case-insensitive equality after trimming."""
    if not subject_name:
        return []
    # Escape single quotes in the name to prevent SQL injection within the
    # spark.sql() path (Databricks does not support parameterised spark.sql).
    safe_name = subject_name.replace("'", "''")
    sql = HISTORICAL_MATCH_SQL.format(subject_name=safe_name)
    try:
        df = spark.sql(sql)
        return [row.asDict() for row in df.collect()]
    except Exception as exc:  # noqa: BLE001
        log.warning("Historical match query failed for '%s': %s", subject_name, exc)
        return []


# ---------------------------------------------------------------------------
# Step 3 — Lakebase writes: monitoring_alerts + review_queue
# ---------------------------------------------------------------------------

MONITORING_ALERT_INSERT = """
INSERT INTO monitoring_alerts
    (document_id, tenant_id, alert_type, details, severity, status, created_at)
VALUES
    (%(document_id)s, %(tenant_id)s, %(alert_type)s, %(details)s,
     'HIGH', 'OPEN', NOW())
ON CONFLICT (document_id, alert_type)
DO UPDATE SET
    details    = EXCLUDED.details,
    status     = 'OPEN',
    updated_at = NOW()
"""

REVIEW_QUEUE_INSERT = """
INSERT INTO review_queue
    (document_id, tenant_id, reason, priority, status, created_at)
VALUES
    (%(document_id)s, %(tenant_id)s, %(reason)s, %(priority)s, 'PENDING', NOW())
ON CONFLICT (document_id)
DO UPDATE SET
    priority   = EXCLUDED.priority,
    reason     = EXCLUDED.reason,
    updated_at = NOW()
"""


def write_alert_and_queue(conn, sar: dict, matches: list[dict]) -> None:
    document_id = sar["document_id"]
    tenant_id = sar["tenant_id"]

    details = {
        "subject_name": sar.get("subject_name"),
        "today_document_id": document_id,
        "today_activity_type": sar.get("suspicious_activity_type"),
        "today_amount": str(sar.get("transaction_amount") or ""),
        "historical_matches": [
            {
                "document_id": m["document_id"],
                "tenant_id": m["tenant_id"],
                "activity_type": m.get("suspicious_activity_type"),
                "reporting_institution": m.get("reporting_institution"),
                "extracted_at": str(m.get("extracted_at") or ""),
            }
            for m in matches
        ],
    }

    with conn.cursor() as cur:
        cur.execute(
            MONITORING_ALERT_INSERT,
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "alert_type": ALERT_TYPE,
                "details": json.dumps(details),
            },
        )
        cur.execute(
            REVIEW_QUEUE_INSERT,
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "reason": "HUMAN_FLAGGED",
                "priority": 1,  # highest priority — AML pattern match
            },
        )
    conn.commit()
    log.info(
        "Alert + review_queue written: document_id=%s matches=%d",
        document_id,
        len(matches),
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
        todays_sars = fetch_todays_sars(spark)
    except Exception:
        log.error("Failed to query Silver:\n%s", traceback.format_exc())
        return 1

    if not todays_sars:
        log.info("No SARs extracted today. Exiting cleanly.")
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
        for sar in todays_sars:
            tenant_id = sar["tenant_id"]
            subject_name = sar.get("subject_name") or ""

            if tenant_id not in tenant_counts:
                tenant_counts[tenant_id] = {"scanned": 0, "actioned": 0}
            tenant_counts[tenant_id]["scanned"] += 1

            matches = find_historical_matches(spark, subject_name)

            if matches:
                log.info(
                    "Pattern match: '%s' — %d historical SAR(s) found.",
                    subject_name,
                    len(matches),
                )
                write_alert_and_queue(conn, sar, matches)
                items_actioned += 1
                tenant_counts[tenant_id]["actioned"] += 1
            else:
                log.debug("No historical matches for subject '%s'.", subject_name)
    except Exception:
        log.error("Error during pattern matching:\n%s", traceback.format_exc())
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
        len(todays_sars),
        items_actioned,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
