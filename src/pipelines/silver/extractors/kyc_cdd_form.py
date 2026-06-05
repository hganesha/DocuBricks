# Databricks notebook source
# DocuBricks — Silver Extraction: KYC / CDD Form
# =================================================
# src/pipelines/silver/extractors/kyc_cdd_form.py
#
# Wave 2 ExtractorAgent notebook.
#
# Regulatory framework
# --------------------
#   - FinCEN CDD Rule (31 CFR § 1010.230) — Customer Due Diligence
#   - Bank Secrecy Act (BSA) / Anti-Money Laundering (AML)
#   - FFIEC BSA/AML Examination Manual
#   - NIST SP 800-63-4 (Identity Assurance)
#   - FATF Recommendations 10, 12, 22 (CDD / PEP / Beneficial Ownership)
#
# DLT graph position
# ------------------
#   silver_route_kyc_cdd_form  (view, extract_router.py)
#       └─ silver_extracted_kyc_cdd_form  (THIS TABLE)
#           └─ gold_fs_kyc_compliance_summary  (Wave 3 Gold)
#
# Confidence thresholds
# ---------------------
#   Drop threshold  : 0.65  (avg_confidence_score < 0.65 → row dropped)
#   Review threshold: 0.87  (avg_confidence_score < 0.87 → status = REVIEW)
#     KYC uses a higher review bar than mortgage (0.82) because BSA/AML
#     regulations impose strict obligations on financial institutions for
#     accurate customer identification, risk rating, and PEP/sanctions screening.
#
# DLT channel : PREVIEW
# Compute     : Serverless
# Target      : docubricks_prod.silver.silver_extracted_kyc_cdd_form
# Pipeline config keys: catalog_name, secret_scope

# COMMAND ----------

import dlt
from pyspark.sql.functions import (
    col,
    current_date,
    current_timestamp,
    get_json_object,
    lit,
    to_date,
    when,
)

from src.pipelines.silver.extractors._base import (
    STANDARD_TABLE_PROPERTIES,
    LakbaseHelper,
    build_extraction_stream,
    build_silver_table,
    get_extraction_prompt,
    update_extraction_status,
)

# COMMAND ----------
# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------

catalog_name: str = spark.conf.get("catalog_name")   # type: ignore[name-defined]  # noqa: F821
secret_scope: str = spark.conf.get("secret_scope")   # type: ignore[name-defined]  # noqa: F821

DOCUMENT_TYPE: str = "kyc_cdd_form"
EXTRACTION_MODEL: str = "databricks-claude-sonnet"   # wave1_schema.json: model_routing.kyc_cdd_form

# Confidence thresholds
DROP_THRESHOLD: float = 0.65   # DLT expect_or_drop: rows below this are discarded
REVIEW_THRESHOLD: float = 0.87  # Lakebase status → REVIEW if confidence in [0.65, 0.87)

# Allowed customer_type enum values (expanded set per task spec; supersedes
# the simplified prompt_v1.txt enum for the structured schema layer)
VALID_CUSTOMER_TYPES: tuple[str, ...] = (
    "Individual",
    "Business",
    "Trust",
    "Estate",
    "GovernmentEntity",
    "NonProfit",
    "FinancialInstitution",
    "Fund",
    "Joint",
    "Other",
)

# COMMAND ----------
# ---------------------------------------------------------------------------
# Lakebase connection pool (singleton for this notebook)
# ---------------------------------------------------------------------------

_lb = LakbaseHelper(secret_scope=secret_scope)

# COMMAND ----------
# ---------------------------------------------------------------------------
# Fallback extraction prompt
#
# Loaded when schema_registry.extraction_prompts is unavailable at startup.
# The registry version (prompt_v1.txt) takes precedence when reachable.
#
# The JSON schema mirrors the kycProfile structure expected by the Gold layer
# (gold_fs_kyc_compliance_summary) and downstream compliance reporting.
# ---------------------------------------------------------------------------

