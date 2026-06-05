# Ingestion Connectors Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add connector-based ingestion so users can either upload files directly or link external file sources that DocuBricks syncs into the existing processing pipeline.

**Architecture:** Keep the current Bronze contract: every ingestion path materializes files under `/Volumes/{catalog}/raw_landing/documents/{tenant_id}/{vertical}/...`, and the existing Autoloader pipeline remains the only Bronze reader. Add a connector registry in Lakebase, connector sync jobs that copy or discover external files, and Portal/Admin UI for creating, testing, scheduling, and monitoring sources.

**Tech Stack:** Python, Streamlit, Databricks Files API, Databricks Jobs, Lakebase/PostgreSQL, Unity Catalog Volumes, DLT Autoloader, pytest, optional provider SDKs for SaaS connectors.

---

## Product Scope

### Supported Ingestion Modes

1. Direct upload
   - Already mostly implemented in `apps/portal/pages/upload.py`.
   - Keep this as the default "Upload files" path.

2. Linked workspace/UC path
   - User links an existing UC Volume path or workspace file path that the Databricks workspace can read.
   - Connector sync copies supported files into the DocuBricks raw landing volume.

3. Cloud object storage
   - S3, ADLS Gen2, and GCS through Unity Catalog external locations or volume paths.
   - Initial implementation should prefer UC-governed paths over raw cloud credentials.

4. SaaS/document repositories
   - SharePoint/OneDrive, Google Drive, Box, SFTP.
   - Implement behind a common connector interface, but ship only one or two providers first.

5. URL/signed-link ingestion
   - User submits a signed URL or HTTPS link for a single file.
   - Background job fetches, hashes, stores, and registers the file.
   - Treat as useful but lower priority than UC path and cloud storage.

### Non-Goals For First Pass

- No bidirectional sync.
- No inline OCR or extraction inside connectors.
- No connector-specific Bronze tables.
- No bypass around the raw landing volume.
- No broad credential storage in app session state.

---

## Landing Contract

All connectors must write files here:

```text
/Volumes/{catalog_name}/raw_landing/documents/{tenant_id}/{vertical}/{source_id}/{document_id}.{file_ext}
```

Direct uploads can continue using:

```text
/Volumes/{catalog_name}/raw_landing/documents/{tenant_id}/{vertical}/{document_id}.{file_ext}
```

Required metadata for every discovered file:

```json
{
  "source_id": "uuid",
  "source_type": "direct_upload | uc_volume | s3 | adls | gcs | sharepoint | google_drive | box | sftp | https_url",
  "source_uri": "provider-specific stable URI",
  "tenant_id": "tenant id",
  "vertical": "fs | healthcare | legal | manufacturing | insurance | real_estate",
  "original_filename": "display filename",
  "content_hash": "sha256",
  "source_modified_at": "timestamp when available",
  "volume_path": "raw landing path"
}
```

---

## Task 1: Add Connector Registry Tables

**Files:**
- Create: `migrations/V009__create_ingestion_connectors.sql`
- Modify: `src/bootstrap/setup_lakebase.py`
- Test: `tests/unit/test_connector_registry_sql.py`

**Step 1: Write the failing test**

Create a test that reads `migrations/V009__create_ingestion_connectors.sql` and asserts it defines:

