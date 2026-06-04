# Databricks notebook source
# DocuBricks — Silver Extract Router
# Layer 2 (continued): silver_classified → per-document-type filtered views
#
# This notebook runs in the same DLT pipeline as parse_classify.py.
# It creates a fan-out: one DLT streaming view per document type that the
# Wave 2 ExtractorAgent notebooks will read via dlt.read_stream().
#
# Routing pattern
# ---------------
#   silver_classified
#     └─ silver_route_mortgage_application  (DLT view)
#     └─ silver_route_kyc_cdd_form          (DLT view)
#     └─ silver_route_aml_sar               (DLT view)
#     └─ silver_route_invoice               (DLT view)
#
# Each route view is a filtered subset of silver_classified.
# Extractor tables (Wave 2) call:
#     dlt.read_stream("silver_route_{document_type}")
# rather than filtering silver_classified themselves, which centralises the
# routing logic and prevents redundant filter expression duplication.
#
# DLT channel: PREVIEW  |  Compute: Serverless
# Target schema: docubricks_prod.silver
# Pipeline config keys: catalog_name, secret_scope

# COMMAND ----------
import dlt
from pyspark.sql.functions import col, current_timestamp

# ---------------------------------------------------------------------------
# Phase 1 document types — extend this list as new verticals are onboarded
# ---------------------------------------------------------------------------
PHASE1_DOCUMENT_TYPES = [
    "mortgage_application",
    "kyc_cdd_form",
    "aml_sar",
    "invoice",
]

# ---------------------------------------------------------------------------
# Route views — one per document type
#
# Using @dlt.view (not @dlt.table) means no Delta table is written — these are
# logical views that exist only within the DLT graph.  This keeps storage costs
# at zero for the routing layer; the extractor tables materialise the subsets.
#
# Column additions at routing time:
# - routed_at       : timestamp of routing event (for latency monitoring)
# - pipeline_stage  : literal tag consumed by platform_health Gold view
# ---------------------------------------------------------------------------

@dlt.view(
    name="silver_route_mortgage_application",
    comment=(
        "Filtered view of silver_classified for document_type = 'mortgage_application'. "
        "Read by silver_extracted_mortgage_application in Wave 2."
    ),
)
def silver_route_mortgage_application():
    """
    Route: mortgage application documents.

    Downstream extractor table (Wave 2):
        silver_extracted_mortgage_application
    Key fields available:
        document_id, tenant_id, vertical, parsed_text, page_count,
        classification_confidence, ingested_date
    """
    return (
        dlt.read_stream("silver_classified")
        .filter(col("document_type") == "mortgage_application")
        .withColumn("routed_at",      current_timestamp())
        .withColumn("pipeline_stage", col("document_type"))
    )


@dlt.view(
    name="silver_route_kyc_cdd_form",
    comment=(
        "Filtered view of silver_classified for document_type = 'kyc_cdd_form'. "
        "Read by silver_extracted_kyc_cdd_form in Wave 2."
    ),
)
def silver_route_kyc_cdd_form():
    """
    Route: KYC / CDD form documents.

    Downstream extractor table (Wave 2):
        silver_extracted_kyc_cdd_form
    """
    return (
        dlt.read_stream("silver_classified")
        .filter(col("document_type") == "kyc_cdd_form")
        .withColumn("routed_at",      current_timestamp())
        .withColumn("pipeline_stage", col("document_type"))
    )


@dlt.view(
    name="silver_route_aml_sar",
    comment=(
        "Filtered view of silver_classified for document_type = 'aml_sar'. "
        "Read by silver_extracted_aml_sar in Wave 2."
    ),
)
def silver_route_aml_sar():
    """
    Route: AML Suspicious Activity Report documents.

    Downstream extractor table (Wave 2):
        silver_extracted_aml_sar
    """
    return (
        dlt.read_stream("silver_classified")
        .filter(col("document_type") == "aml_sar")
        .withColumn("routed_at",      current_timestamp())
        .withColumn("pipeline_stage", col("document_type"))
    )


