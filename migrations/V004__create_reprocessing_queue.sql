CREATE TABLE IF NOT EXISTS reprocessing_queue (
    reprocess_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     TEXT        NOT NULL REFERENCES document_registry(document_id),
    reason          TEXT        NOT NULL,
    target_version  TEXT,
    queued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'PENDING',
    CONSTRAINT valid_reason CHECK (reason IN (
        'SCHEMA_VERSION_CHANGE','MODEL_UPGRADE','MANUAL_TRIGGER',
        'CORRECTION_APPLIED','SCHEMA_VERSION_ROLLBACK'
    )),
    CONSTRAINT valid_reprocess_status CHECK (status IN ('PENDING','PROCESSING','COMPLETE','FAILED')),
    UNIQUE (document_id, status)  -- prevent duplicate pending entries per document
);

CREATE INDEX IF NOT EXISTS idx_reprocess_status_queued
    ON reprocessing_queue (status, queued_at)
    WHERE status = 'PENDING';
