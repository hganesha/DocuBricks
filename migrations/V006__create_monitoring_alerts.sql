CREATE TABLE IF NOT EXISTS monitoring_alerts (
    alert_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type   TEXT,
    tenant_id       TEXT,
    alert_type      TEXT        NOT NULL,
    drift_score     NUMERIC(6,4),
    metric_value    NUMERIC(10,4),
    threshold       NUMERIC(10,4),
    details         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by TEXT,
    CONSTRAINT valid_alert_type CHECK (alert_type IN (
        'CONFIDENCE_DRIFT','QUARANTINE_RATE_HIGH','REVIEW_SLA_BREACH',
        'PIPELINE_STALE','AGENT_FAILURE','SCHEMA_TEST_FAILED'
    ))
);

CREATE INDEX IF NOT EXISTS idx_alerts_unacked
    ON monitoring_alerts (alert_type, created_at DESC)
    WHERE acknowledged_at IS NULL;