- `ingestion_sources`
- `ingestion_source_runs`
- `ingestion_source_files`
- indexes on `tenant_id`, `source_type`, `status`, and `last_seen_at`
- source status constraint: `ACTIVE`, `PAUSED`, `ERROR`, `DELETED`
- run status constraint: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `CANCELLED`

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/unit/test_connector_registry_sql.py -q
```

Expected: fail because migration file does not exist.

**Step 3: Add migration**

Create `migrations/V009__create_ingestion_connectors.sql` with:

- `ingestion_sources`
  - `source_id UUID PRIMARY KEY`
  - `tenant_id TEXT NOT NULL`
  - `vertical TEXT NOT NULL`
  - `source_type TEXT NOT NULL`
  - `display_name TEXT NOT NULL`
  - `source_uri TEXT NOT NULL`
  - `credential_secret_scope TEXT`
  - `credential_secret_key TEXT`
  - `sync_mode TEXT NOT NULL DEFAULT 'incremental'`
  - `schedule_cron TEXT`
  - `status TEXT NOT NULL DEFAULT 'ACTIVE'`
  - `created_by TEXT`
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - `last_sync_at TIMESTAMPTZ`
  - `last_error TEXT`

- `ingestion_source_runs`
  - `run_id UUID PRIMARY KEY`
  - `source_id UUID REFERENCES ingestion_sources(source_id)`
  - `status TEXT NOT NULL DEFAULT 'PENDING'`
  - `started_at TIMESTAMPTZ`
  - `finished_at TIMESTAMPTZ`
  - `files_seen INT NOT NULL DEFAULT 0`
  - `files_copied INT NOT NULL DEFAULT 0`
  - `files_skipped INT NOT NULL DEFAULT 0`
  - `files_failed INT NOT NULL DEFAULT 0`
  - `error TEXT`

- `ingestion_source_files`
  - `source_file_id UUID PRIMARY KEY`
  - `source_id UUID REFERENCES ingestion_sources(source_id)`
  - `document_id TEXT`
  - `source_uri TEXT NOT NULL`
  - `original_filename TEXT NOT NULL`
  - `content_hash TEXT`
  - `source_modified_at TIMESTAMPTZ`
  - `last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - `volume_path TEXT`
  - `status TEXT NOT NULL DEFAULT 'DISCOVERED'`
  - unique key on `(source_id, source_uri)`

**Step 4: Register migration**

Modify `src/bootstrap/setup_lakebase.py` so `MIGRATION_ORDER` includes `V009__create_ingestion_connectors.sql`.

**Step 5: Run test**

Run:

```bash
python3 -m pytest tests/unit/test_connector_registry_sql.py -q
```

Expected: pass.

---

## Task 2: Make Upload Paths Catalog-Aware And Source-Aware

**Files:**
- Modify: `apps/lib/databricks_api.py`
- Modify: `apps/portal/pages/upload.py`
- Test: `tests/unit/test_databricks_upload_paths.py`

**Step 1: Write failing tests**

Test that `build_volume_path()` returns:

```text
/Volumes/acme/raw_landing/documents/tenant-1/fs/doc-1.pdf
```

for direct upload and:

```text
/Volumes/acme/raw_landing/documents/tenant-1/fs/source-9/doc-1.pdf
```

when `source_id="source-9"`.

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/unit/test_databricks_upload_paths.py -q
```

Expected: fail because the helper does not exist and `_VOLUME_ROOT` is hardcoded to `docubricks_prod`.

**Step 3: Implement helper**

In `apps/lib/databricks_api.py`, add:

```python
def build_volume_path(
    catalog_name: str,
    document_id: str,
    tenant_id: str,
    vertical: str,
    file_ext: str,
    source_id: str | None = None,
) -> str:
    source_segment = f"/{source_id}" if source_id else ""
    return (
        f"/Volumes/{catalog_name}/raw_landing/documents/"
        f"{tenant_id}/{vertical}{source_segment}/{document_id}.{file_ext}"
    )
```

Update `upload_to_volume()` to accept `catalog_name` and optional `source_id`.

**Step 4: Update portal upload**

Modify `apps/portal/pages/upload.py` to read catalog from environment:

```python
catalog_name = os.environ.get("CATALOG_NAME", "docubricks_prod")
```

Pass it into `upload_to_volume()`.

**Step 5: Run tests**

Run:

```bash
python3 -m pytest tests/unit/test_databricks_upload_paths.py tests/unit/test_lakebase_helpers.py -q
```

Expected: pass.

---

## Task 3: Add Connector Provider Interface

**Files:**
- Create: `src/connectors/__init__.py`
- Create: `src/connectors/base.py`
- Test: `tests/unit/test_connector_base.py`

**Step 1: Write failing tests**

Test:

- `ConnectorFile` requires `source_uri`, `filename`, and `file_ext`
- unsupported extensions are rejected
- a provider returns iterable `ConnectorFile` objects from `list_files()`

**Step 2: Implement base classes**

Create:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

SUPPORTED_EXTENSIONS = {"pdf", "docx", "doc", "png", "jpg", "jpeg", "tiff", "tif", "html", "htm"}

@dataclass(frozen=True)
class ConnectorFile:
    source_uri: str
    filename: str
    file_ext: str
    size_bytes: int | None = None
    source_modified_at: datetime | None = None
    etag: str | None = None

    def validate(self) -> None:
        if self.file_ext.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {self.file_ext}")

class ConnectorProvider(Protocol):
    def list_files(self) -> list[ConnectorFile]:
        ...

    def read_file(self, item: ConnectorFile) -> bytes:
        ...
```

