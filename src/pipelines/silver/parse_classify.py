# Databricks notebook source
# DocuBricks — Silver Parse & Classify Pipeline
# Layer 2: bronze_documents → silver_parsed → silver_classified
#
# DLT channel: PREVIEW  |  Compute: Serverless
# Target schema: docubricks_prod.silver
# Pipeline config keys: catalog_name, secret_scope

# COMMAND ----------
import dlt
import psycopg2
import psycopg2.pool
from pyspark.sql.functions import (
    col, lit, array, to_date, current_timestamp, to_json,
    when, get_json_object, expr
)

# ---------------------------------------------------------------------------
# Runtime configuration
# ---------------------------------------------------------------------------
CATALOG_NAME = spark.conf.get("catalog_name", "docubricks_prod")
SECRET_SCOPE  = spark.conf.get("secret_scope", "docubricks-prod")

# Confidence threshold for classification acceptance
CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.70

# ---------------------------------------------------------------------------
# Lakebase connection pool
# ---------------------------------------------------------------------------
_conn_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _conn_pool
    if _conn_pool is None:
        conn_string = dbutils.secrets.get(scope=SECRET_SCOPE, key="lakebase-conn-string")
        _conn_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2, maxconn=10, dsn=conn_string
        )
    return _conn_pool


def _get_conn():
    return _get_pool().getconn()


def _release_conn(conn):
    _get_pool().putconn(conn)


# ---------------------------------------------------------------------------
# Lakebase helpers
# ---------------------------------------------------------------------------

