CREATE TABLE IF NOT EXISTS processing_jobs (
    job_run_id          TEXT        PRIMARY KEY,
    pipeline_id         TEXT        NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    status              TEXT        NOT NULL DEFAULT 'RUNNING',
    docs_ingested       INT         NOT NULL DEFAULT 0,
    docs_parsed         INT         NOT NULL DEFAULT 0,
    docs_extracted      INT         NOT NULL DEFAULT 0,
    docs_quarantine     INT         NOT NULL DEFAULT 0,
    docs_failed         INT         NOT NULL DEFAULT 0,
    schema_version_used TEXT,
    error_message       TEXT,
    metadata            JSONB,
    CONSTRAINT valid_job_status CHECK (status IN ('RUNNING','COMPLETE','FAILED','CANCELLED'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_pipeline_started
    ON processing_jobs (pipeline_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status
    ON processing_jobs (status, started_at DESC);