**Step 3: Run test**

Run:

```bash
python3 -m pytest tests/unit/test_connector_base.py -q
```

Expected: pass.

---

## Task 4: Implement UC Volume Connector

**Files:**
- Create: `src/connectors/uc_volume.py`
- Create: `src/connectors/sync.py`
- Test: `tests/unit/test_uc_volume_connector.py`

**Step 1: Write failing tests**

Use a temp directory to simulate source files and assert:

- recursive listing finds supported files
- unsupported extensions are skipped
- file bytes are read exactly
- content hash is stable

**Step 2: Implement provider**

Implement `UCVolumeConnector` that accepts:

```python
UCVolumeConnector(source_uri="/Volumes/acme/source/raw_docs")
```

For unit tests, it should also work with local paths.

**Step 3: Implement sync primitives**

In `src/connectors/sync.py`, add pure helpers:

- `compute_sha256(file_bytes: bytes) -> str`
- `target_volume_path(catalog_name, tenant_id, vertical, source_id, document_id, file_ext) -> str`
- `should_copy(previous_hash, new_hash) -> bool`

Do not call Databricks APIs in pure helpers.

**Step 4: Run tests**

Run:

```bash
python3 -m pytest tests/unit/test_uc_volume_connector.py tests/unit/test_connector_base.py -q
```

Expected: pass.

---

## Task 5: Add Connector Sync Job

**Files:**
- Create: `src/connectors/sync_sources.py`
- Create: `resources/jobs/ops/connector_sync.yml`
- Modify: `databricks.yml`
- Test: `tests/unit/test_connector_sync_job_config.py`

**Step 1: Write failing test**

Assert `resources/jobs/ops/connector_sync.yml` exists and references `src/connectors/sync_sources.py`.

**Step 2: Implement job resource**

Create a Databricks job with parameters:

- `catalog_name`
- `tenant_id`
- `source_id`
- `dry_run`

The job should:

1. Load source configuration from Lakebase.
2. Instantiate the connector provider.
3. List files.
4. Skip files already seen with same hash.
5. Copy new/changed files into raw landing.
6. Insert/update `ingestion_source_files`.
7. Register `document_registry` rows with `status='RECEIVED'`.

**Step 3: Wire into bundle**

Add the new YAML include to `databricks.yml` if resources are explicitly listed there.

**Step 4: Run tests**

Run:

```bash
python3 -m pytest tests/unit/test_connector_sync_job_config.py -q
python3 scripts/check_readiness.py
```

Expected: pass.

---

## Task 6: Add Portal Connector UI

**Files:**
- Modify: `apps/portal/pages/upload.py`
- Create: `apps/portal/pages/connectors.py`
- Modify: `apps/portal/app.py`
- Create: `apps/lib/ingestion_sources.py`
- Test: `tests/unit/test_ingestion_sources.py`

**Step 1: Write failing tests**

Test that `create_ingestion_source()` validates:

- source type
- URI is non-empty
- tenant id is non-empty
- vertical is supported

Test it inserts expected fields into Lakebase through mocked `lb_exec_returning()`.

**Step 2: Add data access helper**

Create `apps/lib/ingestion_sources.py` with:

- `create_ingestion_source()`
- `list_ingestion_sources()`
- `pause_ingestion_source()`
- `resume_ingestion_source()`
- `record_sync_request()`

**Step 3: Add UI tabs**

Update upload page to show:

- `Upload files`
- `Link source`

`Link source` should support first-pass source types:

- UC Volume path
- Cloud external location path
- HTTPS signed file URL

Do not expose OAuth SaaS connector setup in this first UI unless the provider is implemented.

**Step 4: Add connector page**

Add `apps/portal/pages/connectors.py` with:

- source list
- status
- last sync time
- last error
- button: `Sync now`
- button: `Pause` / `Resume`

**Step 5: Run tests**

Run:

```bash
python3 -m pytest tests/unit/test_ingestion_sources.py -q
python3 -m pytest tests/unit -q
```

Expected: pass.

---

## Task 7: Add Admin Connector Observability

