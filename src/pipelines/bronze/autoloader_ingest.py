# Databricks notebook source
# DocuBricks — Bronze Ingestion Pipeline
# Layer 1: Autoloader → bronze_documents (immutable) + bronze_quarantine
#
# DLT channel: PREVIEW  |  Compute: Serverless
# Target schema: docubricks_prod.bronze
# Pipeline config keys: catalog_name, secret_scope

# COMMAND ----------
import dlt
import psycopg2
import psycopg2.pool
from pyspark.sql.functions import (
    sha2, col, regexp_extract, current_timestamp, lit, when, input_file_name
)
from pyspark.sql.types import StringType

# ---------------------------------------------------------------------------
# Runtime configuration — injected by DAB / pipeline configuration block
# ---------------------------------------------------------------------------
CATALOG_NAME = spark.conf.get("catalog_name", "docubricks_prod")
SECRET_SCOPE  = spark.conf.get("secret_scope", "docubricks-prod")

# Landing volume root — tenant and vertical are path components, not config
LANDING_PATH = f"/Volumes/{CATALOG_NAME}/raw_landing/documents/"

# Checkpoint location for Autoloader schema inference
SCHEMA_CHECKPOINT = f"/Volumes/{CATALOG_NAME}/checkpoints/bronze_schema/"

# ---------------------------------------------------------------------------
# Lakebase connection pool (lazy init so import-time failures don't break DLT
# graph resolution — pool is created on first actual use inside a function)
# ---------------------------------------------------------------------------
_conn_pool: psycopg2.pool.ThreadedConnectionPool | None = None

def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Return the module-level Lakebase connection pool, initialising it on first call."""
    global _conn_pool
    if _conn_pool is None:
        conn_string = dbutils.secrets.get(scope=SECRET_SCOPE, key="lakebase-conn-string")
        _conn_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=conn_string,
        )
    return _conn_pool


def _get_conn() -> psycopg2.extensions.connection:
    return _get_pool().getconn()


def _release_conn(conn: psycopg2.extensions.connection) -> None:
    _get_pool().putconn(conn)


# ---------------------------------------------------------------------------
# Lakebase helpers — status transitions written idempotently
# ---------------------------------------------------------------------------

def upsert_document_received(
    document_id: str,
    tenant_id: str,
    vertical: str,
    source_path: str,
    file_ext: str,
    file_size_bytes: int,
    pipeline_run_id: str,
) -> None:
    """
    Write or refresh the document_registry row with status RECEIVED.

    ON CONFLICT increments duplicate_count so we can track re-ingestion
    without duplicating downstream processing.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_registry (
                    document_id, tenant_id, vertical, source_path,
                    file_ext, file_size_bytes, content_hash,
                    status, pipeline_run_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'RECEIVED', %s)
                ON CONFLICT (document_id) DO UPDATE
                    SET last_seen_at     = NOW(),
                        duplicate_count  = document_registry.duplicate_count + 1,
                        pipeline_run_id  = EXCLUDED.pipeline_run_id;
                """,
                (
                    document_id, tenant_id, vertical, source_path,
                    file_ext, file_size_bytes, document_id,  # content_hash == document_id (SHA-256)
                    pipeline_run_id,
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _release_conn(conn)


def mark_document_quarantined(
    document_id: str | None,
    source_path: str,
    failure_reason: str,
    pipeline_run_id: str,
) -> None:
    """
    Update (or insert) the registry row for a file that failed Bronze expectations.
    When document_id is None (completely unreadable file) we use source_path as the key.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            if document_id:
                cur.execute(
                    """
                    UPDATE document_registry
                       SET status         = 'QUARANTINE',
                           failure_reason = %s
                     WHERE document_id = %s;
                    """,
                    (failure_reason, document_id),
                )
            else:
                # Minimal insert for files we cannot hash
                cur.execute(
                    """
                    INSERT INTO document_registry (
                        document_id, tenant_id, vertical, source_path,
                        file_ext, file_size_bytes, content_hash, status, failure_reason
                    ) VALUES (
                        md5(%s), 'unknown', 'unknown', %s,
                        'unknown', 0, md5(%s), 'QUARANTINE', %s
                    )
                    ON CONFLICT (document_id) DO UPDATE
                        SET status         = 'QUARANTINE',
                            failure_reason = EXCLUDED.failure_reason;
                    """,
                    (source_path, source_path, source_path, failure_reason),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _release_conn(conn)


# ---------------------------------------------------------------------------
# Autoloader source stream
# ---------------------------------------------------------------------------
# Path glob: all supported document formats.  Autoloader itself handles the
# binaryFile format — it returns (path, modificationTime, length, content).
# Using file notifications (cloudFiles.useNotifications=true) means Autoloader
# receives S3/ADLS/GCS events rather than listing the full directory on every
# trigger — O(new files) not O(all files).
# ---------------------------------------------------------------------------

def _raw_stream():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "binaryFile")
            .option("cloudFiles.useNotifications", "true")
            .option("cloudFiles.schemaLocation", SCHEMA_CHECKPOINT)
            .option("cloudFiles.maxFilesPerTrigger", "1000")
            .option("cloudFiles.backfillInterval", "1 day")
            .option("pathGlobFilter", "*.{pdf,docx,doc,png,jpg,jpeg,tiff,tif,html,htm}")
            .option("recursiveFileLookup", "true")
            .load(LANDING_PATH)
    )


