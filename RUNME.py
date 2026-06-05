# Databricks notebook source
# MAGIC %md
# MAGIC # ◈ DocuBricks — Document Intelligence Accelerator
# MAGIC
# MAGIC **Document intelligence, natively on Databricks. Built for regulated industries.**
# MAGIC
# MAGIC This notebook is the entry point for the DocuBricks solution accelerator.
# MAGIC It will verify your environment, let you choose a setup path, and optionally
# MAGIC run a smoke test to confirm everything is working.
# MAGIC
# MAGIC **Estimated time:** 10–15 minutes for a full guided install.
# MAGIC
# MAGIC | Resource | Link |
# MAGIC |----------|------|
# MAGIC | Documentation | [docs/quickstart.md](docs/quickstart.md) |
# MAGIC | Configuration reference | [docs/configuration.md](docs/configuration.md) |
# MAGIC | Schema authoring | [docs/schema-authoring.md](docs/schema-authoring.md) |
# MAGIC | Troubleshooting | [docs/troubleshooting.md](docs/troubleshooting.md) |
# MAGIC | Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |

# COMMAND ----------
# MAGIC %md
# MAGIC ## Cell 1 — Configure Parameters
# MAGIC
# MAGIC Fill in the widgets below, then run this cell.
# MAGIC - **catalog_name**: Unity Catalog catalog to deploy into (e.g. `docubricks_dev`)
# MAGIC - **lakebase_conn**: Connection string for your Lakebase instance (leave blank to read from secret scope)
# MAGIC - **tier**: Schema bundle tier — controls which document types and agents are enabled
# MAGIC - **vertical**: Primary vertical to activate in this deployment

# COMMAND ----------

dbutils.widgets.text(
    "catalog_name",
    "docubricks_dev",
    "Catalog Name",
)
dbutils.widgets.text(
    "lakebase_conn",
    "",
    "Lakebase Connection String (optional — leave blank to use secret scope)",
)
dbutils.widgets.dropdown(
    "tier",
    "community",
    ["community", "starter", "professional", "enterprise"],
    "Tier",
)
dbutils.widgets.dropdown(
    "vertical",
    "fs",
    ["fs", "healthcare", "legal"],
    "Primary Vertical",
)

catalog_name  = dbutils.widgets.get("catalog_name")
lakebase_conn = dbutils.widgets.get("lakebase_conn")
tier          = dbutils.widgets.get("tier")
vertical      = dbutils.widgets.get("vertical")