**Files:**
- Create: `apps/admin/pages/ingestion_sources.py`
- Modify: `apps/admin/app.py`
- Test: `tests/unit/test_ingestion_source_queries.py`

**Step 1: Write query tests**

Test query builders for:

- source counts by type/status
- failed run list
- stale source list where `last_sync_at` is older than threshold

**Step 2: Implement page**

Admin page should show:

- total active sources
- failed sources
- files copied in last 24h
- last 20 connector runs
- source detail drilldown

**Step 3: Run tests**

Run:

```bash
python3 -m pytest tests/unit/test_ingestion_source_queries.py -q
```

Expected: pass.

---

## Task 8: Implement HTTPS URL Connector

**Files:**
- Create: `src/connectors/https_url.py`
- Test: `tests/unit/test_https_url_connector.py`

**Step 1: Write failing tests**

Use mocked `httpx.get()` and assert:

- successful fetch returns bytes
- content type is checked when available
- unsupported extension is rejected
- timeout raises a connector-specific error

**Step 2: Implement connector**

Implement a single-file provider for signed URLs:

```python
HTTPSURLConnector(source_uri="https://...")
```

It should infer filename from:

1. `Content-Disposition`
2. URL path basename
3. fallback to `{sha256}.pdf` only when content type is PDF

**Step 3: Run tests**

Run:

```bash
python3 -m pytest tests/unit/test_https_url_connector.py -q
```

Expected: pass.

---

## Task 9: Decide First SaaS Provider

**Files:**
- Modify: `BUILD_PLAN.md`
- Modify: `docs/configuration.md`
- Create one provider plan after decision.

**Recommendation:** Ship SharePoint/OneDrive first for enterprise buyers. It is more likely than Box/Google Drive in financial services and healthcare prospects.

**Decision criteria:**

- Buyer prevalence
- OAuth complexity
- Databricks networking constraints
- Customer security review burden
- Availability of service principal / app-only auth

**Implementation note:**

Do not implement all SaaS providers at once. After UC Volume, cloud path, and HTTPS URL are working, choose one SaaS connector and build it end to end.

---

## Task 10: Documentation And Plan Updates

**Files:**
- Modify: `docs/quickstart.md`
- Modify: `docs/configuration.md`
- Modify: `docs/troubleshooting.md`
- Modify: `BUILD_PLAN.md`

**Step 1: Update docs**

Document:

- Direct upload
- Link UC Volume path
- Link external cloud path
- HTTPS signed URL
- Connector credentials and secret storage
- Connector sync scheduling
- Connector run failures

**Step 2: Update build plan**

Add a new section:

```markdown
### Phase 2.5 - Ingestion Connectors
```

Mark:

- Direct upload: built
- UC/Volume linked source: new
- HTTPS signed URL: new
- Cloud path via UC external location: new
- SharePoint/OneDrive: planned
- Google Drive/Box/SFTP: backlog

**Step 3: Run verification**

Run:

```bash
python3 scripts/check_readiness.py
python3 -m pytest tests/unit -q
npm run lint
npm run build
```

Expected: all local checks pass.

---

## Recommended Milestones

### Milestone 1: Source Registry And Path Contract

Tasks 1-3.

Outcome: connector metadata model exists, upload path is catalog/source aware, and provider interface is test-covered.

### Milestone 2: Linked UC Path Ingestion

Tasks 4-7.

Outcome: users can link a UC Volume/external location path, sync files into raw landing, monitor source runs, and process files through existing Autoloader.

### Milestone 3: URL And Cloud Connector Coverage

Task 8 and cloud-path expansion inside the UC provider.

Outcome: users can link a signed URL or governed cloud path without manually uploading files.

### Milestone 4: First SaaS Connector

Task 9 plus a provider-specific plan.

Outcome: one enterprise document repository works end to end, recommended first target is SharePoint/OneDrive.

---

## Acceptance Criteria

- Direct upload still works.
- A user can create an ingestion source from the Portal.
- A user can sync a linked UC Volume path and see files enter `document_registry`.
- Autoloader processes connector-synced files without pipeline changes.
- Duplicate files are skipped by content hash.
- Connector runs are visible in Portal and Admin.
- Credentials are stored only in Databricks secrets, never in Lakebase plaintext.
- Local unit tests pass.
- `databricks bundle validate` passes once Databricks CLI is installed.