_FALLBACK_PROMPT: str = """\
You are a KYC/CDD document extraction specialist supporting BSA/AML compliance.

## REGULATORY CONTEXT
Extract fields in alignment with:
  - FinCEN CDD Rule (31 CFR § 1010.230)
  - FFIEC BSA/AML Examination Manual
  - FATF Recommendations 10, 12, 22

## TASK
Extract all fields below from the customer due diligence document text.
Return a single JSON object matching the schema. Use null for absent fields.
Set confidence to 0.0 for any null field. Never infer or hallucinate values.

## OUTPUT SCHEMA (JSON)
{
  "kycProfile": {
    "profileId": "<string: institution-assigned KYC profile identifier>",
    "customer": {
      "customerType": "<Individual|Business|Trust|Estate|GovernmentEntity|NonProfit|FinancialInstitution|Fund|Joint|Other>",
      "customerSegment": "<string: e.g. Retail, Private Banking, Commercial, Correspondent>",
      "relationshipStatus": "<Active|Inactive|Pending|Closed|Restricted>"
    },
    "riskAssessment": {
      "overallRiskRating": "<Low|Medium|High|Unrated>",
      "riskScore": "<number: 0.00–100.00>"
    },
    "dueDiligence": {
      "dueDiligenceLevel": "<Simplified|Standard|Enhanced>",
      "cipStatus": "<Completed|Pending|Waived|Failed>",
      "cddStatus": "<Completed|Pending|Expired|NotRequired>",
      "eddStatus": "<Completed|Pending|NotRequired|InProgress>"
    },
    "pepAndAdverseMedia": {
      "pepStatus": "<NotPEP|PEP|FormerPEP|PEPRelative|PEPAssociate|Unknown>"
    },
    "screening": {
      "overallScreeningStatus": "<Clear|PotentialMatch|ConfirmedMatch|Blocked|NotScreened>"
    },
    "beneficialOwnership": {
      "legalEntityCustomerIndicator": "<boolean: true if beneficial ownership data was collected>"
    },
    "monitoring": {
      "monitoringStatus": "<Active|Suspended|Enhanced|Terminated>",
      "periodicReview": {
        "nextReviewDate": "<ISO 8601 date: YYYY-MM-DD>"
      }
    }
  }
}

## RULES
1. customerType must be exactly one of the allowed enum values listed above.
2. pepStatus and sanctions screening status are REQUIRED fields — assign
   "Unknown" / "NotScreened" if the document is silent, never null.
3. legalEntityCustomerIndicator must be boolean: true only if the document
   explicitly states beneficial ownership information was collected.
4. riskScore must be a number between 0.00 and 100.00; use null if absent.
5. nextReviewDate must be ISO 8601 format (YYYY-MM-DD) or null.
6. Do not fabricate values — extraction confidence must reflect document evidence.
"""

# COMMAND ----------
# ---------------------------------------------------------------------------
# Field flattener
#
# Maps extracted JSON paths (kycProfile.*) to typed Spark columns.
# JSON path convention: $.kycProfile.<section>.<field>
#
# Column ordering follows the task specification exactly; audit columns
# (extracted_json, avg_confidence_score, field_confidences, extracted_at,
# ingested_date) are inherited from build_extraction_stream() via
# BASE_EXTRACTION_COLUMNS and do not need to be added here.
# ---------------------------------------------------------------------------


