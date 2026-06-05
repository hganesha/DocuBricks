"""
Bootstrap Job 05 — Lakehouse Monitoring quality monitors.
Creates time-series monitors for each Silver extraction table.
Idempotent: skips tables that already have a monitor.
"""

import os
import sys

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


CATALOG      = _conf("catalog_name",  "CATALOG_NAME",  "docubricks_prod")
SECRET_SCOPE = _conf("secret_scope",  "SECRET_SCOPE",  "docubricks-prod")

# Silver extraction tables (from wave1_pipeline.json)
SILVER_TABLES = [
    f"{CATALOG}.silver.silver_route_mortgage_application",
    f"{CATALOG}.silver.silver_route_kyc_cdd_form",
    f"{CATALOG}.silver.silver_route_aml_sar",
    f"{CATALOG}.silver.silver_route_invoice",
]

# Timestamp column present in all silver extraction tables
TIMESTAMP_COL = "extracted_at"

# Monitoring granularities
GRANULARITIES = ["1 hour", "1 day"]

# Output schema for monitoring metrics (UC path)
MONITORING_OUTPUT_SCHEMA = f"{CATALOG}.monitoring"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Bootstrap Job 05 — Lakehouse Monitoring Setup")
    print(f"  Catalog           : {CATALOG}")
    print(f"  Tables to monitor : {len(SILVER_TABLES)}")
    print(f"  Timestamp column  : {TIMESTAMP_COL}")
    print(f"  Granularities     : {GRANULARITIES}")
    print("=" * 60)

    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.catalog import (
        MonitorTimeSeries,
        MonitorInferenceLog,
    )
    from databricks.sdk.errors import ResourceAlreadyExists, NotFound

    try:
        token = dbutils.secrets.get(SECRET_SCOPE, "databricks-token")  # noqa: F821
    except Exception:
        token = os.environ.get("DATABRICKS_TOKEN", "")

    host = _conf("databricks_host", "DATABRICKS_HOST", "")
    if not host:
        try:
            host = "https://" + spark.conf.get("spark.databricks.workspaceUrl", "")  # noqa: F821
        except Exception:
            pass

    w = WorkspaceClient(host=host, token=token)

    results: dict[str, str] = {}

    for table_name in SILVER_TABLES:
        short_name = table_name.split(".")[-1]
        print(f"\n  Processing: {table_name}")

        # Check if monitor already exists
        try:
            existing = w.quality_monitors.get(table_name=table_name)
            monitor_url = existing.dashboard_id or "(no dashboard yet)"
            print(f"  [SKIP] Monitor already exists for '{table_name}'.")
            results[short_name] = f"exists — dashboard_id={monitor_url}"
            continue
        except NotFound:
            pass  # Does not exist, proceed to create
        except ResourceAlreadyExists:
            print(f"  [SKIP] Monitor already registered for '{table_name}'.")
            results[short_name] = "exists"
            continue
        except Exception as exc:
            # SDK may raise different exception types depending on version
            err_str = str(exc).lower()
            if "already exists" in err_str or "already_exists" in err_str:
                print(f"  [SKIP] Monitor already exists for '{table_name}': {exc}")
                results[short_name] = "exists"
                continue
            if "not found" in err_str or "does_not_exist" in err_str:
                pass  # proceed to create
            else:
                print(f"  [WARN] get monitor returned unexpected error: {exc}")
                # Attempt creation anyway

        # Create monitor
        try:
            print(f"  Creating time-series monitor...")
            monitor = w.quality_monitors.create(
                table_name=table_name,
                assets_dir=f"/Volumes/{CATALOG}/monitoring/monitors/{short_name}",
                output_schema_name=MONITORING_OUTPUT_SCHEMA,
                time_series=MonitorTimeSeries(
                    timestamp_col=TIMESTAMP_COL,
                    granularities=GRANULARITIES,
                ),
                skip_builtin_dashboard=False,
            )
            dashboard_url = monitor.dashboard_id or "(pending)"
            print(f"  [OK] Monitor created. Dashboard ID: {dashboard_url}")
            results[short_name] = f"created — dashboard_id={dashboard_url}"

        except ResourceAlreadyExists:
            print(f"  [SKIP] Monitor already exists (race condition).")
            results[short_name] = "exists"
        except Exception as exc:
            err_str = str(exc).lower()
            if "already exists" in err_str or "already_exists" in err_str:
                print(f"  [SKIP] Monitor already exists: {exc}")
                results[short_name] = "exists"
            else:
                print(f"  [ERROR] Failed to create monitor for '{table_name}': {exc}",
                      file=sys.stderr)
                results[short_name] = f"FAILED: {exc}"
                raise

    # Print dashboard URLs
    print("\n" + "=" * 60)
    print("MONITOR DASHBOARD URLS")
    workspace_base = host.rstrip("/") if host else "<workspace_host>"
    for short_name, status in results.items():
        if "dashboard_id=" in status:
            dash_id = status.split("dashboard_id=")[-1].split()[0]
            if dash_id and dash_id != "(no" and dash_id != "(pending)":
                url = f"{workspace_base}/sql/dashboards/{dash_id}"
            else:
                url = "(dashboard not yet provisioned)"
        else:
            url = "(skipped or failed)"
        print(f"  {short_name:<45} {url}")

    print("\nSUMMARY")
    created = [k for k, v in results.items() if v.startswith("created")]
    skipped = [k for k, v in results.items() if v.startswith("exists")]
    failed  = [k for k, v in results.items() if v.startswith("FAILED")]
    print(f"  Created : {created or 'none'}")
    print(f"  Skipped : {skipped or 'none'}")
    print(f"  Failed  : {failed or 'none'}")
    print("=" * 60)

    if failed:
        raise RuntimeError(f"{len(failed)} monitor(s) failed to create: {failed}")

    print("Bootstrap Job 05 complete.")


main()
