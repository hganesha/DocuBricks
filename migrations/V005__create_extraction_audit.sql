CREATE TABLE IF NOT EXISTS extraction_audit (
    audit_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     TEXT        NOT NULL,
    document_type   TEXT        NOT NULL,
    field_name      TEXT        NOT NULL,
    extracted_value TEXT,
    confidence      NUMERIC(5,4),
    ground_truth    TEXT,
    is_correct      BOOLEAN,
    eval_run_id     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_doctype_field
    ON extraction_audit (document_type, field_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_eval_run
    ON extraction_audit (eval_run_id);
