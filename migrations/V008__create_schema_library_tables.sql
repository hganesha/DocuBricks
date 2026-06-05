-- V008 — Schema inheritance table (Lakebase)
-- NOTE: schema_changelog lives as a Delta table in docubricks_prod.schema_registry
--       (created by setup_schema_registry.py). This migration adds only
--       schema_inheritance — needed for fast runtime lookup without Spark.

-- ── schema_inheritance ─────────────────────────────────────────────────────
-- Tracks parent-child schema relationships for prompt composition.
-- inheritance_mode:
--   EXTENDS    → child prompt is appended after parent prompt
--   SPECIALISES → child replaces parent for that document type entirely
-- override_fields: JSON array of field names where child takes precedence

CREATE TABLE IF NOT EXISTS schema_inheritance (
    child_document_type     TEXT        NOT NULL,
    parent_document_type    TEXT        NOT NULL,
    inheritance_mode        TEXT        NOT NULL DEFAULT 'EXTENDS',
    override_fields         JSONB,
    depth                   INT         NOT NULL DEFAULT 1,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by              TEXT        NOT NULL DEFAULT 'system',
    PRIMARY KEY (child_document_type, parent_document_type),
    CONSTRAINT valid_mode CHECK (inheritance_mode IN ('EXTENDS', 'SPECIALISES'))
);

-- Seed the FS vertical inheritance chain
INSERT INTO schema_inheritance
    (child_document_type, parent_document_type, inheritance_mode, override_fields, depth, created_by)
VALUES
    -- KYC EDD extends standard KYC CDD (adds source of funds, source of wealth, EDD triggers)
    ('kyc_edd_form', 'kyc_cdd_form', 'EXTENDS',
     '["sourceOfFunds", "sourceOfWealth", "eddTriggers", "seniorManagementApproval"]'::jsonb,
     1, 'seed'),
    -- AML SAR specialises KYC CDD (shares party model but replaces the primary extraction target)
    ('aml_sar', 'kyc_cdd_form', 'SPECIALISES',
     '["screening", "regulatoryReports", "cases", "suspiciousActivityType"]'::jsonb,
     1, 'seed')
ON CONFLICT (child_document_type, parent_document_type) DO NOTHING;
