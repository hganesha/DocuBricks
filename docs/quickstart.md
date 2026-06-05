# DocuBricks — Quick Start Guide

This guide takes you from a fresh clone to a running installation with your first document extracted. Allow 15–30 minutes.

---

## Prerequisites

Before you begin, confirm the following are in place:

| Requirement | Minimum Version / Setting | Where to find it |
|-------------|--------------------------|------------------|
| Databricks workspace | Any region | Your Databricks URL |
| Unity Catalog | Enabled | Admin Console → Catalog |
| Foundation Model APIs | Enabled | Admin Console → Model Serving → Enable Foundation Model APIs |
| Lakebase | Instance provisioned | Admin Console → Lakebase → Create Instance |
| Databricks CLI | >= 0.221 | `databricks --version`; install from [docs.databricks.com/dev-tools/cli](https://docs.databricks.com/dev-tools/cli/index.html) |
| Python | >= 3.10 | `python --version` |
| Git | Any recent version | `git --version` |

You will also need:
- A **personal access token** (PAT) for development, or a service principal for CI/CD. Generate a PAT at User Settings → Access Tokens.
- The **HTTP path** for a Serverless SQL warehouse (Compute → SQL Warehouses → your warehouse → Connection Details → HTTP Path).

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/docubricks.git
cd docubricks
```

Authenticate the Databricks CLI against your workspace:

```bash
databricks configure --token
# Paste your workspace URL (e.g. https://adb-1234567890.12.azuredatabricks.net)
# Paste your PAT
```

Verify:

```bash
databricks workspace list /
# Should list workspace root folders without error
```

---

## Step 2: Configure `.env`

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set each variable:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABRICKS_HOST` | Full workspace URL including `https://` | `https://adb-1234.5.azuredatabricks.net` |
| `DATABRICKS_TOKEN` | PAT for local development | `dapiXXXXXXXX` |
| `LAKEBASE_CONN` | PostgreSQL connection string for your Lakebase instance | `postgresql://user:pass@host:5432/docubricks` |
| `SQL_WH_HTTP_PATH` | HTTP path of your Serverless SQL warehouse | `/sql/1.0/warehouses/abc123` |
| `CATALOG_NAME` | Unity Catalog catalog name (overrides `databricks.yml` default) | `docubricks_dev` |

> `LAKEBASE_CONN` and `SQL_WH_HTTP_PATH` should also be stored as Databricks secrets so that agents and apps running inside the workspace can retrieve them. See [Configuration](configuration.md#required-secrets) for instructions.

---

## Step 3: Deploy the Bundle

Deploy to the `dev` target (the default):

```bash
databricks bundle deploy --target dev
```

This command:
1. Validates `databricks.yml` and all referenced resource files
2. Uploads notebooks, pipeline definitions, and job configurations to your workspace
3. Creates or updates DLT pipelines, Workflow jobs, and the Onboarding App

**Expected output:**

```
Uploading bundle files to /Workspace/Users/you@example.com/.bundle/docubricks...
Deploying resources...
  Updating pipeline 'DocuBricks — Ingestion [dev]'...
  Updating pipeline 'DocuBricks — Processing [dev]'...
  Updating pipeline 'DocuBricks — Gold [dev]'...
  Updating job 'DocuBricks — Bootstrap [dev]'...
  Updating app 'docubricks-onboarding'...
Deployment complete!
```

If `bundle validate` fails first, see [Troubleshooting — Issue 1](troubleshooting.md#1-databricks-bundle-validate-fails).

---

## Step 4: Run Bootstrap

The bootstrap job performs 6 ordered steps. Trigger it from the CLI:

```bash
databricks jobs run-now --job-name "DocuBricks — Bootstrap [dev]"
```

Or navigate to **Workflows → DocuBricks — Bootstrap [dev] → Run now** in the UI.

| Step | Script | What it does | Expected output |
|------|--------|-------------|-----------------|
| 1 | `01_create_uc_schemas` | Creates UC schemas: `bronze`, `silver`, `gold`, `schema_registry`, `raw_landing`, `monitoring`, `eval` | "7 schemas created" |
| 2 | `02_run_migrations` | Runs Lakebase migrations V001–V007 (creates `document_registry`, `review_queue`, etc.) | "7 migrations applied" |
| 3 | `03_deploy_pipelines` | Triggers a full refresh of the Ingestion, Processing, and Gold DLT pipelines | Pipelines enter RUNNING state |
| 4 | `04_seed_schema_registry` | Loads extraction prompts, validation rules, and field thresholds for your tier and vertical | "N schema bundles seeded" |
| 5 | `05_configure_genie` | Creates Genie space and grants table permissions | "Genie space configured" |
| 6 | `06_deploy_agents` | Creates scheduled Workflow jobs for vertical agents (skipped if `enable_agents=false`) | "Agents deployed" or "Skipped (enable_agents=false)" |

Monitor progress in the Workflow run's task log. Each step is idempotent — safe to re-run.

---

## Step 5: Open the Portal

After bootstrap completes, find the Onboarding App URL:

```bash
databricks apps list
# Look for docubricks-onboarding in the output, copy the URL
```

Or in the UI: navigate to **Apps → docubricks-onboarding → View app**.

The URL format is:
```
https://<workspace-host>/apps/docubricks-onboarding
```

Open it in your browser. The portal home page should display with your catalog name and tier.

---

## Step 6: Upload Your First Document

1. In the portal, click **Upload Document**.
2. Select a vertical (e.g. **Financial Services**) and document type (e.g. **Mortgage Application**).
3. Drag-and-drop or browse to a PDF or image file.
4. Click **Submit**. The document is assigned a SHA-256 `document_id` and enters the Bronze pipeline.

**What happens next (automated):**
1. Autoloader detects the file in the UC Volume and appends it to `bronze_documents`.
2. The Processing pipeline parses the PDF, classifies the document type, and routes it to the correct Silver extractor.
3. The Foundation Model API runs the extraction prompt and writes structured fields to `silver.extracted_mortgage_application` (or the relevant table for your vertical).
4. The Gold pipeline aggregates the new record into portfolio summaries.

**Check extraction results:**

In the portal, click **Documents → your uploaded file → View extraction**. You should see field values, confidence scores, and any validation flags within a few minutes.

Alternatively, query directly:

```sql
SELECT * FROM docubricks_dev.silver.extracted_mortgage_application
ORDER BY extracted_at DESC
LIMIT 5;
```

---

## Troubleshooting

See the full runbook at [docs/troubleshooting.md](troubleshooting.md). The five most common install issues:

### `databricks bundle validate` fails with YAML error

Check for tab characters (YAML requires spaces), incorrect indentation under `resources:`, or a missing `${}` variable reference. Run `databricks bundle validate 2>&1 | head -40` to see the exact line number.

### UC catalog not found after deploy

The service principal or PAT used for deployment may lack `USE CATALOG` privilege. Grant it: `GRANT USE CATALOG ON CATALOG docubricks_dev TO <principal>;` — an account admin must run this.

### Lakebase connection refused during migration step

Verify the connection string format is `postgresql://user:pass@host:port/dbname` and that the Lakebase instance is in RUNNING state (Admin Console → Lakebase). Check that your IP or the Databricks serverless egress IP is allow-listed in the Lakebase firewall rules.

### Foundation Model API returns 404 during bootstrap step 4

The feature is not enabled. Go to workspace Admin Console → Model Serving → toggle **Enable Foundation Model APIs** on. Requires workspace admin rights.

### Bronze table not receiving documents after upload

The Autoloader pipeline may be using file listing mode instead of file notification mode. Check the pipeline logs for `FileNotFoundException` or stalled `maxFilesPerTrigger`. See [Troubleshooting — Issue 5](troubleshooting.md#5-bronze-table-not-populating) for the fix.
