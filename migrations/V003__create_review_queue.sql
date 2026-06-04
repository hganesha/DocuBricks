CREATE TABLE IF NOT EXISTS review_queue (
    review_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     TEXT        NOT NULL REFERENCES document_registry(document_id),
    tenant_id       TEXT        NOT NULL,
    review_reason   TEXT        NOT NULL,
    priority        INT         NOT NULL DEFAULT 5,
    assigned_to     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sla_due_at      TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    resolution      TEXT,
    corrected_json  JSONB,
    CONSTRAINT valid_reason CHECK (review_reason IN (
        'LOW_CONFIDENCE','CLASSIFICATION_AMBIGUOUS','SCHEMA_VIOLATION',
        'HUMAN_FLAGGED','HIGH_RISK_APPLICATION','KYC_PERIODIC_REFRESH',
        'EOB_DISCREPANCY','CONTRACT_RENEWAL_DUE'
    )),
    CONSTRAINT valid_resolution CHECK (
        resolution IS NULL OR resolution IN (
            'APPROVED','CORRECTED','QUARANTINE','REPROCESS'
        )
    ),
    CONSTRAINT priority_range CHECK (priority BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS idx_review_tenant_priority
    ON review_queue (tenant_id, priority, created_at)
    WHERE resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_review_sla
    ON review_queue (sla_due_at)
    WHERE resolved_at IS NULL;
