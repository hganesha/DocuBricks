"""
Ops Task — Daily health check.
Evaluates four key health metrics and writes alert records to Lakebase.
Raises on any threshold breach so Databricks Workflow marks the task FAILED.
Designed to run once per day as a scheduled Databricks Job.
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

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


SECRET_SCOPE           = _conf("secret_scope",             "SECRET_SCOPE",             "docubricks-prod")
QUARANTINE_RATE_MAX    = float(_conf("quarantine_rate_max",  "QUARANTINE_RATE_MAX",      "0.15"))
MIN_AVG_CONFIDENCE     = float(_conf("min_avg_confidence",   "MIN_AVG_CONFIDENCE",       "0.70"))
STALE_THRESHOLD_MIN    = int(_conf("stale_threshold_minutes", "STALE_THRESHOLD_MINUTES", "60"))

# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

def get_connection():
    try:
        conn_string = dbutils.secrets.get(SECRET_SCOPE, "lakebase-conn-string")  # noqa: F821
    except Exception:
        conn_string = os.environ.get("LAKEBASE_CONN", "")

    if not conn_string:
        raise RuntimeError("LAKEBASE_CONN is not set.")

    import psycopg2
    conn = psycopg2.connect(conn_string)
    conn.autocommit = False
    return conn


# ---------------------------------------------------------------------------
# Alert data class
# ---------------------------------------------------------------------------

@dataclass
class HealthAlert:
    alert_type:   str
    metric_value: float | None
    threshold:    float | None
    details:      dict
    document_type: str | None = None
    tenant_id:    str | None  = None

    def is_breach(self) -> bool:
        return True  # Constructed only when breach is detected


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

def check_quarantine_rate(cursor) -> HealthAlert | None:
    """
    Alert if quarantine rate (QUARANTINE / total processed) in last 24h > 15%.
    """
    cursor.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'QUARANTINE') AS quarantine_count,
            COUNT(*) AS total_count
        FROM document_registry
        WHERE received_at >= NOW() - INTERVAL '24 hours'
    """
    )
    row = cursor.fetchone()
    quarantine_count, total_count = row[0], row[1]

    if total_count == 0:
        print("  [OK ] Quarantine rate: no documents processed in last 24h.")
        return None

    rate = quarantine_count / total_count
    print(
        f"  Quarantine rate: {rate:.2%} "
        f"({quarantine_count}/{total_count}) — threshold {QUARANTINE_RATE_MAX:.0%}"
    )

    if rate > QUARANTINE_RATE_MAX:
        print(f"  [ALERT] Quarantine rate {rate:.2%} exceeds {QUARANTINE_RATE_MAX:.0%}!")
        return HealthAlert(
            alert_type="QUARANTINE_RATE_HIGH",
            metric_value=round(rate, 4),
            threshold=QUARANTINE_RATE_MAX,
            details={
                "quarantine_count": quarantine_count,
                "total_count":      total_count,
                "window_hours":     24,
            },
        )

    print(f"  [OK ] Quarantine rate {rate:.2%} is within threshold.")
    return None


def check_avg_confidence(cursor) -> HealthAlert | None:
    """
    Alert if average extraction_conf in last 24h < 0.70.
    """
    cursor.execute(
        """
        SELECT
            AVG(extraction_conf) AS avg_conf,
            COUNT(*) AS sample_size
        FROM document_registry
        WHERE received_at >= NOW() - INTERVAL '24 hours'
          AND status IN ('EXTRACTED','VALIDATED','COMPLETE')
          AND extraction_conf IS NOT NULL
    """
    )
    row = cursor.fetchone()
    avg_conf, sample_size = row[0], row[1]

    if sample_size == 0 or avg_conf is None:
        print("  [OK ] Confidence check: no extracted documents in last 24h.")
        return None

    avg_conf = float(avg_conf)
    print(
        f"  Avg extraction confidence: {avg_conf:.4f} "
        f"(n={sample_size}) — threshold {MIN_AVG_CONFIDENCE}"
    )

    if avg_conf < MIN_AVG_CONFIDENCE:
        print(f"  [ALERT] Avg confidence {avg_conf:.4f} below {MIN_AVG_CONFIDENCE}!")
        return HealthAlert(
            alert_type="CONFIDENCE_DRIFT",
            metric_value=round(avg_conf, 4),
            threshold=MIN_AVG_CONFIDENCE,
            details={
                "sample_size":  sample_size,
                "window_hours": 24,
            },
        )

    print(f"  [OK ] Avg confidence {avg_conf:.4f} is above threshold.")
    return None