def _flatten_kyc(df):
    """
    Apply all KYC/CDD-specific typed column derivations to the extraction DataFrame.

    Parameters
    ----------
    df : DataFrame
        Output of ai_extract() with column `extracted_json` (string, JSON).

    Returns
    -------
    DataFrame with additional typed columns for every KYC/CDD schema field.

    JSON path reference (wave1_schema.json → kycProfile structure):
        $.kycProfile.profileId
        $.kycProfile.customer.customerType
        $.kycProfile.customer.customerSegment
        $.kycProfile.customer.relationshipStatus
        $.kycProfile.riskAssessment.overallRiskRating
        $.kycProfile.riskAssessment.riskScore
        $.kycProfile.dueDiligence.dueDiligenceLevel
        $.kycProfile.dueDiligence.cipStatus
        $.kycProfile.dueDiligence.cddStatus
        $.kycProfile.dueDiligence.eddStatus
        $.kycProfile.pepAndAdverseMedia.pepStatus
        $.kycProfile.screening.overallScreeningStatus
        $.kycProfile.beneficialOwnership.legalEntityCustomerIndicator
        $.kycProfile.monitoring.monitoringStatus
        $.kycProfile.monitoring.periodicReview.nextReviewDate
    """
    return (
        df
        # ------------------------------------------------------------------
        # Identity / Profile
        # ------------------------------------------------------------------
        .withColumn(
            "kyc_profile_id",
            get_json_object(col("extracted_json"), "$.kycProfile.profileId"),
        )
        # ------------------------------------------------------------------
        # Customer classification
        # ------------------------------------------------------------------
        .withColumn(
            "customer_type",
            get_json_object(col("extracted_json"), "$.kycProfile.customer.customerType"),
        )
        .withColumn(
            "customer_segment",
            get_json_object(col("extracted_json"), "$.kycProfile.customer.customerSegment"),
        )
        .withColumn(
            "relationship_status",
            get_json_object(col("extracted_json"), "$.kycProfile.customer.relationshipStatus"),
        )
        # ------------------------------------------------------------------
        # Risk assessment
        # ------------------------------------------------------------------
        .withColumn(
            "overall_risk_rating",
            get_json_object(col("extracted_json"), "$.kycProfile.riskAssessment.overallRiskRating"),
        )
        .withColumn(
            "risk_score",
            get_json_object(col("extracted_json"), "$.kycProfile.riskAssessment.riskScore")
            .cast("decimal(5,2)"),
        )
        # ------------------------------------------------------------------
        # Due diligence program status
        # ------------------------------------------------------------------
        .withColumn(
            "due_diligence_level",
            get_json_object(col("extracted_json"), "$.kycProfile.dueDiligence.dueDiligenceLevel"),
        )
        .withColumn(
            "cip_status",
            get_json_object(col("extracted_json"), "$.kycProfile.dueDiligence.cipStatus"),
        )
        .withColumn(
            "cdd_status",
            get_json_object(col("extracted_json"), "$.kycProfile.dueDiligence.cddStatus"),
        )
        .withColumn(
            "edd_status",
            get_json_object(col("extracted_json"), "$.kycProfile.dueDiligence.eddStatus"),
        )
        # ------------------------------------------------------------------
        # PEP and adverse media
        # Regulatory note: PEP status must always be present.  The DLT
        # @dlt.expect() below warns when absent; the extraction prompt
        # instructs the model to use "Unknown" rather than null, so a null
        # here indicates a schema mismatch that should be investigated.
        # ------------------------------------------------------------------
        .withColumn(
            "pep_status",
            get_json_object(col("extracted_json"), "$.kycProfile.pepAndAdverseMedia.pepStatus"),
        )
        # ------------------------------------------------------------------
        # Sanctions screening
        # Regulatory note: OFAC / UN / EU list screening is a BSA obligation.
        # A null value here means the document did not record a screening
        # result — this should trigger an EDD workflow in the Gold layer.
        # ------------------------------------------------------------------
        .withColumn(
            "sanctions_screening_status",
            get_json_object(col("extracted_json"), "$.kycProfile.screening.overallScreeningStatus"),
        )
        # ------------------------------------------------------------------
        # Beneficial ownership
        # Regulatory note: FinCEN CDD Rule requires covered financial
        # institutions to collect beneficial ownership information for legal
        # entity customers with ≥25% ownership threshold.
        # legalEntityCustomerIndicator is a boolean in the JSON; cast the
        # string "true"/"false" to a proper boolean column.
        # ------------------------------------------------------------------
        .withColumn(
            "beneficial_ownership_collected",
            when(
                get_json_object(
                    col("extracted_json"),
                    "$.kycProfile.beneficialOwnership.legalEntityCustomerIndicator",
                ).isin("true", "True", "TRUE", "1"),
                lit(True),
            )
            .when(
                get_json_object(
                    col("extracted_json"),
                    "$.kycProfile.beneficialOwnership.legalEntityCustomerIndicator",
                ).isin("false", "False", "FALSE", "0"),
                lit(False),
            )
            .otherwise(lit(None).cast("boolean")),
        )
        # ------------------------------------------------------------------
        # Ongoing monitoring
        # ------------------------------------------------------------------
        .withColumn(
            "monitoring_status",
            get_json_object(col("extracted_json"), "$.kycProfile.monitoring.monitoringStatus"),
        )
        .withColumn(
            "next_review_date",
            to_date(
                get_json_object(
                    col("extracted_json"),
                    "$.kycProfile.monitoring.periodicReview.nextReviewDate",
                ),
                "yyyy-MM-dd",
            ),
        )
    )


