# DocuBricks — Accelerator Build Plan

> **One-line goal:** ship DocuBricks as a production-grade Databricks Marketplace accelerator, deployable into any customer workspace in under 30 minutes, generating $1.5M ARR by month 18.

---

## Table of Contents

1. [What Ships](#1-what-ships)
2. [Repository & Bundle Structure](#2-repository--bundle-structure)
3. [Databricks Asset Bundle Manifest](#3-databricks-asset-bundle-manifest)
4. [Deployment Sequence (Day-Zero Install)](#4-deployment-sequence-day-zero-install)
5. [Tenant Onboarding Flow](#5-tenant-onboarding-flow)
6. [Build Phases](#6-build-phases)
7. [Testing Strategy](#7-testing-strategy)
8. [Marketplace Packaging & Listing](#8-marketplace-packaging--listing)
9. [CI/CD Pipeline](#9-cicd-pipeline)
10. [Critical Path & Risks](#10-critical-path--risks)
11. [Definition of Done](#11-definition-of-done)

---

## 1. What Ships

DocuBricks is packaged as a **Databricks Asset Bundle (DAB)** — infrastructure-as-code that provisions every resource in a target workspace. A customer clones the repo (or installs from Marketplace), runs one command, and the full platform is operational.

### Components per tier

| Component | Community (free) | Starter ($2.5K/mo) | Professional ($8.5K/mo) | Enterprise (custom) |
|---|:---:|:---:|:---:|:---:|
| DLT ingestion + processing pipeline | ✓ | ✓ | ✓ | ✓ |
| FS schema bundle (4 doc types) | ✓ | ✓ | ✓ | ✓ |
| DocuBricks Portal (Databricks App) | ✓ | ✓ | ✓ | ✓ |
| Genie workspace (FS) | — | ✓ | ✓ | ✓ |
| Review & Correction UI | — | ✓ | ✓ | ✓ |
| MLflow eval harness | — | ✓ | ✓ | ✓ |
| Lakehouse Monitoring + OTel | — | ✓ | ✓ | ✓ |
| Admin & Schema Manager | — | — | ✓ | ✓ |
| Vector Search index | — | — | ✓ | ✓ |
| FS Agent library (3 agents) | — | — | ✓ | ✓ |
| 2nd vertical schema bundle | — | — | ✓ | ✓ |
| All 6 verticals + all agents | — | — | — | ✓ |
| Multi-tenant / multi-region | — | — | — | ✓ |
| Custom schema development | — | — | — | ✓ |

Community tier: public GitHub + RUNME.py (Databricks solution accelerator format, no license check).  
Paid tiers: Databricks Marketplace private offer + license key verified at bootstrap time.

### What is NOT bundled

| Item | Why | Customer action |
|---|---|---|
| Lakebase instance | Preview service; customer provisions | Provision in workspace settings; paste connection string into setup wizard |
| Lakeflow Connect source connectors | Source-specific config | Configure per source after install |
| Foundation Model API | Workspace-level toggle | Enable in workspace settings (checkbox) |
| SSO / identity provider | Pre-existing workspace SSO | None; Apps inherits workspace SSO automatically |

---

## 2. Repository & Bundle Structure

```
docubricks/
│
├── databricks.yml                     # DAB manifest — single source of truth
│
├── resources/                         # DAB resource definitions (YAML)
│   ├── pipelines/
│   │   ├── ingestion.yml              # Autoloader → Bronze DLT
│   │   ├── processing.yml             # Bronze → Silver (parse / classify / extract)
│   │   └── gold.yml                   # Silver → Gold (aggregations + mat. views)
│   ├── jobs/
│   │   ├── bootstrap/
│   │   │   ├── 00_setup_uc.yml
│   │   │   ├── 01_schema_registry.yml
│   │   │   ├── 02_load_schemas.yml
│   │   │   ├── 03_monitoring.yml
│   │   │   ├── 04_genie.yml
│   │   │   └── 05_vector_search.yml
│   │   ├── ops/
│   │   │   ├── stale_doc_recovery.yml
│   │   │   ├── schema_test_harness.yml
│   │   │   └── daily_health_check.yml
│   │   └── agents/
│   │       ├── fs_mortgage_risk.yml
│   │       ├── fs_kyc_refresh.yml
│   │       ├── fs_aml_pattern.yml
│   │       ├── legal_contract_expiry.yml
│   │       └── hc_eob_reconciliation.yml
│   └── apps/
│       ├── onboarding.yml             # Setup wizard (see ONBOARDING_SPEC.md)
│       ├── portal.yml
│       ├── review.yml
│       └── admin.yml
│
├── src/                               # Python source
│   ├── pipelines/
│   │   ├── bronze/
│   │   │   └── autoloader_ingest.py
│   │   ├── silver/
│   │   │   ├── parse_classify.py
│   │   │   ├── extract_router.py
│   │   │   └── extractors/
│   │   │       ├── mortgage_application.py
│   │   │       ├── kyc_cdd_form.py
│   │   │       ├── aml_sar.py
│   │   │       └── invoice.py
│   │   └── gold/
│   │       ├── fs_portfolio.py
│   │       └── platform_health.py
│   ├── bootstrap/
│   │   ├── setup_unity_catalog.py
│   │   ├── setup_schema_registry.py
│   │   ├── setup_lakebase.py          # Runs DDL migrations in order
│   │   ├── setup_genie.py             # Genie REST API provisioner
│   │   ├── setup_vector_search.py
│   │   └── setup_monitoring.py
│   ├── agents/
│   │   ├── fs/
│   │   │   ├── mortgage_risk_monitor.py
│   │   │   ├── kyc_refresh.py
│   │   │   └── aml_pattern.py
│   │   ├── healthcare/
│   │   │   └── eob_reconciliation.py
│   │   └── legal/
│   │       └── contract_expiry.py
│   └── ops/
│       ├── stale_doc_recovery.py
│       ├── schema_test_harness.py
│       └── daily_health_check.py
│
├── apps/
│   ├── lib/                           # Shared component library (all apps import this)
│   │   ├── auth.py
│   │   ├── genie.py
│   │   ├── lakebase.py
│   │   ├── sql_warehouse.py
│   │   ├── databricks_api.py
│   │   ├── otel.py
│   │   ├── theme.py
│   │   └── components/
│   │       ├── confidence_badge.py
│   │       ├── status_tracker.py
│   │       ├── field_editor.py
│   │       ├── document_viewer.py
│   │       └── vertical_selector.py
│   ├── onboarding/                    # Setup wizard — see ONBOARDING_SPEC.md
│   │   ├── app.yaml
│   │   ├── app.py
│   │   ├── screens/
│   │   ├── core/
│   │   ├── steps/
│   │   └── requirements.txt
│   ├── portal/
│   │   ├── app.yaml
│   │   ├── app.py
│   │   ├── pages/
│   │   └── requirements.txt
│   ├── review/
│   │   ├── app.yaml
│   │   ├── app.py
│   │   └── pages/
│   └── admin/
│       ├── app.yaml
│       ├── app.py
│       └── pages/
│
├── schemas/                           # Schema bundle artifacts (versioned)
│   ├── fs/
│   │   ├── mortgage_application/
│   │   │   ├── prompt_v1.txt
│   │   │   ├── validation_rules.json
│   │   │   ├── field_thresholds.json
│   │   │   ├── model_routing.json
│   │   │   └── golden_tests/          # ≥ 20 labeled documents per type
│   │   ├── kyc_cdd_form/
│   │   ├── aml_sar/
│   │   └── invoice/
│   └── healthcare/                    # Professional+ tier (Phase 5)
│       ├── eob_cms1500/
│       └── clinical_note_soap/
│
├── migrations/                        # Lakebase DDL (ordered, idempotent)
│   ├── V001__create_document_registry.sql
│   ├── V002__create_processing_jobs.sql
│   ├── V003__create_review_queue.sql
│   ├── V004__create_reprocessing_queue.sql
│   ├── V005__create_extraction_audit.sql
│   ├── V006__create_monitoring_alerts.sql
│   └── V007__create_tenant_registry.sql
│
├── tests/
│   ├── unit/                          # pytest, no Databricks required
│   ├── integration/                   # dev workspace required
│   ├── e2e/                           # staging workspace required
│   └── fixtures/                      # Sample documents for test runs
│       ├── sample_mortgage.pdf
│       ├── sample_kyc.pdf
│       └── sample_aml_sar.pdf
│
├── docs/
│   ├── quickstart.md
│   ├── configuration.md
│   ├── schema-authoring.md
│   └── troubleshooting.md
│
├── .github/workflows/
│   ├── ci.yml                         # PR: unit tests + lint + bundle validate
│   ├── integration.yml                # Merge to main: integration tests in dev
│   └── release.yml                    # Tag: deploy to staging → prod (manual gate)
│
├── ARCHITECTURE.md
├── BUILD_PLAN.md                      # This file
├── ONBOARDING_SPEC.md                 # UX spec for the setup wizard
└── README.md
```

---

## 3. Databricks Asset Bundle Manifest

```yaml
# databricks.yml
bundle:
  name: docubricks

variables:
  catalog_name:
    description: Unity Catalog name for DocuBricks
    default: docubricks_prod
  tier:
    description: "Schema bundle tier: community | starter | professional | enterprise"
    default: community
  secret_scope:
    description: Databricks Secret scope with Lakebase conn + API keys
    default: docubricks-prod
  otel_endpoint:
    description: OTel collector endpoint (empty = disabled)
    default: ""
  enable_agents:
    description: Deploy vertical agent Workflow jobs
    default: "false"
  vertical:
    description: Primary vertical (fs | healthcare | legal)
    default: fs

include:
  - resources/pipelines/*.yml
  - resources/jobs/bootstrap/*.yml
  - resources/jobs/ops/*.yml
  - resources/apps/*.yml
  - resources/jobs/agents/*.yml      # Conditional: only included when enable_agents=true

targets:
  dev:
    mode: development                 # Prefixes all resources [dev username]
    default: true
    variables:
      catalog_name: docubricks_dev
      tier: community
      enable_agents: "false"
    workspace:
      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/docubricks

  staging:
    variables:
      catalog_name: docubricks_staging
      tier: professional
      enable_agents: "true"
    workspace:
      root_path: /Workspace/.bundle/docubricks-staging

  prod:
    mode: production
    variables:
      catalog_name: docubricks_prod
      tier: enterprise
      enable_agents: "true"
    run_as:
      service_principal_name: docubricks-prod-sp
    workspace:
      root_path: /Workspace/.bundle/docubricks-prod
```

---

## 4. Deployment Sequence (Day-Zero Install)

The onboarding wizard (see [ONBOARDING_SPEC.md](ONBOARDING_SPEC.md)) drives the user through this sequence interactively. Each step is idempotent — "Retry from here" is always safe.

```
STEP 0 — Prerequisites (verified by onboarding wizard before deploy button)
   ✓ Databricks workspace: Unity Catalog enabled
   ✓ Databricks workspace: Foundation Model API enabled
   ✓ Lakebase instance provisioned (PostgreSQL endpoint + credentials ready)
   ✓ databricks CLI ≥ 0.221 installed (or wizard uses workspace API directly)

STEP 1 — Bundle deploy  (~90 seconds)
   $ databricks bundle deploy --target prod
   → Registers all pipelines, jobs, apps in the workspace
   → No data created; no jobs run yet

STEP 2 — Unity Catalog namespace  [Bootstrap job 00]  (~30 seconds)
   src/bootstrap/setup_unity_catalog.py
   → CREATE CATALOG IF NOT EXISTS docubricks_prod
   → CREATE SCHEMA: bronze, silver, gold, schema_registry, raw_landing,
                    monitoring, eval
   → CREATE VOLUME: /raw_landing/documents/, /checkpoints/, /monitoring/
   → Apply row-level security filter (tenant_id) on all silver/gold tables
   → Apply column masks: PII fields (SSN, TIN, taxpayer_id)

STEP 3 — Lakebase migrations  [Bootstrap job 01]  (~60 seconds)
   src/bootstrap/setup_lakebase.py
   → Connect via LAKEBASE_CONN secret
   → Run V001–V007 migrations in order (each idempotent: IF NOT EXISTS)
   → Verify all tables, indexes, and constraints are valid
   → Seed tenant_registry with initial tenant from onboarding config

STEP 4 — Schema registry load  [Bootstrap job 02]  (~2 minutes)
   src/bootstrap/setup_schema_registry.py
   → Read schemas/{vertical}/ for the configured tier
   → INSERT extraction_prompts (4 doc types, v1, is_active=true)
   → INSERT validation_rules, field_confidence_thresholds, model_routing
   → Load golden_tests/ into docubricks_prod.eval.ground_truth
   → Run schema test harness against golden set
     • Must pass ≥ 0.85 avg field accuracy to continue
     • Logs results to MLflow experiment /docubricks/schema-tests/

STEP 5 — Intelligence layer  [Bootstrap jobs 03–05, run in parallel]  (~3 minutes)
   03: setup_monitoring.py
       → quality_monitors.create() for each Silver extraction table
       → Register drift alert as Workflow task (runs post-pipeline)
   04: setup_genie.py
       → POST /api/2.0/genie/spaces — create per-vertical Genie workspace
       → Register Gold tables as trusted tables
       → Seed 20 domain-specific questions per vertical
       → Write genie-space-id-{vertical} to Secret scope
   05: setup_vector_search.py
       → Create Vector Search endpoint (if not exists)
       → Create Delta Sync Index on silver_parsed (BGE-large embeddings)
       → Trigger first index sync

STEP 6 — Smoke test  [Automated, runs last]  (~3 minutes)
   → Upload sample_mortgage.pdf from tests/fixtures/
   → Poll Lakebase until status = COMPLETE or FAILED (10 min timeout)
   → Assert: loan_amount extracted, avg_confidence ≥ 0.75
   → Assert: Genie answers "how many documents were processed today?" correctly
   → Print: ✓ DocuBricks is ready. Portal URL: https://...

Total wall-clock time:  ~10 minutes
User interaction time:  ~4 minutes (wizard inputs)
```

### One-command install (CLI path, for engineering teams)

```bash
git clone https://github.com/docubricks/accelerator && cd accelerator
cp .env.example .env          # Fill: DATABRICKS_HOST, TOKEN, LAKEBASE_CONN, CATALOG, TIER
databricks bundle deploy --target prod
databricks bundle run bootstrap_all --target prod
databricks bundle run smoke_test --target prod
```

### Wizard path (non-technical users, no CLI)

The onboarding wizard (a Databricks App, deployed first via CLI or Marketplace install) runs the same sequence through a Streamlit UI. See [ONBOARDING_SPEC.md](ONBOARDING_SPEC.md) for the full screen-by-screen spec.

---

## 5. Tenant Onboarding Flow

After the platform deploys, new tenants are added via the Admin app — no CLI or Databricks access required.

```
Admin app → "Onboard New Tenant"
│
├─ Input: tenant_id, name, vertical, tier, reviewer_emails
│
├─ Lakebase: INSERT INTO tenant_registry, tenant_reviewer_assignments
│
├─ Unity Catalog: bind RLS filter for tenant_id
│                 GRANT SELECT to tenant service principal on silver/gold
│
├─ Genie: add tenant_id to workspace filter instructions
│          (UC RLS enforces isolation; Genie just gets the vocab context)
│
├─ Source path: generate landing path
│               /Volumes/{catalog}/raw_landing/documents/{tenant_id}/{vertical}/
│               → share path with tenant for file drops / connector config
│
├─ Smoke test: upload sample document for this tenant
│              verify it surfaces in Portal filtered to tenant
│
└─ Activate: tenant_registry.status → ACTIVE
             send welcome email with Portal URL

SLA: < 15 minutes from form submit to first document processable
```

**Isolation guarantees:**
- UC RLS on every Silver/Gold query (zero cross-tenant data, even if app sends wrong tenant_id)
- Lakebase: all queries parameterised with tenant_id; enforced at data access layer
- UC Volume: source path scoped by tenant_id directory segment
- Genie: per-vertical workspace; tenant filter baked into workspace instructions

---

## 6. Build Phases

### Phase 0 — Foundation  _(Weeks 1–2, 1 engineer)_

**Goal:** the repo structure exists, DAB deploys without errors in a clean workspace, and Lakebase migrations run.

| Deliverable | Done when |
|---|---|
| Full directory structure committed (§2) | `ls` matches tree |
| `databricks.yml` with dev/staging/prod targets | `databricks bundle validate` passes |
| `migrations/` V001–V007 SQL files | All 7 tables created in a fresh Lakebase |
| `src/bootstrap/setup_lakebase.py` migration runner | Runs idempotently (safe to run twice) |
| `.env.example` with all required keys documented | A new engineer can configure without asking |
| GitHub Actions CI skeleton | Unit test + lint job runs on first PR |
| Stub files for all `src/` + `apps/` modules | `databricks bundle deploy --target dev` succeeds |

**Phase gate:** `databricks bundle deploy --target dev` completes in a clean workspace with no errors.

---

### Phase 1 — Core Pipeline: FS Vertical  _(Weeks 3–6, 2 engineers)_

**Goal:** a real mortgage PDF lands in the Volume, gets parsed, classified, extracted, and appears in Silver with avg_confidence ≥ 0.80.

| Deliverable | Done when |
|---|---|
| `autoloader_ingest.py` — Bronze DLT + file notification Autoloader | Bronze table populates on file drop |
| `parse_classify.py` — ai_parse_document + ai_classify DLT streaming | silver_parsed + silver_classified tables exist |
| 4 extractor files (mortgage, KYC, AML SAR, invoice) | Silver extracted tables exist with typed columns |
| `gold/fs_portfolio.py` — materialized views | Gold table queryable |
| `schemas/fs/*/prompt_v1.txt` — extraction prompts | Schema test harness passes ≥ 0.85 |
| `schemas/fs/*/validation_rules.json` | DLT expectations block bad rows |
| `schemas/fs/*/field_thresholds.json` | Per-field confidence minimums applied |
| `schemas/fs/*/golden_tests/` — ≥ 20 labeled docs per type | Test harness runs against real labelled data |
| `setup_unity_catalog.py` — UC namespace provisioner | All schemas + volumes created idempotently |
| `setup_schema_registry.py` — schema loader | Registry tables populated; test harness passes |
| `stale_doc_recovery.py` — stale state monitor | Documents stuck > 30 min are auto-requeued |

**Phase gate:** Drop a real mortgage PDF into the UC Volume → `document_registry.status = COMPLETE` within 5 minutes, `avg_confidence ≥ 0.80`. Schema test harness: all 4 doc types ≥ 0.85.

---

### Phase 2 — Application Layer  _(Weeks 7–9, 2 engineers)_

**Goal:** a non-technical user can complete the full upload → status → Genie question loop without touching the Databricks workspace.

| Deliverable | Done when |
|---|---|
| `apps/lib/` — full shared library | All 3 apps import without ImportError |
| `apps/onboarding/` — setup wizard | Matches ONBOARDING_SPEC.md: 8 screens, state machine, idempotent provisioner |
| `apps/portal/` — DocuBricks Portal | Upload + status polling + Genie chat + dashboard pages functional |
| `apps/review/` — Review & Correction UI | Queue loads, field editor saves corrections, requeue triggers |
| `apps/admin/` — Admin console | Schema prompt CRUD, accuracy trends, tenant onboarding, job monitor |
| All `app.yaml` manifests | Correct `resources:` allowlists, deploy via DAB |

**Phase gate:** A product manager (stand-in for non-technical user) completes: upload PDF → see COMPLETE status → ask a Genie question → approve a review item. Zero access to Databricks workspace UI required.

---

### Phase 3 — Intelligence Layer  _(Weeks 10–12, 1 engineer + 1 ML engineer)_

**Goal:** Genie answers domain questions correctly, Vector Search is live, FS agents run on schedule and correctly flag test documents.

| Deliverable | Done when |
|---|---|
| `setup_genie.py` — Genie provisioner | FS Genie workspace created with 20 seed questions |
| `setup_vector_search.py` | Delta Sync Index live, first sync complete |
| `fs/mortgage_risk_monitor.py` | Correctly flags seeded high-DTI document; writes to review_queue |
| `fs/kyc_refresh.py` | Correctly identifies overdue KYC profiles; creates refresh tasks |
| `fs/aml_pattern.py` | Correctly cross-references SAR patterns |
| MLflow eval harness wired into pipeline | Post-batch eval task runs; accuracy logged per field |
| `setup_monitoring.py` | Lakehouse Monitoring created for all Silver tables; drift alert fires on injection |
| `apps/lib/otel.py` live in all apps | Upload counter, processing histogram, confidence histogram visible in OTel backend |
| `gold.platform_health` materialized view | Queryable from Genie: "what was avg confidence last week?" |

**Phase gate:** MortgageRiskMonitorAgent runs on schedule, correctly flags a seeded high-DTI document, writes to review_queue, notification fires. Genie correctly answers all 20 seed questions in the FS workspace.

---

### Phase 4 — Schema Library Hardening  _(Weeks 13–14, 1 engineer + 1 domain expert)_

**Goal:** the schema library is fully engineered — promotion gate works, inheritance resolves, changelog is populated. A schema engineer can iterate on prompts without touching code.

| Deliverable | Done when |
|---|---|
| Schema promotion gate — fully wired | New prompt version → test harness auto-runs → activation only on ≥ 0.85 pass |
| `schema_test_harness.py` as Workflow task | Triggers on schema version insert; logs to MLflow |
| Inheritance tables populated | KYC EDD → KYC CDD chain resolves correctly |
| `schema_changelog` populated for all existing schemas | Every historical version has a change_type record |
| Golden test suite ≥ 50 docs per type | Real anonymised documents from design partners |
| Admin app Schema Manager → promotion gate | Engineer sees test results before activating version |

**Phase gate:** An engineer updates a mortgage prompt in the Admin app, the test harness runs automatically, they see the accuracy result (pass/fail), and either promote or reject — without a terminal or notebook.

---

### Phase 5 — Second Vertical + Marketplace Prep  _(Weeks 15–18, 2 engineers + 1 domain expert)_

**Goal:** second vertical is live; the accelerator can be demonstrated to a Databricks prospect in < 45 minutes by a field rep with no engineering support.

| Deliverable | Done when |
|---|---|
| Healthcare schema bundle (EOB, clinical note, lab report, prior auth) OR Legal (NDA, SOW, regulatory submission, court filing) | Schema test harness passes ≥ 0.85 |
| Second vertical agent (EOB reconciliation OR contract expiry) | Agent runs on schedule; correct escalation |
| Tier gating in bootstrap | Professional license check blocks Healthcare bundle in Community tier |
| `README.md` — Databricks solution accelerator format | RUNME.py entry point works in 3 fresh workspaces |
| `docs/` — quickstart, configuration, schema authoring, troubleshooting | A new customer can self-serve from docs alone |
| Demo workspace with anonymised sample docs | Field rep can run full demo without engineering |

**Phase gate:** Databricks field rep runs the accelerator end-to-end in a prospect workspace in under 45 minutes. No engineering support present.

---

### Phase 6 — Design Partners + Marketplace Launch  _(Weeks 19–24, all + 1 solutions engineer)_

**Goal:** first $2,500/month MRR via Marketplace; Databricks co-sell activated.

| Deliverable | Done when |
|---|---|
| 3 design-partner bank deployments (Enterprise tier) | All 3 workspaces COMPLETE for real documents |
| Feedback tracker for schema accuracy gaps | Tracked issues → schema improvements scheduled |
| Databricks Marketplace ISV registration | Account active; able to create listings |
| Community tier public listing | Installable from Marketplace in < 5 min |
| Starter/Professional private listing | Private offer purchasable for first paying customer |
| Databricks AI Accelerator Program application | Submitted (for $250K credits + mentorship) |
| Co-sell activation | Listed in Databricks Partner Solutions Catalog; first co-sell email sent to field |
| Data + AI Summit speaking session OR demo stage slot | Submitted |

**Phase gate:** First $2,500 MRR collected via Marketplace. One Databricks field rep has co-sold the accelerator into an active deal.

---

## 7. Testing Strategy

### Three test levels

| Level | Scope | Runs when | Databricks needed |
|---|---|---|---|
| **Unit** | Pure Python logic: schema inheritance, confidence routing, app components | Every PR | No |
| **Integration** | Autoloader → Bronze → Silver, Lakebase lifecycle, schema registry load | Merge to main | Dev workspace |
| **End-to-end** | Full document flow (upload → COMPLETE → Genie answer), duplicate guard, review flow | Release to staging | Staging workspace |

### Unit tests  _(pytest, no Databricks credential needed)_

```
tests/unit/
├── test_schema_inheritance.py    — resolve_prompt() chain resolution
├── test_confidence_routing.py    — build_field_expectations() output
├── test_lakebase_helpers.py      — lb_query / lb_exec with mock psycopg2
├── test_app_auth.py              — tenant resolution logic
├── test_otel_instruments.py      — metric recording with mock meter
└── test_onboarding_state.py      — state machine transitions + persistence
```

```bash
pytest tests/unit/ -v --cov=src --cov=apps/lib --cov-report=xml
```

### Integration tests  _(dev workspace, run on every merge to main)_

```
tests/integration/
├── test_bronze_pipeline.py       — fixture PDF → Bronze table row within 2 min
├── test_silver_extraction.py     — fixture mortgage PDF → extracted fields match expected
├── test_lakebase_lifecycle.py    — full document_registry state machine transitions
├── test_schema_registry.py       — schema load → resolve_prompt → extraction
└── test_genie_seed_question.py   — Genie returns non-empty result for seed question
```

### End-to-end tests  _(staging workspace, run on every release)_

```
tests/e2e/
├── test_mortgage_full_flow.py    — upload → COMPLETE → Genie answer → agent flag
├── test_kyc_review_flow.py       — upload → REVIEW → correction → COMPLETE
└── test_duplicate_guard.py       — same PDF uploaded twice → second is deduped
```

### Schema promotion gate  _(blocks `is_active` promotion)_

| Document type | Min avg field accuracy | Min labeled test docs |
|---|---|---|
| mortgage_application | 85% | 20 |
| kyc_cdd_form | 87% | 20 |
| aml_sar | 85% | 20 |
| invoice | 82% | 20 |

Promotion to `is_active = true` is blocked programmatically. Results logged to MLflow.

---

## 8. Marketplace Packaging & Listing

### Listing architecture

```
Community (free, GitHub)
  → github.com/docubricks/accelerator
  → RUNME.py entry point (Databricks solution accelerator format)
  → Installs FS Community schema bundle
  → No license key required

Starter · Professional (Databricks Marketplace, paid)
  → Private offer via DocuBricks ISV vendor account
  → License key issued on purchase → checked in bootstrap job 02
  → Annual subscription; billed co-terminous with customer DBU spend

Enterprise (private offer, direct)
  → Negotiated directly; provisioned via private Marketplace offer
  → Custom schema development as professional services add-on
```

### RUNME.py  _(Databricks solution accelerator entry point)_

The `RUNME.py` notebook is the entry point for the free tier — it runs when a user clicks "Open in Databricks" from the GitHub README badge.

```python
# RUNME.py
# Databricks solution accelerator entry point.
# Runs in customer workspace after cloning.

# %md
# # DocuBricks — Document Intelligence Accelerator
# **Prerequisites:** Unity Catalog enabled · Foundation Model API enabled · Lakebase provisioned

# COMMAND ----------
dbutils.widgets.text("catalog_name",   "docubricks_prod")
dbutils.widgets.text("lakebase_conn",  "")
dbutils.widgets.dropdown("vertical",   "fs", ["fs"])

# COMMAND ----------
# Option A: Run the setup wizard (recommended for first-time users)
# Opens the Databricks Apps onboarding UI
displayHTML('<a href="https://{host}/apps/docubricks-onboarding">Open Setup Wizard →</a>')

# Option B: Run headless via notebooks (for engineers / CI)
# %run ./src/bootstrap/setup_unity_catalog
# %run ./src/bootstrap/setup_lakebase
# %run ./src/bootstrap/setup_schema_registry
# %run ./src/bootstrap/setup_genie
# %run ./src/bootstrap/deploy_apps
# %run ./tests/e2e/smoke_test
```

### Marketplace submission checklist

| Item | Owner | Target date |
|---|---|---|
| Databricks ISV vendor account registered | Legal / Finance | Week 14 |
| Marketplace provider profile + listing description | Marketing | Week 15 |
| Community listing screenshots (3 screens) | Design | Week 16 |
| Community tier tested in 3 fresh workspaces (AWS, Azure, GCP) | QA | Week 17 |
| License key server deployed | Engineering | Week 16 |
| Private offer pricing configured (Starter, Professional) | Sales | Week 17 |
| Databricks AI Accelerator Program application submitted | CEO | Week 14 |
| Co-sell profile submitted to Partner Portal | Sales | Week 18 |
| Data + AI Summit talk/demo slot applied for | Marketing | Week 10 |

---

## 9. CI/CD Pipeline

### On every pull request  _(unit tests + lint + DAB validate)_

```yaml
# .github/workflows/ci.yml
on: [pull_request]
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements-dev.txt
      - run: ruff check src/ apps/ tests/       # lint
      - run: mypy src/ apps/lib/                 # type check
      - run: pytest tests/unit/ -v --tb=short --cov=src
      - run: databricks bundle validate --target dev
        env:
          DATABRICKS_HOST:  ${{ secrets.DEV_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DEV_TOKEN }}
```

### On merge to main  _(integration tests in dev workspace)_

```yaml
# .github/workflows/integration.yml
on:
  push:
    branches: [main]
jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: databricks bundle deploy --target dev
      - run: databricks bundle run bootstrap_all --target dev
      - run: databricks bundle run integration_test_suite --target dev
        timeout-minutes: 20
```

### On release tag  _(staging deploy → prod deploy, two manual approval gates)_

```yaml
# .github/workflows/release.yml
on:
  push:
    tags: ["v*"]
jobs:
  staging:
    runs-on: ubuntu-latest
    environment: staging          # Requires manual approval in GitHub
    steps:
      - run: databricks bundle deploy --target staging
      - run: databricks bundle run bootstrap_all --target staging
      - run: databricks bundle run e2e_test_suite --target staging
        timeout-minutes: 30

  production:
    needs: staging
    runs-on: ubuntu-latest
    environment: production       # Second manual approval gate
    steps:
      - run: databricks bundle deploy --target prod
      - run: databricks bundle run smoke_test --target prod
```

### Versioning

| Branch / tag | Deploys to | Gate |
|---|---|---|
| Any PR | Dev (unit + lint only) | Auto |
| Merge to `main` | Dev (integration tests) | Auto |
| `v*` tag | Staging → Prod | Two manual approvals |
| Schema-only change | Staging (schema test harness only) | Schema test harness pass |

Schema bundle versions are independent of app versions. A prompt update ships via `schema_test_harness` Workflow job without a code release.

---

## 10. Critical Path & Risks

| Risk | Phase | Probability | Impact | Mitigation |
|---|---|---|---|---|
| **Lakebase not GA** when needed | 1 | Medium | High | Abstract behind `setup_lakebase.py` interface. If GA slips past Phase 1, use Delta Live Tables for operational state (document_registry as Delta table). Switch to Lakebase when GA without changing pipeline code. |
| **Foundation Model API unavailable** in customer workspace | 1–6 | Low | High | Detect in onboarding wizard (Step 0 check). Surface clear instructions to enable. Provide fallback `ai_query()` endpoint pattern using external model serving (customer's own endpoint). |
| **Golden test documents** hard to source (real docs are sensitive) | 4 | High | Medium | Use synthetically generated documents for Phase 1–3 harness. Replace with real anonymised documents from design partners in Phase 4. Engage design partners at Phase 0. |
| **Databricks Marketplace ISV registration** takes longer than expected | 5–6 | Medium | Medium | Start registration process at the beginning of Phase 3 (minimum 2–4 weeks). Run in parallel with engineering. |
| **Design partner procurement cycles** delay FS feedback | 4–6 | High | Medium | Target design partners via Databricks field reps (warm intro). Start legal/MSA at Phase 0 to compress procurement. Offer design partner a free Enterprise license for Year 1. |
| **Databricks ships native IDP features** (first-mover compression) | All | Medium | High | Schema library depth is the moat, not the pipeline. Stay 2 verticals ahead of any Databricks native offering. Each additional vertical = months of domain expert work that can't be replicated quickly. |
| **Schema accuracy below target** for a doc type | 4 | Medium | Medium | Run test harness on all 4 FS doc types from Phase 1. If accuracy < 0.80, dedicate one domain expert sprint to prompt improvement before Phase 2. Accuracy regressions block the release, not the next sprint. |

---

## 11. Definition of Done

A phase is **Done** when all three pass:

1. **Phase gate test** — the specific acceptance test for that phase passes in a **clean workspace** (not the dev workspace used during development). Clean = no pre-existing DocuBricks resources.
2. **Documentation** — the `docs/` section relevant to that phase is written and reviewed by someone who didn't write the code.
3. **CI green** — `databricks bundle deploy --target staging` and all applicable test levels pass in the release workflow.

### Overall launch readiness checklist

```
Infrastructure
  ☐ bundle deploy in a clean workspace: < 5 minutes
  ☐ full bootstrap sequence: < 10 minutes
  ☐ smoke test: < 3 minutes

Pipeline
  ☐ p95 document processing time: < 5 minutes
  ☐ schema test harness: ≥ 0.85 for all FS doc types
  ☐ quarantine rate on representative corpus: < 5%
  ☐ duplicate guard: second upload of same file = deduped, zero reprocessing

Applications
  ☐ onboarding wizard: completes in < 4 min user interaction (measured)
  ☐ Portal accessible via Apps URL after deploy
  ☐ upload → COMPLETE visible without Databricks workspace access
  ☐ Genie: 10/10 seed questions answered correctly

Observability
  ☐ platform_health Gold view populated within 1h of first document
  ☐ Lakehouse Monitoring drift alert fires on injected confidence drop
  ☐ OTel upload counter increments on document upload (visible in backend)

Agents
  ☐ MortgageRiskMonitorAgent: correctly flags seeded high-DTI document
  ☐ KYCRefreshAgent: correctly identifies overdue profiles
  ☐ Both agents write to review_queue with correct priority and SLA

Marketplace
  ☐ Community tier installs via RUNME.py in 3 fresh workspaces (AWS, Azure, GCP)
  ☐ ISV vendor account active on Databricks Marketplace
  ☐ Co-sell profile live in Databricks Partner Solutions Catalog
  ☐ First paying customer on Starter tier
```

---

*This plan is the build contract. Phase gates are non-negotiable — no phase begins until the previous gate passes in a clean workspace.*
