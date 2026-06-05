"""
DocuBricks — AML SAR Silver Extractor
=======================================
src/pipelines/silver/extractors/aml_sar.py

DLT Streaming Table: silver_extracted_aml_sar
Source view:         silver_route_aml_sar
Document type:       aml_sar
Regulatory frame:    FinCEN BSA e-Filing, SAR form TD F 90-22.47

Confidence thresholds
----------------------
- DROP threshold (DLT expect_or_drop): 0.70
  Rows below 0.70 avg_confidence_score are dropped entirely.
- REVIEW threshold (Lakebase enqueue): 0.90
  AML SARs with confidence < 0.90 are ALWAYS routed to the human review
  queue — regulatory requirement for FinCEN reporting.  Rows that survive
  the 0.70 DROP gate but fall below 0.90 are written to the table AND
  enqueued for review.

Flattened columns
-----------------
  sar_id                    STRING        $.sarId
  subject_name              STRING        $.subjectName
  subject_type              STRING        $.subjectType  (Individual | Business | Other)
  suspicious_activity_type  STRING        $.suspiciousActivityType
  activity_start_date       DATE          $.activityDateRange.startDate
  activity_end_date         DATE          $.activityDateRange.endDate
  transaction_amount        DECIMAL(18,2) $.transactionAmount
  transaction_currency      STRING        $.transactionCurrency
  filing_institution        STRING        $.filingInstitution.name
  filing_institution_type   STRING        $.filingInstitution.type
  filing_date               DATE          $.filingDate
  case_id                   STRING        $.relatedCaseId
  narrative_summary         STRING        $.narrative (truncated to 2000 chars)
  law_enforcement_notified  BOOLEAN       $.lawEnforcementNotifiedIndicator
  --- pass-through from base ---
  extracted_json            STRING
  avg_confidence_score      DOUBLE
  field_confidences         STRING
  extracted_at              TIMESTAMP
  ingested_date             DATE

DLT Expectations
----------------
  expect_or_fail  document_id_present         document_id IS NOT NULL
  expect_or_drop  min_confidence_70           avg_confidence_score >= 0.70
  expect_or_drop  sar_id_present              sar_id IS NOT NULL
  expect_or_drop  subject_name_present        subject_name IS NOT NULL
  expect_or_drop  suspicious_activity_present suspicious_activity_type IS NOT NULL
  expect          transaction_amount_positive  transaction_amount > 0
  expect          filing_date_present         filing_date IS NOT NULL
"""

from __future__ import annotations

import logging

# ---------------------------------------------------------------------------
# DLT / PySpark runtime imports
# Resolved at runtime inside Databricks; guarded for unit-test environments.
# ---------------------------------------------------------------------------
try:
    import dlt
    from pyspark.sql import DataFrame
    from pyspark.sql.functions import (
        col,
        get_json_object,
        substring,
        to_date,
        when,
    )
    _IN_DATABRICKS = True
except ImportError:
    _IN_DATABRICKS = False

