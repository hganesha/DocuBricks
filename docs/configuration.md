# DocuBricks — Configuration Reference

This document describes every configuration knob in DocuBricks: bundle variables, secrets, environment-specific settings, multi-tenant configuration, tier upgrades, and compute sizing.

---

## `databricks.yml` Variables

All variables are declared in the top-level `variables:` block and can be overridden per target or passed on the command line with `--var key=value`.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `catalog_name` | string | `docubricks_prod` | Unity Catalog catalog that DocuBricks deploys into. Use separate catalogs for dev/staging/prod. |
| `tier` | enum | `community` | Schema bundle tier. Controls which document types, agents, and features are enabled. One of: `community`, `starter`, `professional`, `enterprise`. |
| `secret_scope` | string | `docubricks-prod` | Name of the Databricks secret scope that holds API keys and connection strings. |
| `enable_agents` | bool string | `"false"` | Whether to deploy vertical agent Workflow jobs. Set `"true"` for staging and prod. Use `"false"` for dev to avoid unnecessary scheduled runs. |
| `vertical` | enum | `fs` | Primary vertical for this deployment. One of: `fs`, `healthcare`, `legal`. Determines which schema bundles are seeded and which agents are deployed. |
| `sql_warehouse_id` | string | `""` | Serverless SQL warehouse ID used by Genie and Gold query jobs. Find it in Compute → SQL Warehouses → your warehouse → Overview. |
| `otel_endpoint` | string | `""` | OpenTelemetry collector endpoint for distributed tracing. Leave empty to disable. Example: `https://otel.your-org.com:4318`. |

### Overriding Variables at Deploy Time

```bash
# Deploy to staging with a specific warehouse
databricks bundle deploy --target staging \
  --var sql_warehouse_id=abc123def456 \
  --var otel_endpoint=https://otel.example.com:4318
```

### Per-Target Defaults

| Variable | dev | staging | prod |
|----------|-----|---------|------|
| `catalog_name` | `docubricks_dev` | `docubricks_staging` | `docubricks_prod` |
| `tier` | `community` | `professional` | `enterprise` |
| `enable_agents` | `"false"` | `"true"` | `"true"` |

---

## Required Secrets

DocuBricks reads secrets at runtime using `dbutils.secrets.get(scope=<secret_scope>, key=<key>)`. The secret scope name defaults to `docubricks-prod` and is configurable via the `secret_scope` variable.

Create the scope (once per environment):

```bash
databricks secrets create-scope docubricks-prod
```

Then store each secret:

```bash
databricks secrets put-secret docubricks-prod LAKEBASE_CONN \
  --string-value "postgresql://docubricks:password@lakebase-host:5432/docubricks"

databricks secrets put-secret docubricks-prod SQL_WH_HTTP_PATH \
  --string-value "/sql/1.0/warehouses/abc123def456"

databricks secrets put-secret docubricks-prod ANTHROPIC_API_KEY \
  --string-value "sk-ant-..."

# Optional: only required if using non-Databricks FMApi providers
databricks secrets put-secret docubricks-prod OPENAI_API_KEY \
  --string-value "sk-..."
```

| Secret Key | Required | Description |
|------------|----------|-------------|
| `LAKEBASE_CONN` | Yes | PostgreSQL DSN for the Lakebase instance. Format: `postgresql://user:pass@host:port/dbname` |
| `SQL_WH_HTTP_PATH` | Yes | HTTP path of the Serverless SQL warehouse used by agents and Genie |
| `ANTHROPIC_API_KEY` | Conditional | Required if `model_routing` in any schema bundle routes to `claude` outside Databricks FMApi |
| `OPENAI_API_KEY` | Conditional | Required if any schema bundle routes to OpenAI models |
| `OTEL_AUTH_TOKEN` | No | Bearer token for the OpenTelemetry collector, if your collector requires authentication |

### Verifying Secrets

```bash
databricks secrets list-secrets docubricks-prod
# Lists key names (not values) in the scope
```

---

## Environment-Specific Settings

### dev

- Uses `docubricks_dev` catalog — fully isolated from staging and prod data.
- `tier=community` — only FS Phase 1 document types are seeded.
- `enable_agents=false` — no scheduled agent jobs; avoids noise from synthetic test documents.
- Workspace root path is user-scoped: `/Workspace/Users/<you>/.bundle/docubricks` so each developer has an independent deployment.
- DLT pipelines run in development mode (full refresh on each trigger; no optimised writes).

### staging