# COMMAND ----------
# ---------------------------------------------------------------------------
# DLT table: silver_extracted_kyc_cdd_form
#
# Expectations — stricter than mortgage (BSA/AML regulatory obligations):
#
#   expect_or_fail  : document_id IS NOT NULL
#     → pipeline-level invariant; a missing document_id breaks all downstream
#       joins in the Gold layer and compliance audit tables.  Fail the entire
#       pipeline row — this should never occur; if it does, investigate the
#       bronze/parse layer immediately.
#
#   expect_or_drop  : avg_confidence_score >= 0.65
#     → base extraction quality gate.  Rows below 0.65 are too noisy for
#       regulatory use and are discarded rather than silently corrupting the
#       compliance dataset.
#
#   expect_or_drop  : kyc_profile_id IS NOT NULL
#     → every KYC record must have an institution-assigned profile identifier
#       for traceability.  Without it, the row cannot be linked to the
#       customer master record.
#
#   expect_or_drop  : customer_type IN (...)
#     → invalid customer_type values break downstream Gold aggregations and
#       regulatory reporting buckets.  Drop the row; the review_queue (Lakebase)
#       will capture it for human remediation.
#
#   expect (warn)   : pep_status IS NOT NULL
#     → PEP screening may legitimately be absent for customers under Simplified
#       Due Diligence (SDD).  Warn rather than drop so SDD records are not
#       silently discarded; the Gold layer handles NULL pep_status as "not
#       screened" and flags it for periodic review.
#
#   expect (warn)   : sanctions_screening_status IS NOT NULL
#     → OFAC/UN screening results should always be recorded.  A null here
#       indicates the screening result was not captured in the document.
#       The Gold compliance summary will surface these rows for analyst review.
# ---------------------------------------------------------------------------