from src.pipelines.silver.extractors._base import (
    LakbaseHelper,
    build_extraction_stream,
    build_silver_table,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DOCUMENT_TYPE: str = "aml_sar"

# Rows below this score are DROPPED by the DLT expect_or_drop expectation.
DROP_CONFIDENCE_THRESHOLD: float = 0.70

# Rows below this score are ALSO enqueued for human review (regulatory requirement).
# This threshold is enforced by the post-flatten review gate, not by a DLT expectation.
REVIEW_CONFIDENCE_THRESHOLD: float = 0.90

# Maximum characters retained in narrative_summary (FinCEN SAR narrative field).
NARRATIVE_MAX_CHARS: int = 2000

logger = logging.getLogger("docubricks.extractors.aml_sar")

# ---------------------------------------------------------------------------
# Lakebase connection pool (singleton for this notebook process)
# ---------------------------------------------------------------------------

# Initialised lazily via spark.conf at DLT table definition time.
_lakebase: LakbaseHelper | None = None


def _get_lakebase(secret_scope: str) -> LakbaseHelper:
    global _lakebase
    if _lakebase is None:
        _lakebase = LakbaseHelper(secret_scope=secret_scope)
    return _lakebase


# ---------------------------------------------------------------------------
# Flatten function
# ---------------------------------------------------------------------------

def _flatten_aml_sar(df: "DataFrame") -> "DataFrame":
    """
    Flatten extracted_json into typed AML SAR columns.

    Called by build_extraction_stream() after ai_extract() has populated
    the ``extracted_json`` column.

    All date strings are parsed with ISO-8601 format (yyyy-MM-dd) — the
    expected output format from the FinCEN SAR schema prompt.
    """
    return (
        df
        # --- Subject identification ---
        .withColumn(
            "sar_id",
            get_json_object(col("extracted_json"), "$.sarId"),
        )
        .withColumn(
            "subject_name",
            get_json_object(col("extracted_json"), "$.subjectName"),
        )
        .withColumn(
            "subject_type",
            get_json_object(col("extracted_json"), "$.subjectType"),
        )
        # --- Suspicious activity ---
        .withColumn(
            "suspicious_activity_type",
            get_json_object(col("extracted_json"), "$.suspiciousActivityType"),
        )
        # --- Activity date range ---
        .withColumn(
            "activity_start_date",
            to_date(
                get_json_object(col("extracted_json"), "$.activityDateRange.startDate"),
                "yyyy-MM-dd",
            ),
        )
        .withColumn(
            "activity_end_date",
            to_date(
                get_json_object(col("extracted_json"), "$.activityDateRange.endDate"),
                "yyyy-MM-dd",
            ),
        )
        # --- Transaction details ---
        .withColumn(
            "transaction_amount",
            get_json_object(col("extracted_json"), "$.transactionAmount")
            .cast("decimal(18,2)"),
        )
        .withColumn(
            "transaction_currency",
            get_json_object(col("extracted_json"), "$.transactionCurrency"),
        )
        # --- Filing institution ---
        .withColumn(
            "filing_institution",
            get_json_object(col("extracted_json"), "$.filingInstitution.name"),
        )
        .withColumn(
            "filing_institution_type",
            get_json_object(col("extracted_json"), "$.filingInstitution.type"),
        )
        # --- Filing metadata ---
        .withColumn(
            "filing_date",
            to_date(
                get_json_object(col("extracted_json"), "$.filingDate"),
                "yyyy-MM-dd",
            ),
        )
        .withColumn(
            "case_id",
            get_json_object(col("extracted_json"), "$.relatedCaseId"),
        )
        # --- Narrative (truncated to 2000 chars per FinCEN field limit) ---
        .withColumn(
            "narrative_summary",
            substring(
                get_json_object(col("extracted_json"), "$.narrative"),
                1,
                NARRATIVE_MAX_CHARS,
            ),
        )
        # --- Law enforcement flag ---
        .withColumn(
            "law_enforcement_notified",
            when(
                get_json_object(col("extracted_json"), "$.lawEnforcementNotifiedIndicator")
                == "true",
                True,
            )
            .when(
                get_json_object(col("extracted_json"), "$.lawEnforcementNotifiedIndicator")
                == "false",
                False,
            )
            .otherwise(None)
            .cast("boolean"),
        )
    )


# ---------------------------------------------------------------------------
# DLT table registration
# ---------------------------------------------------------------------------

if _IN_DATABRICKS:
    # Read catalog_name / secret_scope from pipeline configuration.
    # These are injected by the DLT pipeline definition (pipeline.json → configuration).
    _catalog_name: str = spark.conf.get("catalog_name")        # type: ignore[name-defined]  # noqa: F821
    _secret_scope: str = spark.conf.get("secret_scope")        # type: ignore[name-defined]  # noqa: F821

    @dlt.table(
        **build_silver_table(
            document_type=DOCUMENT_TYPE,
            required_fields=[
                "sar_id",
                "subject_name",
                "suspicious_activity_type",
                "filing_date",
            ],
            confidence_threshold=DROP_CONFIDENCE_THRESHOLD,
            extra_table_properties={
                "docubricks.vertical":              "fs",
                "docubricks.regulatory_framework":  "FinCEN BSA e-Filing, SAR form TD F 90-22.47",
                "docubricks.review_threshold":      str(REVIEW_CONFIDENCE_THRESHOLD),
            },
            comment=(
                "Extracted structured fields for AML Suspicious Activity Reports (SARs). "
                f"Drop threshold: avg_confidence_score >= {DROP_CONFIDENCE_THRESHOLD}. "
                f"Review (REGULATORY): avg_confidence_score >= {REVIEW_CONFIDENCE_THRESHOLD}. "
                "All rows below the review threshold are enqueued for human review regardless "
                "of whether they pass the drop gate. "
                "Regulatory alignment: FinCEN BSA e-Filing, SAR form TD F 90-22.47. "
                "Populated by Wave 2 AMLSARExtractorAgent."
            ),
        )
    )
    # -----------------------------------------------------------------------
    # System invariant — failure here stops the pipeline (broken upstream data)
    # -----------------------------------------------------------------------
    @dlt.expect_or_fail("document_id_present", "document_id IS NOT NULL")
    # -----------------------------------------------------------------------
    # Quality gates — rows that fail are DROPPED (not quarantined)
    # -----------------------------------------------------------------------
    @dlt.expect_or_drop("min_confidence_70", f"avg_confidence_score >= {DROP_CONFIDENCE_THRESHOLD}")
    @dlt.expect_or_drop("sar_id_present", "sar_id IS NOT NULL")
    @dlt.expect_or_drop("subject_name_present", "subject_name IS NOT NULL")
    @dlt.expect_or_drop("suspicious_activity_present", "suspicious_activity_type IS NOT NULL")
    # -----------------------------------------------------------------------
    # Soft warnings — rows survive but violations are tracked in DLT event log
    # -----------------------------------------------------------------------
    @dlt.expect("transaction_amount_positive", "transaction_amount > 0")
    @dlt.expect("filing_date_present", "filing_date IS NOT NULL")
    def silver_extracted_aml_sar() -> "DataFrame":
        """
        AML SAR Silver extraction table.

        Pipeline:
          1. Read stream from silver_route_aml_sar (produced by extract_router.py)
          2. Call ai_extract() with the active SAR schema prompt (databricks-claude-sonnet)
          3. Flatten JSON result into typed columns via _flatten_aml_sar()
          4. DLT expectations enforce quality gates (see decorators above)
          5. Post-flatten: rows below REVIEW_CONFIDENCE_THRESHOLD (0.90) are enqueued
             for human review via Lakebase — regulatory requirement for FinCEN reporting.
        """
        df = build_extraction_stream(
            document_type=DOCUMENT_TYPE,
            catalog_name=_catalog_name,
            confidence_threshold=DROP_CONFIDENCE_THRESHOLD,
            flatten_fn=_flatten_aml_sar,
            extra_columns=[
                "sar_id",
                "subject_name",
                "subject_type",
                "suspicious_activity_type",
                "activity_start_date",
                "activity_end_date",
                "transaction_amount",
                "transaction_currency",
                "filing_institution",
                "filing_institution_type",
                "filing_date",
                "case_id",
                "narrative_summary",
                "law_enforcement_notified",
            ],
        )

        # ------------------------------------------------------------------
        # Regulatory REVIEW gate (0.90 threshold).
        #
        # build_extraction_stream() returns a Spark DataFrame — we cannot
        # iterate rows inline in a DLT function.  We use a foreachBatch-style
        # pattern via mapInPandas to push status updates to Lakebase without
        # blocking the streaming write.
        #
        # NOTE: The Lakebase enqueue call is fire-and-forget per micro-batch.
        # The DLT expect_or_drop at 0.70 already ensures the row quality
        # floor; the 0.90 review gate is an *additional* regulatory overlay.
        # ------------------------------------------------------------------
        _lb = _get_lakebase(_secret_scope)

        def _enqueue_low_confidence_rows(iterator):
            """
            Pandas UDF iterator: for each partition, enqueue rows whose
            avg_confidence_score is below REVIEW_CONFIDENCE_THRESHOLD.
            """
            for pdf in iterator:
                review_rows = pdf[pdf["avg_confidence_score"] < REVIEW_CONFIDENCE_THRESHOLD]
                for _, row in review_rows.iterrows():
                    try:
                        _lb.enqueue_for_review(
                            document_id=row["document_id"],
                            tenant_id=row.get("tenant_id", "unknown"),
                            review_reason="LOW_CONFIDENCE",
                            # Priority 1 = highest — SAR regulatory requirement
                            priority=1,
                        )
                        logger.info(
                            "AML SAR enqueued for REVIEW: document_id=%s conf=%.4f",
                            row["document_id"],
                            row["avg_confidence_score"],
                        )
                    except Exception as exc:  # noqa: BLE001
                        # Log but do not fail the DLT batch — the row is still written
                        # to the table; a downstream reconciliation job will re-check
                        # review_queue completeness.
                        logger.error(
                            "Failed to enqueue AML SAR for review: document_id=%s error=%s",
                            row.get("document_id", "unknown"),
                            exc,
                        )
                yield pdf

        # Apply review-queue side-effect without mutating the output schema.
        # mapInPandas preserves the DataFrame schema while executing the
        # Lakebase write as a side-effect on the executor.
        schema = df.schema
        df = df.mapInPandas(_enqueue_low_confidence_rows, schema=schema)

        return df
