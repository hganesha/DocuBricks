CREATE TABLE IF NOT EXISTS document_registry (
    document_id         TEXT        PRIMARY KEY,
    tenant_id           TEXT        NOT NULL,
    vertical            TEXT        NOT NULL,
    source_path         TEXT        NOT NULL,
    file_ext            TEXT        NOT NULL,
    file_size_bytes     BIGINT,
    content_hash        TEXT        NOT NULL,
    received_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ,
    duplicate_count     INT         NOT NULL DEFAULT 0,
    legal_hold          BOOLEAN     NOT NULL DEFAULT FALSE,
    legal_hold_reason   TEXT,
    status              TEXT        NOT NULL DEFAULT 'RECEIVED',
    document_type       TEXT,
    classification_conf NUMERIC(5,4),
    extraction_conf     NUMERIC(5,4),
    failure_reason      TEXT,
    pipeline_run_id     TEXT,
    extracted_at        TIMESTAMPTZ,
    review_resolved_at  TIMESTAMPTZ,
    CONSTRAINT valid_status CHECK (status IN (
        'RECEIVED','PARSING','PARSED','CLASSIFYING','CLASSIFIED',
        'EXTRACTING','EXTRACTED','VALIDATED','QUARANTINE','REVIEW','COMPLETE','FAILED'
    )),
    CONSTRAINT valid_vertical CHECK (vertical IN (
        'fs','healthcare','legal','manufacturing','insurance','real_estate'
    ))
);

CREATE INDEX IF NOT EXISTS idx_registry_tenant_status
    ON document_registry (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_registry_vertical_date
    ON document_registry (vertical, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_registry_pipeline_run
    ON document_registry (pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_registry_doc_type
    ON document_registry (document_type, extracted_at DESC);