def check_review_sla(cursor) -> list[HealthAlert]:
    """
    Alert for each item in review_queue that is past its sla_due_at.
    Groups by tenant for concise alerting.
    """
    cursor.execute(
        """
        SELECT
            tenant_id,
            COUNT(*) AS breach_count,
            MIN(sla_due_at) AS earliest_breach
        FROM review_queue
        WHERE resolved_at IS NULL
          AND sla_due_at IS NOT NULL
          AND sla_due_at < NOW()
        GROUP BY tenant_id
        ORDER BY breach_count DESC
    """
    )
    rows = cursor.fetchall()

    if not rows:
        print("  [OK ] Review SLA: no breaches detected.")
        return []

    alerts = []
    for tenant_id, breach_count, earliest_breach in rows:
        print(
            f"  [ALERT] SLA breach: tenant={tenant_id} "
            f"breaches={breach_count} earliest={earliest_breach}"
        )
        alerts.append(
            HealthAlert(
                alert_type="REVIEW_SLA_BREACH",
                metric_value=float(breach_count),
                threshold=0,
                details={
                    "breach_count":    breach_count,
                    "earliest_breach": str(earliest_breach),
                },
                tenant_id=tenant_id,
            )
        )
    return alerts


def check_stale_docs(cursor) -> HealthAlert | None:
    """
    Alert if any document is stuck in processing > STALE_THRESHOLD_MIN minutes.
    """
    stale_statuses = ["PARSING", "CLASSIFYING", "EXTRACTING"]
    cursor.execute(
        """
        SELECT COUNT(*) AS stale_count
        FROM document_registry
        WHERE status = ANY(%s)
          AND received_at < NOW() - INTERVAL '1 minute' * %s
        """,
        (stale_statuses, STALE_THRESHOLD_MIN),
    )
    stale_count = cursor.fetchone()[0]

    print(
        f"  Stale documents (>{STALE_THRESHOLD_MIN}min in intermediate state): {stale_count}"
    )

    if stale_count > 0:
        print(f"  [ALERT] {stale_count} document(s) stale beyond {STALE_THRESHOLD_MIN} minutes!")
        return HealthAlert(
            alert_type="PIPELINE_STALE",
            metric_value=float(stale_count),
            threshold=0,
            details={
                "stale_statuses":      stale_statuses,
                "threshold_minutes":   STALE_THRESHOLD_MIN,
            },
        )

    print(f"  [OK ] No stale documents.")
    return None


# ---------------------------------------------------------------------------
# Alert persistence
# ---------------------------------------------------------------------------

def write_alerts(cursor, alerts: list[HealthAlert]) -> int:
    """Insert alert rows into monitoring_alerts. Returns count written."""
    if not alerts:
        return 0

    import json

    written = 0
    for alert in alerts:
        cursor.execute(
            """
            INSERT INTO monitoring_alerts
                (alert_type, document_type, tenant_id, metric_value, threshold, details, created_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
            """,
            (
                alert.alert_type,
                alert.document_type,
                alert.tenant_id,
                alert.metric_value,
                alert.threshold,
                json.dumps(alert.details),
            ),
        )
        written += 1

    return written


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    run_ts = datetime.now(timezone.utc).isoformat()
    print("=" * 60)
    print("Ops Task — Daily Health Check")
    print(f"  Run time               : {run_ts}")
    print(f"  Quarantine rate max    : {QUARANTINE_RATE_MAX:.0%}")
    print(f"  Min avg confidence     : {MIN_AVG_CONFIDENCE}")
    print(f"  Stale threshold (min)  : {STALE_THRESHOLD_MIN}")
    print(f"  Secret scope           : {SECRET_SCOPE}")
    print("=" * 60)

    conn   = get_connection()
    cursor = conn.cursor()
    alerts: list[HealthAlert] = []

    # 1. Quarantine rate
    print("\n[1/4] Quarantine rate (last 24h)...")
    a = check_quarantine_rate(cursor)
    if a:
        alerts.append(a)

    # 2. Average confidence
    print("\n[2/4] Average extraction confidence (last 24h)...")
    a = check_avg_confidence(cursor)
    if a:
        alerts.append(a)

    # 3. Review queue SLA
    print("\n[3/4] Review queue SLA breaches...")
    sla_alerts = check_review_sla(cursor)
    alerts.extend(sla_alerts)

    # 4. Stale docs
    print(f"\n[4/4] Stale documents (>{STALE_THRESHOLD_MIN} min)...")
    a = check_stale_docs(cursor)
    if a:
        alerts.append(a)

    # Write alerts to Lakebase
    print(f"\nWriting {len(alerts)} alert(s) to monitoring_alerts...")
    n_written = write_alerts(cursor, alerts)
    conn.commit()
    cursor.close()
    conn.close()
    print(f"  [OK] {n_written} alert(s) written.")

    # Summary
    print("\n" + "=" * 60)
    print("HEALTH SUMMARY")
    if not alerts:
        print("  All checks PASSED. Platform is healthy.")
    else:
        print(f"  {len(alerts)} alert(s) detected:")
        for alert in alerts:
            scope = f"tenant={alert.tenant_id}" if alert.tenant_id else "platform-wide"
            print(f"    [{alert.alert_type}] {scope} value={alert.metric_value} threshold={alert.threshold}")
    print("=" * 60)

    if alerts:
        raise RuntimeError(
            f"Daily health check detected {len(alerts)} alert(s). "
            "Review monitoring_alerts table for details."
        )

    print("Daily health check complete — all clear.")


main()
