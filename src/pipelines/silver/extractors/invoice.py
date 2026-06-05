"""
DocuBricks — Invoice Silver Extractor
=======================================
src/pipelines/silver/extractors/invoice.py

DLT Streaming Table: silver_extracted_invoice
Source view:         silver_route_invoice
Document type:       invoice
Regulatory frame:    Standard AP/AR, GAAP

Confidence thresholds
----------------------
- DROP threshold (DLT expect_or_drop): 0.60
  Rows below 0.60 avg_confidence_score are dropped entirely.
- REVIEW threshold (Lakebase enqueue): 0.75
  Invoices with confidence < 0.75 are routed to the AP review queue
  for human verification before payment processing.

Flattened columns
-----------------
  invoice_number   STRING        $.invoiceNumber
  vendor_name      STRING        $.vendorName
  vendor_id        STRING        $.vendorId
  total_amount     DECIMAL(18,2) $.totalAmount
  currency         STRING        $.currency
  invoice_date     DATE          $.invoiceDate
  due_date         DATE          $.dueDate
  payment_terms    STRING        $.paymentTerms
  po_number        STRING        $.purchaseOrderNumber
  tax_amount       DECIMAL(18,2) $.taxAmount
  line_item_count  INT           $.lineItemCount
  gl_account_code  STRING        $.glAccountCode
  approval_status  STRING        $.approvalStatus
  --- pass-through from base ---
  extracted_json       STRING
  avg_confidence_score DOUBLE
  field_confidences    STRING
  extracted_at         TIMESTAMP
  ingested_date        DATE

DLT Expectations
----------------
  expect_or_fail  document_id_present          document_id IS NOT NULL
  expect_or_drop  min_confidence_60            avg_confidence_score >= 0.60
  expect_or_drop  invoice_number_present       invoice_number IS NOT NULL
  expect_or_drop  total_amount_valid           total_amount IS NOT NULL AND total_amount > 0
  expect          due_date_present             due_date IS NOT NULL
  expect          vendor_name_present          vendor_name IS NOT NULL
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
        to_date,
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

DOCUMENT_TYPE: str = "invoice"

# Rows below this score are DROPPED by the DLT expect_or_drop expectation.
DROP_CONFIDENCE_THRESHOLD: float = 0.60

# Rows below this score are enqueued for AP review queue.
REVIEW_CONFIDENCE_THRESHOLD: float = 0.75

logger = logging.getLogger("docubricks.extractors.invoice")

# ---------------------------------------------------------------------------
# Lakebase connection pool (singleton for this notebook process)
# ---------------------------------------------------------------------------

_lakebase: LakbaseHelper | None = None


def _get_lakebase(secret_scope: str) -> LakbaseHelper:
    global _lakebase
    if _lakebase is None:
        _lakebase = LakbaseHelper(secret_scope=secret_scope)
    return _lakebase


# ---------------------------------------------------------------------------
# Flatten function
# ---------------------------------------------------------------------------

def _flatten_invoice(df: "DataFrame") -> "DataFrame":
    """
    Flatten extracted_json into typed Invoice columns.

    Called by build_extraction_stream() after ai_extract() has populated
    the ``extracted_json`` column.

    Date fields are parsed with ISO-8601 format (yyyy-MM-dd).
    Monetary fields are cast to DECIMAL(18,2) for GAAP-compliant precision.
    line_item_count is cast to INT after extraction (LLM returns a string).
    """
    return (
        df
        # --- Vendor identification ---
        .withColumn(
            "invoice_number",
            get_json_object(col("extracted_json"), "$.invoiceNumber"),
        )
        .withColumn(
            "vendor_name",
            get_json_object(col("extracted_json"), "$.vendorName"),
        )
        .withColumn(
            "vendor_id",
            get_json_object(col("extracted_json"), "$.vendorId"),
        )
        # --- Monetary fields ---
        .withColumn(
            "total_amount",
            get_json_object(col("extracted_json"), "$.totalAmount")
            .cast("decimal(18,2)"),
        )
        .withColumn(
            "currency",
            get_json_object(col("extracted_json"), "$.currency"),
        )
        # --- Date fields ---
        .withColumn(
            "invoice_date",
            to_date(
                get_json_object(col("extracted_json"), "$.invoiceDate"),
                "yyyy-MM-dd",
            ),
        )
        .withColumn(
            "due_date",
            to_date(
                get_json_object(col("extracted_json"), "$.dueDate"),
                "yyyy-MM-dd",
            ),
        )
        # --- AP workflow fields ---
        .withColumn(
            "payment_terms",
            get_json_object(col("extracted_json"), "$.paymentTerms"),
        )
        .withColumn(
            "po_number",
            get_json_object(col("extracted_json"), "$.purchaseOrderNumber"),
        )
        .withColumn(
            "tax_amount",
            get_json_object(col("extracted_json"), "$.taxAmount")
            .cast("decimal(18,2)"),
        )
        .withColumn(
            "line_item_count",
            get_json_object(col("extracted_json"), "$.lineItemCount")
            .cast("int"),
        )
        # --- GL / approval fields ---
        .withColumn(
            "gl_account_code",
            get_json_object(col("extracted_json"), "$.glAccountCode"),
        )
        .withColumn(
            "approval_status",
            get_json_object(col("extracted_json"), "$.approvalStatus"),
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
                "invoice_number",
                "vendor_name",
                "total_amount",
                "due_date",
            ],
            confidence_threshold=DROP_CONFIDENCE_THRESHOLD,
            extra_table_properties={
                "docubricks.vertical":              "fs",
                "docubricks.regulatory_framework":  "Standard AP/AR, GAAP",
                "docubricks.review_threshold":      str(REVIEW_CONFIDENCE_THRESHOLD),
            },
            comment=(
                "Extracted structured fields for vendor invoices (AP workflow). "
                f"Drop threshold: avg_confidence_score >= {DROP_CONFIDENCE_THRESHOLD}. "
                f"Review threshold: avg_confidence_score >= {REVIEW_CONFIDENCE_THRESHOLD}. "
                "Rows below the review threshold are enqueued for AP review before payment. "
                "Regulatory alignment: Standard AP/AR, GAAP. "
                "Populated by Wave 2 InvoiceExtractorAgent."
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
    @dlt.expect_or_drop("min_confidence_60", f"avg_confidence_score >= {DROP_CONFIDENCE_THRESHOLD}")
    @dlt.expect_or_drop("invoice_number_present", "invoice_number IS NOT NULL")
    @dlt.expect_or_drop(
        "total_amount_valid",
        "total_amount IS NOT NULL AND total_amount > 0",
    )
    # -----------------------------------------------------------------------
    # Soft warnings — rows survive but violations are tracked in DLT event log
    # -----------------------------------------------------------------------
    @dlt.expect("due_date_present", "due_date IS NOT NULL")
    @dlt.expect("vendor_name_present", "vendor_name IS NOT NULL")
    def silver_extracted_invoice() -> "DataFrame":
        """
        Invoice Silver extraction table.

        Pipeline:
          1. Read stream from silver_route_invoice (produced by extract_router.py)
          2. Call ai_extract() with the active invoice schema prompt (databricks-dbrx-instruct)
          3. Flatten JSON result into typed columns via _flatten_invoice()
          4. DLT expectations enforce quality gates (see decorators above)
          5. Post-flatten: rows below REVIEW_CONFIDENCE_THRESHOLD (0.75) are enqueued
             for AP review via Lakebase — prevents low-confidence invoices from entering
             the payment workflow without human sign-off.
        """
        df = build_extraction_stream(
            document_type=DOCUMENT_TYPE,
            catalog_name=_catalog_name,
            confidence_threshold=DROP_CONFIDENCE_THRESHOLD,
            flatten_fn=_flatten_invoice,
            extra_columns=[
                "invoice_number",
                "vendor_name",
                "vendor_id",
                "total_amount",
                "currency",
                "invoice_date",
                "due_date",
                "payment_terms",
                "po_number",
                "tax_amount",
                "line_item_count",
                "gl_account_code",
                "approval_status",
            ],
        )

        # ------------------------------------------------------------------
        # AP REVIEW gate (0.75 threshold).
        #
        # Rows that survive the 0.60 DROP gate but fall below 0.75 are
        # written to the table AND enqueued for human review.  This prevents
        # questionable invoices from auto-approving into the payment run.
        #
        # The Lakebase write is a side-effect executed per partition via
        # mapInPandas, keeping the DLT streaming semantics intact.
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
                            # Priority 3 = standard AP review (lower than regulatory)
                            priority=3,
                        )
                        logger.info(
                            "Invoice enqueued for REVIEW: document_id=%s conf=%.4f",
                            row["document_id"],
                            row["avg_confidence_score"],
                        )
                    except Exception as exc:  # noqa: BLE001
                        # Log but do not fail the DLT batch — the row is still written
                        # to the table; a downstream reconciliation job handles any
                        # missed review_queue inserts.
                        logger.error(
                            "Failed to enqueue invoice for review: document_id=%s error=%s",
                            row.get("document_id", "unknown"),
                            exc,
                        )
                yield pdf

        # Apply review-queue side-effect without mutating the output schema.
        schema = df.schema
        df = df.mapInPandas(_enqueue_low_confidence_rows, schema=schema)

        return df
