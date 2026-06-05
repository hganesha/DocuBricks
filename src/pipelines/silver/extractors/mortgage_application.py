# Databricks notebook source
# DocuBricks — Silver Extractor: Mortgage Application
# Wave 2 ExtractorAgent — MortgageExtractorAgent
# ====================================================
#
# Reads from:  silver_route_mortgage_application  (DLT view in extract_router.py)
# Writes to:   docubricks_prod.silver.silver_extracted_mortgage_application
#
# Regulatory alignment: URLA / MISMO v3.x, HMDA, TRID
# Model:               databricks-dbrx-instruct  (fallback: databricks-claude-sonnet)
# Confidence threshold (drop):   0.60  — rows below this are dropped from Silver
# Confidence threshold (review):  0.80  — rows below this are flagged REVIEW in Lakebase
#
# DLT channel: PREVIEW  |  Compute: Serverless
# Target schema: docubricks_prod.silver
# Pipeline config keys: catalog_name, secret_scope

# COMMAND ----------

import dlt
from pyspark.sql.functions import (
    col,
    current_timestamp,
    expr,
    get_json_object,
    lit,
    to_date,
    when,
)

from src.pipelines.silver.extractors._base import (
    build_silver_table,
    get_extraction_prompt,
    update_extraction_status,
    STANDARD_TABLE_PROPERTIES,
)

# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------

catalog_name: str = spark.conf.get("catalog_name")       # type: ignore[name-defined]  # noqa: F821
secret_scope: str = spark.conf.get("secret_scope")       # type: ignore[name-defined]  # noqa: F821

DOCUMENT_TYPE: str = "mortgage_application"

# Confidence thresholds aligned with field_thresholds.json and validation_rules.json
CONFIDENCE_DROP_THRESHOLD: float = 0.60    # avg_confidence_score below this → row dropped
CONFIDENCE_REVIEW_THRESHOLD: float = 0.80  # avg_confidence_score below this → REVIEW status

# ---------------------------------------------------------------------------
# Field flattener — mortgage_application
#
# Maps JSON paths from the ai_extract() result (MISMO v3.x aligned) to typed
# Silver columns.  All DECIMAL casts use try_cast() semantics via Spark's
# cast() which returns null on parse failure rather than raising.
#
# JSON paths mirror the structure documented in prompt_v1.txt and the
# extraction output format section of that prompt.
# ---------------------------------------------------------------------------

def _flatten_mortgage(df):
    """
    Accept the DataFrame immediately after ai_extract() writes extracted_json,
    avg_confidence_score, and field_confidences, and return a new DataFrame
    with all typed mortgage-specific columns appended.

    All get_json_object() calls are tolerant of missing keys — they return null
    rather than failing, matching the DLT expect_or_drop / expect semantics
    defined on the table below.
    """
    return (
        df
        # ------------------------------------------------------------------
        # Loan-level fields  ($.loan.* paths align to MISMO v3.x / URLA)
        # ------------------------------------------------------------------
        .withColumn(
            "loan_amount",
            get_json_object(col("extracted_json"), "$.loan.requestedLoanAmount")
            .cast("decimal(18,2)"),
        )
        .withColumn(
            "loan_purpose",
            get_json_object(col("extracted_json"), "$.loan.loanPurpose"),
        )
        .withColumn(
            "loan_type",
            get_json_object(col("extracted_json"), "$.loan.loanType"),
        )
        .withColumn(
            "occupancy_type",
            get_json_object(col("extracted_json"), "$.loan.occupancyType"),
        )
        .withColumn(
            "interest_rate_percent",
            get_json_object(col("extracted_json"), "$.loan.interestRatePercent")
            .cast("decimal(6,4)"),
        )
        .withColumn(
            "loan_term_months",
            get_json_object(col("extracted_json"), "$.loan.loanTermMonths")
            .cast("int"),
        )
        # ------------------------------------------------------------------
        # Borrower identity fields
        # ------------------------------------------------------------------
        .withColumn(
            "borrower_last_name",
            get_json_object(col("extracted_json"), "$.borrowers[0].fullName.lastName"),
        )
        .withColumn(
            "borrower_first_name",
            get_json_object(col("extracted_json"), "$.borrowers[0].fullName.firstName"),
        )
        # ------------------------------------------------------------------
        # Underwriting ratios
        # ------------------------------------------------------------------
        .withColumn(
            "debt_to_income_ratio",
            get_json_object(
                col("extracted_json"),
                "$.underwriting.ratios.totalDebtExpenseRatioPercent",
            ).cast("decimal(5,2)"),
        )
        .withColumn(
            "ltv_percent",
            get_json_object(col("extracted_json"), "$.underwriting.ratios.ltvPercent")
            .cast("decimal(5,2)"),
        )
        # ------------------------------------------------------------------
        # Credit
        # ------------------------------------------------------------------
        .withColumn(
            "credit_score",
            get_json_object(
                col("extracted_json"),
                "$.credit.representativeCreditScore.score",
            ).cast("int"),
        )
        # ------------------------------------------------------------------
        # Subject property
        # ------------------------------------------------------------------
        .withColumn(
            "property_address",
            get_json_object(
                col("extracted_json"), "$.subjectProperty.address.streetLine1"
            ),
        )
        .withColumn(
            "property_state",
            get_json_object(
                col("extracted_json"), "$.subjectProperty.address.stateCode"
            ),
        )
        .withColumn(
            "appraisal_value",
            get_json_object(
                col("extracted_json"),
                "$.subjectProperty.valuation.appraisedValue",
            ).cast("decimal(18,2)"),
        )
    )