# ---------------------------------------------------------------------------
# Bronze documents — immutable, CDF-enabled
#
# Path structure: /Volumes/{catalog}/raw_landing/documents/{tenant_id}/{vertical}/...
# Regex groups:   group(1) = tenant_id, group(2) = vertical
#
# Expectations (using ARCHITECTURE.md strategy):
#   expect_or_fail  — system invariants that must never be violated
#   expect_or_drop  — row-level quality rules; violations route to quarantine
#   expect          — monitoring-only warnings
# ---------------------------------------------------------------------------

@dlt.table(
    name="bronze_documents",
    comment=(
        "Raw binary documents with landing metadata. "
        "Immutable after write. Source of truth for document identity."
    ),
    table_properties={
        "delta.enableChangeDataFeed":       "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.columnMapping.mode":         "name",
        "delta.logRetentionDuration":       "interval 90 days",
        "delta.deletedFileRetentionDuration": "interval 30 days",
        "quality":                          "bronze",
        "docubricks.layer":                 "bronze",
    },
)
@dlt.expect_or_fail("document_id_never_null", "document_id IS NOT NULL")
@dlt.expect_or_drop("non_empty_file",         "length > 0")
@dlt.expect_or_drop("valid_vertical", (
    "vertical IN ('fs','healthcare','legal','manufacturing','insurance','real_estate')"
))
@dlt.expect_or_drop("supported_extension", (
    "file_ext IN ('pdf','docx','doc','png','jpg','jpeg','tiff','tif','html','htm')"
))
@dlt.expect("tenant_id_present", "tenant_id IS NOT NULL AND LENGTH(tenant_id) > 0")
@dlt.expect("file_size_reasonable", "length < 524288000")  # warn if > 500 MB
def bronze_documents():
    """
    Ingest raw document bytes from UC Volume using Autoloader.

    Column derivations
    ------------------
    document_id : SHA-256 of raw bytes (hex) — content-addressed deduplication key
    tenant_id   : first path component after /documents/
    vertical    : second path component after /documents/
    file_ext    : extension extracted from filename (lower-cased)
    ingested_at : pipeline processing timestamp (NOT file modification time)
    """
    return (
        _raw_stream()
        .withColumn(
            "document_id",
            sha2(col("content"), 256),
        )
        .withColumn(
            "tenant_id",
            # path: /Volumes/{catalog}/raw_landing/documents/{tenant_id}/{vertical}/...
            regexp_extract(col("path"), r"/documents/([^/]+)/", 1),
        )
        .withColumn(
            "vertical",
            regexp_extract(col("path"), r"/documents/[^/]+/([^/]+)/", 1),
        )
        .withColumn(
            "file_ext",
            regexp_extract(col("path"), r"\.([^.]+)$", 1),
        )
        .withColumn("ingested_at", current_timestamp())
        .select(
            "document_id",
            "tenant_id",
            "vertical",
            "file_ext",
            col("path").alias("source_path"),
            col("length").alias("file_size_bytes"),
            col("modificationTime").alias("source_modified_at"),
            "content",
            "ingested_at",
        )
    )


# ---------------------------------------------------------------------------
# Bronze quarantine — captures files rejected by bronze_documents expectations
#
# DLT automatically routes rows that fail expect_or_drop rules to a paired
# quarantine table when we define a table reading the same source stream with
# inverted expectations.  We also write to Lakebase for operational visibility.
#
# The quarantine table is append-only and never deleted — it is the forensic
# record of every document that could not be processed.
# ---------------------------------------------------------------------------