print(f"catalog_name  = {catalog_name}")
print(f"tier          = {tier}")
print(f"vertical      = {vertical}")
print(f"lakebase_conn = {'(from widget)' if lakebase_conn else '(will read from secret scope)'}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Cell 2 — Prerequisites Check
# MAGIC
# MAGIC This cell verifies that your workspace meets the minimum requirements before
# MAGIC attempting deployment.  All checks must pass (✓) before continuing.

# COMMAND ----------

import re

checks_passed = True

# ── Check 1: Unity Catalog enabled ──────────────────────────────────────────
try:
    spark.sql(f"SHOW SCHEMAS IN {catalog_name}").collect()
    print(f"✓  Unity Catalog accessible: {catalog_name}")
except Exception as e:
    print(f"✗  Unity Catalog check failed for '{catalog_name}': {e}")
    print("   → Enable Unity Catalog in your workspace and create the catalog,")
    print("     or change the catalog_name widget to an existing catalog.")
    checks_passed = False

# ── Check 2: Foundation Model API accessible ────────────────────────────────
try:
    result = spark.sql(
        "SELECT ai_query('databricks-claude-sonnet', 'ping') AS response"
    ).collect()
    print("✓  Foundation Model API (databricks-claude-sonnet) accessible")
except Exception as e:
    print(f"✗  Foundation Model API not accessible: {e}")
    print("   → Go to workspace Settings → Model Serving → Enable Foundation Model APIs.")
    checks_passed = False

# ── Check 3: Lakebase connection string present ─────────────────────────────
resolved_conn = lakebase_conn
if not resolved_conn:
    try:
        secret_scope = spark.conf.get("secret_scope", "docubricks-prod")
        resolved_conn = dbutils.secrets.get(scope=secret_scope, key="LAKEBASE_CONN")
        print(f"✓  Lakebase connection string found in secret scope '{secret_scope}'")
    except Exception as e:
        print(f"✗  Lakebase connection string not found: {e}")
        print("   → Either enter it in the lakebase_conn widget above, or store it as")
        print("     LAKEBASE_CONN in your Databricks secret scope 'docubricks-prod'.")
        checks_passed = False
else:
    if re.match(r"^postgresql://", resolved_conn) or re.match(r"^host=", resolved_conn):
        print("✓  Lakebase connection string provided via widget")
    else:
        print("✗  Lakebase connection string format looks wrong.")
        print("   → Expected: postgresql://user:pass@host:port/dbname")
        checks_passed = False

# ── Summary ──────────────────────────────────────────────────────────────────
print()
if checks_passed:
    print("All prerequisites passed. Proceed to Option A or Option B below.")
else:
    print("One or more prerequisite checks failed. Resolve the issues above before continuing.")
    raise SystemExit("Prerequisites not met — see output above.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Option A — Setup Wizard (Recommended)
# MAGIC
# MAGIC The DocuBricks Onboarding App guides you through configuration, secret setup,
# MAGIC vertical selection, and first-document upload via a browser UI.
# MAGIC
# MAGIC Click **Open Setup Wizard** to launch it in a new tab.

# COMMAND ----------

workspace_host = spark.conf.get("spark.databricks.workspaceUrl", "your-workspace")
app_url = f"https://{workspace_host}/apps/docubricks-onboarding"

displayHTML(f"""
<div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd;
            border-radius: 8px; max-width: 560px; background: #f9f9f9;">
  <h3 style="margin-top: 0;">◈ DocuBricks Setup Wizard</h3>
  <p>The guided setup wizard will walk you through:</p>
  <ol>
    <li>Confirming secrets and environment variables</li>
    <li>Selecting verticals and document types</li>
    <li>Running the 6-step bootstrap</li>
    <li>Uploading your first test document</li>
    <li>Verifying extraction results</li>
  </ol>
  <a href="{app_url}" target="_blank"
     style="display: inline-block; padding: 10px 20px; background: #FF3621;
            color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">
    Open Setup Wizard ↗
  </a>
  <p style="margin-bottom: 0; color: #666; font-size: 12px;">
    URL: <code>{app_url}</code><br>
    (Deploy the bundle first if this link returns 404.)
  </p>
</div>
""")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Option B — Headless Bootstrap
# MAGIC
# MAGIC If you prefer a fully scripted install without the UI, uncomment and run the
# MAGIC cells below in order.  Each `%run` executes one bootstrap step.
# MAGIC
# MAGIC **Steps:**
# MAGIC 1. Create UC schemas and volumes
# MAGIC 2. Run Lakebase migrations (V001–V007)
# MAGIC 3. Deploy DLT pipelines
# MAGIC 4. Seed schema registry
# MAGIC 5. Configure Genie space
# MAGIC 6. Deploy vertical agents (if `enable_agents=true`)

# COMMAND ----------

# Uncomment to run headless bootstrap (Option B):

# %run ./bootstrap/01_create_uc_schemas {"catalog_name": catalog_name}
# %run ./bootstrap/02_run_migrations {"catalog_name": catalog_name, "lakebase_conn": resolved_conn}
# %run ./bootstrap/03_deploy_pipelines {"catalog_name": catalog_name, "tier": tier, "vertical": vertical}
# %run ./bootstrap/04_seed_schema_registry {"catalog_name": catalog_name, "tier": tier}
# %run ./bootstrap/05_configure_genie {"catalog_name": catalog_name}
# %run ./bootstrap/06_deploy_agents {"catalog_name": catalog_name, "vertical": vertical}

print("Option B: uncomment the %run cells above and run this cell to execute headless bootstrap.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Smoke Test
# MAGIC
# MAGIC Run this cell after completing either Option A or Option B to confirm the
# MAGIC installation is working correctly.  The test uploads a synthetic document,
# MAGIC waits for extraction, and validates the Silver table output.
# MAGIC
# MAGIC **Uncomment the cell below to run.**

# COMMAND ----------

# Uncomment to run smoke test after install:

# %run ./tests/smoke_test {"catalog_name": catalog_name, "vertical": vertical, "lakebase_conn": resolved_conn}
print("Smoke test: uncomment the %run cell above and run this cell after completing bootstrap.")