# ---------------------------------------------------------------------------
# DLT table definition
# ---------------------------------------------------------------------------

@dlt.table(
    **build_silver_table(
        document_type=DOCUMENT_TYPE,
        required_fields=[
            "loan_amount",
            "loan_purpose",
            "loan_type",
            "borrower_last_name",
            "borrower_first_name",
            "debt_to_income_ratio",
            "ltv_percent",
            "credit_score",
            "property_state",
            "occupancy_type",
            "interest_rate_percent",
        ],
        confidence_threshold=CONFIDENCE_DROP_THRESHOLD,
        extra_table_properties={
            "docubricks.vertical":            "fs",
            "docubricks.regulatory_standard": "URLA/MISMO_v3.x,HMDA,TRID",
            "docubricks.extraction_model":    "databricks-dbrx-instruct",
            "docubricks.review_threshold":    str(CONFIDENCE_REVIEW_THRESHOLD),
        },
    )
)
# ---------------------------------------------------------------------------
# System invariant — fail the entire micro-batch if document_id is absent.
# A row without a document_id cannot be traced back to the source registry
# and would silently corrupt audit trails.
# ---------------------------------------------------------------------------
@dlt.expect_or_fail(
    "document_id_present",
    "document_id IS NOT NULL",
)
# ---------------------------------------------------------------------------
# Extraction quality gate — drop rows where avg extraction confidence is below
# the minimum acceptance threshold (0.60).  These rows are quarantined rather
# than written to Silver, preventing low-quality data from reaching Gold.
# ---------------------------------------------------------------------------
@dlt.expect_or_drop(
    "extraction_min_confidence",
    "avg_confidence_score >= 0.60",
)
# ---------------------------------------------------------------------------
# Core mortgage field gate — drop rows where loan_amount is missing or
# non-positive.  A mortgage record without a loan amount is unusable for
# HMDA LAR, TRID disclosures, AUS submission, or portfolio analytics.
# ---------------------------------------------------------------------------
@dlt.expect_or_drop(
    "loan_amount_positive",
    "loan_amount IS NOT NULL AND loan_amount > 0",
)
# ---------------------------------------------------------------------------
# Loan purpose validity — drop rows with a loan_purpose outside the allowed
# MISMO/URLA enumeration.  Invalid values break downstream AUS and HMDA routing.
# ---------------------------------------------------------------------------
@dlt.expect_or_drop(
    "loan_purpose_valid_enum",
    "loan_purpose IN ('Purchase','Refinance','CashOutRefinance','Construction',"
    "'ConstructionPermanent','HomeEquity','HELOC','Other')",
)
# ---------------------------------------------------------------------------
# Loan type validity — drop rows with an unrecognised loan_type.
# Affects investor delivery, MIP/funding fee calculation, and HMDA reporting.
# ---------------------------------------------------------------------------
@dlt.expect_or_drop(
    "loan_type_valid_enum",
    "loan_type IN ('Conventional','FHA','VA','USDA','Jumbo','Portfolio','NonQM','Other')",
)
# ---------------------------------------------------------------------------
# Borrower identity — drop rows without a non-blank borrower last name.
# Cannot process OFAC screening, credit authorisation, or legal instruments
# without borrower identity.
# ---------------------------------------------------------------------------
@dlt.expect_or_drop(
    "borrower_last_name_present",
    "borrower_last_name IS NOT NULL AND LENGTH(TRIM(borrower_last_name)) > 0",
)
# ---------------------------------------------------------------------------
# LTV range guard — drop rows where LTV is clearly impossible (>105% or <=0).
# These indicate an extraction error and must not enter portfolio analytics.
# ---------------------------------------------------------------------------
@dlt.expect_or_drop(
    "ltv_reasonable_range",
    "ltv_percent IS NULL OR (ltv_percent > 0 AND ltv_percent <= 105)",
)
# ---------------------------------------------------------------------------
# DTI range guard — drop rows where the back-end DTI is outside 0–100%.
# An out-of-range DTI value is an extraction artefact, not a real underwriting ratio.
# ---------------------------------------------------------------------------
@dlt.expect_or_drop(
    "dti_reasonable_range",
    "debt_to_income_ratio IS NULL OR (debt_to_income_ratio > 0 AND debt_to_income_ratio < 100)",
)
# ---------------------------------------------------------------------------
# Interest rate range guard — drop rows where the stated rate is outside 0–30%.
# Protects against unit-conversion errors (e.g., 6.875 entered as 687.5).
# ---------------------------------------------------------------------------
@dlt.expect_or_drop(
    "interest_rate_reasonable",
    "interest_rate_percent IS NULL OR (interest_rate_percent > 0 AND interest_rate_percent < 30)",
)
# ---------------------------------------------------------------------------
# DTI present — warn only.  DTI is an HMDA-reportable field and a critical
# ATR/QM metric, but some early-stage applications may arrive without it.
# Rows are kept; the warning surfaces in DLT event logs and Gold metrics.
# ---------------------------------------------------------------------------
@dlt.expect(
    "dti_present",
    "debt_to_income_ratio IS NOT NULL",
)
# ---------------------------------------------------------------------------
# Loan term standard values — warn only.  Non-standard terms (e.g., 84 months)
# are legal but unusual; flagged for review rather than dropped.
# ---------------------------------------------------------------------------
@dlt.expect(
    "loan_term_standard_values",
    "loan_term_months IS NULL OR loan_term_months IN (60,84,120,180,240,300,360,480)",
)
# ---------------------------------------------------------------------------
# HMDA LAR completeness — warn only.  State, occupancy type, and loan amount
# are required for HMDA filing; missing values prevent regulatory reporting
# but do not invalidate the Silver record itself.
# ---------------------------------------------------------------------------
@dlt.expect(
    "hmda_reportable_fields_present",
    "property_state IS NOT NULL AND occupancy_type IS NOT NULL AND loan_amount IS NOT NULL",
)
def silver_extracted_mortgage_application():
    """
    Wave 2 Silver extractor for document_type = 'mortgage_application'.

    Pipeline
    --------
    1. Read the routed stream from silver_route_mortgage_application.
    2. Load the active extraction prompt from schema_registry.
    3. Call ai_extract() (Databricks native SQL function) to produce a JSON result.
    4. Flatten the JSON into typed Silver columns.
    5. Emit the final DataFrame — DLT expectations applied above handle quality gates.

    Post-write side-effects (row-level Lakebase status updates) are applied via
    a foreachBatch call registered on the stream outside the @dlt.table function.

    Status transitions in document_registry:
        CLASSIFIED  →  EXTRACTING  →  EXTRACTED   (avg_confidence_score >= 0.80)
        CLASSIFIED  →  EXTRACTING  →  REVIEW      (avg_confidence_score in [0.60, 0.80))

    Rows with avg_confidence_score < 0.60 are dropped by expect_or_drop before
    reaching Lakebase (DLT never emits them to Silver storage).

    Columns produced
    ----------------
    Passthrough from route view:
        document_id, tenant_id, vertical, file_ext, source_path, file_size_bytes,
        ingested_at, ingested_date, page_count, document_type, classification_confidence

    Extraction output:
        extracted_json         STRING        full JSON from ai_extract()
        avg_confidence_score   DOUBLE        mean confidence across all fields
        field_confidences      STRING        per-field confidence map (JSON)
        extraction_model       STRING        model identifier
        extracted_at           TIMESTAMP     extraction wall-clock time

    Mortgage-specific typed fields:
        loan_amount            DECIMAL(18,2)
        loan_purpose           STRING
        loan_type              STRING
        occupancy_type         STRING
        interest_rate_percent  DECIMAL(6,4)
        loan_term_months       INT
        borrower_last_name     STRING
        borrower_first_name    STRING
        debt_to_income_ratio   DECIMAL(5,2)
        ltv_percent            DECIMAL(5,2)
        credit_score           INT
        property_address       STRING
        property_state         STRING
        appraisal_value        DECIMAL(18,2)
    """
    # ------------------------------------------------------------------
    # Step 1 — Load the versioned extraction prompt from schema_registry.
    # Raises ValueError if no active prompt is found and no fallback is set.
    # Using the fallback prompt text from prompt_v1.txt is intentional: it
    # lets the pipeline continue if the registry is temporarily unavailable,
    # while the warning in logs surfaces the issue for operators.
    # ------------------------------------------------------------------
    schema_prompt: str = get_extraction_prompt(
        catalog_name=catalog_name,
        document_type=DOCUMENT_TYPE,
        fallback_prompt=None,   # fail fast: registry must be reachable in production
    )

    # ------------------------------------------------------------------
    # Step 2 — Read the routed streaming view for this document type.
    # The view is defined in extract_router.py and filters silver_classified
    # to document_type = 'mortgage_application'.
    # ------------------------------------------------------------------
    df = dlt.read_stream("silver_route_mortgage_application")

    # ------------------------------------------------------------------
    # Step 3 — Call ai_extract() via Spark expr().
    #
    # ai_extract() is a Databricks-native SQL function:
    #   ai_extract(text_col, prompt_string) → struct{
    #       result:         string   (JSON blob of extracted fields)
    #       avg_confidence: double   (mean confidence over all fields)
    #       field_scores:   map<string,double>  (per-field confidence)
    #   }
    #
    # The prompt is embedded as a Spark literal so the SQL expression is
    # self-contained and does not require a UDF or broadcast variable.
    # Single-quotes inside the prompt are escaped by doubling them.
    # ------------------------------------------------------------------
    safe_prompt = schema_prompt.replace("'", "''")

    df = (
        df
        .withColumn(
            "_extraction_result",
            expr(f"ai_extract(parsed_text, '{safe_prompt}')"),
        )
        # Unpack the struct returned by ai_extract
        .withColumn("extracted_json",       col("_extraction_result.result"))
        .withColumn("avg_confidence_score", col("_extraction_result.avg_confidence").cast("double"))
        .withColumn(
            "field_confidences",
            # Serialise the map<string,double> to a JSON string for portability
            # across consumers that may not support MapType natively.
            expr("to_json(_extraction_result.field_scores)"),
        )
        .withColumn("extraction_model",     lit("databricks-dbrx-instruct"))
        .withColumn("extracted_at",         current_timestamp())
        .drop("_extraction_result", "routed_at", "pipeline_stage")
    )

    # ------------------------------------------------------------------
    # Step 4 — Flatten the extracted JSON into typed Silver columns.
    # _flatten_mortgage() adds all mortgage-specific columns via
    # get_json_object() which returns null (not an exception) on missing paths.
    # ------------------------------------------------------------------
    df = _flatten_mortgage(df)

    # ------------------------------------------------------------------
    # Step 5 — Project the final column set.
    # Ordering mirrors BASE_EXTRACTION_COLUMNS + mortgage-specific additions
    # to produce a deterministic schema for downstream Gold consumers.
    # ------------------------------------------------------------------
    return df.select(
        # ---- passthrough identity / lineage columns --------------------
        "document_id",
        "tenant_id",
        "vertical",
        "file_ext",
        "source_path",
        "file_size_bytes",
        "ingested_at",
        "ingested_date",
        "page_count",
        "document_type",
        "classification_confidence",
        # ---- extraction metadata columns ------------------------------
        "extracted_json",
        "avg_confidence_score",
        "field_confidences",
        "extraction_model",
        "extracted_at",
        # ---- mortgage-specific typed columns --------------------------
        "loan_amount",
        "loan_purpose",
        "loan_type",
        "occupancy_type",
        "interest_rate_percent",
        "loan_term_months",
        "borrower_last_name",
        "borrower_first_name",
        "debt_to_income_ratio",
        "ltv_percent",
        "credit_score",
        "property_address",
        "property_state",
        "appraisal_value",
    )