- Uses `docubricks_staging` catalog.
- `tier=professional` — all verticals available for integration testing.
- `enable_agents=true` — agents run on their normal schedules against realistic staging data.
- Workspace root path is shared: `/Workspace/.bundle/docubricks-staging` — single deployment per environment.
- Use a dedicated service principal for staging deployments (not personal PAT).

### prod

- Uses `docubricks_prod` catalog.
- `tier=enterprise` — full feature set, custom schema bundles, dedicated support SLA.
- `mode=production` in `databricks.yml` — enables run-as service principal, production-grade DLT settings, and prevents accidental full-refresh triggers.
- Deploy only via CI/CD pipeline; never deploy to prod from a developer laptop.
- The `run_as` service principal (`docubricks-prod-sp`) must have `USE CATALOG`, `CREATE SCHEMA`, and `ALL PRIVILEGES` on the `docubricks_prod` catalog.

---

## Configuring Multiple Tenants

DocuBricks is multi-tenant by design. Each document carries a `tenant_id` that propagates through Bronze, Silver, and Gold. All Lakebase tables are also partitioned by `tenant_id`.

### Registering a New Tenant

Insert a row into the `tenant_registry` Lakebase table:

```sql
INSERT INTO tenant_registry (tenant_id, tenant_name, vertical, tier, created_at)
VALUES ('acme-corp', 'Acme Corporation', 'fs', 'starter', NOW());
```

Then map reviewers to the tenant in `tenant_reviewer_assignments`:

```sql
INSERT INTO tenant_reviewer_assignments (tenant_id, reviewer_email, role, created_at)
VALUES ('acme-corp', 'reviewer@acme.com', 'REVIEWER', NOW());
```

### Per-Tenant Volume Paths

Documents are ingested from per-tenant UC Volume paths:

```
/Volumes/docubricks_prod/raw_landing/documents/{tenant_id}/{vertical}/
```

Grant the tenant's service account write access to their specific path only:

```sql
GRANT WRITE VOLUME ON VOLUME docubricks_prod.raw_landing.documents
  TO `tenant-acme-sp`
  WHERE path LIKE '/documents/acme-corp/%';
```

### Per-Tenant Schema Overrides

In `professional` and `enterprise` tiers, tenants can have custom extraction prompts stored in the `schema_registry` schema. The extractor pipeline checks `schema_registry.prompt_overrides` for a tenant-specific prompt before falling back to the default.

---

## Changing Tiers (Upgrade Path)

Tiers are cumulative — each tier includes all features of the tier below it.

### Community → Starter

1. Update `tier` in `databricks.yml` (or pass `--var tier=starter`).
2. Obtain and store a Starter license key:
   ```bash
   databricks secrets put-secret docubricks-prod DOCUBRICKS_LICENSE_KEY \
     --string-value "<license-key-from-sales>"
   ```
3. Re-deploy the bundle: `databricks bundle deploy --target prod`.
4. Re-run bootstrap step 4 (`04_seed_schema_registry`) to seed Starter schema bundles.

### Starter → Professional

Same process as above with `tier=professional`. Additionally:
- Set `enable_agents=true` to activate vertical agents.
- Provision a Serverless SQL warehouse and set `sql_warehouse_id`.
- Configure Genie by running bootstrap step 5.

### Professional → Enterprise

Contact `sales@docubricks.io`. Enterprise deployments include:
- Custom schema bundle authoring with dedicated solution engineering support.
- Private VPC / BYOC deployment option.
- Custom SLA and dedicated CSM.

---

## Compute Sizing Recommendations

DocuBricks uses Databricks Serverless for all pipelines by default (`serverless: true` in `databricks.yml`). No cluster sizing is required for standard workloads.

If you override to classic compute (e.g. for network policy reasons), use the following as a starting point:

| Workload | Recommended Instance | Notes |
|----------|---------------------|-------|
| Ingestion pipeline (Bronze) | `i3.xlarge` × 2 workers | I/O bound; memory-optimised not needed |
| Processing pipeline (Silver) | `m5.2xlarge` × 4 workers | CPU bound during Foundation Model API calls |
| Gold pipeline | `m5.xlarge` × 2 workers | Light aggregation; scales down overnight |
| Agent jobs | Single-node `m5.large` | Short-lived; Serverless is preferred |
| Bootstrap jobs | Single-node `m5.large` | One-time; any instance works |

For very high document volumes (> 100k documents/day), contact `support@docubricks.io` for architecture guidance on horizontal scaling and DLT pipeline partitioning.