@dlt.view(
    name="silver_route_invoice",
    comment=(
        "Filtered view of silver_classified for document_type = 'invoice'. "
        "Read by silver_extracted_invoice in Wave 2."
    ),
)
def silver_route_invoice():
    """
    Route: Invoice / accounts payable documents.

    Downstream extractor table (Wave 2):
        silver_extracted_invoice
    """
    return (
        dlt.read_stream("silver_classified")
        .filter(col("document_type") == "invoice")
        .withColumn("routed_at",      current_timestamp())
        .withColumn("pipeline_stage", col("document_type"))
    )


# ---------------------------------------------------------------------------
# Routing audit table
#
# This table records how many documents were routed to each type per micro-batch.
# It does NOT store the document rows (those live in the route views / extractor
# tables).  This is a lightweight accounting record for the platform_health Gold
# pipeline and the operations dashboard.
# ---------------------------------------------------------------------------

@dlt.table(
    name="silver_routing_audit",
    comment=(
        "Routing audit: count of documents routed to each document type per day. "
        "Lightweight operational accounting — does not duplicate document rows."
    ),
    table_properties={
        "delta.enableChangeDataFeed":       "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact":   "true",
        "quality":                          "silver",
        "docubricks.layer":                 "silver",
        "docubricks.stage":                 "routing_audit",
    },
)
@dlt.expect_or_fail("document_id_in_audit", "document_id IS NOT NULL")
def silver_routing_audit():
    """
    One row per document that passes through the router.

    Columns:
    - document_id           : natural key
    - tenant_id             : for per-tenant monitoring
    - document_type         : the route this document was sent to
    - classification_confidence : confidence at routing time
    - ingested_date         : date partition for Gold aggregations
    - routed_at             : routing timestamp
    - route_target          : name of the destination extractor table (string)
    - review_required       : true when confidence is in the [0.70, 0.80) range
    """
    from pyspark.sql.functions import lit, when

    return (
        dlt.read_stream("silver_classified")
        .filter(col("document_type").isin(PHASE1_DOCUMENT_TYPES))
        .withColumn("routed_at", current_timestamp())
        .withColumn(
            "route_target",
            col("document_type"),  # matches the view name pattern
        )
        .withColumn(
            "review_required",
            when(col("classification_confidence") < 0.80, lit(True)).otherwise(lit(False)),
        )
        .select(
            "document_id",
            "tenant_id",
            "vertical",
            "document_type",
            "classification_confidence",
            "ingested_date",
            "routed_at",
            "route_target",
            "review_required",
        )
    )


# ---------------------------------------------------------------------------
# Unrouted documents — doc types not in Phase 1
#
# These are valid, high-confidence classified documents whose type is not yet
# supported by an extractor.  Capturing them here prevents data loss and lets
# the platform report on unmet demand for new extractors.
# ---------------------------------------------------------------------------

@dlt.table(
    name="silver_unrouted",
    comment=(
        "Classified documents whose document_type has no Phase 1 extractor. "
        "Preserved for Wave 3+ extractor implementation. Never deleted."
    ),
    table_properties={
        "delta.enableChangeDataFeed":       "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "quality":                          "silver",
        "docubricks.layer":                 "silver",
        "docubricks.stage":                 "unrouted",
    },
)
def silver_unrouted():
    """
    Captures documents for which no extractor exists yet.

    Wave 3+ ExtractorAgents should check this table first when assessing backlog
    for a new document type.
    """
    return (
        dlt.read_stream("silver_classified")
        .filter(~col("document_type").isin(PHASE1_DOCUMENT_TYPES))
        .withColumn("routed_at", current_timestamp())
        .select(
            "document_id",
            "tenant_id",
            "vertical",
            "document_type",
            "classification_confidence",
            "ingested_date",
            "parsed_text",
            "page_count",
            "routed_at",
        )
    )