# ---------------------------------------------------------------------------
# Post-write Lakebase status updates
#
# DLT streaming tables do not support arbitrary side-effects inside the
# @dlt.table function body — the function must return a pure DataFrame.
# Instead we attach a foreachBatch listener on the Delta Change Data Feed
# stream that DLT writes automatically when delta.enableChangeDataFeed=true.
#
# This block runs AFTER DLT commits each micro-batch to
# silver_extracted_mortgage_application, so the status update in
# document_registry is always consistent with what was actually written.
#
# Status logic
# ------------
#   avg_confidence_score >= CONFIDENCE_REVIEW_THRESHOLD (0.80)  → "VALIDATED"
#       mapped to update_extraction_status(...) which calls
#       LakbaseHelper.complete_extraction() → stores "EXTRACTED" in the registry
#
#   avg_confidence_score in [0.60, 0.80)                        → "REVIEW"
#       update_extraction_status() called with confidence value below the
#       complete_extraction() internal threshold → stores "REVIEW" in registry
#       LakbaseHelper.enqueue_for_review() is also called to insert a row
#       into review_queue for the human review workflow.
#
#   avg_confidence_score < 0.60                                  → (dropped)
#       DLT expect_or_drop("extraction_min_confidence") drops these rows
#       before they reach Silver storage, so no Lakebase update is needed.
#
# Note: update_extraction_status() is idempotent — it uses WHERE status = 'EXTRACTING'
# guards in the underlying SQL, so replaying a micro-batch is safe.
# ---------------------------------------------------------------------------

