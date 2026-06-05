"""
DocuBricks — FS Mortgage Risk Monitor Agent
Daily agent (07:00 UTC). Finds high-risk mortgage applications extracted in the
last 24 hours and queues them for underwriter review with an LLM risk briefing.

Tables read  : docubricks_prod.silver.extracted_mortgage_application
Tables write : Lakebase review_queue, extraction_audit
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
log = logging.getLogger("mortgage_risk_monitor")

AGENT_NAME = "mortgage_risk_monitor"
VERTICAL = "fs"
PRIORITY = 2
SLA_HOURS = 4


def get_spark() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def get_lakebase_conn(spark: SparkSession):
    """Return a psycopg2 connection using the secret stored in the secret scope."""
    secret_scope = spark.conf.get("secret_scope", "docubricks-prod")
    conn_str = dbutils.secrets.get(scope=secret_scope, key="LAKEBASE_CONN")  # noqa: F821
    return psycopg2.connect(conn_str)


# ---------------------------------------------------------------------------
# Step 1 — Query Silver for high-risk applications (last 24 h)
# ---------------------------------------------------------------------------

HIGH_RISK_SQL = """
SELECT
    document_id,
    tenant_id,
    borrower_last_name,
    loan_amount,
    debt_to_income_ratio,
    ltv_percent,
    credit_score,
    occupancy_type,
    extracted_at
FROM docubricks_prod.silver.extracted_mortgage_application
WHERE
    extracted_at > current_timestamp() - INTERVAL 24 HOURS
    AND (
        debt_to_income_ratio > 0.43
        OR ltv_percent > 0.95
        OR credit_score < 620
    )
"""


def fetch_high_risk_applications(spark: SparkSession) -> list[dict]:
    log.info("Querying Silver for high-risk mortgage applications (last 24 h)…")
    df = spark.sql(HIGH_RISK_SQL)
    rows = [row.asDict() for row in df.collect()]
    log.info("Found %d high-risk application(s).", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Step 2 — LLM risk briefing via ai_query()
# ---------------------------------------------------------------------------

def generate_risk_briefing(spark: SparkSession, dti: float, ltv: float, score: int) -> str:
    """Call Databricks ai_query() to get a 2-sentence underwriter risk briefing."""
    prompt = (
        f"Generate a 2-sentence underwriter risk briefing for: "
        f"DTI={dti:.1%}, LTV={ltv:.1%}, Score={score}. "
        f"Identify the primary risk factor."
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
# Step 3 — Lakebase writes
# ---------------------------------------------------------------------------

REVIEW_QUEUE_INSERT = """
INSERT INTO review_queue
    (document_id, tenant_id, reason, priority, sla_hours, status, created_at)
VALUES
    (%(document_id)s, %(tenant_id)s, %(reason)s, %(priority)s,
     %(sla_hours)s, 'PENDING', NOW())
ON CONFLICT (document_id)
DO UPDATE SET
    priority = EXCLUDED.priority,
    reason   = EXCLUDED.reason,
    sla_hours = EXCLUDED.sla_hours,
    updated_at = NOW()
"""

EXTRACTION_AUDIT_INSERT = """
INSERT INTO extraction_audit
    (document_id, tenant_id, field_name, field_value, created_at)
VALUES
    (%(document_id)s, %(tenant_id)s, 'risk_briefing', %(field_value)s, NOW())
ON CONFLICT (document_id, field_name)
DO UPDATE SET
    field_value = EXCLUDED.field_value,
    updated_at  = NOW()
"""


def write_to_lakebase(
    conn,
    application: dict,
    briefing: str,
) -> None:
    document_id = application["document_id"]
    tenant_id = application["tenant_id"]

    with conn.cursor() as cur:
        # Insert / upsert review_queue row
        cur.execute(
            REVIEW_QUEUE_INSERT,
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "reason": "HIGH_RISK_APPLICATION",
                "priority": PRIORITY,
                "sla_hours": SLA_HOURS,
            },
        )

        # Persist the LLM briefing in extraction_audit if we got one
        if briefing:
            cur.execute(
                EXTRACTION_AUDIT_INSERT,
                {
                    "document_id": document_id,
                    "tenant_id": tenant_id,
                    "field_value": briefing,
                },
            )

    conn.commit()
    log.info("Lakebase updated for document_id=%s", document_id)


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
        applications = fetch_high_risk_applications(spark)
    except Exception:
        log.error("Failed to query Silver:\n%s", traceback.format_exc())
        return 1

    if not applications:
        log.info("No high-risk applications found in the last 24 h. Exiting cleanly.")
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
    # Group by tenant for agent_activity rows
    tenant_counts: dict[str, dict] = {}

    try:
        for app in applications:
            tenant_id = app["tenant_id"]
            dti = float(app.get("debt_to_income_ratio") or 0.0)
            ltv = float(app.get("ltv_percent") or 0.0)
            score = int(app.get("credit_score") or 0)

            briefing = generate_risk_briefing(spark, dti, ltv, score)
            write_to_lakebase(conn, app, briefing)
            items_actioned += 1

            if tenant_id not in tenant_counts:
                tenant_counts[tenant_id] = {"scanned": 0, "actioned": 0}
            tenant_counts[tenant_id]["scanned"] += 1
            tenant_counts[tenant_id]["actioned"] += 1
    except Exception:
        log.error("Error processing applications:\n%s", traceback.format_exc())
        conn.close()
        return 1
    finally:
        conn.close()

    # Write one agent_activity row per tenant
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
        len(applications),
        items_actioned,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