@dlt.table(
    **build_silver_table(
        document_type=DOCUMENT_TYPE,
        required_fields=[
            "kyc_profile_id",
            "customer_type",
            "overall_risk_rating",
            "pep_status",
            "sanctions_screening_status",
            "due_diligence_level",
            "beneficial_ownership_collected",
            "risk_score",
            "relationship_status",
        ],
        confidence_threshold=DROP_THRESHOLD,
        extra_table_properties={
            "docubricks.vertical":              "fs",
            "docubricks.regulatory_framework":  "FinCEN_CDD,BSA,FFIEC,NIST_SP800-63-4",
            "docubricks.review_threshold":      str(REVIEW_THRESHOLD),
            "docubricks.extraction_model":      EXTRACTION_MODEL,
            "docubricks.pii_tier":              "tier_1",   # highest PII sensitivity
        },
        comment=(
            "Extracted structured fields for KYC / CDD forms. "
            "Regulatory alignment: FinCEN CDD Rule (31 CFR § 1010.230), BSA/AML, "
            "FFIEC BSA/AML Examination Manual, NIST SP 800-63-4. "
            "Required fields: kyc_profile_id, customer_type, overall_risk_rating, "
            "pep_status, sanctions_screening_status, due_diligence_level, "
            "beneficial_ownership_collected, risk_score, relationship_status. "
            f"Drop threshold: {DROP_THRESHOLD}. Review threshold: {REVIEW_THRESHOLD}. "
            "Populated by Wave 2 KYCExtractorAgent. "
            "Downstream: docubricks_prod.gold.fs_kyc_compliance_summary."
        ),
    )
)
# ------------------------------------------------------------------
# System invariant — fail the row (and alert) if document_id is absent.
# This guard is placed first because all subsequent expectations and
# Gold-layer joins depend on it.
# ------------------------------------------------------------------
@dlt.expect_or_fail(
    "document_id_present",
    "document_id IS NOT NULL",
)
# ------------------------------------------------------------------
# Extraction quality gate — rows with insufficient extraction confidence
# are discarded rather than admitted to the compliance dataset.
# ------------------------------------------------------------------
@dlt.expect_or_drop(
    "extraction_min_confidence",
    f"avg_confidence_score >= {DROP_THRESHOLD}",
)
# ------------------------------------------------------------------
# Profile identifier — required for downstream Gold joins and audit.
# ------------------------------------------------------------------
@dlt.expect_or_drop(
    "kyc_profile_id_present",
    "kyc_profile_id IS NOT NULL",
)
# ------------------------------------------------------------------
# Customer type — must be one of the documented enum values so that
# downstream Gold aggregations and regulatory reports are stable.
# ------------------------------------------------------------------
@dlt.expect_or_drop(
    "customer_type_valid_enum",
    "customer_type IN ("
    "'Individual','Business','Trust','Estate','GovernmentEntity',"
    "'NonProfit','FinancialInstitution','Fund','Joint','Other'"
    ")",
)
# ------------------------------------------------------------------
# PEP screening — warn only; Simplified DD customers may have no PEP
# screening record on file.  The Gold layer handles nulls explicitly.
# ------------------------------------------------------------------
@dlt.expect(
    "pep_status_present",
    "pep_status IS NOT NULL",
)
# ------------------------------------------------------------------
# Sanctions screening — warn only; a null here means the document did
# not record an OFAC/UN screening outcome and needs analyst review.
# ------------------------------------------------------------------
@dlt.expect(
    "sanctions_screening_status_present",
    "sanctions_screening_status IS NOT NULL",
)
def silver_extracted_kyc_cdd_form():
    """
    Silver extraction table for KYC / CDD forms.

    Reads from  : silver_route_kyc_cdd_form  (DLT view, extract_router.py)
    Writes to   : docubricks_prod.silver.silver_extracted_kyc_cdd_form
    Model       : databricks-claude-sonnet (wave1_schema.json model_routing)
    Cluster by  : tenant_id, document_type, ingested_date

    Schema fields (beyond BASE_EXTRACTION_COLUMNS)
    -----------------------------------------------
    kyc_profile_id                STRING   $.kycProfile.profileId
    customer_type                 STRING   $.kycProfile.customer.customerType
    customer_segment              STRING   $.kycProfile.customer.customerSegment
    relationship_status           STRING   $.kycProfile.customer.relationshipStatus
    overall_risk_rating           STRING   $.kycProfile.riskAssessment.overallRiskRating
    risk_score                    DECIMAL(5,2) $.kycProfile.riskAssessment.riskScore
    due_diligence_level           STRING   $.kycProfile.dueDiligence.dueDiligenceLevel
    cip_status                    STRING   $.kycProfile.dueDiligence.cipStatus
    cdd_status                    STRING   $.kycProfile.dueDiligence.cddStatus
    edd_status                    STRING   $.kycProfile.dueDiligence.eddStatus
    pep_status                    STRING   $.kycProfile.pepAndAdverseMedia.pepStatus
    sanctions_screening_status    STRING   $.kycProfile.screening.overallScreeningStatus
    beneficial_ownership_collected BOOLEAN  $.kycProfile.beneficialOwnership.legalEntityCustomerIndicator
    monitoring_status             STRING   $.kycProfile.monitoring.monitoringStatus
    next_review_date              DATE     $.kycProfile.monitoring.periodicReview.nextReviewDate

    Plus BASE_EXTRACTION_COLUMNS (inherited):
    document_id, tenant_id, vertical, file_ext, source_path, file_size_bytes,
    ingested_at, ingested_date, page_count, document_type,
    classification_confidence, extracted_json, avg_confidence_score,
    field_confidences, extraction_model, extracted_at
    """
    return build_extraction_stream(
        document_type=DOCUMENT_TYPE,
        catalog_name=catalog_name,
        confidence_threshold=DROP_THRESHOLD,
        flatten_fn=_flatten_kyc,
        fallback_prompt=_FALLBACK_PROMPT,
    )