def _update_lakebase_statuses(micro_batch_df, batch_id):  # noqa: ARG001
    """
    foreachBatch callback — called by Spark after DLT commits each micro-batch.

    Iterates over the document_id / avg_confidence_score pairs in the batch
    and calls update_extraction_status() for each row.  Lakebase writes are
    fast (single-row UPDATE per document) and the batch sizes in a serverless
    DLT pipeline are small, so Python-level iteration is acceptable here.

    For very high-throughput deployments, replace the collectAsList() with
    a JDBC batch-write or a Lakebase stored procedure to reduce round-trips.
    """
    from src.pipelines.silver.extractors._base import (
        LakbaseHelper,
        enqueue_for_extraction_review,
    )

    helper = LakbaseHelper(secret_scope=secret_scope)

    rows = (
        micro_batch_df
        .select("document_id", "tenant_id", "avg_confidence_score")
        .filter(col("document_id").isNotNull())
        .collect()
    )

    for row in rows:
        doc_id = row["document_id"]
        tenant_id = row["tenant_id"]
        conf = float(row["avg_confidence_score"]) if row["avg_confidence_score"] is not None else 0.0

        if conf >= CONFIDENCE_REVIEW_THRESHOLD:
            # High-confidence extraction — transition to VALIDATED / EXTRACTED
            update_extraction_status(
                document_id=doc_id,
                extraction_conf=conf,
                confidence_threshold=CONFIDENCE_REVIEW_THRESHOLD,
                secret_scope=secret_scope,
            )
        else:
            # Low-to-mid confidence extraction — flag for human review
            # conf >= CONFIDENCE_DROP_THRESHOLD is guaranteed by expect_or_drop above
            update_extraction_status(
                document_id=doc_id,
                extraction_conf=conf,
                confidence_threshold=CONFIDENCE_REVIEW_THRESHOLD,  # will resolve to REVIEW
                secret_scope=secret_scope,
            )
            enqueue_for_extraction_review(
                document_id=doc_id,
                tenant_id=tenant_id,
                review_reason="LOW_CONFIDENCE",
                secret_scope=secret_scope,
            )

    helper.close()


