"""
DocuBricks — FS KYC Periodic Refresh Agent
Weekly agent (Monday 06:00 UTC). Finds KYC/CDD profiles whose next_review_date
falls within the next 30 days and queues them for analyst review.

Tables read  : docubricks_prod.silver.extracted_kyc_cdd_form
               Lakebase reprocessing_queue (exclusion list)
               Lakebase tenant_reviewer_assignments (reviewer assignment)
Tables write : Lakebase review_queue
               docubricks_prod.gold.agent_activity
"""

from __future__ import annotations

import logging
import sys
import traceback
from datetime import date, datetime, timezone

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
log = logging.getLogger("kyc_refresh")

AGENT_NAME = "kyc_refresh"
VERTICAL = "fs"

# Priority thresholds (days until next_review_date)
PRIORITY_URGENT = 1      # <= 7 days
PRIORITY_HIGH = 2        # 8–14 days
PRIORITY_NORMAL = 3      # 15–30 days


def get_spark() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def get_lakebase_conn(spark: SparkSession):
    secret_scope = spark.conf.get("secret_scope", "docubricks-prod")
    conn_str = dbutils.secrets.get(scope=secret_scope, key="LAKEBASE_CONN")  # noqa: F821
    return psycopg2.connect(conn_str)


# ---------------------------------------------------------------------------
# Step 1 — Query Silver for KYC profiles due for review (next 30 days)
# ---------------------------------------------------------------------------

KYC_DUE_SQL = """
SELECT
    document_id,
    tenant_id,
    overall_risk_rating,
    next_review_date
FROM docubricks_prod.silver.extracted_kyc_cdd_form
WHERE
    next_review_date BETWEEN current_date() AND current_date() + 30
    AND document_id NOT IN (
        SELECT document_id
        FROM reprocessing_queue
        WHERE status = 'PENDING'
    )
"""


def fetch_kyc_due(spark: SparkSession) -> list[dict]:
    log.info("Querying Silver for KYC profiles due in the next 30 days…")
    df = spark.sql(KYC_DUE_SQL)
    rows = [row.asDict() for row in df.collect()]
    log.info("Found %d KYC profile(s) due for review.", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Step 2 — Determine priority based on days to review
# ---------------------------------------------------------------------------

def compute_priority(next_review_date) -> int:
    """Return 1/2/3 priority based on how many days until next_review_date."""
    today = date.today()
    if hasattr(next_review_date, "date"):
        review_dt = next_review_date.date()
    else:
        review_dt = next_review_date  # already a date object
    days_remaining = (review_dt - today).days
    if days_remaining <= 7:
        return PRIORITY_URGENT
    if days_remaining <= 14:
        return PRIORITY_HIGH
    return PRIORITY_NORMAL


# ---------------------------------------------------------------------------
# Step 3 — Fetch reviewer for vertical from Lakebase
# ---------------------------------------------------------------------------

REVIEWER_QUERY = """
SELECT reviewer_id
FROM tenant_reviewer_assignments
WHERE tenant_id = %(tenant_id)s
  AND vertical   = 'fs'
ORDER BY assigned_at DESC
LIMIT 1
"""


def fetch_reviewer(cur, tenant_id: str) -> str | None:
    cur.execute(REVIEWER_QUERY, {"tenant_id": tenant_id})
    row = cur.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Step 4 — Lakebase write: review_queue
# ---------------------------------------------------------------------------

REVIEW_QUEUE_INSERT = """
INSERT INTO review_queue
    (document_id, tenant_id, reason, priority, assigned_reviewer_id,
     status, created_at)
VALUES
    (%(document_id)s, %(tenant_id)s, %(reason)s, %(priority)s,
     %(reviewer_id)s, 'PENDING', NOW())
ON CONFLICT (document_id)
DO UPDATE SET
    priority             = EXCLUDED.priority,
    reason               = EXCLUDED.reason,
    assigned_reviewer_id = EXCLUDED.assigned_reviewer_id,
    updated_at           = NOW()
"""


def write_review_queue(conn, profile: dict, priority: int, reviewer_id: str | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            REVIEW_QUEUE_INSERT,
            {
                "document_id": profile["document_id"],
                "tenant_id": profile["tenant_id"],
                "reason": "KYC_PERIODIC_REFRESH",
                "priority": priority,
                "reviewer_id": reviewer_id,
            },
        )
    conn.commit()
    log.info(
        "review_queue updated: document_id=%s priority=%d reviewer=%s",
        profile["document_id"],
        priority,
        reviewer_id,
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

    try:
        profiles = fetch_kyc_due(spark)
    except Exception:
        log.error("Failed to query Silver:\n%s", traceback.format_exc())
        return 1

    if not profiles:
        log.info("No KYC profiles due for review in the next 30 days. Exiting cleanly.")
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
        with conn.cursor() as reviewer_cur:
            for profile in profiles:
                tenant_id = profile["tenant_id"]
                priority = compute_priority(profile.get("next_review_date"))
                reviewer_id = fetch_reviewer(reviewer_cur, tenant_id)

                write_review_queue(conn, profile, priority, reviewer_id)
                items_actioned += 1

                if tenant_id not in tenant_counts:
                    tenant_counts[tenant_id] = {"scanned": 0, "actioned": 0}
                tenant_counts[tenant_id]["scanned"] += 1
                tenant_counts[tenant_id]["actioned"] += 1
    except Exception:
        log.error("Error processing KYC profiles:\n%s", traceback.format_exc())
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
        len(profiles),
        items_actioned,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
