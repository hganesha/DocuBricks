"""
Bootstrap Job 00 — Unity Catalog namespace provisioning.
Creates catalog, schemas, and volumes for DocuBricks.
Run once before any other bootstrap jobs.
Idempotent: all DDL uses IF NOT EXISTS.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Config: prefer spark.conf, fall back to environment variables
# ---------------------------------------------------------------------------
def _conf(key: str, env_var: str, default: str = "") -> str:
    try:
        val = spark.conf.get(key, default)  # noqa: F821 (spark is a global in Databricks)
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(env_var, default)


CATALOG    = _conf("catalog_name",  "CATALOG_NAME",  "docubricks_prod")
SECRET_SCOPE = _conf("secret_scope", "SECRET_SCOPE", "docubricks-prod")

UC_SCHEMAS = [
    "bronze",
    "silver",
    "gold",
    "schema_registry",
    "raw_landing",
    "monitoring",
    "eval",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_sql(statement: str, label: str = "") -> None:
    """Execute a SQL statement via spark.sql; raise on error."""
    try:
        spark.sql(statement)  # noqa: F821
        if label:
            print(f"  [OK] {label}")
    except Exception as exc:
        print(f"  [ERROR] {label}: {exc}", file=sys.stderr)
        raise


def sql_exists(query: str) -> bool:
    """Return True if the query returns at least one row."""
    return spark.sql(query).count() > 0  # noqa: F821


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def setup_catalog() -> str:
    """Create catalog if it does not exist; return 'created' or 'exists'."""
    exists = sql_exists(
        f"SELECT catalog_name FROM system.information_schema.catalogs "
        f"WHERE catalog_name = '{CATALOG}'"
    )
    if exists:
        print(f"Catalog '{CATALOG}' already exists — skipping.")
        return "exists"
    run_sql(f"CREATE CATALOG IF NOT EXISTS `{CATALOG}`", f"CREATE CATALOG {CATALOG}")
    return "created"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

def setup_schemas() -> dict:
    """Create each UC schema; return dict of schema -> status."""
    results = {}
    for schema in UC_SCHEMAS:
        fqn = f"`{CATALOG}`.`{schema}`"
        exists = sql_exists(
            f"SELECT schema_name FROM system.information_schema.schemata "
            f"WHERE catalog_name = '{CATALOG}' AND schema_name = '{schema}'"
        )
        if exists:
            print(f"  Schema {fqn} already exists — skipping.")
            results[schema] = "exists"
        else:
            run_sql(f"CREATE SCHEMA IF NOT EXISTS {fqn}", f"CREATE SCHEMA {fqn}")
            results[schema] = "created"
    return results


# ---------------------------------------------------------------------------
# Volumes
# ---------------------------------------------------------------------------

VOLUMES = [
    # (schema, volume_name, comment)
    ("raw_landing", "documents",   "Raw document uploads, partitioned by tenant and vertical"),
    ("bronze",      "checkpoints", "DLT and Structured Streaming checkpoint data"),
    ("monitoring",  "monitoring",  "Lakehouse Monitoring metric output files"),
]

def setup_volumes() -> dict:
    """Create each UC Managed Volume; return dict of volume -> status."""
    results = {}
    for schema, volume, comment in VOLUMES:
        fqn = f"`{CATALOG}`.`{schema}`.`{volume}`"
        exists = sql_exists(
            f"SELECT volume_name FROM system.information_schema.volumes "
            f"WHERE catalog_name = '{CATALOG}' AND schema_name = '{schema}' "
            f"AND volume_name = '{volume}'"
        )
        if exists:
            print(f"  Volume {fqn} already exists — skipping.")
            results[f"{schema}/{volume}"] = "exists"
        else:
            run_sql(
                f"CREATE VOLUME IF NOT EXISTS {fqn} COMMENT '{comment}'",
                f"CREATE VOLUME {fqn}",
            )
            results[f"{schema}/{volume}"] = "created"
    return results


# ---------------------------------------------------------------------------
# Row-level security placeholder
# ---------------------------------------------------------------------------
# The actual table binding happens after Silver DLT tables are created.
# This function writes the row filter function definition into the catalog
# so it is ready to attach once Silver tables exist.

RLS_FUNCTION_SQL = f"""
CREATE OR REPLACE FUNCTION `{CATALOG}`.`silver`.`rls_tenant_filter`(tenant_id STRING)
RETURN IS_ACCOUNT_GROUP_MEMBER('admin') OR tenant_id = CURRENT_USER()
"""

RLS_ATTACH_TEMPLATE = """
-- To activate RLS on a silver extraction table, run:
-- ALTER TABLE {catalog}.silver.{table}
--   SET ROW FILTER {catalog}.silver.rls_tenant_filter ON (tenant_id);
""".strip()

SILVER_EXTRACTION_TABLES = [
    "silver_parsed",
    "silver_classified",
    "silver_route_mortgage_application",
    "silver_route_kyc_cdd_form",
    "silver_route_aml_sar",
    "silver_route_invoice",
]

def setup_rls_function() -> str:
    """Create the row filter function; return status string."""
    try:
        run_sql(RLS_FUNCTION_SQL, "CREATE FUNCTION silver.rls_tenant_filter")
        return "created"
    except Exception as exc:
        # Non-fatal: tables may not exist yet on first run
        print(f"  [WARN] RLS function creation skipped or failed: {exc}")
        return "skipped"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Bootstrap Job 00 — Unity Catalog Setup")
    print(f"  Catalog      : {CATALOG}")
    print(f"  Secret scope : {SECRET_SCOPE}")
    print("=" * 60)

    # 1. Catalog
    print("\n[1/4] Catalog")
    cat_status = setup_catalog()

    # 2. Schemas
    print("\n[2/4] Schemas")
    schema_results = setup_schemas()

    # 3. Volumes
    print("\n[3/4] Volumes")
    volume_results = setup_volumes()

    # 4. RLS function
    print("\n[4/4] Row-level security function")
    rls_status = setup_rls_function()
    print(f"  To bind RLS to silver tables after DLT pipeline runs:")
    for tbl in SILVER_EXTRACTION_TABLES:
        print(f"    ALTER TABLE {CATALOG}.silver.{tbl} "
              f"SET ROW FILTER {CATALOG}.silver.rls_tenant_filter ON (tenant_id);")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Catalog '{CATALOG}'          : {cat_status}")
    created_schemas = [k for k, v in schema_results.items() if v == "created"]
    existed_schemas = [k for k, v in schema_results.items() if v == "exists"]
    print(f"  Schemas created              : {created_schemas or 'none'}")
    print(f"  Schemas already existed      : {existed_schemas or 'none'}")
    created_vols = [k for k, v in volume_results.items() if v == "created"]
    existed_vols = [k for k, v in volume_results.items() if v == "exists"]
    print(f"  Volumes created              : {created_vols or 'none'}")
    print(f"  Volumes already existed      : {existed_vols or 'none'}")
    print(f"  RLS function                 : {rls_status}")
    print("=" * 60)
    print("Bootstrap Job 00 complete.")


main()
