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
#     └─ silver_route_<doc_type>  (DLT view, one per entry in schema_catalog.json)
#
# Route views are registered dynamically from schema_catalog.json so that adding
# a new schema bundle requires no edits to this file.  Falls back to the original
# Phase 1 hard-coded list if the catalog cannot be read.
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
import json
import os
from pathlib import Path

import dlt
from pyspark.sql.functions import col, current_timestamp

# ---------------------------------------------------------------------------
# Catalog-driven document-type list
# ---------------------------------------------------------------------------
_CATALOG_FALLBACK = [
    "mortgage_application",
    "kyc_cdd_form",
    "aml_sar",
    "invoice",
]


def _load_supported_doc_types() -> list[str]:
    """
    Load doc types to route from schema_catalog.json.
    Falls back to _CATALOG_FALLBACK if the catalog cannot be read.
    Reads from DOCUBRICKS_SCHEMAS_PATH env var, then common Databricks workspace paths.
    """
    search_paths = []
    env_path = os.environ.get("DOCUBRICKS_SCHEMAS_PATH")
    if env_path:
        search_paths.append(Path(env_path) / "schema_catalog.json")
    # Common Databricks workspace paths
    search_paths += [
        Path("/Workspace/Shared/docubricks/Schemas/schema_catalog.json"),
        Path("/dbfs/docubricks/Schemas/schema_catalog.json"),
        # Local dev / CI path relative to this file
        Path(__file__).resolve().parents[4] / "Schemas" / "schema_catalog.json",
    ]
    for catalog_path in search_paths:
        try:
            data = json.loads(catalog_path.read_text(encoding="utf-8"))
            doc_types = [
                e["doc_type"]
                for e in data.get("document_types", [])
                if (
                    isinstance(e, dict)
                    and e.get("availability") == "available"
                    and e.get("rollout_status") == "registry_ready"
                )
            ]
            if doc_types:
                return doc_types
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            continue
    return list(_CATALOG_FALLBACK)


SUPPORTED_DOC_TYPES: list[str] = _load_supported_doc_types()

# ---------------------------------------------------------------------------
# Route views — one per supported document type (registered dynamically)
#
# Using @dlt.view (not @dlt.table) means no Delta table is written — these are
# logical views that exist only within the DLT graph.  This keeps storage costs
# at zero for the routing layer; the extractor tables materialise the subsets.
#
# Column additions at routing time:
# - routed_at       : timestamp of routing event (for latency monitoring)
# - pipeline_stage  : literal tag consumed by platform_health Gold view
# ---------------------------------------------------------------------------


def _register_route_view(doc_type: str) -> None:
    """Register one DLT route view for doc_type using a closure."""
    @dlt.view(
        name=f"silver_route_{doc_type}",
        comment=(
            f"Filtered view of silver_classified for document_type = '{doc_type}'. "
            f"Read by silver_extracted_{doc_type} in Wave 2."
        ),
    )
    def _route():
        return (
            dlt.read_stream("silver_classified")
            .filter(col("document_type") == doc_type)
            .withColumn("routed_at",      current_timestamp())
            .withColumn("pipeline_stage", col("document_type"))
        )


for _doc_type in SUPPORTED_DOC_TYPES:
    _register_route_view(_doc_type)


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
        .filter(col("document_type").isin(SUPPORTED_DOC_TYPES))
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
        .filter(~col("document_type").isin(SUPPORTED_DOC_TYPES))
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