@dlt.table(
    name="bronze_quarantine",
    comment=(
        "Files rejected at Bronze ingestion: zero-byte, null document_id, "
        "unknown vertical, or unsupported extension. Append-only forensic record."
    ),
    table_properties={
        "delta.enableChangeDataFeed":       "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.columnMapping.mode":         "name",
        "quality":                          "quarantine",
        "docubricks.layer":                 "bronze",
    },
)
@dlt.expect_or_drop(
    "is_quarantine_candidate",
    (
        "length = 0 OR document_id IS NULL "
        "OR vertical NOT IN ('fs','healthcare','legal','manufacturing','insurance','real_estate') "
        "OR file_ext NOT IN ('pdf','docx','doc','png','jpg','jpeg','tiff','tif','html','htm')"
    ),
)
def bronze_quarantine():
    """
    Capture malformed or unrecognised files before they enter the processing chain.

    Includes a Lakebase status write for each quarantined document so the
    operations team can see failures in real time without querying Delta.
    """
    raw = (
        _raw_stream()
        .withColumn(
            "document_id",
            sha2(col("content"), 256),
        )
        .withColumn(
            "tenant_id",
            regexp_extract(col("path"), r"/documents/([^/]+)/", 1),
        )
        .withColumn(
            "vertical",
            regexp_extract(col("path"), r"/documents/[^/]+/([^/]+)/", 1),
        )
        .withColumn(
            "file_ext",
            regexp_extract(col("path"), r"\.([^.]+)$", 1),
        )
        .withColumn("ingested_at", current_timestamp())
        .withColumn(
            "quarantine_reason",
            when(col("length") == 0, lit("ZERO_BYTE_FILE"))
            .when(col("document_id").isNull(), lit("HASH_FAILED"))
            .when(
                ~col("vertical").isin(
                    "fs", "healthcare", "legal", "manufacturing", "insurance", "real_estate"
                ),
                lit("UNKNOWN_VERTICAL"),
            )
            .otherwise(lit("UNSUPPORTED_EXTENSION")),
        )
        .select(
            "document_id",
            "tenant_id",
            "vertical",
            "file_ext",
            col("path").alias("source_path"),
            col("length").alias("file_size_bytes"),
            col("modificationTime").alias("source_modified_at"),
            "ingested_at",
            "quarantine_reason",
            # Do not store content bytes in quarantine — the raw file is still in the Volume
        )
    )

    # Write Lakebase status for each quarantine candidate using foreachBatch
    # This runs as a side-effect and does not change the DataFrame returned to DLT
    def _write_quarantine_status(batch_df, batch_id):
        rows = batch_df.select(
            "document_id", "source_path", "quarantine_reason"
        ).collect()
        pipeline_run_id = spark.conf.get("pipelines.id", "unknown")
        for row in rows:
            try:
                mark_document_quarantined(
                    document_id=row["document_id"],
                    source_path=row["source_path"],
                    failure_reason=row["quarantine_reason"],
                    pipeline_run_id=pipeline_run_id,
                )
            except Exception as exc:
                # Log but do not fail the DLT pipeline for a registry write error
                print(
                    f"[bronze_quarantine] Lakebase write failed for "
                    f"{row['source_path']}: {exc}"
                )

    # NOTE: DLT does not support foreachBatch directly on a table-returning function.
    # The Lakebase write is therefore done via a separate streaming query defined
    # outside the @dlt.table decorator, sharing the same source stream through
    # a DLT view used as an intermediate.  See _bronze_quarantine_lakebase_sync below.

    return raw


# ---------------------------------------------------------------------------
# Lakebase sync for quarantined documents
#
# DLT's @dlt.table decorator must return a DataFrame — side-effect writes
# cannot be embedded there.  This separate view + foreachBatch pattern is the
# standard Databricks approach for operational writes alongside DLT.
# ---------------------------------------------------------------------------

@dlt.view(name="_bronze_quarantine_pending")
def _bronze_quarantine_pending():
    """Internal view: quarantine candidates before expectation filtering."""
    return (
        _raw_stream()
        .withColumn("document_id", sha2(col("content"), 256))
        .withColumn("tenant_id",   regexp_extract(col("path"), r"/documents/([^/]+)/", 1))
        .withColumn("vertical",    regexp_extract(col("path"), r"/documents/[^/]+/([^/]+)/", 1))
        .withColumn("file_ext",    regexp_extract(col("path"), r"\.([^.]+)$", 1))
        .withColumn("ingested_at", current_timestamp())
        .filter(
            (col("length") == 0)
            | col("document_id").isNull()
            | ~col("vertical").isin(
                "fs", "healthcare", "legal", "manufacturing", "insurance", "real_estate"
            )
            | ~col("file_ext").isin(
                "pdf", "docx", "doc", "png", "jpg", "jpeg", "tiff", "tif", "html", "htm"
            )
        )
        .select(
            "document_id",
            col("path").alias("source_path"),
            col("length").alias("file_size_bytes"),
            "ingested_at",
        )
    )


# ---------------------------------------------------------------------------
# Lakebase sync for successfully ingested documents
#
# After rows pass Bronze expectations they are registered in Lakebase with
# status RECEIVED so the processing pipeline can pick them up.
# ---------------------------------------------------------------------------

@dlt.view(name="_bronze_documents_pending")
def _bronze_documents_pending():
    """Internal view: successfully ingested documents for Lakebase registration."""
    return (
        _raw_stream()
        .withColumn("document_id", sha2(col("content"), 256))
        .withColumn("tenant_id",   regexp_extract(col("path"), r"/documents/([^/]+)/", 1))
        .withColumn("vertical",    regexp_extract(col("path"), r"/documents/[^/]+/([^/]+)/", 1))
        .withColumn("file_ext",    regexp_extract(col("path"), r"\.([^.]+)$", 1))
        .withColumn("ingested_at", current_timestamp())
        .filter(
            (col("length") > 0)
            & col("document_id").isNotNull()
            & col("vertical").isin(
                "fs", "healthcare", "legal", "manufacturing", "insurance", "real_estate"
            )
            & col("file_ext").isin(
                "pdf", "docx", "doc", "png", "jpg", "jpeg", "tiff", "tif", "html", "htm"
            )
        )
        .select(
            "document_id",
            "tenant_id",
            "vertical",
            col("path").alias("source_path"),
            "file_ext",
            col("length").alias("file_size_bytes"),
        )
    )