def update_status_parsing(document_id: str, pipeline_run_id: str) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE document_registry
                   SET status = 'PARSING', pipeline_run_id = %s
                 WHERE document_id = %s AND status = 'RECEIVED';
                """,
                (pipeline_run_id, document_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _release_conn(conn)


def update_status_parsed(document_id: str) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE document_registry
                   SET status = 'PARSED'
                 WHERE document_id = %s AND status = 'PARSING';
                """,
                (document_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _release_conn(conn)


def update_status_classified(
    document_id: str,
    document_type: str,
    classification_conf: float,
) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE document_registry
                   SET status              = 'CLASSIFIED',
                       document_type       = %s,
                       classification_conf = %s
                 WHERE document_id = %s AND status IN ('PARSED', 'CLASSIFYING');
                """,
                (document_type, classification_conf, document_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _release_conn(conn)


def enqueue_for_review(
    document_id: str,
    tenant_id: str,
    review_reason: str,
    pipeline_run_id: str,
) -> None:
    """
    Insert a review_queue row for documents that fail classification confidence.
    Uses ON CONFLICT DO NOTHING so replaying is safe.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_queue (
                    document_id, tenant_id, review_reason, priority, sla_due_at
                ) VALUES (
                    %s, %s, %s, 3, NOW() + INTERVAL '48 hours'
                )
                ON CONFLICT DO NOTHING;
                """,
                (document_id, tenant_id, review_reason),
            )
            cur.execute(
                """
                UPDATE document_registry
                   SET status = 'REVIEW'
                 WHERE document_id = %s;
                """,
                (document_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _release_conn(conn)


# ---------------------------------------------------------------------------
# Dynamic classification labels
#
# Labels are loaded from schema_registry.document_type_labels at pipeline
# startup.  If the table is unavailable (e.g., cold-start race) we fall back
# to a hard-coded default set so the pipeline is resilient.
# ---------------------------------------------------------------------------

def _load_classification_labels() -> list[str]:
    """
    Load active classification labels from the schema registry.
    Returns a flat list of label strings sorted alphabetically for determinism.
    """
    try:
        labels_df = spark.table(
            f"{CATALOG_NAME}.schema_registry.document_type_labels"
        ).filter("is_active = true").select("label").distinct()
        labels = [row["label"] for row in labels_df.collect()]
        if labels:
            return sorted(labels)
    except Exception as exc:
        print(f"[parse_classify] Could not load labels from schema_registry: {exc}. Using defaults.")

    # Hard-coded Phase 1 FS fallback — never empty so ai_classify always has labels
    return sorted([
        "mortgage_application",
        "kyc_cdd_form",
        "aml_sar",
        "invoice",
        # Extended labels for future verticals (present in schema_registry by wave 2)
        "clinical_note_soap",
        "eob_cms1500",
        "lab_report",
        "prior_auth",
        "nda_msa",
        "sow",
        "policy_document",
        "claims_acord",
        "trade_confirmation",
        "drug_label",
        "regulatory_submission",
        "court_filing",
        "underwriting_memo",
        "loss_run",
        "ip_filing",
    ])


# Load once at notebook initialisation — DLT re-initialises per pipeline run
_CLASSIFICATION_LABELS: list[str] = _load_classification_labels()

# ---------------------------------------------------------------------------
# Silver Parsed — Bronze → Parsed text
#
# ai_parse_document() is a Databricks-native SQL function.  It accepts binary
# content and returns a struct: {text, page_count, layout, status, error_message}.
# Calling it as a Column expression (not a UDF) lets Photon batch and pipeline
# the calls for maximum throughput.
#
# The raw `content` binary column is dropped here — downstream tables never
# need to re-read raw bytes.  The UC Volume holds the original file.
# ---------------------------------------------------------------------------

@dlt.table(
    name="silver_parsed",
    comment=(
        "Parsed text and layout metadata extracted from bronze_documents. "
        "Content (binary) dropped; parsed_text is the canonical artefact."
    ),
    cluster_by=["tenant_id", "vertical", "ingested_date"],
    table_properties={
        "delta.enableChangeDataFeed":           "true",
        "delta.autoOptimize.optimizeWrite":     "true",
        "delta.autoOptimize.autoCompact":       "true",
        "delta.enableDeletionVectors":          "true",
        "delta.logRetentionDuration":           "interval 30 days",
        "delta.deletedFileRetentionDuration":   "interval 14 days",
        "quality":                              "silver",
        "docubricks.layer":                     "silver",
        "docubricks.stage":                     "parsed",
    },
)
@dlt.expect_or_fail("document_id_present",  "document_id IS NOT NULL")
@dlt.expect_or_drop("parse_succeeded",      "parse_status = 'SUCCESS'")
@dlt.expect("has_content", "parsed_text IS NOT NULL AND char_length(parsed_text) > 50")
@dlt.expect("page_count_positive", "page_count IS NULL OR page_count > 0")
def silver_parsed():
    """
    Call ai_parse_document() on each incoming bronze document.

    Adds derived columns:
    - parsed_text    : extracted text (string)
    - page_count     : number of pages / sections
    - layout_json    : layout structure serialised as JSON string
    - parse_status   : 'SUCCESS' or 'FAILURE' (drives expect_or_drop)
    - parse_error    : error message when parse_status = 'FAILURE'
    - ingested_date  : date partition derived from ingested_at
    """
    return (
        dlt.read_stream("bronze_documents")
        .withColumn(
            "parsed_result",
            expr("ai_parse_document(content)"),  # Databricks native SQL function
        )
        .withColumn("parsed_text",   col("parsed_result.text"))
        .withColumn("page_count",    col("parsed_result.page_count"))
        .withColumn("layout_json",   to_json(col("parsed_result.layout")))
        .withColumn("parse_status",  col("parsed_result.status"))
        .withColumn("parse_error",   col("parsed_result.error_message"))
        .withColumn("ingested_date", to_date(col("ingested_at")))
        .drop("content", "parsed_result")  # Raw binary removed; never needed downstream
        .select(
            "document_id",
            "tenant_id",
            "vertical",
            "file_ext",
            "source_path",
            "file_size_bytes",
            "source_modified_at",
            "ingested_at",
            "ingested_date",
            "parsed_text",
            "page_count",
            "layout_json",
            "parse_status",
            "parse_error",
        )
    )


# ---------------------------------------------------------------------------
# Silver Classified — Parsed → Classified
#
# ai_classify() is a Databricks-native SQL function.  It accepts a text string
# and an array of candidate label strings, and returns a struct:
# {label, score, runner_up_label, runner_up_score}.
#
# Labels are loaded dynamically from schema_registry at pipeline init so a
# new document type can be added by inserting a row in the registry table —
# no code change required.
#
# Rows with classification_confidence < CLASSIFICATION_CONFIDENCE_THRESHOLD
# are dropped and the document is enqueued for human review via Lakebase.
# ---------------------------------------------------------------------------

@dlt.table(
    name="silver_classified",
    comment=(
        "Classification results per document. "
        f"Only rows with confidence >= {CLASSIFICATION_CONFIDENCE_THRESHOLD} are retained. "
        "Low-confidence rows route to silver_classification_review."
    ),
    cluster_by=["tenant_id", "document_type", "ingested_date"],
    table_properties={
        "delta.enableChangeDataFeed":           "true",
        "delta.autoOptimize.optimizeWrite":     "true",
        "delta.autoOptimize.autoCompact":       "true",
        "delta.enableDeletionVectors":          "true",
        "delta.logRetentionDuration":           "interval 30 days",
        "delta.deletedFileRetentionDuration":   "interval 14 days",
        "quality":                              "silver",
        "docubricks.layer":                     "silver",
        "docubricks.stage":                     "classified",
    },
)
@dlt.expect_or_fail("document_id_present_classified", "document_id IS NOT NULL")
@dlt.expect_or_drop(
    "classified_with_confidence",
    f"document_type IS NOT NULL AND classification_confidence >= {CLASSIFICATION_CONFIDENCE_THRESHOLD}",
)
@dlt.expect(
    "known_phase1_doc_type",
    "document_type IN ('mortgage_application','kyc_cdd_form','aml_sar','invoice')",
)
@dlt.expect("runner_up_gap_healthy", "classification_confidence - runner_up_score >= 0.10")
def silver_classified():
    """
    Classify each parsed document using ai_classify() with dynamic label set.

    Added columns:
    - document_type             : top-1 classification label
    - classification_confidence : top-1 score
    - runner_up_label           : second-best label (for ambiguity detection)
    - runner_up_score           : second-best score
    - classification_model      : model identifier (informational)
    - classified_at             : timestamp of classification
    """
    label_array = array(*[lit(label) for label in _CLASSIFICATION_LABELS])

    return (
        dlt.read_stream("silver_parsed")
        .withColumn(
            "classification_result",
            expr(
                "ai_classify(parsed_text, array("
                + ", ".join(f"'{lbl}'" for lbl in _CLASSIFICATION_LABELS)
                + "))"
            ),
        )
        .withColumn("document_type",             col("classification_result.label"))
        .withColumn("classification_confidence", col("classification_result.score").cast("double"))
        .withColumn("runner_up_label",           col("classification_result.runner_up_label"))
        .withColumn("runner_up_score",           col("classification_result.runner_up_score").cast("double"))
        .withColumn("classification_model",      lit("databricks-dbrx-instruct"))
        .withColumn("classified_at",             current_timestamp())
        .drop("classification_result")
        .select(
            "document_id",
            "tenant_id",
            "vertical",
            "file_ext",
            "source_path",
            "file_size_bytes",
            "source_modified_at",
            "ingested_at",
            "ingested_date",
            "parsed_text",
            "page_count",
            "layout_json",
            "parse_status",
            "document_type",
            "classification_confidence",
            "runner_up_label",
            "runner_up_score",
            "classification_model",
            "classified_at",
        )
    )


# ---------------------------------------------------------------------------
# Silver Classification Review — low-confidence documents
#
# Documents that fail the classification confidence threshold are captured here
# rather than being silently discarded.  This table feeds the human review
# queue in the DocuBricks Portal.
# ---------------------------------------------------------------------------

@dlt.table(
    name="silver_classification_review",
    comment=(
        f"Documents with classification_confidence < {CLASSIFICATION_CONFIDENCE_THRESHOLD}. "
        "Routed for human review. Never deleted — forensic record."
    ),
    table_properties={
        "delta.enableChangeDataFeed":       "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "quality":                          "quarantine",
        "docubricks.layer":                 "silver",
        "docubricks.stage":                 "classification_review",
    },
)
@dlt.expect_or_drop(
    "is_low_confidence",
    f"document_type IS NULL OR classification_confidence < {CLASSIFICATION_CONFIDENCE_THRESHOLD}",
)
def silver_classification_review():
    """
    Captures low-confidence classified rows for human review.

    These rows are also inserted into the Lakebase review_queue by the
    operations post-processing job (not inline here, to avoid DLT side-effect
    constraints).
    """
    label_array_sql = (
        "array("
        + ", ".join(f"'{lbl}'" for lbl in _CLASSIFICATION_LABELS)
        + ")"
    )

    return (
        dlt.read_stream("silver_parsed")
        .withColumn(
            "classification_result",
            expr(f"ai_classify(parsed_text, {label_array_sql})"),
        )
        .withColumn("document_type",             col("classification_result.label"))
        .withColumn("classification_confidence", col("classification_result.score").cast("double"))
        .withColumn("runner_up_label",           col("classification_result.runner_up_label"))
        .withColumn("runner_up_score",           col("classification_result.runner_up_score").cast("double"))
        .withColumn("review_reason",             lit("LOW_CONFIDENCE"))
        .withColumn("classified_at",             current_timestamp())
        .drop("classification_result")
        .filter(
            col("document_type").isNull()
            | (col("classification_confidence") < CLASSIFICATION_CONFIDENCE_THRESHOLD)
        )
        .select(
            "document_id",
            "tenant_id",
            "vertical",
            "file_ext",
            "source_path",
            "file_size_bytes",
            "ingested_at",
            "ingested_date",
            "parsed_text",
            "page_count",
            "document_type",
            "classification_confidence",
            "runner_up_label",
            "runner_up_score",
            "review_reason",
            "classified_at",
        )
    )
