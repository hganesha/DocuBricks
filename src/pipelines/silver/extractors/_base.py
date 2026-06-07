"""
DocuBricks — Extractor Base Module
====================================
src/pipelines/silver/extractors/_base.py

NOT a DLT notebook.  This module is imported by Wave 2 ExtractorAgent notebooks.

Purpose
-------
Provides the canonical pattern for all Silver extraction tables:
    1. Read from the typed route view in silver (silver_route_{document_type})
    2. Call ai_extract() with a versioned schema prompt from schema_registry
    3. Flatten the JSON result into typed columns
    4. Apply DLT expectations (system invariants + quality rules)
    5. Write Lakebase status updates at each stage

Usage in a Wave 2 extractor notebook
-------------------------------------
    from src.pipelines.silver.extractors._base import (
        build_silver_table,
        get_extraction_prompt,
        update_extraction_status,
        STANDARD_TABLE_PROPERTIES,
    )

    # Define doc-type-specific field flatteners
    def flatten_mortgage(df):
        return (
            df
            .withColumn("loan_amount",
                get_json_object(col("extracted_json"), "$.loan.requestedLoanAmount")
                .cast("decimal(18,2)"))
            .withColumn("loan_purpose",
                get_json_object(col("extracted_json"), "$.loan.loanPurpose"))
            ...
        )

    # Register the DLT table
    @dlt.table(
        **build_silver_table(
            document_type="mortgage_application",
            required_fields=["loan_amount", "loan_purpose"],
            confidence_threshold=0.65,
            extra_table_properties={"docubricks.vertical": "fs"},
        )
    )
    @dlt.expect_or_fail("document_id_present", "document_id IS NOT NULL")
    @dlt.expect_or_drop("required_loan_fields",
                        "loan_amount IS NOT NULL AND loan_purpose IS NOT NULL")
    @dlt.expect_or_drop("extraction_min_confidence", "avg_confidence_score >= 0.65")
    def silver_extracted_mortgage_application():
        return build_extraction_stream(
            document_type="mortgage_application",
            confidence_threshold=0.65,
            flatten_fn=flatten_mortgage,
        )

Public API
----------
- STANDARD_TABLE_PROPERTIES           : dict  — base Delta properties for all extractor tables
- build_silver_table(...)              : dict  — kwargs for @dlt.table decorator
- get_extraction_prompt(...)           : str   — versioned schema prompt from registry
- build_extraction_stream(...)         : DataFrame — DLT streaming table body
- update_extraction_status(...)        : None  — Lakebase EXTRACTING/EXTRACTED/REVIEW update
- enqueue_for_extraction_review(...)   : None  — Lakebase review_queue insert
- LakbaseHelper                        : class — connection pool wrapper for extractor notebooks
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import psycopg2
import psycopg2.pool

# PySpark / DLT imports are resolved at runtime inside Databricks
# Do not import at module level — this file is also used in unit tests off-cluster
try:
    import dlt
    from pyspark.sql import DataFrame
    from pyspark.sql.functions import (
        col, current_timestamp, expr, get_json_object, lit, to_date, when
    )
    _IN_DATABRICKS = True
except ImportError:
    _IN_DATABRICKS = False

logger = logging.getLogger("docubricks.extractors._base")


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def _get_schema_model(catalog_name: str, document_type: str) -> str:
    """
    Read the primary extraction model for document_type from schema_model_routing.
    Falls back to claude-sonnet if the registry is unavailable or returns no row.
    Safe to call in unit tests — returns the fallback when not in Databricks.
    """
    if not _IN_DATABRICKS:
        return "databricks-claude-sonnet"
    try:
        row = (
            spark.table(f"{catalog_name}.schema_registry.schema_model_routing")  # type: ignore[name-defined]  # noqa: F821
            .filter(
                (col("doc_type") == document_type) & (col("is_active") == True)  # noqa: E712
            )
            .first()
        )
        if row is not None and row["model_endpoint"]:
            return str(row["model_endpoint"])
    except Exception as exc:
        logger.warning(
            "Could not read schema_model_routing for document_type=%s: %s",
            document_type,
            exc,
        )
    return "databricks-claude-sonnet"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default confidence threshold for extraction quality checks
DEFAULT_CONFIDENCE_THRESHOLD: float = 0.65

# Base Delta table properties applied to every extractor table
STANDARD_TABLE_PROPERTIES: dict[str, str] = {
    "delta.enableChangeDataFeed":           "true",
    "delta.autoOptimize.optimizeWrite":     "true",
    "delta.autoOptimize.autoCompact":       "true",
    "delta.enableDeletionVectors":          "true",
    "delta.logRetentionDuration":           "interval 30 days",
    "delta.deletedFileRetentionDuration":   "interval 14 days",
    "quality":                              "silver",
    "docubricks.layer":                     "silver",
    "docubricks.stage":                     "extracted",
}

# Columns emitted by build_extraction_stream() before flatten_fn is applied.
# Extractors can select from these plus any columns their flatten_fn adds.
BASE_EXTRACTION_COLUMNS = [
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
    "extracted_json",
    "avg_confidence_score",
    "field_confidences",
    "extraction_model",
    "extracted_at",
]

# ---------------------------------------------------------------------------
# Lakebase helper class
# ---------------------------------------------------------------------------

class LakbaseHelper:
    """
    Thread-safe Lakebase (PostgreSQL) connection pool wrapper.

    Instantiate once per extractor notebook at module level:

        _lb = LakbaseHelper(secret_scope="docubricks-prod")

    Then call status update methods as needed.
    """

    def __init__(
        self,
        secret_scope: str = "docubricks-prod",
        min_conn: int = 1,
        max_conn: int = 8,
    ) -> None:
        self._secret_scope = secret_scope
        self._min_conn = min_conn
        self._max_conn = max_conn
        self._pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None

    def _ensure_pool(self) -> psycopg2.pool.ThreadedConnectionPool:
        if self._pool is None:
            # dbutils is available as a global in Databricks notebooks
            conn_string = dbutils.secrets.get(  # type: ignore[name-defined]  # noqa: F821
                scope=self._secret_scope,
                key="lakebase-conn-string",
            )
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self._min_conn,
                maxconn=self._max_conn,
                dsn=conn_string,
            )
        return self._pool

    def _get_conn(self) -> psycopg2.extensions.connection:
        return self._ensure_pool().getconn()

    def _release_conn(self, conn: psycopg2.extensions.connection) -> None:
        self._ensure_pool().putconn(conn)

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def begin_extraction(self, document_id: str, pipeline_run_id: str) -> None:
        """
        Transition document_registry status: CLASSIFIED → EXTRACTING.

        The WHERE clause guards against double-processing: if status is already
        EXTRACTING or beyond, this is a no-op (idempotent).
        """
        self._execute(
            """
            UPDATE document_registry
               SET status         = 'EXTRACTING',
                   pipeline_run_id = %s
             WHERE document_id = %s
               AND status = 'CLASSIFIED';
            """,
            (pipeline_run_id, document_id),
        )

    def complete_extraction(
        self,
        document_id: str,
        extraction_conf: float,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        """
        Transition document_registry status: EXTRACTING → EXTRACTED or REVIEW.

        Rows below the confidence threshold are flagged as REVIEW rather than
        EXTRACTED so the human review workflow can pick them up.
        """
        new_status = "EXTRACTED" if extraction_conf >= confidence_threshold else "REVIEW"
        self._execute(
            """
            UPDATE document_registry
               SET status         = %s,
                   extraction_conf = %s,
                   extracted_at    = NOW()
             WHERE document_id = %s
               AND status = 'EXTRACTING';
            """,
            (new_status, extraction_conf, document_id),
        )

    def fail_extraction(self, document_id: str, reason: str) -> None:
        """Mark a document as FAILED in the registry with a failure reason."""
        self._execute(
            """
            UPDATE document_registry
               SET status         = 'FAILED',
                   failure_reason = %s
             WHERE document_id = %s;
            """,
            (reason, document_id),
        )

    def enqueue_for_review(
        self,
        document_id: str,
        tenant_id: str,
        review_reason: str = "LOW_CONFIDENCE",
        priority: int = 3,
    ) -> None:
        """
        Insert into review_queue and update document_registry.status = REVIEW.

        ON CONFLICT DO NOTHING makes this idempotent — replaying will not
        create duplicate review items.

        review_reason must be one of:
            LOW_CONFIDENCE | CLASSIFICATION_AMBIGUOUS | SCHEMA_VIOLATION | HUMAN_FLAGGED
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO review_queue (
                        document_id, tenant_id, review_reason, priority, sla_due_at
                    ) VALUES (
                        %s, %s, %s, %s, NOW() + INTERVAL '48 hours'
                    )
                    ON CONFLICT DO NOTHING;
                    """,
                    (document_id, tenant_id, review_reason, priority),
                )
                cur.execute(
                    """
                    UPDATE document_registry
                       SET status = 'REVIEW'
                     WHERE document_id = %s
                       AND status NOT IN ('COMPLETE', 'QUARANTINE');
                    """,
                    (document_id,),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._release_conn(conn)

    def log_extraction_audit(
        self,
        document_id: str,
        document_type: str,
        field_name: str,
        extracted_value: Optional[str],
        confidence: Optional[float],
        eval_run_id: Optional[str] = None,
    ) -> None:
        """
        Write a single field-level extraction audit record.

        Called by the post-pipeline MLflow eval harness (Wave 3), not inline
        during DLT streaming.  Exposed here so eval scripts can reuse the
        connection pool.
        """
        self._execute(
            """
            INSERT INTO extraction_audit (
                document_id, document_type, field_name,
                extracted_value, confidence, eval_run_id
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (document_id, document_type, field_name, extracted_value, confidence, eval_run_id),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute(self, sql: str, params: tuple) -> None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._release_conn(conn)

    def close(self) -> None:
        """Close all connections in the pool. Call on notebook teardown."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None


# ---------------------------------------------------------------------------
# Prompt retrieval
# ---------------------------------------------------------------------------

def get_extraction_prompt(
    catalog_name: str,
    document_type: str,
    fallback_prompt: Optional[str] = None,
) -> str:
    """
    Load the latest active extraction prompt for document_type from the
    schema_registry.extraction_prompts table.

    Parameters
    ----------
    catalog_name    : Unity Catalog name (e.g. 'docubricks_prod')
    document_type   : e.g. 'mortgage_application'
    fallback_prompt : returned if the registry query fails; set to None to
                      raise instead of falling back

    Returns
    -------
    str : the prompt text to pass to ai_extract()

    Raises
    ------
    ValueError if no active prompt is found and fallback_prompt is None.
    """
    if not _IN_DATABRICKS:
        raise RuntimeError("get_extraction_prompt() requires a Databricks runtime.")

    try:
        row = (
            spark.table(f"{catalog_name}.schema_registry.extraction_prompts")  # type: ignore[name-defined]  # noqa: F821
            .filter(
                (col("document_type") == document_type)
                & (col("is_active") == True)  # noqa: E712
            )
            .orderBy(col("version").desc())
            .first()
        )
        if row is not None:
            return row["prompt_text"]
    except Exception as exc:
        logger.warning("Could not load prompt from schema_registry: %s", exc)

    if fallback_prompt is not None:
        logger.warning(
            "Using fallback prompt for document_type=%s. "
            "Update schema_registry.extraction_prompts to override.",
            document_type,
        )
        return fallback_prompt

    raise ValueError(
        f"No active extraction prompt found for document_type='{document_type}' "
        f"in {catalog_name}.schema_registry.extraction_prompts, "
        "and no fallback_prompt was provided."
    )


# ---------------------------------------------------------------------------
# Table definition helper
# ---------------------------------------------------------------------------

def build_silver_table(
    document_type: str,
    required_fields: list[str],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    extra_table_properties: Optional[dict[str, str]] = None,
    comment: Optional[str] = None,
) -> dict:
    """
    Build the keyword arguments for the @dlt.table decorator for an extractor table.

    This function returns a dict that can be spread with ** into @dlt.table.
    It does NOT register any expectations — those must be added as separate
    @dlt.expect_or_* decorators above the function decorated with @dlt.table.

    Parameters
    ----------
    document_type          : e.g. 'mortgage_application'
    required_fields        : list of column names that must be non-null
                             (used to build the comment; actual expectations
                             are in the caller)
    confidence_threshold   : minimum avg_confidence_score for extraction acceptance
    extra_table_properties : additional Delta properties to merge over the base set
    comment                : override the auto-generated table comment

    Returns
    -------
    dict with keys: name, comment, cluster_by, table_properties
    """
    table_name = f"silver_extracted_{document_type}"
    props = dict(STANDARD_TABLE_PROPERTIES)
    props["docubricks.document_type"] = document_type
    props["docubricks.confidence_threshold"] = str(confidence_threshold)
    if extra_table_properties:
        props.update(extra_table_properties)

    required_str = ", ".join(required_fields) if required_fields else "(none specified)"
    auto_comment = (
        f"Extracted structured fields for document_type='{document_type}'. "
        f"Required fields: {required_str}. "
        f"Minimum extraction confidence: {confidence_threshold}. "
        "Populated by Wave 2 ExtractorAgent."
    )

    return {
        "name":             table_name,
        "comment":          comment or auto_comment,
        "cluster_by":       ["tenant_id", "document_type", "ingested_date"],
        "table_properties": props,
    }


# ---------------------------------------------------------------------------
# Extraction stream builder
# ---------------------------------------------------------------------------

def build_extraction_stream(
    document_type: str,
    catalog_name: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    flatten_fn: Optional[Callable] = None,
    fallback_prompt: Optional[str] = None,
    extra_columns: Optional[list[str]] = None,
) -> "DataFrame":
    """
    Build the body of a Silver extractor DLT streaming table.

    This is the core implementation function called by every Wave 2 extractor.

    Parameters
    ----------
    document_type        : e.g. 'mortgage_application'
    catalog_name         : Unity Catalog name (e.g. 'docubricks_prod')
    confidence_threshold : rows with avg_confidence_score < this are flagged
                           (DLT expect_or_drop in the caller enforces the drop)
    flatten_fn           : callable(df: DataFrame) -> DataFrame that adds typed
                           columns from extracted_json.  If None, only the base
                           columns are returned (useful for testing the wiring).
    fallback_prompt      : passed to get_extraction_prompt() if registry lookup fails
    extra_columns        : additional columns to include in the final select
                           (beyond BASE_EXTRACTION_COLUMNS + flatten_fn outputs)

    Returns
    -------
    DataFrame ready to be returned from a @dlt.table function.

    Stream source
    -------------
    dlt.read_stream("silver_route_{document_type}")
    — defined in extract_router.py

    AI function
    -----------
    ai_extract(parsed_text, schema_prompt) → struct{
        result:         string (JSON),
        avg_confidence: double,
        field_scores:   map<string, double>
    }
    """
    if not _IN_DATABRICKS:
        raise RuntimeError("build_extraction_stream() requires a Databricks runtime.")

    schema_prompt = get_extraction_prompt(
        catalog_name=catalog_name,
        document_type=document_type,
        fallback_prompt=fallback_prompt,
    )

    # Resolve model name once before building the DataFrame chain
    schema_model = _get_schema_model(catalog_name, document_type)

    route_view = f"silver_route_{document_type}"

    df = (
        dlt.read_stream(route_view)
        .withColumn(
            "extraction_result",
            # ai_extract is a Databricks-native SQL function:
            # ai_extract(text_column, prompt_string) → struct
            expr(f"ai_extract(parsed_text, '{schema_prompt.replace(chr(39), chr(39)*2)}')"),
        )
        .withColumn("extracted_json",      col("extraction_result.result"))
        .withColumn("avg_confidence_score", col("extraction_result.avg_confidence").cast("double"))
        .withColumn("field_confidences",    col("extraction_result.field_scores"))
        .withColumn("extraction_model",     lit(schema_model))
        .withColumn("extracted_at",         current_timestamp())
        .drop("extraction_result", "routed_at", "pipeline_stage")
    )

    # Apply the document-type-specific field flattener provided by Wave 2 agent
    if flatten_fn is not None:
        df = flatten_fn(df)

    # Build the final column list
    output_columns = list(BASE_EXTRACTION_COLUMNS)
    if extra_columns:
        output_columns.extend(extra_columns)

    # Add any columns added by flatten_fn that are not already in the list
    if flatten_fn is not None:
        for c in df.columns:
            if c not in output_columns:
                output_columns.append(c)

    # Select only columns that exist in the current DataFrame to avoid errors
    # if a flatten_fn skips optional fields
    available = set(df.columns)
    final_columns = [c for c in output_columns if c in available]

    return df.select(final_columns)


# ---------------------------------------------------------------------------
# Lakebase convenience functions (module-level wrappers)
#
# These exist for notebooks that prefer function-style calls over instantiating
# LakbaseHelper.  They create a module-level singleton on first call.
# ---------------------------------------------------------------------------

_default_helper: Optional[LakbaseHelper] = None


def _get_default_helper(secret_scope: str = "docubricks-prod") -> LakbaseHelper:
    global _default_helper
    if _default_helper is None:
        _default_helper = LakbaseHelper(secret_scope=secret_scope)
    return _default_helper


def update_extraction_status(
    document_id: str,
    extraction_conf: float,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    secret_scope: str = "docubricks-prod",
    pipeline_run_id: str = "unknown",
) -> None:
    """
    Module-level convenience: begin + complete extraction status in one call.

    Transitions: CLASSIFIED → EXTRACTING → EXTRACTED (or REVIEW if low conf).
    """
    helper = _get_default_helper(secret_scope)
    helper.begin_extraction(document_id, pipeline_run_id)
    helper.complete_extraction(document_id, extraction_conf, confidence_threshold)


def enqueue_for_extraction_review(
    document_id: str,
    tenant_id: str,
    review_reason: str = "LOW_CONFIDENCE",
    secret_scope: str = "docubricks-prod",
) -> None:
    """
    Module-level convenience: insert into review_queue and set status = REVIEW.
    """
    _get_default_helper(secret_scope).enqueue_for_review(
        document_id=document_id,
        tenant_id=tenant_id,
        review_reason=review_reason,
    )
