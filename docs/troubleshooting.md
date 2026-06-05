# DocuBricks — Troubleshooting Runbook

This runbook covers the 10 most common operational issues. Each entry has **Symptoms**, **Root Cause**, and **Resolution**.

---

## 1. `databricks bundle validate` Fails

**Symptoms**
- CLI exits with a non-zero code immediately after `databricks bundle deploy` or `databricks bundle validate`.
- Error message references a YAML parse error, unknown key, or missing required field.

**Root Cause**
YAML is whitespace-sensitive and `databricks.yml` uses strict key validation. Common causes:
- Tab characters used instead of spaces (YAML forbids tabs as indentation).
- A `${var.xxx}` reference where `xxx` is not declared in the `variables:` block.
- An indentation mismatch under `resources.pipelines` or `resources.jobs` (Databricks Asset Bundles require exact 2-space indentation at each level).
- A library notebook path that does not exist in the workspace or local repository.

**Resolution**
```bash
databricks bundle validate 2>&1
```
The output will include the file name and line number of the first error. Common fixes:

- Replace tabs with spaces: `sed -i 's/\t/  /g' databricks.yml`
- Verify all `${var.xxx}` references have a corresponding entry in `variables:`.
- Check that all notebook paths under `libraries:` exist relative to the repo root.
- If the error is `unknown field "xxx"`, check the [Databricks Asset Bundles schema reference](https://docs.databricks.com/dev-tools/bundles/index.html) — the field name may have changed in your CLI version. Upgrade the CLI with `pip install --upgrade databricks-cli`.

---

## 2. UC Catalog Not Found

**Symptoms**
- Bootstrap step 1 fails with: `[SCHEMA_NOT_FOUND] Schema 'docubricks_dev.bronze' not found.`
- Or: `[CATALOG_NOT_FOUND] Catalog 'docubricks_dev' not found.`
- Or DLT pipeline fails immediately with a catalog access error.

**Root Cause**
The identity running the job (service principal or PAT owner) does not have `USE CATALOG` or `CREATE SCHEMA` privileges on the target catalog, or the catalog does not exist yet.

**Resolution**
1. Verify the catalog exists:
   ```sql
   SHOW CATALOGS LIKE 'docubricks_dev';
   ```
   If it does not exist, create it (account admin required):
   ```sql
   CREATE CATALOG IF NOT EXISTS docubricks_dev;
   ```
2. Grant privileges (metastore admin or catalog owner required):
   ```sql
   GRANT USE CATALOG, CREATE SCHEMA, USE SCHEMA, CREATE TABLE, CREATE VOLUME
     ON CATALOG docubricks_dev
     TO `your-service-principal-or-user@example.com`;
   ```
3. For the DLT pipeline specifically, the pipeline's run-as identity also needs `CREATE TABLE` on the `bronze`, `silver`, and `gold` schemas.
4. Re-run the bootstrap job.

---

## 3. Lakebase Connection Refused

**Symptoms**
- Bootstrap step 2 (run migrations) fails with: `psycopg2.OperationalError: could not connect to server: Connection refused`.
- Or: `timeout expired` when trying to reach the Lakebase host.
- Agents fail at startup with a Lakebase connection error.

**Root Cause**
Three common causes:
1. The connection string is in the wrong format or contains a typo.
2. The Lakebase instance is stopped or in a maintenance window.
3. The Serverless compute egress IP is not allow-listed in Lakebase network access rules.

**Resolution**
1. Verify the connection string format:
   ```
   postgresql://username:password@host.lakebase.databricks.com:5432/docubricks
   ```
   Not `jdbc:postgresql://...` (that is the JDBC format, not the psycopg2 format).

2. Check Lakebase instance state in Admin Console → Lakebase. If the instance is STOPPED, click Start. Allow 2–3 minutes for startup.

3. Check network access rules. In Admin Console → Lakebase → your instance → Network access, verify that either:
   - "Allow all Databricks compute" is enabled, or
   - The serverless egress IP range for your cloud region is listed. Refer to your Databricks account team for the current serverless egress IP ranges.

4. Test connectivity from a notebook:
   ```python
   import psycopg2
   conn_str = dbutils.secrets.get(scope="docubricks-prod", key="LAKEBASE_CONN")
   conn = psycopg2.connect(conn_str, connect_timeout=5)
   print("Connected:", conn.status)
   conn.close()
   ```

---

## 4. Foundation Model API Not Found

**Symptoms**
- Bootstrap step 4 fails with: `[RESOURCE_DOES_NOT_EXIST] Endpoint 'databricks-claude-sonnet' not found.`
- Or Silver extractor fails during extraction with a 404 from the Model Serving endpoint.
- `ai_query('databricks-claude-sonnet', ...)` raises `AnalysisException`.

**Root Cause**
Foundation Model APIs (pay-per-token endpoints) are not enabled in the workspace. This is a workspace-level setting that requires admin access to toggle.

**Resolution**
1. Log in to the Databricks workspace as an admin.
2. Go to **Settings → Admin Console → Model Serving**.
3. Find the **Foundation Model APIs** toggle and enable it.
4. Wait 2–3 minutes for the endpoints to become available.
5. Verify:
   ```sql
   SELECT ai_query('databricks-claude-sonnet', 'hello') AS response
   ```
   Should return a short text response without error.

Note: Foundation Model APIs incur per-token charges billed to your Databricks account. Ensure your account has an active payment method or credit allocation.

---

## 5. Bronze Table Not Populating

**Symptoms**
- Documents are uploaded to the UC Volume successfully (you can see them with `dbutils.fs.ls`).
- The Ingestion DLT pipeline is RUNNING but `bronze_documents` has zero new rows.
- Pipeline event log shows the streaming source is not processing new files.

**Root Cause**
Autoloader has two modes for detecting new files:
- **File notification mode** (preferred): uses cloud storage event notifications for low-latency, scalable detection.
- **Directory listing mode** (fallback): lists the directory on each trigger interval.

If the Autoloader source is stuck in listing mode on a large volume, it may miss new files or be throttled by the cloud storage API. Alternatively, file notifications may not be configured, causing Autoloader to fall back to listing mode silently.

**Resolution**
1. Check the pipeline event log for: `"cloudFiles.useNotifications" is not set` or `Falling back to directory listing`.

2. If using listing mode, force a trigger:
   ```python
   # In a notebook attached to the pipeline cluster
   spark.sql("REFRESH TABLE docubricks_dev.bronze.bronze_documents")
   ```

3. To enable file notification mode (recommended for production):
   - For Azure: configure Event Grid notifications on the ADLS Gen2 storage account.
   - For AWS: configure S3 event notifications via SQS.
   - For GCS: configure Pub/Sub notifications on the GCS bucket.
   - Set `cloudFiles.useNotifications = true` in the Autoloader source options in `src/pipelines/bronze/autoloader_ingest.py`.

4. If the volume has > 100k files and listing mode is the only option, set `cloudFiles.maxFilesPerTrigger` to a reasonable value (e.g. `1000`) and `cloudFiles.backfillInterval` to `1 day` to prevent full rescans on restart.

5. After fixing, stop and restart the Ingestion pipeline to pick up the configuration change.

---

## 6. Extraction Confidence Below Threshold

**Symptoms**
- Silver tables are being written but many fields are `null`.
- `extraction_metrics_daily` shows `avg_confidence` below `0.65` for a document type.
- Records are entering the review queue with reason `LOW_CONFIDENCE` at an unexpectedly high rate.

**Root Cause**
The extraction prompt is not specific enough for the document population, or the documents have an unusual format/layout that the prompt was not written for (e.g. scanned handwritten forms, non-English text, or an unusual template from a specific institution).

**Resolution**
1. Retrieve a sample of low-confidence records:
   ```sql
   SELECT document_id, confidence_score, raw_extraction_json
   FROM docubricks_dev.silver.silver_classified
   WHERE confidence_score < 0.65
     AND document_type = 'eob_cms1500'
   ORDER BY extracted_at DESC
   LIMIT 10;
   ```

2. Inspect the `raw_extraction_json` to understand what the model is producing vs. what is expected.

3. Open `schema_registry/<vertical>/<document_type>/prompt.txt` and:
   - Add concrete examples of how the problematic fields appear in your documents.
   - Clarify ambiguous field descriptions.
   - For date fields, explicitly list the date formats that appear in your documents.

4. Add new golden test cases covering the problematic document variants.

5. Run the schema promotion gate and confirm the pass rate improves before deploying the updated prompt.

6. If confidence remains low despite prompt tuning, consider routing the document type to `databricks-claude-sonnet` (the most capable model) and raising `timeout_seconds` in `model_routing.json`.

---

## 7. Genie Not Answering Domain Questions

**Symptoms**
- Genie responds with "I don't have enough information to answer that" for questions about your document data.
- Or Genie returns data from the wrong tables.
- Or Genie is not visible in the workspace at all.

**Root Cause**
Three common causes:
1. Bootstrap step 5 (configure Genie) did not run or failed silently.
2. The Gold tables that Genie should query have not been granted to the Genie space's run-as identity.
3. The Genie space was not seeded with domain-specific question examples (semantic context), so Genie cannot resolve ambiguous natural-language queries to the right tables and columns.

**Resolution**
1. Verify the Genie space exists:
   - Navigate to **SQL → Genie** in the workspace sidebar.
   - If no DocuBricks space appears, re-run bootstrap step 5:
     ```bash
     databricks jobs run-now \
       --job-name "DocuBricks — Bootstrap [dev]" \
       --job-parameters '{"step": "05_configure_genie"}'
     ```

2. Check table permissions:
   ```sql
   SHOW GRANTS ON TABLE docubricks_dev.gold.fs_mortgage_portfolio;
   ```
   The Genie service principal must have `SELECT` on all Gold tables. Grant if missing:
   ```sql
   GRANT SELECT ON ALL TABLES IN SCHEMA docubricks_dev.gold
     TO `genie-service-principal@your-org.com`;
   ```

3. Seed the Genie space with domain context by adding curated question-answer pairs in the Genie space settings. Example seed questions to add:
   - "How many mortgage applications were processed this week?"
   - "Which tenants have the most high-risk applications?"
   - "What is the average extraction confidence for EOB documents?"

4. Ensure `sql_warehouse_id` is set in `databricks.yml` and points to a RUNNING Serverless SQL warehouse.

---

## 8. Review Queue Not Loading in App

**Symptoms**
- The DocuBricks Onboarding or Portal App loads but the review queue tab is empty or shows a connection error.
- Browser console shows: `Error: Failed to fetch review queue: Connection refused` or `ECONNREFUSED`.

**Root Cause**
The App does not have access to the `LAKEBASE_CONN` secret. Databricks Apps run with their own identity and must have secrets explicitly configured in the App's environment — they do not inherit secrets from the workspace secret scope automatically.

**Resolution**
1. Navigate to **Apps → docubricks-onboarding → Settings → Environment variables**.

2. Add the secret as an environment variable:
   - Key: `LAKEBASE_CONN`
   - Value: the PostgreSQL connection string (or reference it from the secret scope using the Apps secrets integration).

3. Preferred approach — use the Apps secrets integration:
   ```yaml
   # In resources/apps/onboarding.yml
   env:
     - name: LAKEBASE_CONN
       valueFrom:
         secretRef:
           scope: docubricks-prod
           key: LAKEBASE_CONN
   ```
   Then re-deploy: `databricks bundle deploy --target dev`.

4. Restart the App after updating environment variables (Apps do not hot-reload secrets).

5. Verify by opening the App and checking the review queue — it should now display pending items.

---

## 9. Schema Test Harness Failing with Pass Rate < 0.85

**Symptoms**
- The schema promotion gate job exits with `FAILED (pass rate: 0.72 < threshold: 0.85)`.
- Specific golden tests are listed as failed in the output.
- Failure is consistent across runs (not intermittent).

**Root Cause**
The extraction prompt is not producing the expected output for the failing test cases. This is typically caused by:
- Ambiguous field descriptions that the model interprets differently across document variants.
- A field format in the golden test that is more specific than what the model reliably extracts (e.g. expecting `["CPT-99213"]` but the model returns `["99213"]` without the `CPT-` prefix).
- A confidence threshold that is too high for a field the model can extract but not with high certainty.

**Resolution**
1. Identify the failure pattern. Group failing tests by the field that is wrong:
   ```
   Failed tests:
     test_014 — procedure_codes: expected ["CPT-99213","CPT-85025"], got ["CPT-99213"]
     test_017 — billed_amount: expected 1250.00, got null (confidence 0.61)
   ```

2. For extraction errors (wrong value, not null):
   - Open the failing test's `input.document_text` and manually identify the field in the text.
   - Update `prompt.txt` to add an example showing how that field appears.
   - Re-run the gate after updating the prompt.

3. For null-due-to-low-confidence:
   - The model is finding the field but with low confidence.
   - Lower the `field_thresholds.json` threshold for that field, or improve the prompt to increase confidence.
   - If the document text in the test genuinely does not contain the field clearly, update the golden test's expected output to `null` and adjust the test's description.

4. For format mismatches (e.g. `99213` vs `CPT-99213`):
   - Either update the prompt to say "always include the `CPT-` prefix" with an example, or update the golden tests to accept both formats (use the `tolerance` key for numeric fields; for string fields, update the expected value to match what the model reliably produces).

5. Once the pass rate reaches >= 0.85, re-run the promotion gate to confirm before deploying to staging.

---

## 10. Agent Not Writing to `review_queue` — Lakebase Connection Pool Exhausted

**Symptoms**
- An agent job completes successfully (exit 0) but no new rows appear in `review_queue`.
- Or the agent job fails with: `psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections`.
- Or: `psycopg2.pool.PoolError: connection pool exhausted`.

**Root Cause**
Multiple agent jobs running concurrently are each opening psycopg2 connections and not closing them promptly, exhausting the Lakebase connection limit. Lakebase (PostgreSQL-compatible) has a default `max_connections` of 100. In production with many tenants and parallel agent runs, this limit can be hit.

**Resolution**
1. **Immediate fix** — identify and terminate idle connections:
   ```sql
   -- Run this in a Lakebase/psql session as superuser
   SELECT pid, usename, application_name, state, query_start
   FROM pg_stat_activity
   WHERE state = 'idle'
     AND application_name LIKE '%docubricks%'
   ORDER BY query_start;

   -- Terminate idle connections older than 5 minutes
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle'
     AND application_name LIKE '%docubricks%'
     AND query_start < now() - interval '5 minutes';
   ```

2. **Short-term fix** — ensure every agent closes connections in a `finally` block. Check that all agent scripts follow the pattern from `mortgage_risk_monitor.py`:
   ```python
   try:
       conn = get_lakebase_conn(spark)
       # ... do work ...
   finally:
       conn.close()
   ```
   Any agent that opens a connection inside a loop without closing it in `finally` will leak connections on exception.

3. **Long-term fix** — use PgBouncer connection pooling in front of Lakebase.
   - Deploy a PgBouncer instance (can run as a Databricks App or as a sidecar container).
   - Update `LAKEBASE_CONN` to point to PgBouncer instead of directly to Lakebase.
   - Configure PgBouncer in `transaction` pooling mode with `pool_size=20` and `max_client_conn=200`.
   - This allows many agent connections to share a small number of actual Lakebase connections.

4. **Operational fix** — stagger agent schedules. If all agents run at the same minute (e.g. 07:00 UTC), add a 1–2 minute offset to each agent's cron schedule in `databricks.yml` to spread connection peaks.
