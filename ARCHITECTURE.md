# DocuBricks — Platform Architecture

> **Design mandate:** every architectural decision must demonstrably improve at least one of: robustness, performance, or durability. Decisions that trade these properties for development speed are explicitly deferred to post-MVP.

---

## Table of Contents

1. [Architecture Principles](#1-architecture-principles)
2. [System Topology](#2-system-topology)
3. [Layer 0 — Source Connectivity](#3-layer-0--source-connectivity)
4. [Layer 1 — Ingestion Pipeline](#4-layer-1--ingestion-pipeline)
5. [Layer 2 — Document Processing](#5-layer-2--document-processing)
6. [Layer 3 — Schema Binding & Validation](#6-layer-3--schema-binding--validation)
7. [Layer 4 — Governed Storage](#7-layer-4--governed-storage)
8. [Layer 5 — Operational Registry (Lakebase)](#8-layer-5--operational-registry-lakebase)
9. [Layer 6 — Serving & Intelligence](#9-layer-6--serving--intelligence)
10. [Layer 7 — Databricks Apps (Experience Layer)](#10-layer-7--databricks-apps-experience-layer)
11. [Layer 8 — Orchestration](#11-layer-8--orchestration)
12. [Robustness Design](#12-robustness-design)
13. [Performance Architecture](#13-performance-architecture)
14. [Durability Guarantees](#14-durability-guarantees)
15. [Security & Governance](#15-security--governance)
16. [Schema Extension Pattern](#16-schema-extension-pattern)
17. [Operational Runbook](#17-operational-runbook)
18. [Known Failure Modes & Mitigations](#18-known-failure-modes--mitigations)
19. [Capacity Planning](#19-capacity-planning)
20. [Observability](#20-observability)
21. [Schema Library](#21-schema-library)
22. [Vertical Agent Library](#22-vertical-agent-library)

---

## 1. Architecture Principles

These are constraints, not guidelines. Every component is evaluated against all five.

| Principle | Statement |
|---|---|
| **Exactly-once delivery** | A document is processed exactly once unless explicitly requeued. Duplicate ingestion is handled by content-addressed document IDs before any AI call is made. |
| **Fail loud, fail fast** | Pipeline failures surface immediately to Workflows alerts and to the Lakebase `processing_jobs` table. Silent partial success is treated as a defect, not a feature. |
| **Data never leaves Unity Catalog** | Raw bytes, parsed text, extracted fields, embeddings, and audit logs all live inside Unity Catalog. No external AI vendor receives document data — Databricks Foundation Model API proxies all LLM calls within the security boundary. |
| **Schema is the contract** | Every table in Silver and Gold is defined by a DLT schema with enforced expectations. A schema change is a versioned migration, not an in-place alter. |
| **Every write is idempotent** | All pipeline tasks use `MERGE INTO` with `document_id` as the natural key. Replaying a task from checkpoint produces the same result. |

---

## 2. System Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 7 — DATABRICKS APPS (Single user-facing experience surface)          │
│                                                                             │
│   ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐   │
│   │  DocuBricks Portal  │  │  Review & Correction │  │  Admin & Schema  │   │
│   │  · Document upload  │  │  · Confidence flags  │  │  · Prompt mgmt   │   │
│   │  · Processing status│  │  · Field correction  │  │  · Accuracy KPIs │   │
│   │  · Genie chat embed │  │  · Human approval    │  │  · Tenant setup  │   │
│   │  · Vertical dashbrd │  │  · Requeue trigger   │  │  · Job monitor   │   │
│   └─────────────────────┘  └─────────────────────┘  └──────────────────┘   │
│                                                                             │
│  Auth: Databricks SSO (no separate auth layer)                              │
│  Data: Unity Catalog RLS — tenant isolation automatic                       │
│  Infra: Databricks Serverless (no cluster management)                       │
└───────┬──────────────────────┬─────────────────────────────────────────────┘
        │  Genie / Jobs /      │  SQL Warehouse /
        │  Files API           │  Lakebase (psycopg2)
        ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 6 — SERVING & INTELLIGENCE (APIs consumed by Apps)                   │
│  AI/BI Genie · Vector Search · AI/BI Dashboards · Agent Bricks             │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SOURCES (any document origin)                                              │
│  SharePoint/OneDrive · S3/ADLS/GCS · Email webhooks · Legacy ECM           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │  raw bytes (PDF, DOCX, images, HTML)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 0 — CONNECTIVITY                                                     │
│  Lakeflow Connect (SaaS) · Autoloader cloudFiles · API webhooks             │
│  → lands raw files into Unity Catalog Volumes (UC Volume = object store)    │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │  file arrival events → Autoloader trigger
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — INGESTION (Lakeflow Pipeline / DLT)                              │
│  Autoloader (exactly-once) → BRONZE registry + raw_content                 │
│  Checkpoint: UC Volume /checkpoints/{pipeline_id}                           │
│  Dead-letter: bronze_quarantine (unreadable files)                          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │  parsed tokens + layout metadata
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 2 — DOCUMENT PROCESSING (DLT Streaming Tables)                       │
│  ai_parse_document() → ai_classify() → schema router                        │
│  Parallel extraction per document_type:                                     │
│    ai_extract(text, schema_prompt) → JSON + confidence_score                │
│  MLflow eval harness: field-level accuracy tracking per batch               │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │  schema-bound structured rows
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — SCHEMA BINDING & VALIDATION (DLT Expectations)                   │
│  SILVER tables: dlt.expect_or_drop() per domain schema                      │
│  Quarantine: silver_quarantine (low confidence / schema violations)         │
│  Human review queue → surfaced in UI → manual correction → requeue          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │  validated, high-confidence rows
                                 ▼
┌────────────────────────────────────────────────────────────┐   ┌───────────────────────┐
│  LAYER 4 — GOVERNED STORAGE                                │   │  LAYER 5 — LAKEBASE   │
│  Delta Lake (Silver + Gold)                                │   │  PostgreSQL OLTP       │
│  Liquid clustering by (doc_type, tenant, date)             │◄──┤  document_registry     │
│  Unity Catalog lineage + row/column ACL                    │   │  processing_jobs       │
│  Time travel: 30d Silver · 90d Gold                        │   │  review_queue          │
│  CDF enabled → downstream CDC consumers                    │   │  extraction_audit      │
│  UC Volumes: raw file archive (cold storage tier)          │   │  reprocessing_queue    │
└────────────────────────────────┬───────────────────────────┘   └───────────────────────┘
                                 │  governed data + vector index
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 6 — SERVING & INTELLIGENCE                                           │
│  AI/BI Genie (per-vertical NL interface, consumed by Apps Genie widget)     │
│  Mosaic AI Vector Search (hybrid semantic + keyword retrieval)              │
│  AI/BI Dashboards (pre-aggregated Gold views, embeddable in Apps)           │
│  Vertical Agent Library (FS · Healthcare · Legal · Manufacturing)           │
│  Databricks Model Serving (custom fine-tuned extractors)                    │
└─────────────────────────────────────────────────────────────────────────────┘

◀────────────────── CROSS-CUTTING: OBSERVABILITY ─────────────────────────────▶
  OTel traces/metrics (Apps layer) · Lakehouse Monitoring (Silver/Gold tables)
  DLT Event Log · Databricks System Tables · MLflow Model Monitoring
  → all feeds into docubricks_prod.gold.platform_health (Genie-queryable)
```

---

## 3. Layer 0 — Source Connectivity

### 3.1 Unity Catalog Volumes as the Landing Zone

All raw documents land in **UC Volumes** — not DBFS, not raw S3 paths. UC Volumes provide:
- Unity Catalog governance and lineage from the first byte
- Path-based access control (no credentials in code)
- Automatic audit logging of file access

```
catalog: docubricks_prod
  schema: raw_landing
    volume: /Volumes/docubricks_prod/raw_landing/documents/
      {tenant_id}/
        {vertical}/          # fs | healthcare | legal | manufacturing
          {year}/{month}/{day}/
            {document_id}.{ext}
```

`document_id` is computed **before** the file lands: `SHA-256(file_bytes)`, hex-encoded. This enables exact deduplication at ingestion without reading the file twice.

### 3.2 Connector Matrix

| Source | Mechanism | Notes |
|---|---|---|
| SharePoint / OneDrive | Lakeflow Connect managed connector | Incremental via Graph API delta token |
| S3 / ADLS / GCS | Autoloader `cloudFiles` with file notifications (SQS/Event Grid/Pub-Sub) | Prefer file notification over directory listing — O(new files) not O(all files) |
| Email attachments | Custom Databricks Job + IMAP/Exchange API → writes to UC Volume | Rate-limited; attachment size cap enforced at connector |
| API / webhook push | Databricks REST endpoint → Workflow trigger → writes to UC Volume | Payload size: 50MB cap; larger → reject with 413 |
| Legacy ECM (FileNet, OpenText) | JDBC / CMIS connector → Databricks Job → UC Volume | Scheduled batch pull; certified connector list maintained in runbook |

### 3.3 Idempotent Landing

The landing job writes file metadata to Lakebase `document_registry` **before** moving the file to the UC Volume:

```sql
-- Lakebase (PostgreSQL)
INSERT INTO document_registry (
    document_id, source_path, tenant_id, vertical,
    file_size_bytes, content_hash, received_at, status
) VALUES (
    $1, $2, $3, $4, $5, $6, NOW(), 'RECEIVED'
)
ON CONFLICT (document_id) DO UPDATE
    SET last_seen_at = NOW(),
        duplicate_count = document_registry.duplicate_count + 1;
```

If `document_id` already exists, the file is not written to the Volume again. Deduplication is complete before any compute runs.

---

## 4. Layer 1 — Ingestion Pipeline

### 4.1 Autoloader Configuration

```python
bronze_stream = (
    spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "binaryFile")             # read raw bytes
        .option("cloudFiles.useNotifications", "true")          # event-driven, not polling
        .option("cloudFiles.schemaLocation",
                "/Volumes/docubricks_prod/checkpoints/bronze_schema/")
        .option("cloudFiles.maxFilesPerTrigger", "1000")        # bounded micro-batch
        .option("cloudFiles.backfillInterval", "1 day")         # periodic completeness scan
        .option("pathGlobFilter", "*.{pdf,docx,png,jpg,tiff,html}")
        .load("/Volumes/docubricks_prod/raw_landing/documents/")
)
```

**Why file notifications over directory listing:** directory listing scans all files on each trigger — O(total files). File notifications deliver only new file events — O(new files). At 100k documents/day, directory listing degrades measurably within weeks.

### 4.2 Bronze DLT Table

```python
@dlt.table(
    name="bronze_documents",
    comment="Raw binary documents with landing metadata. Immutable after write.",
    table_properties={
        "delta.enableChangeDataFeed": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.columnMapping.mode": "name",     # schema evolution safe
        "quality": "bronze"
    }
)
@dlt.expect_or_drop("non_empty_file", "length > 0")
@dlt.expect_or_drop("valid_document_id", "document_id IS NOT NULL")
@dlt.expect_or_drop("known_vertical", "vertical IN ('fs', 'healthcare', 'legal', 'manufacturing', 'insurance', 'real_estate')")
def bronze_documents():
    return (
        bronze_stream
        .withColumn("document_id", sha2(col("content"), 256))
        .withColumn("tenant_id",   regexp_extract(col("path"), r"/(\w+)/\w+/\w+/", 1))
        .withColumn("vertical",    regexp_extract(col("path"), r"/\w+/(\w+)/", 1))
        .withColumn("file_ext",    regexp_extract(col("path"), r"\.(\w+)$", 1))
        .withColumn("ingested_at", current_timestamp())
        .select(
            "document_id", "tenant_id", "vertical", "file_ext",
            "path", "length", "modificationTime", "content", "ingested_at"
        )
    )
```

**Bronze invariants:**
- Never update or delete bronze rows. They are the immutable audit record.
- `content` column stores raw bytes. This means VACUUM retention must account for binary storage costs.
- Change Data Feed enabled — downstream tasks consume CDC events, not full scans.

### 4.3 Quarantine for Unreadable Files

```python
@dlt.table(name="bronze_quarantine", table_properties={"quality": "quarantine"})
@dlt.expect_or_drop("is_quarantine_candidate", "length == 0 OR document_id IS NULL")
def bronze_quarantine():
    # DLT automatically routes expectation failures here when expect_or_drop is paired
    # with a quarantine table using the same source stream
    ...
```

All quarantined files trigger a Lakebase status update:
```sql
UPDATE document_registry SET status = 'QUARANTINE', failure_reason = $1
WHERE document_id = $2;
```

---

## 5. Layer 2 — Document Processing

### 5.1 Parse (Bronze → Parsed)

`ai_parse_document` is called **once per document**, at this stage. All downstream extraction reads the parsed output — never the raw binary.

```python
@dlt.table(
    name="silver_parsed",
    cluster_by=["vertical", "tenant_id", "ingested_date"],
    table_properties={
        "delta.enableChangeDataFeed": "true",
        "delta.autoOptimize.autoCompact": "true",
        "quality": "silver"
    }
)
@dlt.expect_or_drop("parse_succeeded", "parse_status = 'SUCCESS'")
@dlt.expect("has_content", "char_length(parsed_text) > 50")     # warn, do not drop
def silver_parsed():
    return (
        dlt.read_stream("bronze_documents")
        .withColumn("parsed_result",
            ai_parse_document(col("content")))                   # Databricks native fn
        .withColumn("parsed_text",   col("parsed_result.text"))
        .withColumn("page_count",    col("parsed_result.page_count"))
        .withColumn("layout_json",   to_json(col("parsed_result.layout")))
        .withColumn("parse_status",  col("parsed_result.status"))
        .withColumn("parse_error",   col("parsed_result.error_message"))
        .withColumn("ingested_date", to_date(col("ingested_at")))
        .drop("content")                                         # drop binary; parsed text is the artefact
    )
```

**Performance note:** `ai_parse_document` is Databricks-native and benefits from Photon's vectorised execution. Do not call it inside a UDF — call it as a SQL function expression so Photon can batch and pipeline calls.

### 5.2 Classify (Route to Schema)

```python
@dlt.table(name="silver_classified")
@dlt.expect_or_drop("classified", "document_type IS NOT NULL AND classification_confidence >= 0.70")
def silver_classified():
    LABEL_MAP = {
        "fs":           ["mortgage_application", "kyc_cdd_form", "aml_sar", "trade_confirmation", "invoice"],
        "healthcare":   ["clinical_note_soap", "eob_cms1500", "lab_report", "prior_auth", "drug_label"],
        "legal":        ["nda_msa", "sow", "ip_filing", "regulatory_submission", "court_filing"],
        "insurance":    ["policy_document", "claims_acord", "underwriting_memo", "loss_run"],
    }
    all_labels = [label for labels in LABEL_MAP.values() for label in labels]

    return (
        dlt.read_stream("silver_parsed")
        .withColumn("classification_result",
            ai_classify(col("parsed_text"), array([lit(l) for l in all_labels])))
        .withColumn("document_type",             col("classification_result.label"))
        .withColumn("classification_confidence", col("classification_result.score"))
        .withColumn("classification_model",      lit("databricks-dbrx-instruct"))
    )
```

Low-confidence classifications (`< 0.70`) are dropped from the main stream and routed to `silver_quarantine` via DLT expectations. They simultaneously write to the Lakebase `review_queue` for human classification.

### 5.3 Extraction (Schema-Bound)

Extraction runs as a **separate DLT streaming table per document type**. This allows independent tuning, rollback, and scaling per schema without affecting others.

```python
# Pattern repeated for each document type with its own schema prompt
@dlt.table(name="silver_extracted_mortgage_application")
@dlt.expect_or_drop("extraction_min_confidence",
                    "avg_confidence_score >= 0.65")
@dlt.expect_or_drop("required_loan_fields",
                    "loan_amount IS NOT NULL AND loan_purpose IS NOT NULL")
def silver_extracted_mortgage_application():
    schema_prompt = spark.table(
        "docubricks_prod.schema_registry.extraction_prompts"
    ).filter("document_type = 'mortgage_application' AND is_active = true"
    ).orderBy(desc("version")).first()["prompt_text"]

    return (
        dlt.read_stream("silver_classified")
        .filter(col("document_type") == "mortgage_application")
        .withColumn("extraction_result",
            ai_extract(col("parsed_text"), lit(schema_prompt)))
        .withColumn("extracted_json",     col("extraction_result.result"))
        .withColumn("avg_confidence_score", col("extraction_result.avg_confidence"))
        .withColumn("field_confidences",  col("extraction_result.field_scores"))
        # Flatten JSON into typed columns using schema definition
        .withColumn("loan_amount",
            get_json_object(col("extracted_json"), "$.loan.requestedLoanAmount").cast("decimal(18,2)"))
        .withColumn("loan_purpose",
            get_json_object(col("extracted_json"), "$.loan.loanPurpose"))
        .withColumn("borrower_name",
            get_json_object(col("extracted_json"), "$.borrowers[0].fullName.lastName"))
        .withColumn("debt_to_income_ratio",
            get_json_object(col("extracted_json"), "$.underwriting.ratios.totalDebtExpenseRatioPercent").cast("decimal(5,2)"))
        .withColumn("extracted_at", current_timestamp())
    )
```

**Schema prompt versioning:** extraction prompts live in `docubricks_prod.schema_registry.extraction_prompts`, not in code. This decouples schema evolution from code deployment. A schema engineer can update a prompt, bump the version, and the next pipeline run uses the new version — without a code change.

### 5.4 MLflow Evaluation After Each Batch

```python
# Called from the Workflow task that runs after each DLT pipeline batch
import mlflow

def evaluate_extraction_batch(document_type: str, batch_id: str):
    df = spark.table(f"docubricks_prod.silver.extracted_{document_type}") \
              .filter(f"batch_id = '{batch_id}'")

    # Compare against ground-truth for documents with known labels
    ground_truth = spark.table("docubricks_prod.eval.ground_truth") \
                        .filter(f"document_type = '{document_type}'")

    with mlflow.start_run(run_name=f"eval_{document_type}_{batch_id}"):
        eval_result = mlflow.evaluate(
            data=df.join(ground_truth, "document_id", "inner").toPandas(),
            targets="ground_truth_json",
            predictions="extracted_json",
            model_type="question-answering",
            extra_metrics=[field_accuracy_metric, confidence_calibration_metric]
        )
        mlflow.log_metric("avg_field_accuracy", eval_result.metrics["avg_field_accuracy"])
        mlflow.log_metric("low_confidence_rate",
            df.filter("avg_confidence_score < 0.65").count() / df.count())
```

MLflow evaluation results feed back into the `extraction_audit` table in Lakebase, which powers the accuracy trend dashboard in Genie.

---

## 6. Layer 3 — Schema Binding & Validation

### 6.1 Medallion Architecture

```
Bronze   — raw binary + metadata. Immutable. Never queried directly by users.
Silver   — parsed + classified + extracted. Schema-validated. Source of truth for all analytics.
Gold     — pre-aggregated business views. Optimised for Genie queries and dashboards.
Quarantine — rows rejected at any stage, with rejection reason and original row. Never deleted.
```

### 6.2 DLT Expectation Strategy

Three levels of expectation severity:

| Expectation | DLT Function | Effect |
|---|---|---|
| Fatal data quality violation | `dlt.expect_or_fail()` | Halts the entire pipeline. Used for system-level invariants (e.g., `document_id IS NOT NULL`). |
| Recoverable row-level violation | `dlt.expect_or_drop()` | Drops the row from the table, routes to quarantine, logs to Lakebase. Used for business quality rules. |
| Monitoring-only warning | `dlt.expect()` | Logs the violation count to DLT Event Log. Does not affect data flow. Used for trend monitoring. |

```python
# Example: Silver KYC table expectations
@dlt.table(name="silver_extracted_kyc_cdd")
@dlt.expect_or_fail("document_id_present",     "document_id IS NOT NULL")
@dlt.expect_or_drop("profile_id_extracted",    "kyc_profile_id IS NOT NULL")
@dlt.expect_or_drop("customer_type_valid",     "customer_type IN ('Individual','Business','Trust','Estate','GovernmentEntity','NonProfit','FinancialInstitution','Fund','Joint','Other')")
@dlt.expect_or_drop("minimum_confidence",      "avg_confidence_score >= 0.65")
@dlt.expect("pep_screening_present",           "pep_status IS NOT NULL")   # warn; PEP may be absent
@dlt.expect("beneficial_ownership_complete",   "beneficial_ownership_collected = true OR bo_exemption_reason IS NOT NULL")
def silver_extracted_kyc_cdd():
    ...
```

### 6.3 Gold Aggregation Tables

Gold tables are **materialized views** over Silver, pre-joined for common Genie query patterns. They are refreshed by a downstream Workflow task after each Silver write.

```sql
-- Gold: FS portfolio summary (refreshed hourly)
CREATE OR REPLACE MATERIALIZED VIEW docubricks_prod.gold.fs_mortgage_portfolio AS
SELECT
    tenant_id,
    date_trunc('week', extracted_at)          AS week,
    COUNT(*)                                  AS application_count,
    SUM(loan_amount)                          AS total_loan_amount,
    AVG(debt_to_income_ratio)                 AS avg_dti,
    PERCENTILE_CONT(0.5) WITHIN GROUP
        (ORDER BY loan_amount)                AS median_loan_amount,
    COUNT_IF(debt_to_income_ratio > 0.43)     AS high_dti_count,
    COUNT_IF(avg_confidence_score < 0.80)     AS low_confidence_count
FROM docubricks_prod.silver.extracted_mortgage_application
GROUP BY 1, 2;
```

---

## 7. Layer 4 — Governed Storage

### 7.1 Delta Lake Table Properties (All Silver/Gold Tables)

```sql
ALTER TABLE docubricks_prod.silver.extracted_mortgage_application
SET TBLPROPERTIES (
    'delta.enableChangeDataFeed'              = 'true',
    'delta.autoOptimize.optimizeWrite'        = 'true',
    'delta.autoOptimize.autoCompact'          = 'true',
    'delta.deletionVectors.enabled'           = 'true',   -- efficient soft deletes for GDPR/CCPA
    'delta.dataSkippingNumIndexedCols'        = '10',
    'delta.logRetentionDuration'             = 'interval 90 days',
    'delta.deletedFileRetentionDuration'      = 'interval 30 days',
    'quality'                                 = 'silver',
    'docubricks.vertical'                     = 'fs',
    'docubricks.document_type'                = 'mortgage_application',
    'docubricks.schema_version'               = '2.1'
);
```

### 7.2 Liquid Clustering

Liquid clustering replaces static `ZORDER` and `PARTITION BY`. It is adaptive — clustering keys can be changed without a full rewrite.

```sql
-- Applied at table creation; Databricks re-clusters incrementally in background
ALTER TABLE docubricks_prod.silver.extracted_mortgage_application
CLUSTER BY (tenant_id, document_type, ingested_date);

-- For Gold tables optimised for Genie (query patterns: tenant + date range)
ALTER TABLE docubricks_prod.gold.fs_mortgage_portfolio
CLUSTER BY (tenant_id, week);
```

**Why liquid clustering over partitioning:** partitioning on `ingested_date` creates one directory per day forever. Liquid clustering maintains a bounded number of clustered files regardless of cardinality and adapts as query patterns change.

### 7.3 Bloom Filters for High-Cardinality Lookups

```sql
-- Add bloom filter on document_id for point lookups (registry → Delta)
CREATE BLOOMFILTER INDEX ON TABLE docubricks_prod.silver.extracted_mortgage_application
    FOR COLUMNS (document_id OPTIONS (fpp=0.01),
                 borrower_name OPTIONS (fpp=0.05));
```

### 7.4 Time Travel & Recovery

```sql
-- Restore a table to a known-good state after a bad batch
RESTORE TABLE docubricks_prod.silver.extracted_kyc_cdd
    TO VERSION AS OF 142;    -- version from before the bad extraction run

-- Point-in-time audit query
SELECT *
FROM docubricks_prod.silver.extracted_kyc_cdd
    TIMESTAMP AS OF '2026-05-15 14:00:00'
WHERE document_id = 'abc123';
```

### 7.5 Unity Catalog Namespace

```
docubricks_prod (catalog)
  ├── raw_landing (schema)
  │     └── [UC Volume] /documents/{tenant_id}/{vertical}/...
  ├── bronze (schema)
  │     ├── bronze_documents
  │     └── bronze_quarantine
  ├── silver (schema)
  │     ├── silver_parsed
  │     ├── silver_classified
  │     ├── silver_extracted_mortgage_application
  │     ├── silver_extracted_kyc_cdd_form
  │     ├── silver_extracted_aml_sar
  │     ├── silver_extracted_kyc_cdd      [→ KYC schema: 40 canonical domains]
  │     ├── silver_quarantine
  │     └── silver_review_candidates
  ├── gold (schema)
  │     ├── fs_mortgage_portfolio
  │     ├── fs_kyc_compliance_summary
  │     ├── fs_aml_alerts
  │     └── [one view per vertical × use case]
  ├── schema_registry (schema)
  │     ├── extraction_prompts            [versioned schema prompts]
  │     ├── document_type_labels          [classification label registry]
  │     └── validation_rules              [per-field validation config]
  └── eval (schema)
        ├── ground_truth                  [labeled documents for MLflow eval]
        └── accuracy_trends               [historical eval metrics]
```

### 7.6 Unity Catalog Access Control

```sql
-- Tenant isolation: row-level security via row filter
CREATE ROW FILTER docubricks_prod.silver.rls_tenant_filter
    ON (tenant_id STRING)
    RETURN current_user() IN (
        SELECT user_email FROM docubricks_prod.access.tenant_users
        WHERE tenant_id = tenant_id
    );

ALTER TABLE docubricks_prod.silver.extracted_mortgage_application
    SET ROW FILTER docubricks_prod.silver.rls_tenant_filter ON (tenant_id);

-- Column masking for PII fields
CREATE MASK docubricks_prod.silver.mask_ssn
    USING COLUMNS (ssn STRING)
    RETURN CASE
        WHEN is_account_admin() THEN ssn
        ELSE CONCAT('***-**-', RIGHT(ssn, 4))
    END;

ALTER TABLE docubricks_prod.silver.extracted_kyc_cdd_form
    ALTER COLUMN taxpayer_id SET MASK docubricks_prod.silver.mask_ssn;
```

---

## 8. Layer 5 — Operational Registry (Lakebase)

Lakebase provides the **transactional backbone** that Delta Lake cannot: sub-second point reads, mutable job state, queue semantics. This is the operational brain; Delta Lake is the analytical brain.

### 8.1 Schema

```sql
-- document_registry: single source of truth for every document's lifecycle
CREATE TABLE document_registry (
    document_id         TEXT        PRIMARY KEY,
    tenant_id           TEXT        NOT NULL,
    vertical            TEXT        NOT NULL,
    source_path         TEXT        NOT NULL,
    file_ext            TEXT        NOT NULL,
    file_size_bytes     BIGINT,
    content_hash        TEXT        NOT NULL,   -- SHA-256, same as document_id
    received_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ,
    duplicate_count     INT         NOT NULL DEFAULT 0,
    status              TEXT        NOT NULL DEFAULT 'RECEIVED',
    -- RECEIVED | PARSING | PARSED | CLASSIFYING | CLASSIFIED
    -- EXTRACTING | EXTRACTED | VALIDATED | QUARANTINE | REVIEW | COMPLETE | FAILED
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
    ))
);

CREATE INDEX idx_registry_tenant_status   ON document_registry (tenant_id, status);
CREATE INDEX idx_registry_vertical_date   ON document_registry (vertical, received_at DESC);
CREATE INDEX idx_registry_pipeline_run    ON document_registry (pipeline_run_id);

-- processing_jobs: one row per Databricks Workflow run
CREATE TABLE processing_jobs (
    job_run_id      TEXT        PRIMARY KEY,
    pipeline_id     TEXT        NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'RUNNING',
    docs_ingested   INT         DEFAULT 0,
    docs_parsed     INT         DEFAULT 0,
    docs_extracted  INT         DEFAULT 0,
    docs_quarantine INT         DEFAULT 0,
    docs_failed     INT         DEFAULT 0,
    error_message   TEXT,
    metadata        JSONB
);

-- review_queue: documents requiring human review before finalisation
CREATE TABLE review_queue (
    review_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     TEXT        NOT NULL REFERENCES document_registry(document_id),
    tenant_id       TEXT        NOT NULL,
    review_reason   TEXT        NOT NULL,
    -- LOW_CONFIDENCE | CLASSIFICATION_AMBIGUOUS | SCHEMA_VIOLATION | HUMAN_FLAGGED
    priority        INT         NOT NULL DEFAULT 5,  -- 1=highest
    assigned_to     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sla_due_at      TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    resolution      TEXT,       -- APPROVED | CORRECTED | QUARANTINE | REPROCESS
    corrected_json  JSONB,      -- human-corrected extraction output
    CONSTRAINT valid_reason CHECK (review_reason IN (
        'LOW_CONFIDENCE','CLASSIFICATION_AMBIGUOUS','SCHEMA_VIOLATION','HUMAN_FLAGGED'
    ))
);

CREATE INDEX idx_review_tenant_priority ON review_queue (tenant_id, priority, created_at)
    WHERE resolved_at IS NULL;

-- reprocessing_queue: documents queued for re-extraction (schema update, model change)
CREATE TABLE reprocessing_queue (
    reprocess_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     TEXT        NOT NULL REFERENCES document_registry(document_id),
    reason          TEXT        NOT NULL,
    -- SCHEMA_VERSION_CHANGE | MODEL_UPGRADE | MANUAL_TRIGGER | CORRECTION_APPLIED
    target_version  TEXT,       -- schema_version to re-extract against
    queued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'PENDING'
);

-- extraction_audit: per-field accuracy log for MLflow eval
CREATE TABLE extraction_audit (
    audit_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     TEXT        NOT NULL,
    document_type   TEXT        NOT NULL,
    field_name      TEXT        NOT NULL,
    extracted_value TEXT,
    confidence      NUMERIC(5,4),
    ground_truth    TEXT,
    is_correct      BOOLEAN,
    eval_run_id     TEXT,       -- MLflow run ID
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_doctype_field ON extraction_audit (document_type, field_name, created_at DESC);
```

### 8.2 Connection Management

```python
# databricks_secrets for connection string — never hardcoded
import psycopg2
from databricks.sdk.runtime import dbutils

LAKEBASE_CONN = dbutils.secrets.get(scope="docubricks-prod", key="lakebase-conn-string")

# Connection pool (use PgBouncer sidecar or Lakebase built-in pooling)
from psycopg2 import pool
_conn_pool = pool.ThreadedConnectionPool(minconn=2, maxconn=20, dsn=LAKEBASE_CONN)

def get_conn():
    return _conn_pool.getconn()

def release_conn(conn):
    _conn_pool.putconn(conn)
```

### 8.3 Status Transitions

Every status change in Lakebase is written **before** the corresponding compute step begins, and updated **after** it completes. If a step crashes mid-execution, the registry shows the in-progress state — the pipeline's Workflow retry logic detects stale `PARSING`/`EXTRACTING` states and re-queues them.

```python
def begin_extraction(document_id: str, pipeline_run_id: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE document_registry
               SET status = 'EXTRACTING', pipeline_run_id = $1
             WHERE document_id = $2 AND status = 'CLASSIFIED'
        """, (pipeline_run_id, document_id))
        # Returns 0 rows if status != CLASSIFIED → idempotent guard

def complete_extraction(document_id: str, confidence: float):
    with get_conn() as conn:
        conn.execute("""
            UPDATE document_registry
               SET status = CASE WHEN $1 >= 0.65 THEN 'VALIDATED' ELSE 'REVIEW' END,
                   extraction_conf = $1,
                   extracted_at = NOW()
             WHERE document_id = $2
        """, (confidence, document_id))
```

---

## 9. Layer 6 — Serving & Intelligence

### 9.1 Genie Workspaces

One Genie workspace per vertical, configured with domain-specific vocabulary, trusted tables, and seed questions.

```
docubricks_prod.gold.fs_*          → "DocuBricks FS Genie"
docubricks_prod.gold.healthcare_*  → "DocuBricks Healthcare Genie"
docubricks_prod.gold.legal_*       → "DocuBricks Legal Genie"
```

Genie configuration per workspace:
- **Trusted tables:** only Gold views (never Silver directly — Silver is for engineers)
- **Metric definitions:** pre-registered metrics (e.g., `avg_dti`, `high_dti_count`) so Genie resolves terms consistently
- **Seed questions:** 20 vertical-specific seed questions per workspace to bootstrap Genie's understanding
- **Compute:** Serverless SQL warehouse (0-cluster warm-up, per-second billing, auto-scales to 0)

Sample FS Genie seed questions:
```
"Show me all mortgage applications with DTI > 43% submitted this month"
"Which KYC profiles have missing PEP screening results?"
"How many AML SARs were filed last quarter by risk tier?"
"What is the average extraction confidence for mortgage documents this week?"
```

### 9.2 Mosaic AI Vector Search

Used for semantic document retrieval — "find contracts similar to this one" — and as the RAG retrieval layer for Agent Bricks workflows.

```python
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()

# Create a Delta Sync Index — auto-syncs from Silver table
vsc.create_delta_sync_index(
    endpoint_name="docubricks-vector-search",
    index_name="docubricks_prod.silver.mortgage_text_index",
    source_table_name="docubricks_prod.silver.silver_parsed",
    pipeline_type="TRIGGERED",          # sync on demand after each pipeline run
    primary_key="document_id",
    embedding_source_column="parsed_text",
    embedding_model_endpoint_name="databricks-bge-large-en",  # Databricks-hosted BGE
    columns_to_sync=["document_id", "tenant_id", "vertical", "document_type",
                     "ingested_date", "page_count"]
)
```

**Hybrid search:** queries hit both the vector index (semantic similarity) and Delta Lake (keyword / structured filters) and results are merged. Databricks Vector Search supports this natively via `filters` parameter on query.

### 9.3 Agent Bricks (Multi-Step Workflows)

```python
from databricks.agents import AgentFramework

@AgentFramework.tool(description="Query structured extraction results for a document")
def query_document_fields(document_id: str, fields: list[str]) -> dict:
    return spark.table("docubricks_prod.silver.extracted_mortgage_application") \
                .filter(f"document_id = '{document_id}'") \
                .select(fields) \
                .first() \
                .asDict()

@AgentFramework.tool(description="Flag a document for human review")
def flag_for_review(document_id: str, reason: str) -> str:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO review_queue (document_id, tenant_id, review_reason, priority, sla_due_at)
            SELECT document_id, tenant_id, $1, 3, NOW() + INTERVAL '24 hours'
            FROM document_registry WHERE document_id = $2
            ON CONFLICT DO NOTHING
        """, (reason, document_id))
    return f"Document {document_id} flagged for review: {reason}"
```

Example Agent Bricks workflow: **Contract Expiry Monitor**
1. Query Gold for contracts expiring in 30–90 days
2. Retrieve full extracted contract for each
3. Identify counterparty, renewal terms, legal contact from extracted fields
4. Generate renewal briefing via `ai_query()`
5. Write briefing to Lakebase `notifications` table → surface in dashboard

### 9.4 Databricks Model Serving

For document types where generic models underperform (e.g., highly structured ACORD claims forms), fine-tuned extractors are served via Databricks Model Serving:

```python
import mlflow.pyfunc

class FineTunedExtractor(mlflow.pyfunc.PythonModel):
    def predict(self, context, model_input, params=None):
        # Calls the fine-tuned extraction model
        ...

# Register in MLflow Model Registry
mlflow.pyfunc.log_model(
    artifact_path="extractor",
    python_model=FineTunedExtractor(),
    registered_model_name="docubricks_acord_extractor",
    await_registration_for=120
)
```

The serving endpoint is then called from the `ai_query()` function within the extraction DLT task:
```sql
SELECT ai_query(
    'docubricks-acord-extractor',
    CONCAT(schema_prompt, '\n\nDocument:\n', parsed_text)
) AS extraction_result
FROM silver_classified
WHERE document_type = 'claims_acord'
```

---

## 10. Layer 7 — Databricks Apps (Experience Layer)

Databricks Apps is the runtime that turns every backend capability — Genie, Delta tables, Lakebase, Workflows, Vector Search — into a single, coherent product experience. The user never touches a notebook, a SQL editor, or a Databricks cluster configuration. They interact with the DocuBricks application, which speaks Databricks APIs on their behalf.

Apps run inside the Databricks workspace on serverless compute. Authentication is handled by Databricks SSO — no separate auth layer, no token management on the user side. Unity Catalog row-level security applies automatically based on the app's service principal, so tenants are isolated without any application-level filtering code.

### 10.1 App Inventory

| App | Framework | Primary users | Core responsibilities |
|---|---|---|---|
| **DocuBricks Portal** | Streamlit | Business users (analysts, compliance officers, loan officers) | Document upload, processing status, Genie chat widget, vertical dashboards |
| **Review & Correction UI** | Streamlit | Domain reviewers, QA analysts | Human review queue, field-level correction, confidence visualisation, requeue trigger |
| **Admin & Schema Manager** | Streamlit | Platform engineers, schema owners | Schema prompt CRUD, extraction accuracy trends, tenant onboarding, job monitoring |

### 10.2 App Manifest (`app.yaml`)

Each app is declared as a YAML manifest committed to the repo. Databricks Apps deploys directly from this manifest — no Dockerfile, no Kubernetes config.

```yaml
# apps/portal/app.yaml — DocuBricks Portal
command: ["streamlit", "run", "app.py", "--server.port", "8080", "--server.headless", "true"]

dependencies:
  - requirements.txt

env:
  - name: DOCUBRICKS_ENV
    value: "production"
  - name: GENIE_SPACE_ID_FS
    valueFrom:
      secretRef:
        scope: docubricks-prod
        key: genie-space-id-fs
  - name: GENIE_SPACE_ID_HEALTHCARE
    valueFrom:
      secretRef:
        scope: docubricks-prod
        key: genie-space-id-healthcare
  - name: LAKEBASE_CONN
    valueFrom:
      secretRef:
        scope: docubricks-prod
        key: lakebase-conn-string
  - name: PIPELINE_JOB_ID
    valueFrom:
      secretRef:
        scope: docubricks-prod
        key: pipeline-job-id

resources:
  sql_warehouses:
    - id: docubricks-serverless-wh        # Serverless SQL warehouse for Gold queries
      permission: CAN_USE
  jobs:
    - id: docubricks-main-pipeline        # Main DLT pipeline job
      permission: CAN_MANAGE_RUN          # Can trigger runs, not edit the job
  volumes:
    - name: docubricks_prod.raw_landing.documents
      permission: READ_WRITE              # Upload raw files
  serving_endpoints:
    - name: databricks-bge-large-en       # For ad-hoc semantic search from UI
      permission: CAN_QUERY
```

**Why this matters for security:** the `resources` block is an explicit allowlist — the app's service principal can only access resources enumerated here. No wildcard workspace access. An engineer reading `app.yaml` sees the complete data access surface of the app.

### 10.3 DocuBricks Portal — Core Flows

#### Document Upload Flow

```python
# portal/upload.py
import hashlib, os, requests, streamlit as st
import psycopg2

DATABRICKS_HOST  = os.environ["DATABRICKS_HOST"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]   # injected by Apps runtime

def compute_document_id(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def upload_to_volume(file_bytes: bytes, document_id: str,
                     tenant_id: str, vertical: str, file_ext: str) -> str:
    volume_path = (
        f"/Volumes/docubricks_prod/raw_landing/documents"
        f"/{tenant_id}/{vertical}/{document_id}.{file_ext}"
    )
    resp = requests.put(
        f"{DATABRICKS_HOST}/api/2.0/fs/files{volume_path}",
        headers={
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
            "Content-Type": "application/octet-stream"
        },
        data=file_bytes
    )
    resp.raise_for_status()
    return volume_path

def register_in_lakebase(document_id: str, source_path: str,
                          tenant_id: str, vertical: str,
                          file_size: int, content_hash: str):
    conn = psycopg2.connect(os.environ["LAKEBASE_CONN"])
    with conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO document_registry
                (document_id, source_path, tenant_id, vertical,
                 file_size_bytes, content_hash, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'RECEIVED')
            ON CONFLICT (document_id) DO UPDATE
                SET last_seen_at = NOW(), duplicate_count = document_registry.duplicate_count + 1
            RETURNING duplicate_count
        """, (document_id, source_path, tenant_id, vertical, file_size, content_hash))
        duplicate_count = cur.fetchone()[0]
    return duplicate_count

def trigger_pipeline(document_id: str, tenant_id: str) -> str:
    resp = requests.post(
        f"{DATABRICKS_HOST}/api/2.1/jobs/run-now",
        headers={"Authorization": f"Bearer {DATABRICKS_TOKEN}"},
        json={
            "job_id": int(os.environ["PIPELINE_JOB_ID"]),
            "notebook_params": {
                "trigger_document_id": document_id,
                "tenant_id": tenant_id
            }
        }
    )
    resp.raise_for_status()
    return str(resp.json()["run_id"])

# Streamlit upload widget
uploaded = st.file_uploader("Drop documents here", type=["pdf","docx","png","jpg","tiff"])
vertical = st.selectbox("Vertical", ["fs", "healthcare", "legal", "insurance"])

if uploaded and st.button("Process"):
    file_bytes = uploaded.read()
    document_id = compute_document_id(file_bytes)
    tenant_id   = st.session_state["tenant_id"]   # set at login from Databricks SSO claims
    file_ext    = uploaded.name.rsplit(".", 1)[-1].lower()

    with st.spinner("Uploading..."):
        path = upload_to_volume(file_bytes, document_id, tenant_id, vertical, file_ext)
        dup  = register_in_lakebase(document_id, path, tenant_id, vertical,
                                    len(file_bytes), document_id)

    if dup > 0:
        st.warning(f"This document was seen before ({dup} times). Duplicate skipped.")
    else:
        run_id = trigger_pipeline(document_id, tenant_id)
        st.success(f"Processing started. Run ID: `{run_id}`")
        st.session_state["tracking_doc"] = document_id
```

#### Processing Status — Real-Time Polling

```python
# portal/status.py — status page reads Lakebase, not Delta (sub-second latency)
import time, psycopg2, streamlit as st

STATUS_EMOJI = {
    "RECEIVED":    "📥", "PARSING":     "⚙️",  "PARSED":      "✅",
    "CLASSIFYING": "🔍", "CLASSIFIED":  "✅",  "EXTRACTING":  "⚙️",
    "EXTRACTED":   "✅", "VALIDATED":   "✅",  "COMPLETE":    "🎉",
    "REVIEW":      "👁️", "QUARANTINE":  "⚠️",  "FAILED":      "❌",
}

def get_status(document_id: str) -> dict:
    conn = psycopg2.connect(os.environ["LAKEBASE_CONN"])
    with conn.cursor() as cur:
        cur.execute("""
            SELECT document_id, status, document_type,
                   classification_conf, extraction_conf,
                   failure_reason, extracted_at, received_at
            FROM document_registry WHERE document_id = %s
        """, (document_id,))
        row = cur.fetchone()
        cols = [desc[0] for desc in cur.description]
        return dict(zip(cols, row)) if row else {}

if doc_id := st.session_state.get("tracking_doc"):
    placeholder = st.empty()
    while True:
        info = get_status(doc_id)
        status = info.get("status", "UNKNOWN")
        with placeholder.container():
            st.metric("Status", f"{STATUS_EMOJI.get(status, '?')}  {status}")
            if info.get("document_type"):
                st.metric("Detected Type", info["document_type"])
            if info.get("extraction_conf"):
                st.metric("Extraction Confidence", f"{info['extraction_conf']:.0%}")
            if status == "REVIEW":
                st.warning("This document requires human review.")
                st.page_link("pages/review.py", label="Open Review Queue →")
        if status in ("COMPLETE", "QUARANTINE", "FAILED"):
            break
        time.sleep(2)
```

#### Embedded Genie Chat Widget

```python
# portal/genie_chat.py
import os, requests, time, streamlit as st

DATABRICKS_HOST  = os.environ["DATABRICKS_HOST"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]

GENIE_SPACES = {
    "fs":          os.environ["GENIE_SPACE_ID_FS"],
    "healthcare":  os.environ.get("GENIE_SPACE_ID_HEALTHCARE", ""),
    "legal":       os.environ.get("GENIE_SPACE_ID_LEGAL", ""),
}

def ask_genie(space_id: str, question: str) -> str:
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}

    # Start conversation
    r = requests.post(
        f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space_id}/start-conversation",
        headers=headers,
        json={"content": question}
    )
    r.raise_for_status()
    body           = r.json()
    conversation_id = body["conversation_id"]
    message_id      = body["message_id"]

    # Poll until complete (Genie is async)
    for _ in range(60):
        r = requests.get(
            f"{DATABRICKS_HOST}/api/2.0/genie/spaces/{space_id}"
            f"/conversations/{conversation_id}/messages/{message_id}",
            headers=headers
        )
        msg = r.json()
        if msg.get("status") == "COMPLETED":
            # Return the query result description or the SQL result summary
            attachments = msg.get("attachments", [])
            for att in attachments:
                if att.get("text"):
                    return att["text"]["content"]
                if att.get("query"):
                    return f"```sql\n{att['query']['query']}\n```\n\n{att['query'].get('description','')}"
            return msg.get("content", "No result.")
        if msg.get("status") in ("FAILED", "CANCELLED"):
            return f"Genie could not answer: {msg.get('error', 'unknown error')}"
        time.sleep(1)
    return "Genie timed out. Please try a simpler question."

# Streamlit chat widget
vertical = st.session_state.get("vertical", "fs")
space_id = GENIE_SPACES.get(vertical)

st.subheader(f"Ask your documents ({vertical.upper()})")
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask_genie(space_id, prompt)
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
```

### 10.4 Review & Correction UI

The review app reads from Lakebase `review_queue`, renders the original document alongside extracted fields and confidence scores, and lets a reviewer approve, correct, or quarantine.

```python
# apps/review/app.py
import os, json, requests, psycopg2, streamlit as st

def load_review_queue(tenant_id: str) -> list[dict]:
    conn = psycopg2.connect(os.environ["LAKEBASE_CONN"])
    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.review_id, r.document_id, r.review_reason, r.priority,
                   r.created_at, r.sla_due_at,
                   d.document_type, d.classification_conf, d.extraction_conf,
                   d.source_path
            FROM review_queue r
            JOIN document_registry d USING (document_id)
            WHERE r.tenant_id = %s AND r.resolved_at IS NULL
            ORDER BY r.priority ASC, r.created_at ASC
            LIMIT 50
        """, (tenant_id,))
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def load_extracted_fields(document_id: str, document_type: str) -> dict:
    from databricks import sql
    conn = sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
        http_path=os.environ["SQL_WH_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"]
    )
    with conn.cursor() as cur:
        table = f"docubricks_prod.silver.extracted_{document_type.replace('-','_')}"
        cur.execute(f"SELECT * FROM {table} WHERE document_id = ?", (document_id,))
        row = cur.fetchone()
        cols = [desc[0] for desc in cur.description]
        return dict(zip(cols, row)) if row else {}

def resolve_review(review_id: str, resolution: str, corrected: dict | None = None):
    conn = psycopg2.connect(os.environ["LAKEBASE_CONN"])
    with conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE review_queue
               SET resolved_at   = NOW(),
                   resolution    = %s,
                   corrected_json = %s
             WHERE review_id = %s
        """, (resolution, json.dumps(corrected) if corrected else None, review_id))
        if resolution == "REPROCESS":
            cur.execute("""
                INSERT INTO reprocessing_queue (document_id, reason)
                SELECT document_id, 'CORRECTION_APPLIED'
                FROM review_queue WHERE review_id = %s
            """, (review_id,))

# Streamlit review UI
queue = load_review_queue(st.session_state["tenant_id"])
if not queue:
    st.success("Review queue is empty.")
else:
    item     = queue[0]
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Original Document")
        # Render PDF/image inline via Files API
        doc_url = f"{os.environ['DATABRICKS_HOST']}/api/2.0/fs/files{item['source_path']}"
        st.markdown(f"[Open document]({doc_url})")
        st.caption(f"Type: **{item['document_type']}** · Confidence: **{item['extraction_conf']:.0%}**")
        st.caption(f"Reason for review: **{item['review_reason']}**")

    with col2:
        st.subheader("Extracted Fields")
        fields = load_extracted_fields(item["document_id"], item["document_type"])
        corrected = {}
        for field, value in fields.items():
            if field.startswith("_") or field == "document_id":
                continue
            corrected[field] = st.text_input(field, value=str(value) if value else "")

    st.divider()
    c1, c2, c3 = st.columns(3)
    if c1.button("✅ Approve as-is"):
        resolve_review(item["review_id"], "APPROVED")
        st.rerun()
    if c2.button("💾 Save corrections & reprocess"):
        resolve_review(item["review_id"], "REPROCESS", corrected)
        st.rerun()
    if c3.button("🗑️ Quarantine"):
        resolve_review(item["review_id"], "QUARANTINE")
        st.rerun()
```

### 10.5 Admin & Schema Manager

The admin app provides schema engineers with a no-SQL interface to manage extraction prompts, monitor accuracy trends, and onboard tenants.

```python
# apps/admin/pages/schema_prompts.py
from databricks import sql
import streamlit as st

def list_prompts() -> list[dict]:
    with get_sql_conn().cursor() as cur:
        cur.execute("""
            SELECT document_type, vertical, version, is_active,
                   preferred_model, updated_at
            FROM docubricks_prod.schema_registry.extraction_prompts
            ORDER BY vertical, document_type, version DESC
        """)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

def save_prompt(document_type: str, vertical: str,
                prompt_text: str, preferred_model: str):
    with get_sql_conn().cursor() as cur:
        # Deactivate current active version
        cur.execute("""
            UPDATE docubricks_prod.schema_registry.extraction_prompts
               SET is_active = false
             WHERE document_type = ? AND vertical = ? AND is_active = true
        """, (document_type, vertical))
        # Insert new version
        cur.execute("""
            INSERT INTO docubricks_prod.schema_registry.extraction_prompts
                (document_type, vertical, version, is_active, preferred_model, prompt_text, updated_at)
            SELECT ?, ?, COALESCE(MAX(version), 0) + 1, true, ?, ?, NOW()
            FROM docubricks_prod.schema_registry.extraction_prompts
            WHERE document_type = ? AND vertical = ?
        """, (document_type, vertical, preferred_model, prompt_text, document_type, vertical))

# Schema management UI
st.title("Schema Prompt Manager")
prompts = list_prompts()
for p in prompts:
    with st.expander(f"{p['vertical']} / {p['document_type']}  v{p['version']}  {'🟢' if p['is_active'] else '⚪'}"):
        st.caption(f"Model: {p['preferred_model']} · Updated: {p['updated_at']}")
        if p["is_active"] and st.button("Edit active prompt", key=p["document_type"]):
            st.session_state["editing"] = p["document_type"]
```

### 10.6 Authentication & Tenant Resolution

Databricks Apps handles authentication via the workspace's identity provider (Entra ID, Okta, or Databricks-native SSO). The app receives the authenticated user's email and group memberships via request context — no separate auth layer.

```python
# apps/shared/auth.py
import os, streamlit as st
from databricks.sdk import WorkspaceClient

def get_current_user() -> dict:
    """
    Databricks Apps injects DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET
    for the app's service principal. The logged-in *user* identity is available
    via the X-Forwarded-User header (set by the Apps proxy).
    """
    user_email = st.context.headers.get("X-Forwarded-User", "")
    if not user_email:
        st.error("Could not determine user identity. Please log in via Databricks.")
        st.stop()
    return {"email": user_email}

def resolve_tenant(user_email: str) -> str:
    """Look up which tenant this user belongs to from the tenant registry."""
    conn = psycopg2.connect(os.environ["LAKEBASE_CONN"])
    with conn.cursor() as cur:
        cur.execute("""
            SELECT tenant_id FROM tenant_users
            WHERE user_email = %s AND is_active = true
        """, (user_email,))
        row = cur.fetchone()
        if not row:
            st.error("Your account is not associated with any tenant. Contact your administrator.")
            st.stop()
        return row[0]
```

Unity Catalog row-level security (see §15) enforces data isolation at the query layer — even if a bug in the app passed the wrong `tenant_id`, the RLS policy would return zero rows. Defence in depth.

### 10.7 App Deployment Pipeline

```yaml
# .github/workflows/deploy-apps.yml (or Databricks Asset Bundle equivalent)
stages:
  - name: Deploy Portal
    run: databricks apps deploy --app-name docubricks-portal
                                --source-code-path apps/portal/
                                --environment production

  - name: Deploy Review UI
    run: databricks apps deploy --app-name docubricks-review
                                --source-code-path apps/review/
                                --environment production

  - name: Deploy Admin
    run: databricks apps deploy --app-name docubricks-admin
                                --source-code-path apps/admin/
                                --environment production
```

Apps are deployed from a Databricks Asset Bundle (`databricks.yml`) alongside the DLT pipeline definitions and Workflow configurations — a single deployment artifact for the entire platform.

### 10.8 What Users Never See

The table below maps every piece of Databricks infrastructure to the app abstraction that hides it:

| Infrastructure reality | User-facing abstraction |
|---|---|
| Autoloader + DLT pipeline run | "Processing…" status indicator |
| Delta Lake Silver table query | Field values in Review UI |
| Lakebase `document_registry` poll | Real-time status badge |
| Genie Conversation API | Chat input box |
| Unity Catalog row-level security | Tenant data appears correctly filtered; user never configures it |
| MLflow accuracy metrics | "Extraction confidence" percentage |
| Vector Search similarity query | "Similar documents" section in Portal |
| Agent Bricks workflow execution | "Automate this" button action |
| DLT `reprocessing_queue` trigger | "Reprocess" button in Review UI |
| Databricks Jobs API run-now | "Process" button on upload page |
| OpenTelemetry traces + Lakehouse Monitoring | Invisible to users; visible on Admin health dashboard |

### 10.9 App Component Library

All three DocuBricks apps import from a shared internal library (`apps/lib/`). This keeps connection management, authentication, API wrappers, and UI components consistent and avoids duplication across apps.

#### Library Structure

```
apps/
└── lib/
    ├── auth.py                   # SSO identity, tenant resolution, session guard
    ├── genie.py                  # Genie Conversation API client (async, retry, streaming)
    ├── lakebase.py               # PostgreSQL connection pool + typed query helpers
    ├── sql_warehouse.py          # Databricks SQL connector with result caching
    ├── databricks_api.py         # Files API, Jobs API, Model Serving wrappers
    ├── otel.py                   # OpenTelemetry tracer + meter singletons
    ├── theme.py                  # Shared Streamlit page config, color palette, fonts
    └── components/
        ├── document_viewer.py    # Inline PDF / image renderer via Files API
        ├── confidence_badge.py   # Color-coded confidence score chip (🔴/🟡/🟢)
        ├── status_tracker.py     # Auto-polling status card (reads Lakebase)
        ├── field_editor.py       # Editable field grid for Review UI
        ├── vertical_selector.py  # Vertical + tenant picker with Genie space routing
        └── schema_diff.py        # Side-by-side prompt diff for Admin schema editor
```

#### Core shared modules

```python
# apps/lib/lakebase.py — one pool shared across all app pages via st.cache_resource
import os, psycopg2, psycopg2.pool, streamlit as st
from contextlib import contextmanager

@st.cache_resource
def _pool() -> psycopg2.pool.ThreadedConnectionPool:
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=2, maxconn=20,
        dsn=os.environ["LAKEBASE_CONN"]
    )

@contextmanager
def lakebase_conn():
    pool = _pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)

def lb_query(sql: str, params: tuple = ()) -> list[dict]:
    with lakebase_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

def lb_exec(sql: str, params: tuple = ()) -> int:
    with lakebase_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount
```

```python
# apps/lib/sql_warehouse.py — cached Databricks SQL connection
import os, streamlit as st
from databricks import sql
from functools import lru_cache

@st.cache_resource
def _wh_conn():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
        http_path=os.environ["SQL_WH_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
        session_configuration={"spark.sql.ansi.enabled": "true"}
    )

def wh_query(sql_text: str, params: tuple = ()) -> list[dict]:
    with _wh_conn().cursor() as cur:
        cur.execute(sql_text, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
```

```python
# apps/lib/components/confidence_badge.py
import streamlit as st

CONFIDENCE_THRESHOLDS = {
    "high":   (0.85, "🟢", "#e6f4ea", "#137333"),
    "medium": (0.65, "🟡", "#fef7e0", "#b06000"),
    "low":    (0.0,  "🔴", "#fce8e6", "#c5221f"),
}

def confidence_badge(score: float | None, label: str = "Confidence") -> None:
    if score is None:
        st.caption(f"{label}: —")
        return
    for tier, (threshold, emoji, bg, fg) in CONFIDENCE_THRESHOLDS.items():
        if score >= threshold:
            st.markdown(
                f'<span style="background:{bg};color:{fg};padding:2px 8px;'
                f'border-radius:99px;font-size:12px">{emoji} {score:.0%}</span>',
                unsafe_allow_html=True
            )
            return

def confidence_bar(field_scores: dict[str, float]) -> None:
    """Render a mini bar chart of per-field confidence scores."""
    import pandas as pd
    df = pd.DataFrame(
        [(k, v) for k, v in field_scores.items()],
        columns=["field", "confidence"]
    ).sort_values("confidence")
    st.bar_chart(df.set_index("field"), color="#185FA5", height=180)
```

```python
# apps/lib/components/status_tracker.py
import time, streamlit as st
from lib.lakebase import lb_query

STATUS_CONFIG = {
    "RECEIVED":    {"emoji": "📥", "color": "#5F5E5A", "done": False},
    "PARSING":     {"emoji": "⚙️", "color": "#185FA5", "done": False},
    "CLASSIFYING": {"emoji": "🔍", "color": "#185FA5", "done": False},
    "EXTRACTING":  {"emoji": "⚙️", "color": "#185FA5", "done": False},
    "VALIDATED":   {"emoji": "✅", "color": "#0F6E56", "done": False},
    "COMPLETE":    {"emoji": "🎉", "color": "#0F6E56", "done": True},
    "REVIEW":      {"emoji": "👁️", "color": "#854F0B", "done": True},
    "QUARANTINE":  {"emoji": "⚠️", "color": "#993C1D", "done": True},
    "FAILED":      {"emoji": "❌", "color": "#A32D2D", "done": True},
}

def status_tracker(document_id: str, poll_interval: float = 2.0) -> str:
    """Blocking status poller. Returns final status when terminal state reached."""
    placeholder = st.empty()
    while True:
        rows = lb_query(
            "SELECT status, document_type, extraction_conf, failure_reason "
            "FROM document_registry WHERE document_id = %s",
            (document_id,)
        )
        if not rows:
            time.sleep(poll_interval)
            continue
        info   = rows[0]
        status = info["status"]
        cfg    = STATUS_CONFIG.get(status, {"emoji": "?", "color": "#000", "done": False})
        with placeholder.container():
            col1, col2, col3 = st.columns(3)
            col1.metric("Status", f"{cfg['emoji']}  {status}")
            if info.get("document_type"):
                col2.metric("Document Type", info["document_type"])
            if info.get("extraction_conf") is not None:
                col3.metric("Confidence", f"{info['extraction_conf']:.0%}")
            if status == "FAILED" and info.get("failure_reason"):
                st.error(f"Failure reason: {info['failure_reason']}")
        if cfg["done"]:
            return status
        time.sleep(poll_interval)
```

```python
# apps/lib/theme.py — applied once at app entry point
import streamlit as st

def apply_docubricks_theme():
    st.set_page_config(
        page_title="DocuBricks",
        page_icon="🧱",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { background: #0C447C; }
    [data-testid="stSidebar"] * { color: #E6F1FB !important; }
    .stMetric label { font-size: 11px; letter-spacing: .07em; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)
```

---

## 11. Layer 8 — Orchestration

### 11.1 Workflow DAG

```
[File Arrival Trigger] ──▶ [01_ingest_to_bronze]
                                    │
                                    ▼
                           [02_parse_classify]
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
         [03_extract_fs]  [03_extract_hc]  [03_extract_legal]
                    │               │               │
                    └───────────────┴───────────────┘
                                    │
                                    ▼
                           [04_validate_silver]
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
          [05_refresh_gold]              [05_mlflow_eval]
                    │
                    ▼
        [06_refresh_vector_index]
                    │
                    ▼
        [07_notify_on_completion]
```

### 11.2 Retry & Timeout Policy

```yaml
# Databricks Workflow job configuration
tasks:
  - task_key: "03_extract_fs"
    retry_on_timeout: true
    max_retries: 3
    min_retry_interval_millis: 120000   # 2 min base
    retry_backoff_factor: 2             # 2min → 4min → 8min
    timeout_seconds: 14400              # 4 hours hard cap
    health:
      - metric: RUN_DURATION_SECONDS
        op: GREATER_THAN
        value: 10800                    # alert if > 3h (before timeout)

  - task_key: "02_parse_classify"
    retry_on_timeout: true
    max_retries: 2
    min_retry_interval_millis: 60000
    timeout_seconds: 7200
```

### 11.3 Stale State Recovery

A scheduled job (runs every 15 minutes) detects documents stuck in intermediate states:

```sql
-- Lakebase: find documents stuck in processing states
SELECT document_id, status, pipeline_run_id, received_at
FROM document_registry
WHERE status IN ('PARSING', 'CLASSIFYING', 'EXTRACTING')
  AND received_at < NOW() - INTERVAL '30 minutes'
ORDER BY received_at;
```

Stale documents are moved to `FAILED` status and added to `reprocessing_queue`. This handles the case where a Databricks job dies without completing its status update.

---

## 12. Robustness Design

### 12.1 Dead Letter Queue Strategy

Every layer has a quarantine destination. No data is silently lost.

| Layer | Failure Condition | Destination | Recovery |
|---|---|---|---|
| Landing | File is zero bytes or unreadable | `bronze_quarantine` Delta table | Manual re-upload after source fix |
| Parse | `ai_parse_document` returns error | `silver_quarantine` + Lakebase `QUARANTINE` status | Reprocess queue after model or format fix |
| Classify | Confidence < 0.70 | `silver_quarantine` + Lakebase `REVIEW` | Human classification via review UI |
| Extract | Confidence < 0.65 OR required fields null | `silver_quarantine` + Lakebase `REVIEW` | Human correction via review UI |
| Validate | DLT `expect_or_drop` violation | `silver_quarantine` with `violation_reason` | Schema fix → reprocess |

### 12.2 Circuit Breaker for AI Endpoints

The extraction tasks monitor AI endpoint error rates within each micro-batch. If error rate exceeds threshold, the task pauses and alerts — preventing runaway retries against a degraded model endpoint.

```python
def extract_with_circuit_breaker(df, schema_prompt: str, error_threshold: float = 0.05):
    results = df.withColumn("result", ai_extract(col("parsed_text"), lit(schema_prompt)))
    error_rate = results.filter("result.status = 'ERROR'").count() / results.count()

    if error_rate > error_threshold:
        # Write all rows to reprocessing_queue
        # Raise exception → Workflow marks task as FAILED → alert fires
        raise RuntimeError(
            f"AI endpoint error rate {error_rate:.1%} exceeds threshold {error_threshold:.1%}. "
            f"Circuit breaker open. {df.count()} documents queued for reprocessing."
        )
    return results
```

### 12.3 Idempotency Guarantees

| Operation | Idempotency mechanism |
|---|---|
| File landing | `ON CONFLICT (document_id) DO UPDATE` in Lakebase; file not re-written to Volume |
| Bronze write | Autoloader checkpoint + `document_id` as Delta natural key; MERGE used for any re-run |
| Silver extraction | DLT streaming with checkpoint state; replaying from checkpoint is safe |
| Gold refresh | `CREATE OR REPLACE MATERIALIZED VIEW` — always deterministic |
| Lakebase status update | `UPDATE WHERE status = 'PREVIOUS_STATE'` — transition only if in expected state |

### 12.4 Multi-Tenant Isolation

- Row-level security in Unity Catalog (see §7.6) — queries auto-filtered by `tenant_id`
- Separate Genie workspaces per tenant (larger deployments) or per vertical (shared tenants)
- Lakebase queries always parameterised with `tenant_id` — no cross-tenant data leakage possible
- Separate UC schemas per tenant available for strict isolation requirements (enterprise tier)

### 12.5 Human-in-the-Loop for Regulated Documents

For document types where accuracy SLAs are contractual (e.g., AML SARs, KYC EDD):

```
extraction_conf < 0.80 → automatic review queue entry
              < 0.65 → mandatory human review before COMPLETE status
            "PROHIBITED" risk rating in KYC → always human review regardless of confidence
```

Review UI (outside this architecture doc, but interface contracts here):
- Reads from Lakebase `review_queue` and joins Delta Silver for extracted fields
- Displays original document alongside extracted fields and confidence scores
- Human submits correction → `corrected_json` written to Lakebase
- Triggers `REPROCESS` entry → pipeline re-runs extraction with human-corrected input
- Correction stored in `extraction_audit` as ground-truth for MLflow eval

---

## 13. Performance Architecture

### 13.1 Compute Selection Matrix

| Workload | Compute Type | Rationale |
|---|---|---|
| Lakeflow / DLT pipeline | Serverless DLT compute | Auto-scaling, no cluster cold-start; Photon enabled by default |
| MLflow evaluation | Job Compute (GPU instance if fine-tuned model) | Isolated; doesn't compete with production DLT |
| Genie queries | Serverless SQL Warehouse | Auto-scales to 0; per-second billing; shared across tenants |
| Vector Search index sync | Serverless (managed by Databricks) | No user-managed cluster |
| Agent Bricks workflows | Serverless Model Serving | Pay-per-call; scales to 0 between requests |
| Lakebase | Neon serverless PostgreSQL | Auto-scales compute/storage independently |

### 13.2 Throughput Targets

| Document Volume | Strategy |
|---|---|
| < 10k docs/day | Single DLT pipeline, all extraction in one task |
| 10k–500k docs/day | Parallel extraction tasks per document type (current architecture) |
| 500k–5M docs/day | Partition extraction by tenant; multiple DLT pipelines; Autoloader maxFilesPerTrigger tuning |
| > 5M docs/day | Streaming DLT (continuous mode) + ai_extract batch inference with ONNX-optimized models |

### 13.3 Photon Acceleration

All Silver and Gold SQL operations benefit from Photon automatically on Serverless DLT. Key operations where Photon provides the largest gains:

- `ai_extract` batch calls — Photon pipelines multiple function calls
- JSON parsing (`from_json`, `get_json_object`) — Photon-native
- Aggregations in Gold materialized views — Photon vectorised aggregation
- `MERGE INTO` for idempotent writes — Photon-optimised merge

### 13.4 Query Performance for Genie

Gold materialized views are pre-joined and pre-aggregated. Genie queries should never hit Silver.

Additional optimisations on Gold tables:
```sql
-- Pre-aggregate the most common Genie query patterns
-- Tenant + time-bucket + document type
CREATE OR REPLACE MATERIALIZED VIEW docubricks_prod.gold.extraction_metrics_daily AS
SELECT
    tenant_id,
    vertical,
    document_type,
    DATE(extracted_at)              AS extraction_date,
    COUNT(*)                        AS document_count,
    AVG(avg_confidence_score)       AS avg_confidence,
    PERCENTILE_CONT(0.5) WITHIN GROUP
        (ORDER BY avg_confidence_score) AS median_confidence,
    COUNT_IF(avg_confidence_score < 0.65) AS review_required_count,
    SUM(page_count)                 AS total_pages_processed
FROM docubricks_prod.silver.silver_classified
GROUP BY 1,2,3,4;
```

The Serverless SQL Warehouse serving Genie also caches query results for 60 seconds for identical queries — high-value for shared Genie workspaces with multiple concurrent users.

### 13.5 Vector Search Performance

- Index type: **Delta Sync Index** (auto-syncs; read-optimised)
- Embedding model: `databricks-bge-large-en` (fastest Databricks-hosted option with good accuracy)
- Sync trigger: after each DLT pipeline completes (`TRIGGERED` mode) — not continuous
- Query-time filter: always include `tenant_id` filter to reduce search space

```python
results = vsc.get_index(
    endpoint_name="docubricks-vector-search",
    index_name="docubricks_prod.silver.mortgage_text_index"
).similarity_search(
    columns=["document_id", "document_type", "ingested_date"],
    query_text="mortgage application with cash-out refinance",
    filters={"tenant_id": current_tenant_id},    # mandatory; drives index pruning
    num_results=10
)
```

---

## 14. Durability Guarantees

### 14.1 Delta Lake ACID Guarantees

All Silver and Gold tables use Delta Lake's optimistic concurrency control:

- **Atomicity:** DLT tasks write entire micro-batches atomically. A partial batch leaves no orphaned rows.
- **Consistency:** DLT expectations enforce schema and quality constraints before commit.
- **Isolation:** Concurrent reads always see a consistent snapshot. Writers do not block readers.
- **Durability:** Delta transaction log is backed by cloud object storage (S3/ADLS/GCS) — same durability SLA as the underlying cloud (99.999999999% for S3).

### 14.2 Autoloader Checkpoint Durability

Autoloader checkpoints are stored in Unity Catalog Volumes (backed by cloud object storage):
```
/Volumes/docubricks_prod/checkpoints/
  autoloader_bronze/
  dlt_silver_parsed/
  dlt_silver_classified/
  dlt_silver_extracted_{document_type}/
```

Checkpoint loss would cause Autoloader to reprocess files — harmless given idempotent design, but expensive. Mitigations:
- Checkpoints stored in a **separate storage account** from raw data (different failure domain)
- Databricks workspace cross-region replication (enterprise)
- Checkpoint directories **never** vacuumed or deleted by automation

### 14.3 Lakebase (PostgreSQL) Durability

Lakebase uses Neon's architecture:
- **Write-ahead log (WAL):** all writes are WAL-persisted before acknowledged
- **WAL archiving:** archived to cloud storage continuously — point-in-time recovery to any second within the retention window
- **Branching:** Lakebase supports instant database branches — use this for pre-migration testing without touching production data
- **Automated backups:** daily full backup + continuous WAL archiving = RPO < 1 minute

Lakebase recovery targets:

| Scenario | Recovery Mechanism | RTO |
|---|---|---|
| Single query corruption | ROLLBACK (in-flight) | Immediate |
| Accidental table truncation | Point-in-time restore | < 30 min |
| Regional outage | Failover to standby (enterprise) | < 15 min |
| Schema migration failure | Restore from pre-migration branch | < 10 min |

### 14.4 Time Travel Policy

| Table Tier | Log Retention | Deleted File Retention | Purpose |
|---|---|---|---|
| Bronze | 90 days | 90 days | Full re-extraction window |
| Silver | 30 days | 30 days | Correction and audit window |
| Gold | 14 days | 14 days | Business query point-in-time |
| Schema registry | 365 days | 365 days | Full prompt version history |

```sql
-- Verify time travel is working; run this weekly in ops checks
SELECT
    version,
    timestamp,
    operation,
    operationMetrics.numOutputRows AS rows_written
FROM (DESCRIBE HISTORY docubricks_prod.silver.extracted_mortgage_application)
LIMIT 20;
```

### 14.5 UC Volume Raw File Archive

Raw document bytes are retained in UC Volumes with a lifecycle policy:
- **Hot tier (0–30 days):** Standard storage — fast re-read for reprocessing
- **Cool tier (31–90 days):** Infrequent access storage — reprocessing still possible
- **Archive tier (91–365 days):** For compliance retention; reprocessing requires restore (hours)
- **Delete (365+ days):** Unless legal hold is active in `document_registry.legal_hold = true`

```python
# Set legal hold before any scheduled deletion sweep
with get_conn() as conn:
    conn.execute("""
        UPDATE document_registry
           SET legal_hold = true, legal_hold_reason = $1
         WHERE document_id = ANY($2::text[])
    """, (reason, document_ids))
```

---

## 15. Security & Governance

### 15.1 Credential Management

| Secret | Storage | Access pattern |
|---|---|---|
| Lakebase connection string | Databricks Secret Scope | `dbutils.secrets.get()` in Jobs only; never in notebooks |
| Source system API keys (SharePoint, ECM) | Databricks Secret Scope per connector | Lakeflow Connect managed; key rotated via connector config |
| Foundation Model API (if external) | Databricks Secret Scope | Used only if FMAPI doesn't cover the required model |
| Unity Catalog service principal | Databricks service principal + Entra/IAM role | Workspace-level; no personal credentials in pipelines |

### 15.2 Data Classification

Every table column carries a Unity Catalog `tag` for data classification:

```sql
ALTER TABLE docubricks_prod.silver.extracted_kyc_cdd_form
    ALTER COLUMN taxpayer_id    SET TAGS ('pii' = 'true', 'classification' = 'government_id');
ALTER TABLE docubricks_prod.silver.extracted_kyc_cdd_form
    ALTER COLUMN ssn_masked     SET TAGS ('pii' = 'true', 'classification' = 'ssn');
ALTER TABLE docubricks_prod.silver.extracted_mortgage_application
    ALTER COLUMN loan_amount    SET TAGS ('classification' = 'financial');
ALTER TABLE docubricks_prod.silver.extracted_mortgage_application
    ALTER COLUMN ethnicity_code SET TAGS ('classification' = 'government_monitoring',
                                          'access_restriction' = 'fair_lending_only');
```

Column tags drive automated access control decisions and are queryable via Unity Catalog's information schema for compliance reporting.

### 15.3 Audit Logging

Unity Catalog automatically generates audit logs for all data access events. These are delivered to a Delta table in a designated audit catalog:

```sql
-- Audit log destination (configured in workspace settings)
-- docubricks_audit.system.access

-- Sample audit query: who accessed KYC data in the last 24 hours
SELECT
    event_time, user_identity.email, request_params.table_full_name,
    request_params.operation_type
FROM docubricks_audit.system.access
WHERE event_time > NOW() - INTERVAL '24 hours'
  AND request_params.table_full_name LIKE '%kyc%'
ORDER BY event_time DESC;
```

### 15.4 Network Security

- All compute runs inside the customer's Databricks workspace VPC
- No internet egress from DLT pipelines — all AI calls go through Databricks Foundation Model API within the security boundary
- Lakebase: private endpoint within the workspace network; no public internet access
- UC Volumes: private bucket endpoint; no public bucket access

---

## 16. Schema Extension Pattern

Adding a new vertical (e.g., Real Estate) or a new document type within an existing vertical follows a strict protocol. No schema change requires modifying DLT pipeline code.

### Step 1 — Register the New Document Type

```sql
-- schema_registry.document_type_labels
INSERT INTO docubricks_prod.schema_registry.document_type_labels VALUES
('purchase_agreement', 'real_estate', true, NOW(), 'v1.0');
```

### Step 2 — Create the Extraction Prompt

```sql
-- schema_registry.extraction_prompts
INSERT INTO docubricks_prod.schema_registry.extraction_prompts VALUES
(
    'purchase_agreement',
    'real_estate',
    1,            -- version
    true,         -- is_active
    'databricks-claude-sonnet',  -- preferred model
    '{{prompt_text_here}}',
    NOW()
);
```

The classifier's label list is dynamically built from `document_type_labels` — no code change required.

### Step 3 — Define the Silver Table

```sql
CREATE TABLE IF NOT EXISTS docubricks_prod.silver.extracted_purchase_agreement (
    document_id             STRING      NOT NULL,
    tenant_id               STRING      NOT NULL,
    -- ... domain-specific fields from real estate purchase agreement schema
    purchase_price          DECIMAL(18,2),
    property_address        STRING,
    closing_date            DATE,
    contingencies           ARRAY<STRING>,
    earnest_money_amount    DECIMAL(18,2),
    extracted_json          STRING,     -- full JSON for fields not promoted to columns
    avg_confidence_score    DOUBLE,
    extracted_at            TIMESTAMP
)
CLUSTER BY (tenant_id, ingested_date)
TBLPROPERTIES (
    'delta.enableChangeDataFeed'   = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'quality'                      = 'silver',
    'docubricks.document_type'     = 'purchase_agreement'
);
```

### Step 4 — Add DLT Task

A single new DLT streaming table is added using the generic extraction pattern (§5.3). The Workflow DAG is updated to include this task in the parallel extraction group.

### Step 5 — Add Gold View + Genie Seed Questions

```sql
CREATE OR REPLACE MATERIALIZED VIEW docubricks_prod.gold.real_estate_portfolio AS ...
```

Register seed questions in the Genie workspace. New vertical is live.

**Total time to add a new document type:** schema expert + 1 engineer, 1–2 weeks (prompt engineering + validation + Gold view + Genie setup). No DLT pipeline code changes to existing tasks.

---

## 17. Operational Runbook

### 17.1 Daily Health Checks

Run via a scheduled Databricks Job (5 AM UTC):

```python
checks = {
    "quarantine_rate":
        "SELECT COUNT(*) / total FROM silver_quarantine WHERE DATE(quarantined_at) = CURRENT_DATE()",
    "avg_confidence_24h":
        "SELECT AVG(avg_confidence_score) FROM silver.extracted_* WHERE extracted_at > NOW() - INTERVAL '24 hours'",
    "stale_processing_docs":
        # Lakebase: docs stuck > 30min in intermediate states
    "review_queue_sla_breach":
        # Lakebase: review_queue WHERE sla_due_at < NOW() AND resolved_at IS NULL
    "vector_index_lag":
        # Vector Search: check index sync timestamp vs last DLT completion
}
```

Alert thresholds (PagerDuty / Slack webhook via Databricks notification):

| Metric | Warning | Critical |
|---|---|---|
| Quarantine rate | > 5% of daily volume | > 15% of daily volume |
| Avg confidence | < 0.78 | < 0.70 |
| Review queue SLA breach | Any | > 10 items |
| Stale processing docs | > 5 docs > 1h | > 1 doc > 4h |
| DLT pipeline duration | > 2h | > 3.5h (pre-timeout alert) |

### 17.2 Reprocessing a Batch

```python
# Trigger reprocessing of all documents from a specific date + tenant
def reprocess_batch(tenant_id: str, date: str, reason: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO reprocessing_queue (document_id, reason, queued_at)
            SELECT document_id, $1, NOW()
            FROM document_registry
            WHERE tenant_id = $2
              AND DATE(received_at) = $3::date
              AND status NOT IN ('QUARANTINE')
            ON CONFLICT DO NOTHING
        """, (reason, tenant_id, date))
    # Trigger Workflow run targeting only reprocessing_queue items
    trigger_reprocess_workflow()
```

### 17.3 Schema Prompt Rollback

```sql
-- Deactivate a problematic prompt version
UPDATE docubricks_prod.schema_registry.extraction_prompts
   SET is_active = false
 WHERE document_type = 'mortgage_application' AND version = 5;

-- Reactivate previous version
UPDATE docubricks_prod.schema_registry.extraction_prompts
   SET is_active = true
 WHERE document_type = 'mortgage_application' AND version = 4;
```

Next pipeline run automatically picks up v4. Documents extracted with v5 are added to `reprocessing_queue` via:
```sql
INSERT INTO reprocessing_queue (document_id, reason, target_version)
SELECT document_id, 'SCHEMA_VERSION_ROLLBACK', '4'
FROM document_registry
WHERE document_type = 'mortgage_application'
  AND pipeline_run_id IN (
      SELECT job_run_id FROM processing_jobs
      WHERE schema_version_used = '5'
  );
```

---

## 18. Known Failure Modes & Mitigations

| Failure Mode | Probability | Impact | Detection | Mitigation |
|---|---|---|---|---|
| `ai_parse_document` returns partial text for complex multi-page PDFs | Medium | Wrong extractions downstream | Confidence < threshold; page count mismatch | Retry with higher resolution; flag for human review |
| `ai_classify` assigns wrong document type | Medium | Extractions run against wrong schema | MLflow eval accuracy drop; user report | Classification confidence threshold + human review queue |
| Lakebase connection exhaustion under burst load | Low | Status updates fail; documents stuck in intermediate states | Connection pool metrics; stale state monitor | PgBouncer connection pooling; `max_retries` in connection code |
| Delta table `OPTIMIZE` lock contention | Low | Slow queries temporarily | Slow Genie response; query timeout | Schedule OPTIMIZE during off-peak; `delta.autoOptimize` instead |
| Databricks ships a breaking change to `ai_extract` API | Medium | All extraction fails | Pipeline failure alert | Version-lock the function; abstract behind a wrapper; test in staging before workspace upgrade |
| Schema prompt token limit exceeded for long documents | Medium | Truncated extraction | `parse_error` field populated; low confidence | Chunk document; extract per-section; merge results |
| UC Volume regional outage | Very low | Ingestion halts | Pipeline failure alert | Multi-region Volume replication (enterprise); graceful degradation — queue incoming files, process on recovery |
| Databricks Apps cold start on first user request | Low | 3–8 second delay for first page load | User-visible latency | Keep-alive ping from health-check endpoint; Streamlit `st.cache_resource` for connection objects |
| Apps service principal token expiration | Low | All app API calls fail with 401 | App error page visible to users | Use OAuth M2M with short-lived tokens; Apps runtime auto-refreshes on each request |
| Genie Conversation API rate limit hit | Medium (shared tenant) | Chat widget returns error | 429 response from Genie API | Per-tenant rate limit enforcement in app; exponential backoff with user-visible "Genie is busy" message |
| Document upload > 50 MB via Files API | Medium | API rejects with 413 | HTTP error on upload | Client-side file size check before upload; server-side chunked upload for large files; 100 MB hard cap |
| Review queue SLA breach (no reviewer assigned) | Medium | Regulated document stuck without human sign-off | Lakebase `sla_due_at < NOW()` monitor | Auto-escalation to team lead after 4h; Admin app shows SLA breach dashboard; PagerDuty alert |

---

## 19. Capacity Planning

### 19.1 Storage Growth Model

| Tier | Size per document (avg) | 100k docs/day | 1M docs/day |
|---|---|---|---|
| UC Volume (raw bytes) | 2 MB | 200 GB/day | 2 TB/day |
| Bronze (raw + metadata) | 2.1 MB | 210 GB/day | 2.1 TB/day |
| Silver parsed text | 50 KB | 5 GB/day | 50 GB/day |
| Silver extracted JSON | 10 KB | 1 GB/day | 10 GB/day |
| Gold aggregated views | < 1 MB total | Negligible | Negligible |
| Vector Search index | ~1 KB/doc | 100 MB/day | 1 GB/day |
| Lakebase operational tables | ~5 KB/doc | 500 MB/day | 5 GB/day |

**Practical budget:** at 100k documents/day, total storage growth is ~220 GB/day before compression. Delta Lake typically achieves 3–5× compression on columnar data (Silver/Gold). Raw bytes in UC Volume compress to ~40% original size with Parquet/ZSTD at rest.

### 19.2 Compute Cost Drivers

| Cost driver | Optimization lever |
|---|---|
| `ai_parse_document` calls | Deduplicate before parsing — never parse the same `document_id` twice |
| `ai_extract` calls | Batch extraction across micro-batches; model-agnostic selection (cheapest capable model) |
| Serverless DLT compute | Minimize data shuffles; cluster-by keys aligned with filter patterns |
| Vector Search sync | `TRIGGERED` mode (not continuous) — sync only after each pipeline batch |
| Lakebase compute | Scale to 0 between batch windows; right-size connection pool |

### 19.3 Scaling Thresholds

| Metric | Current architecture handles | Scale action |
|---|---|---|
| Documents per day | Up to 500k | Add parallel extraction tasks per tenant |
| Tenants | Up to 500 (shared Silver schema with RLS) | Dedicate schemas per tenant above 500 |
| Page count per document | Up to 200 pages | Chunked parsing for > 200 pages |
| Concurrent Genie users | Up to 50 (auto-scale SQL warehouse) | Add cluster size tiers |
| Vector Search queries/sec | Up to 1,000 QPS per endpoint | Add endpoint replicas |

---

## 20. Observability

Observability operates at two distinct layers: **application observability** (what is the app doing, who is using it, where is it slow) via OpenTelemetry, and **data observability** (is the extracted data healthy, is confidence drifting, are tables growing as expected) via Databricks Lakehouse Monitoring and System Tables.

### 20.1 OpenTelemetry Instrumentation (Application Layer)

All three DocuBricks apps share a single OTel setup from `apps/lib/otel.py`. Traces cover the full document journey from upload click to terminal pipeline state. Metrics cover throughput, confidence distributions, and queue depths.

```python
# apps/lib/otel.py
import os, streamlit as st
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

@st.cache_resource
def _setup_otel():
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")

    tp = TracerProvider()
    if endpoint:
        tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(tp)

    mp = MeterProvider(metric_readers=[
        PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=endpoint) if endpoint else None,
            export_interval_millis=30_000
        )
    ] if endpoint else [])
    metrics.set_meter_provider(mp)

_setup_otel()
tracer = trace.get_tracer("docubricks")
meter  = metrics.get_meter("docubricks")

# ── Instruments ──────────────────────────────────────────────────────────────
docs_uploaded = meter.create_counter(
    "docubricks.documents.uploaded",
    unit="1", description="Documents submitted for processing"
)
processing_duration = meter.create_histogram(
    "docubricks.processing.duration_seconds",
    unit="s", description="Wall-clock time from upload to COMPLETE/FAILED"
)
extraction_confidence = meter.create_histogram(
    "docubricks.extraction.confidence",
    unit="1", description="Per-document average extraction confidence score"
)
review_queue_depth = meter.create_up_down_counter(
    "docubricks.review_queue.depth",
    unit="1", description="Documents currently awaiting human review"
)
genie_latency = meter.create_histogram(
    "docubricks.genie.response_seconds",
    unit="s", description="Genie Conversation API round-trip latency"
)
```

#### Tracing the document journey end-to-end

```python
# apps/portal/upload.py — annotated upload flow
import time
from lib.otel import tracer, docs_uploaded, processing_duration, extraction_confidence

def upload_and_process(file_bytes: bytes, tenant_id: str,
                        vertical: str, file_ext: str) -> str:
    document_id = compute_document_id(file_bytes)
    t0 = time.monotonic()

    with tracer.start_as_current_span("docubricks.upload") as span:
        span.set_attribute("document.id",          document_id)
        span.set_attribute("document.tenant_id",   tenant_id)
        span.set_attribute("document.vertical",    vertical)
        span.set_attribute("document.size_bytes",  len(file_bytes))

        with tracer.start_as_current_span("docubricks.volume_write"):
            path = upload_to_volume(file_bytes, document_id, tenant_id, vertical, file_ext)

        with tracer.start_as_current_span("docubricks.registry_write"):
            dup = register_in_lakebase(document_id, path, tenant_id, vertical,
                                       len(file_bytes), document_id)

        if dup > 0:
            span.set_attribute("document.duplicate", True)
            return document_id          # skip pipeline trigger for duplicates

        with tracer.start_as_current_span("docubricks.pipeline_trigger"):
            run_id = trigger_pipeline(document_id, tenant_id)
            span.set_attribute("pipeline.run_id", run_id)

    docs_uploaded.add(1, {"tenant_id": tenant_id, "vertical": vertical,
                          "file_ext": file_ext})

    # Non-blocking: record duration + confidence once processing completes
    final_status = status_tracker(document_id)          # polls Lakebase
    processing_duration.record(
        time.monotonic() - t0,
        {"tenant_id": tenant_id, "vertical": vertical, "status": final_status}
    )
    conf_row = lb_query(
        "SELECT extraction_conf FROM document_registry WHERE document_id = %s",
        (document_id,)
    )
    if conf_row and conf_row[0]["extraction_conf"] is not None:
        extraction_confidence.record(
            float(conf_row[0]["extraction_conf"]),
            {"tenant_id": tenant_id, "vertical": vertical}
        )
    return document_id
```

OTel backend options (configure via `OTEL_EXPORTER_OTLP_ENDPOINT` secret):
- **Grafana Cloud** — native OTel ingestion; Tempo for traces, Prometheus for metrics
- **Datadog** — OTel collector sidecar in Databricks workspace
- **Databricks itself** — write spans/metrics to a Gold Delta table via a custom OTel exporter (no external dependency)

### 20.2 Databricks Lakehouse Monitoring (Data Layer)

Lakehouse Monitoring automatically profiles Silver extraction tables over time. It detects confidence score drift, null rate increases, and schema changes — the first signs that an extraction schema or model is degrading.

```python
# scripts/setup_lakehouse_monitoring.py
# Run once per document type at schema onboarding time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import (
    MonitorTimeSeries, MonitorInferenceLog, MonitorSnapshot
)

w = WorkspaceClient()

MONITORED_TABLES = [
    # (table_name, timestamp_col, label_col, prediction_col)
    ("docubricks_prod.silver.extracted_mortgage_application",
     "extracted_at", None, "avg_confidence_score"),
    ("docubricks_prod.silver.extracted_kyc_cdd_form",
     "extracted_at", None, "avg_confidence_score"),
    ("docubricks_prod.silver.extracted_aml_sar",
     "extracted_at", None, "avg_confidence_score"),
]

for table_name, ts_col, label_col, pred_col in MONITORED_TABLES:
    short_name = table_name.split(".")[-1]
    w.quality_monitors.create(
        table_name=table_name,
        assets_dir=f"/Volumes/docubricks_prod/monitoring/{short_name}",
        output_schema_name="docubricks_prod.monitoring",
        time_series=MonitorTimeSeries(
            timestamp_col=ts_col,
            granularities=["1 hour", "1 day", "1 week"]
        ),
        # If we have ground truth labels, use InferenceLog for accuracy tracking
        inference_log=MonitorInferenceLog(
            timestamp_col=ts_col,
            prediction_col=pred_col,
            problem_type="PROBLEM_TYPE_REGRESSION"
        ) if label_col else None,
        skip_builtin_dashboard=False   # auto-create Databricks dashboard
    )
```

Lakehouse Monitoring outputs two tables per monitored table:

| Output table | Contains |
|---|---|
| `docubricks_prod.monitoring.{table}_profile_metrics` | Column-level statistics (mean, stddev, null %, quantiles) per time window |
| `docubricks_prod.monitoring.{table}_drift_metrics` | Statistical drift scores (KS test, chi-square) vs. baseline window |

**Alert on confidence drift:**
```python
# Databricks Workflows task: runs after each DLT pipeline batch
def check_confidence_drift(document_type: str, drift_threshold: float = 0.15):
    rows = wh_query(f"""
        SELECT drift_type, column_name, drift_score
        FROM docubricks_prod.monitoring.extracted_{document_type}_drift_metrics
        WHERE window_end_time = (
            SELECT MAX(window_end_time)
            FROM docubricks_prod.monitoring.extracted_{document_type}_drift_metrics
        )
          AND column_name = 'avg_confidence_score'
          AND drift_score > {drift_threshold}
    """)
    if rows:
        # Write alert to Lakebase + trigger Slack/PagerDuty
        for row in rows:
            lb_exec("""
                INSERT INTO monitoring_alerts (document_type, alert_type, drift_score, created_at)
                VALUES (%s, 'CONFIDENCE_DRIFT', %s, NOW())
            """, (document_type, row["drift_score"]))
        raise RuntimeError(
            f"Confidence drift detected for {document_type}: "
            f"{rows[0]['drift_score']:.3f} > threshold {drift_threshold}"
        )
```

### 20.3 DLT Event Log (Pipeline Health)

```sql
-- Real-time pipeline health — queryable from Genie
SELECT
    timestamp,
    event_type,
    origin.flow_name                        AS pipeline_stage,
    details:num_output_rows::INT            AS rows_written,
    details:num_affected_rows::INT          AS rows_quarantined,
    details:expectation_results             AS dq_results
FROM event_log("docubricks_prod.bronze.bronze_documents")
WHERE timestamp > NOW() - INTERVAL '24 hours'
  AND event_type IN ('FLOW_PROGRESS', 'METRICS')
ORDER BY timestamp DESC;
```

### 20.4 Databricks System Tables (Built-in Observability)

System tables provide billing, access audit, and lakeflow history without any setup.

```sql
-- AI function cost tracking — critical for margin management
SELECT
    sku_name,
    DATE(usage_date)              AS date,
    SUM(usage_quantity)           AS dbus,
    SUM(usage_quantity * list_price) AS estimated_cost_usd
FROM system.billing.usage
WHERE sku_name LIKE '%AI%'
  AND usage_date > CURRENT_DATE - 30
GROUP BY 1, 2
ORDER BY 2 DESC, 4 DESC;

-- Per-tenant data access audit
SELECT
    DATE(event_time)              AS date,
    request_params.table_full_name AS table_name,
    COUNT(DISTINCT user_identity.email) AS unique_users,
    COUNT(*)                      AS query_count
FROM system.access.audit
WHERE service_name = 'dataAccess'
  AND request_params.table_full_name LIKE 'docubricks_prod%'
  AND event_time > NOW() - INTERVAL '7 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 4 DESC;

-- Lakeflow pipeline run history
SELECT
    pipeline_id, run_id,
    start_time, end_time,
    DATEDIFF(SECOND, start_time, end_time) AS duration_sec,
    state, cause
FROM system.lakeflow.pipeline_events
WHERE pipeline_id = :pipeline_id
ORDER BY start_time DESC
LIMIT 50;
```

### 20.5 Unified Observability Gold View

All observability signals converge in a single Gold materialized view, queryable from the Admin app and from Genie:

```sql
CREATE OR REPLACE MATERIALIZED VIEW docubricks_prod.gold.platform_health AS
WITH extraction_stats AS (
    SELECT
        DATE(extracted_at)      AS date,
        tenant_id,
        vertical,
        document_type,
        COUNT(*)                AS docs_processed,
        AVG(avg_confidence_score) AS avg_confidence,
        PERCENTILE_CONT(0.05) WITHIN GROUP
            (ORDER BY avg_confidence_score) AS p5_confidence,
        COUNT_IF(avg_confidence_score < 0.65) AS review_count,
        COUNT_IF(avg_confidence_score IS NULL) AS failed_count
    FROM docubricks_prod.silver.silver_classified
    WHERE extracted_at > NOW() - INTERVAL '90 days'
    GROUP BY 1, 2, 3, 4
),
queue_stats AS (
    -- Read from Lakebase via external table or scheduled sync
    SELECT
        DATE(created_at)       AS date,
        tenant_id,
        COUNT(*)               AS items_queued,
        COUNT_IF(resolved_at IS NOT NULL) AS items_resolved,
        AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0)
                               AS avg_resolution_hours
    FROM docubricks_prod.monitoring.review_queue_snapshot  -- daily Lakebase snapshot
    GROUP BY 1, 2
)
SELECT
    e.date, e.tenant_id, e.vertical, e.document_type,
    e.docs_processed, e.avg_confidence, e.p5_confidence,
    e.review_count, e.failed_count,
    q.items_queued, q.items_resolved, q.avg_resolution_hours
FROM extraction_stats e
LEFT JOIN queue_stats q
    ON e.date = q.date AND e.tenant_id = q.tenant_id;
```

---

## 21. Schema Library

The schema library is the primary IP asset of DocuBricks. It is an engineered system, not a folder of text files. It has versioning, inheritance, a promotion gate, a test harness, and a changelog — the same disciplines applied to production code.

### 21.1 Full Schema Registry Structure

```
docubricks_prod.schema_registry
├── extraction_prompts          — versioned prompt templates (active flag)
├── document_type_labels        — classification label registry
├── validation_rules            — per-field validation expressions
├── field_confidence_thresholds — minimum acceptable confidence per field
├── schema_inheritance          — parent–child schema relationships
├── schema_test_cases           — golden test documents + expected output
├── schema_changelog            — every version change with rationale
└── schema_model_routing        — preferred model per document type
```

### 21.2 Schema Inheritance

Complex verticals share common structure. Rather than duplicating prompts, child schemas extend parent schemas:

```sql
CREATE TABLE docubricks_prod.schema_registry.schema_inheritance (
    child_document_type   TEXT NOT NULL,
    parent_document_type  TEXT NOT NULL,
    inheritance_mode      TEXT NOT NULL DEFAULT 'EXTENDS',
    -- EXTENDS: parent prompt prefix + child suffix (additive)
    -- SPECIALISES: child replaces parent for this doc type only
    override_fields       ARRAY<STRING>,  -- fields where child overrides parent default
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    PRIMARY KEY (child_document_type, parent_document_type)
);

-- Example: KYC EDD extends standard KYC CDD
INSERT INTO docubricks_prod.schema_registry.schema_inheritance VALUES
('kyc_edd_form', 'kyc_cdd_form', 'EXTENDS',
 ARRAY['sourceOfFunds', 'sourceOfWealth', 'eddTriggers'], NOW());

-- AML SAR has its own chain
INSERT INTO docubricks_prod.schema_registry.schema_inheritance VALUES
('aml_sar_filing', 'kyc_cdd_form', 'SPECIALISES',
 ARRAY['screening', 'regulatoryReports', 'cases'], NOW());
```

The extraction task resolves the inheritance chain at runtime:

```python
def resolve_prompt(document_type: str, version: int | None = None) -> str:
    """Walk inheritance chain and compose the full extraction prompt."""
    rows = wh_query("""
        WITH RECURSIVE chain AS (
            SELECT child_document_type, parent_document_type, inheritance_mode, 0 AS depth
            FROM docubricks_prod.schema_registry.schema_inheritance
            WHERE child_document_type = ?
            UNION ALL
            SELECT i.child_document_type, i.parent_document_type, i.inheritance_mode, c.depth + 1
            FROM docubricks_prod.schema_registry.schema_inheritance i
            JOIN chain c ON i.child_document_type = c.parent_document_type
        )
        SELECT p.prompt_text, c.inheritance_mode, c.depth
        FROM chain c
        JOIN docubricks_prod.schema_registry.extraction_prompts p
            ON p.document_type = c.child_document_type
           AND p.is_active = true
        ORDER BY c.depth DESC          -- deepest ancestor first
    """, (document_type,))

    composed = ""
    for row in rows:
        if row["inheritance_mode"] == "EXTENDS":
            composed = composed + "\n\n" + row["prompt_text"]
        else:  # SPECIALISES — replace entirely
            composed = row["prompt_text"]
    return composed.strip()
```

### 21.3 Per-Field Confidence Thresholds

Different fields carry different accuracy requirements. A mortgage `loan_amount` must be near-perfect; a `preferred_communication_method` can tolerate lower confidence.

```sql
CREATE TABLE docubricks_prod.schema_registry.field_confidence_thresholds (
    document_type        TEXT    NOT NULL,
    field_name           TEXT    NOT NULL,
    min_confidence       NUMERIC(4,3) NOT NULL DEFAULT 0.650,
    review_on_breach     BOOLEAN NOT NULL DEFAULT TRUE,
    fail_on_breach       BOOLEAN NOT NULL DEFAULT FALSE,  -- hard fail vs soft review
    regulatory_required  BOOLEAN NOT NULL DEFAULT FALSE,  -- BSA/HMDA/HL7 mandated field
    PRIMARY KEY (document_type, field_name)
);

-- FS: mortgage application field thresholds
INSERT INTO docubricks_prod.schema_registry.field_confidence_thresholds VALUES
('mortgage_application', 'loan_amount',            0.950, true,  true,  true),
('mortgage_application', 'debt_to_income_ratio',   0.900, true,  false, true),
('mortgage_application', 'borrower_name',           0.900, true,  false, true),
('mortgage_application', 'loan_purpose',            0.850, true,  false, true),
('mortgage_application', 'property_address',        0.850, true,  false, false),
('mortgage_application', 'credit_score',            0.950, true,  true,  true),
('mortgage_application', 'occupancy_type',          0.800, false, false, false);

-- FS: KYC CDD field thresholds (stricter — BSA/AML mandated)
INSERT INTO docubricks_prod.schema_registry.field_confidence_thresholds VALUES
('kyc_cdd_form', 'taxpayer_id',           0.990, true,  true,  true),
('kyc_cdd_form', 'beneficial_ownership',  0.950, true,  true,  true),
('kyc_cdd_form', 'pep_status',            0.950, true,  true,  true),
('kyc_cdd_form', 'customer_type',         0.900, true,  false, true),
('kyc_cdd_form', 'sanctions_screening',   0.990, true,  true,  true);
```

The DLT extraction task reads these thresholds dynamically and applies them as `expect_or_drop` conditions:

```python
def build_field_expectations(document_type: str) -> list[tuple[str, str]]:
    """Return (expectation_name, sql_expression) pairs from the threshold registry."""
    thresholds = wh_query("""
        SELECT field_name, min_confidence, fail_on_breach
        FROM docubricks_prod.schema_registry.field_confidence_thresholds
        WHERE document_type = ?
    """, (document_type,))

    expectations = []
    for t in thresholds:
        fn    = t["field_name"]
        conf  = t["min_confidence"]
        # field_confidences is a MAP<STRING, DOUBLE> column in Silver extraction tables
        expr  = f"COALESCE(field_confidences['{fn}'], 0.0) >= {conf}"
        name  = f"confidence_{fn}"
        expectations.append((name, expr, t["fail_on_breach"]))
    return expectations
```

### 21.4 Schema Test Harness (Promotion Gate)

A schema version cannot be marked `is_active = true` until it passes the golden test set for that document type. The test harness is a Databricks Workflow task that runs automatically when a new version is inserted.

```python
# scripts/schema_test_harness.py
import mlflow
from lib.sql_warehouse import wh_query
from lib.lakebase import lb_exec

def run_schema_tests(document_type: str, candidate_version: int) -> bool:
    """
    Run candidate schema against the golden test set.
    Returns True if accuracy >= promotion threshold.
    """
    golden_docs = wh_query("""
        SELECT parsed_text, expected_json, test_case_id
        FROM docubricks_prod.schema_registry.schema_test_cases
        WHERE document_type = ? AND is_active = true
    """, (document_type,))

    if not golden_docs:
        raise ValueError(f"No golden test cases found for {document_type}. "
                         "Add at least 20 labeled documents before promoting a schema.")

    prompt = resolve_prompt(document_type, version=candidate_version)
    results = []

    with mlflow.start_run(
        experiment_name=f"/docubricks/schema-tests/{document_type}",
        run_name=f"v{candidate_version}_promotion_gate"
    ):
        for doc in golden_docs:
            extracted = call_ai_extract(doc["parsed_text"], prompt)
            accuracy  = compute_field_accuracy(extracted, doc["expected_json"])
            results.append(accuracy)
            mlflow.log_metric(f"field_accuracy_{doc['test_case_id']}", accuracy)

        avg_accuracy = sum(results) / len(results)
        mlflow.log_metric("avg_field_accuracy", avg_accuracy)
        mlflow.log_metric("test_cases_run",     len(results))
        mlflow.log_param("document_type",       document_type)
        mlflow.log_param("schema_version",      candidate_version)

        threshold = 0.85
        passed    = avg_accuracy >= threshold
        mlflow.log_metric("passed", int(passed))

    # Record result in schema changelog
    lb_exec("""
        INSERT INTO schema_changelog
            (document_type, version, change_type, changed_by, change_reason,
             accuracy_after, changed_at)
        VALUES (%s, %s, %s, 'schema_test_harness', %s, %s, NOW())
    """, (
        document_type, candidate_version,
        "PROMOTED" if passed else "PROMOTION_FAILED",
        f"Avg field accuracy: {avg_accuracy:.3f} ({'PASS' if passed else 'FAIL'}, threshold {threshold})",
        avg_accuracy
    ))

    if passed:
        # Deactivate previous version, activate new
        lb_exec("""
            UPDATE schema_registry.extraction_prompts
               SET is_active = false
             WHERE document_type = %s AND is_active = true
        """, (document_type,))
        lb_exec("""
            UPDATE schema_registry.extraction_prompts
               SET is_active = true
             WHERE document_type = %s AND version = %s
        """, (document_type, candidate_version))

    return passed
```

### 21.5 Schema Changelog

Every schema state change — creation, promotion, rollback, deprecation — is recorded with the actor, reason, and accuracy delta.

```sql
CREATE TABLE docubricks_prod.schema_registry.schema_changelog (
    change_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type    TEXT        NOT NULL,
    version          INT         NOT NULL,
    change_type      TEXT        NOT NULL,
    -- CREATED | PROMOTED | PROMOTION_FAILED | ROLLED_BACK | DEPRECATED | MANUALLY_ACTIVATED
    changed_by       TEXT        NOT NULL,
    change_reason    TEXT,
    accuracy_before  NUMERIC(5,4),
    accuracy_after   NUMERIC(5,4),
    mlflow_run_id    TEXT,       -- link to the evaluation run
    changed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_change_type CHECK (change_type IN (
        'CREATED','PROMOTED','PROMOTION_FAILED','ROLLED_BACK',
        'DEPRECATED','MANUALLY_ACTIVATED'
    ))
);
```

### 21.6 Schema Model Routing

Different document types perform best with different foundation models. This is configured per document type, not in code.

```sql
CREATE TABLE docubricks_prod.schema_registry.schema_model_routing (
    document_type      TEXT    PRIMARY KEY,
    preferred_model    TEXT    NOT NULL,
    -- 'databricks-claude-sonnet'  — complex legal/regulatory reasoning
    -- 'databricks-dbrx-instruct'  — fast general extraction
    -- 'databricks-gemini-flash'   — multimodal (tables, images, stamps)
    -- 'docubricks-acord-extractor' — fine-tuned for ACORD claims forms
    fallback_model     TEXT    NOT NULL DEFAULT 'databricks-dbrx-instruct',
    max_tokens         INT     NOT NULL DEFAULT 4096,
    temperature        NUMERIC(3,2) NOT NULL DEFAULT 0.0,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO docubricks_prod.schema_registry.schema_model_routing VALUES
('mortgage_application', 'databricks-dbrx-instruct',  'databricks-claude-sonnet', 4096, 0.0, NOW()),
('kyc_cdd_form',         'databricks-claude-sonnet',  'databricks-dbrx-instruct', 8192, 0.0, NOW()),
('aml_sar_filing',       'databricks-claude-sonnet',  'databricks-dbrx-instruct', 8192, 0.0, NOW()),
('claims_acord',         'docubricks-acord-extractor','databricks-dbrx-instruct', 2048, 0.0, NOW()),
('clinical_note_soap',   'databricks-claude-sonnet',  'databricks-dbrx-instruct', 6144, 0.0, NOW()),
('eob_cms1500',          'databricks-gemini-flash',   'databricks-dbrx-instruct', 2048, 0.0, NOW()),
-- Gemini for multimodal: EOB forms have complex table layouts + stamps
('nda_msa',              'databricks-claude-sonnet',  'databricks-dbrx-instruct', 8192, 0.0, NOW());
```

---

## 22. Vertical Agent Library

Agents are the proactive intelligence layer — they monitor extracted data, detect conditions requiring action, and either act autonomously or surface the right information to the right human at the right time. Each vertical has a library of purpose-built agents defined as Agent Bricks workflows.

### 22.1 Agent Architecture Pattern

Every DocuBricks agent follows the same structure:

```python
# Pattern: every agent = trigger condition + tool set + escalation path
from databricks.agents import AgentFramework, tool, agent
from lib.lakebase import lb_query, lb_exec
from lib.sql_warehouse import wh_query
from lib.databricks_api import trigger_workflow, send_notification

@agent(
    name="mortgage_risk_monitor",
    description="Monitors extracted mortgage applications for risk threshold breaches",
    schedule="0 7 * * *",          # daily at 07:00 UTC
    vertical="fs"
)
class MortgageRiskMonitorAgent:
    @tool(description="Query mortgage portfolio for DTI or LTV violations")
    def find_high_risk_applications(self, dti_threshold: float = 0.43,
                                     ltv_threshold: float = 0.95) -> list[dict]:
        return wh_query("""
            SELECT document_id, tenant_id, borrower_name, loan_amount,
                   debt_to_income_ratio, ltv_percent, extracted_at
            FROM docubricks_prod.silver.extracted_mortgage_application
            WHERE extracted_at > NOW() - INTERVAL '24 hours'
              AND (debt_to_income_ratio > ? OR ltv_percent > ?)
              AND document_id NOT IN (
                  SELECT document_id FROM review_queue WHERE resolved_at IS NULL
              )
            ORDER BY debt_to_income_ratio DESC
        """, (dti_threshold, ltv_threshold))

    @tool(description="Flag a document for underwriter review with a structured briefing")
    def flag_for_underwriter_review(self, document_id: str,
                                     risk_summary: str) -> str:
        lb_exec("""
            INSERT INTO review_queue
                (document_id, tenant_id, review_reason, priority, sla_due_at)
            SELECT document_id, tenant_id, 'HIGH_RISK_APPLICATION', 2,
                   NOW() + INTERVAL '4 hours'
            FROM document_registry WHERE document_id = %s
            ON CONFLICT DO NOTHING
        """, (document_id,))
        send_notification(
            channel="underwriting-alerts",
            message=f"High-risk mortgage flagged: `{document_id}`\n{risk_summary}"
        )
        return f"Flagged {document_id} for underwriter review"

    @tool(description="Generate a risk briefing for a mortgage application")
    def generate_risk_briefing(self, document_id: str) -> str:
        fields = wh_query("""
            SELECT borrower_name, loan_amount, debt_to_income_ratio,
                   ltv_percent, loan_purpose, occupancy_type,
                   credit_score, property_address
            FROM docubricks_prod.silver.extracted_mortgage_application
            WHERE document_id = ?
        """, (document_id,))[0]
        # Uses ai_query with Claude for reasoning
        return ai_query("databricks-claude-sonnet",
            f"Generate a concise underwriter risk briefing for this mortgage application. "
            f"Identify key risk factors and compensating factors. Application data: {fields}")
```

### 22.2 Financial Services Agent Library

| Agent | Trigger | Tools | Escalation |
|---|---|---|---|
| `MortgageRiskMonitorAgent` | Daily 07:00 UTC | query_silver, flag_review, generate_briefing | Underwriting team Slack + review queue |
| `KYCRefreshAgent` | Weekly Mon 06:00 UTC | query_monitoring_dates, generate_refresh_tasks | Compliance team assignment |
| `AMLPatternAgent` | After each AML SAR batch | cross_ref_existing_sars, flag_potential_filing | Compliance officer review queue (SLA 24h) |
| `ContractExpiryAgent` | Daily 08:00 UTC | query_expiry_dates, generate_renewal_brief | Legal team email + Admin dashboard |
| `InvoiceReconciliationAgent` | On new invoice batch | match_to_po, flag_discrepancy | AP team review queue |

```python
@agent(name="kyc_refresh_agent", schedule="0 6 * * 1", vertical="fs")
class KYCRefreshAgent:
    @tool(description="Find KYC profiles due for periodic refresh within the next 30 days")
    def find_due_for_refresh(self) -> list[dict]:
        return wh_query("""
            SELECT document_id, tenant_id, customer_type,
                   overall_risk_rating, next_review_date,
                   DATEDIFF(DAY, CURRENT_DATE, next_review_date) AS days_until_due
            FROM docubricks_prod.silver.extracted_kyc_cdd_form
            WHERE next_review_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 30
              AND document_id NOT IN (
                  SELECT document_id FROM reprocessing_queue
                  WHERE status = 'PENDING'
              )
            ORDER BY days_until_due ASC
        """)

    @tool(description="Create a KYC refresh task in the review queue")
    def create_refresh_task(self, document_id: str, days_until_due: int) -> str:
        priority = 1 if days_until_due <= 7 else (2 if days_until_due <= 14 else 3)
        lb_exec("""
            INSERT INTO review_queue
                (document_id, tenant_id, review_reason, priority,
                 sla_due_at, assigned_to)
            SELECT document_id, tenant_id, 'KYC_PERIODIC_REFRESH', %s,
                   NOW() + (%s * INTERVAL '1 day'),
                   (SELECT reviewer_email FROM tenant_reviewer_assignments
                    WHERE tenant_id = document_registry.tenant_id
                      AND vertical = 'fs' AND is_active = true LIMIT 1)
            FROM document_registry WHERE document_id = %s
            ON CONFLICT DO NOTHING
        """, (priority, days_until_due - 2, document_id))
        return f"KYC refresh task created for {document_id}, priority {priority}"
```

### 22.3 Healthcare Agent Library

| Agent | Trigger | Tools | Escalation |
|---|---|---|---|
| `EOBReconciliationAgent` | On new EOB batch | match_to_claim, compute_variance, flag_discrepancy | Billing team review queue |
| `ClinicalNoteSummaryAgent` | On new clinical note | summarise_soap, flag_abnormal_values, check_medication_interactions | Physician dashboard alert |
| `PriorAuthStatusAgent` | Daily 06:00 UTC | check_auth_expiry, flag_renewal, generate_renewal_request | Care coordinator review |
| `DrugLabelChangeAgent` | Weekly | diff_against_previous_version, flag_safety_changes | Pharmacovigilance team |

```python
@agent(name="eob_reconciliation_agent", vertical="healthcare",
       trigger_event="dlt_batch_complete:extracted_eob_cms1500")
class EOBReconciliationAgent:
    @tool(description="Match an EOB to its corresponding claim and compute variance")
    def reconcile_eob(self, eob_document_id: str) -> dict:
        eob = wh_query("""
            SELECT claim_number, billed_amount, allowed_amount,
                   paid_amount, patient_responsibility, service_date,
                   procedure_codes, provider_npi
            FROM docubricks_prod.silver.extracted_eob_cms1500
            WHERE document_id = ?
        """, (eob_document_id,))[0]

        claim = wh_query("""
            SELECT billed_amount AS expected_billed,
                   approved_amount AS expected_allowed
            FROM docubricks_prod.silver.extracted_prior_auth
            WHERE claim_number = ?
              AND provider_npi = ?
        """, (eob["claim_number"], eob["provider_npi"]))

        if not claim:
            return {"status": "UNMATCHED", "eob_document_id": eob_document_id}

        variance = abs(float(eob["billed_amount"]) - float(claim[0]["expected_billed"]))
        return {
            "status": "MATCHED" if variance < 1.0 else "DISCREPANT",
            "variance_usd": variance,
            "eob_document_id": eob_document_id,
            "claim_number": eob["claim_number"]
        }

    @tool(description="Flag a discrepant EOB for billing team review")
    def flag_discrepancy(self, eob_document_id: str, variance_usd: float) -> str:
        priority = 1 if variance_usd > 1000 else (2 if variance_usd > 100 else 3)
        lb_exec("""
            INSERT INTO review_queue
                (document_id, tenant_id, review_reason, priority, sla_due_at)
            SELECT document_id, tenant_id, 'EOB_DISCREPANCY', %s,
                   NOW() + INTERVAL '48 hours'
            FROM document_registry WHERE document_id = %s
            ON CONFLICT DO NOTHING
        """, (priority, eob_document_id))
        return f"EOB {eob_document_id} flagged: ${variance_usd:.2f} variance, priority {priority}"
```

### 22.4 Legal Agent Library

| Agent | Trigger | Tools | Escalation |
|---|---|---|---|
| `ContractExpiryAgent` | Daily 08:00 UTC | query_expiry, generate_renewal_brief, assign_reviewer | Legal team dashboard + email |
| `RegulatoryDeadlineAgent` | Daily 07:00 UTC | query_submission_deadlines, flag_upcoming, generate_checklist | Compliance team Slack |
| `RiskClauseAgent` | On new contract batch | identify_unusual_clauses, compare_to_standard_template, flag_for_counsel | Legal counsel review queue |
| `NDAScopeAgent` | On new NDA batch | extract_permitted_uses, flag_broad_scope, check_term_length | Legal team review |

```python
@agent(name="contract_expiry_agent", schedule="0 8 * * *", vertical="legal")
class ContractExpiryAgent:
    @tool(description="Find contracts expiring within a configurable window")
    def find_expiring_contracts(self, days_ahead: int = 90) -> list[dict]:
        return wh_query("""
            SELECT document_id, tenant_id, counterparty_name,
                   contract_type, expiry_date, auto_renew,
                   renewal_notice_days, governing_law,
                   DATEDIFF(DAY, CURRENT_DATE, expiry_date) AS days_remaining
            FROM docubricks_prod.silver.extracted_nda_msa
            WHERE expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + ?
              AND document_id NOT IN (
                  SELECT document_id FROM review_queue WHERE resolved_at IS NULL
              )
            ORDER BY days_remaining ASC
        """, (days_ahead,))

    @tool(description="Generate a contract renewal briefing using Claude")
    def generate_renewal_briefing(self, document_id: str) -> str:
        fields = wh_query("""
            SELECT counterparty_name, contract_type, expiry_date,
                   auto_renew, renewal_notice_days, key_obligations,
                   governing_law, original_term_months
            FROM docubricks_prod.silver.extracted_nda_msa
            WHERE document_id = ?
        """, (document_id,))[0]

        return ai_query("databricks-claude-sonnet",
            f"Generate a concise contract renewal briefing for legal counsel. "
            f"Include: renewal deadline (notice period), key obligations to review, "
            f"whether auto-renewal applies, and recommended action. "
            f"Contract details: {fields}")

    @tool(description="Write renewal briefing to review queue with deadline")
    def schedule_renewal_review(self, document_id: str,
                                 briefing: str, days_remaining: int) -> str:
        priority = 1 if days_remaining <= 14 else (2 if days_remaining <= 30 else 3)
        lb_exec("""
            INSERT INTO review_queue
                (document_id, tenant_id, review_reason, priority, sla_due_at)
            SELECT document_id, tenant_id, 'CONTRACT_RENEWAL_DUE', %s,
                   NOW() + (%s * INTERVAL '1 day')
            FROM document_registry WHERE document_id = %s
            ON CONFLICT DO NOTHING
        """, (priority, max(days_remaining - 7, 1), document_id))
        # Store briefing in extraction_audit for Admin app display
        lb_exec("""
            INSERT INTO extraction_audit
                (document_id, document_type, field_name, extracted_value, created_at)
            VALUES (%s, 'nda_msa', 'renewal_briefing', %s, NOW())
        """, (document_id, briefing))
        return f"Renewal review scheduled for {document_id}, priority {priority}"
```

### 22.5 Manufacturing / Supply Chain Agent Library

| Agent | Trigger | Tools | Escalation |
|---|---|---|---|
| `SupplierContractRiskAgent` | Weekly | query_expiring_supplier_contracts, flag_sole_source_risk | Procurement team |
| `CertificateExpiryAgent` | Daily | query_cert_expiry, flag_expiring, notify_supplier | Quality team |
| `BOMMismatchAgent` | On new BOM batch | compare_bom_to_previous_version, flag_unauthorised_changes | Engineering review |

### 22.6 Agent Deployment & Monitoring

Agents are deployed as Databricks Workflows jobs, not as always-on services. They run on a schedule or on event triggers (DLT batch completion), use serverless compute, and scale to zero between runs.

```yaml
# databricks.yml — agent job definitions (Databricks Asset Bundle)
resources:
  jobs:
    mortgage_risk_monitor:
      name: "DocuBricks — Mortgage Risk Monitor (FS)"
      schedule:
        quartz_cron_expression: "0 0 7 * * ?"
        timezone_id: "UTC"
      tasks:
        - task_key: run_agent
          notebook_task:
            notebook_path: /agents/fs/mortgage_risk_monitor.py
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: "Standard_DS3_v2"
            num_workers: 0                # single-node; agents are not data-parallel
      email_notifications:
        on_failure: ["platform-oncall@docubricks.com"]
      health:
        - metric: RUN_DURATION_SECONDS
          op: GREATER_THAN
          value: 1800           # alert if agent runs > 30 min
```

Agent run results are written to `docubricks_prod.gold.agent_activity`:

```sql
CREATE OR REPLACE TABLE docubricks_prod.gold.agent_activity (
    run_id          TEXT        NOT NULL,
    agent_name      TEXT        NOT NULL,
    vertical        TEXT        NOT NULL,
    tenant_id       TEXT        NOT NULL,
    items_scanned   INT,
    items_actioned  INT,
    items_escalated INT,
    run_duration_sec INT,
    run_date        DATE        NOT NULL,
    status          TEXT        NOT NULL
) CLUSTER BY (vertical, tenant_id, run_date);
```

This table powers the "Agent Activity" view in the Admin app and is Genie-queryable: *"How many contracts were flagged by the expiry agent last month?"*

---

*This document is the authoritative architecture reference for DocuBricks. All infrastructure changes, schema additions, and new vertical onboardings must be evaluated against the robustness, performance, and durability requirements stated in §1.*