# COMMAND ----------
# ---------------------------------------------------------------------------
# Post-extraction Lakebase status update
#
# Runs as a foreachBatch sink on the extracted stream.  For each micro-batch,
# we iterate the extracted rows and:
#   1. Transition status: CLASSIFIED → EXTRACTING → EXTRACTED (or REVIEW).
#   2. Enqueue REVIEW documents into review_queue with priority=1 (highest)
#      because KYC non-compliance carries BSA penalty exposure.
#
# This runs OUTSIDE the @dlt.table function so that Lakebase writes are not
# inside the DLT planning context (which is pure DataFrame / lazy evaluation).
#
# Note: DLT Serverless does not natively expose forEachBatch on managed
# streaming tables.  In production this hook is wired via a companion
# streaming job that reads the CDF feed of silver_extracted_kyc_cdd_form and
# drives Lakebase updates.  The implementation is shown here as the canonical
# pattern for the KYC extractor.
# ---------------------------------------------------------------------------


def _update_kyc_lakebase_status(micro_batch_df, batch_id: int) -> None:
    """
    foreachBatch function: update Lakebase document_registry for each extracted row.

    Called by the companion CDF streaming job (not inline in the DLT pipeline).
    Kept in this module so the logic is co-located with the extractor it serves.

    Parameters
    ----------
    micro_batch_df : DataFrame
        Batch of rows from silver_extracted_kyc_cdd_form (CDF feed).
    batch_id       : int
        Spark Structured Streaming batch identifier.
    """
    pipeline_run_id = str(batch_id)

    rows = micro_batch_df.select(
        "document_id",
        "tenant_id",
        "avg_confidence_score",
    ).collect()

    for row in rows:
        doc_id = row["document_id"]
        tenant = row["tenant_id"]
        conf = float(row["avg_confidence_score"]) if row["avg_confidence_score"] is not None else 0.0

        try:
            # Transition: CLASSIFIED → EXTRACTING → EXTRACTED / REVIEW
            update_extraction_status(
                document_id=doc_id,
                extraction_conf=conf,
                confidence_threshold=REVIEW_THRESHOLD,   # KYC uses 0.87, not 0.65
                secret_scope=secret_scope,
                pipeline_run_id=pipeline_run_id,
            )

            # Enqueue low-confidence rows for human review at highest priority.
            # Priority 1 = highest urgency (KYC/BSA SLA: 48-hour review window)
            if conf < REVIEW_THRESHOLD:
                _lb.enqueue_for_review(
                    document_id=doc_id,
                    tenant_id=tenant,
                    review_reason="LOW_CONFIDENCE",
                    priority=1,
                )

        except Exception as exc:  # noqa: BLE001
            # Log and continue — a Lakebase failure must not abort the DLT pipeline.
            # The CDF-based companion job has its own retry / dead-letter mechanism.
            import logging as _logging
            _logging.getLogger("docubricks.extractors.kyc_cdd_form").error(
                "Lakebase status update failed for document_id=%s batch_id=%s: %s",
                doc_id,
                batch_id,
                exc,
            )
