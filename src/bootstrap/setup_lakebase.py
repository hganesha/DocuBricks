"""
Bootstrap Job 01 — Lakebase DDL migrations V001-V007.
Runs migration SQL files in order. Idempotent.
Designed to run as a Databricks Job on serverless compute.
"""

import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _conf(key: str, env_var: str, default: str = "") -> str:
    try:
        val = spark.conf.get(key, default)  # noqa: F821
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(env_var, default)


SECRET_SCOPE = _conf("secret_scope", "SECRET_SCOPE", "docubricks-prod")

# Migration files live relative to the repo root.
# In a Databricks Job the repo is checked out; use the workspace file path.
REPO_ROOT = Path(
    os.environ.get("REPO_ROOT", "/Workspace/Repos/docubricks/DocuBricks")
)
MIGRATIONS_DIR = REPO_ROOT / "migrations"

MIGRATION_ORDER = [
    "V001__create_document_registry.sql",
    "V002__create_processing_jobs.sql",
    "V003__create_review_queue.sql",
    "V004__create_reprocessing_queue.sql",
    "V005__create_extraction_audit.sql",
    "V006__create_monitoring_alerts.sql",
    "V007__create_tenant_registry.sql",
]

EXPECTED_TABLES = [
    "document_registry",
    "processing_jobs",
    "review_queue",
    "reprocessing_queue",
    "extraction_audit",
    "monitoring_alerts",
    "tenant_registry",
]

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

def get_connection():
    """
    Return a psycopg2 connection to Lakebase.
    Reads conn string from Databricks secret scope, then env var fallback.
    """
    try:
        conn_string = dbutils.secrets.get(SECRET_SCOPE, "lakebase-conn-string")  # noqa: F821
    except Exception:
        conn_string = os.environ.get("LAKEBASE_CONN", "")

    if not conn_string:
        raise RuntimeError(
            "LAKEBASE_CONN is not set. "
            f"Provide via dbutils.secrets (scope='{SECRET_SCOPE}', key='lakebase-conn-string') "
            "or environment variable LAKEBASE_CONN."
        )

    try:
        import psycopg2
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        return conn
    except ImportError:
        # Databricks serverless may use databricks-connect; try psycopg2-binary
        raise RuntimeError(
            "psycopg2 not available. Add 'psycopg2-binary' to the job's library dependencies."
        )


# ---------------------------------------------------------------------------
# Migration runner
# ---------------------------------------------------------------------------

def read_migration(filename: str) -> str:
    """Read SQL text from the migrations directory."""
    path = MIGRATIONS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Migration file not found: {path}")
    return path.read_text(encoding="utf-8")


def run_migration(conn, version_tag: str, sql: str) -> str:
    """
    Execute a migration SQL block.
    Returns 'applied' or 'skipped' (if already applied per migration_log).
    """
    cursor = conn.cursor()

    # Ensure migration tracking table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS migration_log (
            version     TEXT PRIMARY KEY,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            duration_ms INT
        )
    """)

    # Check if already applied
    cursor.execute(
        "SELECT version FROM migration_log WHERE version = %s", (version_tag,)
    )
    if cursor.fetchone():
        cursor.close()
        return "skipped"

    # Apply migration
    t0 = time.monotonic()
    cursor.execute(sql)
    duration_ms = int((time.monotonic() - t0) * 1000)

    # Record in log
    cursor.execute(
        "INSERT INTO migration_log (version, duration_ms) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (version_tag, duration_ms),
    )
    cursor.close()
    return f"applied ({duration_ms} ms)"


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_tables(conn) -> dict:
    """
    Query information_schema to confirm all expected tables exist.
    Returns dict of table_name -> bool.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
        """,
        (EXPECTED_TABLES,),
    )
    found = {row[0] for row in cursor.fetchall()}
    cursor.close()
    return {t: (t in found) for t in EXPECTED_TABLES}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Bootstrap Job 01 — Lakebase DDL Migrations")
    print(f"  Secret scope   : {SECRET_SCOPE}")
    print(f"  Migrations dir : {MIGRATIONS_DIR}")
    print("=" * 60)

    # Connect
    print("\nConnecting to Lakebase...")
    conn = get_connection()
    print("  Connected.")

    # Run migrations
    print(f"\nRunning {len(MIGRATION_ORDER)} migration(s)...")
    results: dict[str, str] = {}
    errors: list[str] = []

    for filename in MIGRATION_ORDER:
        # Extract version tag, e.g. "V001"
        version_tag = filename.split("__")[0]
        try:
            sql = read_migration(filename)
            status = run_migration(conn, version_tag, sql)
            results[version_tag] = status
            icon = "SKIP" if status == "skipped" else " OK "
            print(f"  [{icon}] {version_tag} ({filename}) — {status}")
        except Exception as exc:
            status = f"FAILED: {exc}"
            results[version_tag] = status
            errors.append(f"{version_tag}: {exc}")
            print(f"  [FAIL] {version_tag} ({filename}) — {exc}", file=sys.stderr)

    # Verify tables
    print("\nVerifying tables in information_schema.tables...")
    try:
        table_status = verify_tables(conn)
        all_present = True
        for table, present in table_status.items():
            icon = " OK " if present else "MISS"
            print(f"  [{icon}] {table}")
            if not present:
                all_present = False
    except Exception as exc:
        print(f"  [WARN] Table verification query failed: {exc}", file=sys.stderr)
        all_present = False

    conn.close()

    # Summary
    applied   = [k for k, v in results.items() if v.startswith("applied")]
    skipped   = [k for k, v in results.items() if v == "skipped"]
    failed    = [k for k, v in results.items() if v.startswith("FAILED")]

    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Applied  : {applied or 'none'}")
    print(f"  Skipped  : {skipped or 'none'}")
    print(f"  Failed   : {failed or 'none'}")
    print(f"  All tables present: {all_present}")
    print("=" * 60)

    if errors:
        raise RuntimeError(
            f"{len(errors)} migration(s) failed:\n" + "\n".join(errors)
        )

    if not all_present:
        raise RuntimeError(
            "One or more expected tables are missing after migrations. "
            "Check the output above for details."
        )

    print("Bootstrap Job 01 complete.")


main()