# ---------------------------------------------------------------------------
# Wire the foreachBatch callback to the Silver table's CDF output stream.
#
# We read the Change Data Feed of the Silver table (populated by DLT) and
# apply the Lakebase status updates in a separate Structured Streaming query.
# This keeps the DLT graph pure (no side-effects in table functions) while
# ensuring status updates happen reliably after each commit.
#
# The checkpoint path is scoped to the table name and stored in DBFS under
# the pipeline's working directory so it survives cluster restarts.
#
# Guard: only attach the stream when running inside Databricks DLT context.
# Unit tests and CI jobs import this module off-cluster and must not trigger
# a streaming query.
# ---------------------------------------------------------------------------

try:
    _cdf_stream = (
        spark  # type: ignore[name-defined]  # noqa: F821
        .readStream
        .format("delta")
        .option("readChangeFeed", "true")
        .option("startingVersion", "latest")
        .table(f"{catalog_name}.silver.silver_extracted_mortgage_application")
    )

    (
        _cdf_stream
        .filter(col("_change_type").isin("insert", "update_postimage"))
        .writeStream
        .foreachBatch(_update_lakebase_statuses)
        .option(
            "checkpointLocation",
            f"/dbfs/docubricks/checkpoints/{catalog_name}/silver_extracted_mortgage_application_lakebase",
        )
        .trigger(availableNow=True)
        .start()
    )
except Exception as _stream_err:  # noqa: BLE001
    # Log but do not fail the notebook import — the DLT table definition above
    # is the primary deliverable; the CDF stream is a best-effort side-car.
    import logging as _logging
    _logging.getLogger("docubricks.extractors.mortgage_application").warning(
        "Could not attach Lakebase CDF stream: %s. "
        "Status updates in document_registry will not be applied for this run. "
        "Verify that the Silver table exists and CDF is enabled.",
        _stream_err,
    )
