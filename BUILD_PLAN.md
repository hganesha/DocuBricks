# DocuBricks — Accelerator Build Plan

> **One-line goal:** ship DocuBricks as a production-grade Databricks Marketplace accelerator, deployable into any customer workspace in under 30 minutes, generating $1.5M ARR by month 18.

## Current Build Status

> Built by AI agent swarm (8 parallel agents across 2 waves). Reviewed and corrected against local verification on 2026-06-05.

| Phase | Goal | Status | Gate met? |
|---|---|---|---|
| **Phase 0 — Foundation** | Repo scaffold, DAB manifest, migrations, CI/CD | ✅ Built locally | 🔄 Readiness passes; `databricks` CLI unavailable for DAB validation |
| **Phase 1 — Core Pipeline** | Bronze→Silver→Gold, 4 FS extractors, schema bundle | 🔄 Implemented on disk, not workspace-verified | ⏳ Awaiting clean workspace smoke test |
| **Phase 2 — Application Layer** | Portal, Review UI, Admin, shared lib, onboarding app | ✅ Built locally | 🔄 Frontend build/lint and unit tests pass; workspace UX walkthrough pending |
| **Phase 3 — Intelligence Layer** | Genie, Vector Search, FS agents, OTel, Monitoring | 🔄 Implemented on disk, not workspace-verified | ⏳ Awaiting agent schedule / monitoring tests |
| **Phase 4 — Schema Hardening** | Promotion gate, changelog, schema asset gates | ✅ Repo-side complete | 🔄 Synthetic corpus + gate pass; real/anonymized corpus and workspace promotion run remain |
| **Phase 5 — 2nd Vertical + Marketplace** | Healthcare schemas, RUNME.py, demo workspace | ✅ Repo-side complete | 🔄 Healthcare/demo/Marketplace prep assets pass; Marketplace account and live demo workspace remain |
| **Phase 6 — Design Partners + Launch** | 3 bank deployments, Marketplace listing, co-sell | ⏳ Not started | — |

**Delivered on disk:** 68 Python files, 27 TypeScript/TSX files, 28 YAML resource files, 158 JSON files, and 19 Markdown docs, excluding `node_modules`, `dist`, `.git`, and worktrees.

**Fresh local verification on 2026-06-05:**

| Check | Result | Notes |
|---|---|---|
| `python3 scripts/check_readiness.py` | PASS | 32 required paths present, including `apps/onboarding/app.py` and `apps/onboarding/app.yaml` |
| `python3 scripts/validate_schema_assets.py` | PASS | FS: 20 goldens per type, 80 aggregate. Healthcare: 5 goldens per type across EOB, clinical note, lab report, prior auth |
| `python3 -m pytest tests/unit -q` | PASS | 131 passed |
| `npm run build` in `apps/onboarding-web` | PASS | TypeScript and Vite production build pass |
| `npm run lint` in `apps/onboarding-web` | PASS | ESLint clean |
| `databricks bundle validate` | FAIL | `databricks` command not installed on PATH |

**Planning implication:** local repo checks are now clean and Phases 4–5 are complete for repository assets. Workspace deployment, Marketplace registration, and design-partner corpus collection remain external gates before production launch.

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

Items marked ✅ exist on disk. Items marked ⏳ are planned but not yet built.

```
docubricks/
│
├── databricks.yml                     ✅ DAB manifest — dev/staging/prod targets
├── .env.example                       ✅ All required config keys documented
├── AGENT_SWARM.md                     ✅ Agent dependency graph + contract protocol
│
├── resources/                         ✅ All DAB resource definitions written
│   ├── pipelines/
│   │   ├── ingestion.yml              ✅
│   │   ├── processing.yml             ✅
│   │   └── gold.yml                   ✅
│   ├── jobs/
│   │   ├── bootstrap/
│   │   │   ├── 00_setup_uc.yml        ✅
│   │   │   ├── 01_schema_registry.yml ✅
│   │   │   ├── 02_load_schemas.yml    ✅
│   │   │   ├── 03_monitoring.yml      ✅
│   │   │   ├── 04_genie.yml           ✅
│   │   │   └── 05_vector_search.yml   ✅
│   │   ├── ops/
│   │   │   ├── stale_doc_recovery.yml ✅
│   │   │   ├── schema_test_harness.yml✅
│   │   │   └── daily_health_check.yml ✅
│   │   └── agents/
│   │       ├── fs_mortgage_risk.yml   ✅
│   │       ├── fs_kyc_refresh.yml     ✅
│   │       ├── fs_aml_pattern.yml     ✅
│   │       ├── legal_contract_expiry.yml ✅
│   │       └── hc_eob_reconciliation.yml ⏳ Phase 5
│   └── apps/
│       ├── onboarding.yml             ✅
│       ├── portal.yml                 ✅
│       ├── review.yml                 ✅
│       └── admin.yml                  ✅
│
├── src/
│   ├── pipelines/
│   │   ├── bronze/
│   │   │   └── autoloader_ingest.py   ✅ 449 lines — file notification Autoloader
│   │   ├── silver/
│   │   │   ├── parse_classify.py      ✅ 466 lines — ai_parse + ai_classify DLT
│   │   │   ├── extract_router.py      ✅ routes by document_type
│   │   │   └── extractors/
│   │   │       ├── _base.py           ✅ 593 lines — shared extractor pattern
│   │   │       ├── mortgage_application.py ✅ 590L — 14 typed cols, 0.80 review
│   │   │       ├── kyc_cdd_form.py    ✅ 577L — 15 typed cols, 0.87 review (BSA)
│   │   │       ├── aml_sar.py         ✅ 363L — 0.90 review (FinCEN)
│   │   │       └── invoice.py         ✅ 327L — AP workflow
│   │   └── gold/
│   │       ├── fs_portfolio.py        ✅ mortgage/KYC/AML Gold views
│   │       └── platform_health.py     ✅ unified observability Gold view
│   ├── bootstrap/
│   │   ├── setup_unity_catalog.py     ✅ catalog + schemas + volumes + RLS
│   │   ├── setup_lakebase.py          ✅ migration runner (migration_log idempotency)
│   │   ├── setup_schema_registry.py   ✅ MERGE-based schema loader
│   │   ├── setup_genie.py             ✅ Genie REST API + 20 seed questions
│   │   ├── setup_vector_search.py     ✅ BGE-large Delta Sync Index
│   │   └── setup_monitoring.py        ✅ Lakehouse Monitoring per Silver table
│   ├── agents/
│   │   ├── fs/
│   │   │   ├── mortgage_risk_monitor.py ✅ daily DTI/LTV/score flags + Claude briefing
│   │   │   ├── kyc_refresh.py           ✅ weekly 30-day look-ahead + reviewer assign
│   │   │   └── aml_pattern.py           ✅ daily cross-reference + HIGH alert
│   │   ├── healthcare/
│   │   │   └── eob_reconciliation.py    ⏳ Phase 5
│   │   └── legal/
│   │       └── contract_expiry.py       ✅ daily 90-day look-ahead + Claude briefing
│   └── ops/
│       ├── stale_doc_recovery.py        ✅ 15-min poll; >30min stuck → FAILED + requeue
│       ├── schema_test_harness.py       ✅ ai_query eval + MLflow + promotion gate
│       └── daily_health_check.py        ✅ 4-check suite + monitoring_alerts write
│
├── apps/
│   ├── lib/                           ✅ Shared library — all 3 Streamlit apps import this
│   │   ├── __init__.py                ✅
│   │   ├── auth.py                    ✅ SSO + tenant resolution + role enforcement
│   │   ├── genie.py                   ✅ async Genie Conversation API client
│   │   ├── lakebase.py                ✅ ThreadedConnectionPool + lb_query/exec helpers
│   │   ├── sql_warehouse.py           ✅ @st.cache_resource SQL connector + wh_query_df
│   │   ├── databricks_api.py          ✅ Files API, Jobs API, volume upload, pipeline trigger
│   │   ├── otel.py                    ✅ OTel setup + 5 pre-created instruments
│   │   ├── theme.py                   ✅ DocuBricks Streamlit theme
│   │   └── components/
│   │       ├── __init__.py            ✅
│   │       ├── confidence_badge.py    ✅ green/amber/red score badge
│   │       ├── status_tracker.py      ✅ auto-polling status card
│   │       ├── field_editor.py        ✅ editable field grid + diff view
│   │       ├── document_viewer.py     ✅ PDF iframe / image / download fallback
│   │       └── vertical_selector.py   ✅ tenant-aware vertical picker + Genie routing
│   ├── onboarding-web/                ✅ ALREADY EXISTED — React 19 + Vite + Zustand
│   │   └── src/api/databricks/
│   │       └── index.ts               ✅ 1,550L — real DatabricksAPI: all 15 provision steps
│   ├── portal/                        ✅ DocuBricks Portal (Streamlit)
│   │   ├── app.yaml                   ✅ resource allowlist: warehouse, jobs, volumes
│   │   ├── app.py                     ✅ theme + session + nav router
│   │   ├── requirements.txt           ✅
│   │   └── pages/
│   │       ├── upload.py              ✅ SHA-256 dedup + OTel-traced upload flow
│   │       ├── status.py              ✅ real-time Lakebase polling + field detail
│   │       ├── genie_chat.py          ✅ vertical-aware chat + seed pills + OTel
│   │       └── dashboard.py           ✅ date-range filtered Gold views
│   ├── review/                        ✅ Review & Correction UI (Streamlit)
│   │   ├── app.py                     ✅
│   │   └── pages/
│   │       ├── queue.py               ✅ document_viewer + field_editor + 3-button form
│   │       └── field_editor_page.py   ✅ 7-day history + field_diff_view
│   └── admin/                         ✅ Admin & Schema Manager (Streamlit)
│       ├── app.py                     ✅
│       └── pages/
│           ├── schema_prompts.py      ✅ versioned prompt CRUD + promotion gate trigger
│           ├── accuracy_trends.py     ✅ WoW confidence alerts + low-field ranking
│           ├── tenant_onboarding.py   ✅ new tenant form + smoke-test poller
│           └── job_monitor.py         ✅ run history + stale doc requeue
│
├── Schemas/                           ✅ FS schema bundle (all 4 doc types)
│   └── fs/
│       ├── mortgage_application/      ✅ URLA/MISMO-aligned — prompt, rules, thresholds,
│       │   └── golden_tests/             model_routing, 20 synthetic golden tests per FS type
│       ├── kyc_cdd_form/              ✅ BSA/FinCEN CDD Rule — 40 canonical domains
│       ├── aml_sar/                   ✅ FinCEN e-Filing schema aligned
│       ├── invoice/                   ✅ AP/AR standard
│       └── healthcare/                ✅ Professional bundle — 4 doc types, 5 demo goldens each
│
├── migrations/                        ✅ All 8 Lakebase DDL files (idempotent)
│   ├── V001__create_document_registry.sql   ✅ (+ 4 indexes)
│   ├── V002__create_processing_jobs.sql     ✅
│   ├── V003__create_review_queue.sql        ✅ (+ SLA partial index)
│   ├── V004__create_reprocessing_queue.sql  ✅ (UNIQUE conflict guard)
│   ├── V005__create_extraction_audit.sql    ✅
│   ├── V006__create_monitoring_alerts.sql   ✅ (CHECK constraint on alert_type)
│   ├── V007__create_tenant_registry.sql     ✅ (+ tenant_users, onboarding_sessions)
│   └── V008__create_schema_library_tables.sql ✅ (schema inheritance + changelog)
│
├── tests/
│   ├── unit/                          ✅ 6 files, 131 tests, no Databricks required
│   │   ├── test_schema_inheritance.py ✅ 30 tests — resolve_prompt chain
│   │   ├── test_confidence_routing.py ✅ 35 tests — threshold routing logic
│   │   ├── test_lakebase_helpers.py   ✅ 28 tests — mock psycopg2 pool
│   │   ├── test_onboarding_state.py   ✅ 35 tests — state machine + persistence
│   │   ├── test_check_readiness.py    ✅ prerequisite checks
│   │   └── test_schema_asset_coverage.py ✅ Phase 4/5 asset coverage gate
│   ├── integration/
│   │   └── test_lakebase_lifecycle.py ✅ 22 tests (@pytest.mark.integration)
│   ├── e2e/
│   │   └── smoke_test.py              ✅ 8-step end-to-end (upload → Genie answer)
│   └── fixtures/
│       └── sample_mortgage.pdf        ✅ placeholder
│
├── .github/workflows/
│   ├── ci.yml                         ✅ PR: ruff + mypy + pytest unit + bundle validate
│   ├── integration.yml                ✅ merge to main: deploy dev + integration tests
│   └── release.yml                    ✅ tag v*: staging (auto) → prod (2x manual gate)
│
├── .contracts/                        ✅ Agent handoff contracts (wave0 + wave1 × 4)
├── ARCHITECTURE.md                    ✅ 22-section technical architecture (2,956L)
├── AGENT_SWARM.md                     ✅ Swarm design: dependency graph + sync protocol
├── BUILD_PLAN.md                      ✅ This file
├── ONBOARDING_SPEC.md                 ✅ UX spec (8 screens, state machine, provisioner)
└── README.md                          ✅ Marketplace/customer entry docs exist
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
    description: Primary vertical (fs | healthcare | legal | insurance | manufacturing | real_estate)
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

### Phase 0 — Foundation  🔄 MOSTLY BUILT, GATE OPEN  _(built by agent swarm, Wave 0)_

**Goal:** the repo structure exists, DAB deploys without errors in a clean workspace, and Lakebase migrations run.

| Deliverable | Status |
|---|---|
| Full directory structure (§2) | ✅ Built |
| `databricks.yml` — dev/staging/prod targets | ✅ Built |
| `migrations/` V001–V008 SQL files | ✅ Built (8 files, indexes + constraints + schema inheritance) |
| `src/bootstrap/setup_lakebase.py` — migration runner | ✅ Built (migration_log idempotency) |
| `.env.example` — all required keys documented | ✅ Built |
| GitHub Actions CI/CD (ci.yml, integration.yml, release.yml) | ✅ Built |
| All DAB resource YAML stubs | ✅ Built |
| Local readiness check | ❌ Fails: `resources/apps/onboarding.yml` points to missing `apps/onboarding/` |
| Bundle validation | ❌ Not run: Databricks CLI unavailable locally |

**Phase gate:** `databricks bundle validate --target dev` and `databricks bundle deploy --target dev` — ❌ not met yet.

---

### Phase 1 — Core Pipeline: FS Vertical  🔄 IMPLEMENTED, NOT GATE-VERIFIED  _(built by Wave 1 + Wave 2 agents)_

**Goal:** a real mortgage PDF lands in the Volume, gets parsed, classified, extracted, and appears in Silver with avg_confidence ≥ 0.80.

| Deliverable | Status |
|---|---|
| `autoloader_ingest.py` — Bronze DLT, file notification Autoloader | ✅ 449 lines |
| `parse_classify.py` — ai_parse_document + ai_classify | ✅ 466 lines |
| `extract_router.py` — fan-out routing per document_type | ✅ Built |
| `extractors/_base.py` — shared extractor pattern | ✅ 593 lines |
| 4 extractor files (mortgage 590L, KYC 577L, AML SAR 363L, invoice 327L) | ✅ Built |
| `gold/fs_portfolio.py` — mortgage/KYC/AML Gold views | ✅ Built |
| `gold/platform_health.py` — observability Gold view | ✅ Built |
| `Schemas/fs/*/prompt_v1.txt` — URLA/BSA/FinCEN-aligned prompts | ✅ Built |
| `Schemas/fs/*/validation_rules.json` — DLT expectation configs | ✅ Built |
| `Schemas/fs/*/field_thresholds.json` — per-field confidence minimums | ✅ Built |
| `Schemas/fs/*/model_routing.json` | ✅ Built |
| `Schemas/fs/*/golden_tests/` — 20 synthetic tests per type | ✅ Built (80 total FS seed docs) |
| `setup_unity_catalog.py` — UC namespace + RLS provisioner | ✅ Built |
| `setup_schema_registry.py` — MERGE-based schema loader | ✅ Built |
| `stale_doc_recovery.py` — 30-min stuck doc recovery | ✅ Built |
| `daily_health_check.py` — 4-metric health suite | ✅ Built |
| `schema_test_harness.py` — MLflow-backed promotion gate | ✅ Built |

**Local verification:** unit test suite passes locally; no live Databricks pipeline run has been recorded.

**Phase gate:** Drop a real mortgage PDF → `document_registry.status = COMPLETE` within 5 min, `avg_confidence ≥ 0.80`. ⏳ Pending workspace deployment.

---

### Phase 2 — Application Layer  ✅ BUILT LOCALLY, WORKSPACE UX PENDING  _(built by Wave 2 agents)_

**Goal:** a non-technical user completes the full upload → status → Genie question loop without touching the Databricks workspace.

| Deliverable | Status |
|---|---|
| `apps/lib/` — shared library (7 modules + 5 components) | ✅ Built |
| `apps/onboarding-web/` — React/Vite setup wizard | ✅ Built; `npm run build` and `npm run lint` pass |
| `apps/onboarding/` — Databricks App source for `resources/apps/onboarding.yml` | ✅ Built; includes Streamlit app source and state helpers |
| `apps/portal/` — Upload, Status, Genie chat, Dashboard pages | ✅ Built (8 files) |
| `apps/review/` — Review queue + field diff history | ✅ Built (5 files) |
| `apps/admin/` — Schema prompts, accuracy trends, tenant onboarding, job monitor | ✅ Built (6 files) |
| All `app.yaml` manifests with resource allowlists | ✅ Built |

**Note:** onboarding now has both the React/Vite implementation (`apps/onboarding-web/`) and the DAB-compatible Streamlit app source (`apps/onboarding/`).

**Phase gate:** Non-technical walkthrough: upload → COMPLETE → Genie question → review approval without workspace access. ⏳ needs workspace walkthrough.

---

### Phase 3 — Intelligence Layer  🔄 IMPLEMENTED, NOT GATE-VERIFIED  _(built by Wave 2 agents)_

**Goal:** Genie answers domain questions correctly, Vector Search is live, FS agents run on schedule and flag test documents.

| Deliverable | Status |
|---|---|
| `setup_genie.py` — Genie REST API provisioner + 20 FS seed questions | ✅ Built |
| `setup_vector_search.py` — BGE-large Delta Sync Index | ✅ Built |
| `setup_monitoring.py` — Lakehouse Monitoring per Silver table | ✅ Built |
| `fs/mortgage_risk_monitor.py` — daily DTI/LTV/credit score flagging + Claude briefing | ✅ Built |
| `fs/kyc_refresh.py` — weekly 30-day look-ahead + priority routing | ✅ Built |
| `fs/aml_pattern.py` — daily cross-reference + MONITORING_ALERT write | ✅ Built |
| `legal/contract_expiry.py` — daily 90-day look-ahead (bonus: Phase 5 item done early) | ✅ Built |
| `apps/lib/otel.py` — 5 OTel instruments live in all 3 Streamlit apps | ✅ Built |
| `gold.platform_health` materialized view | ✅ Built |

**Phase gate:** MortgageRiskMonitorAgent flags seeded high-DTI document → review_queue → notification. ⏳ Pending workspace deployment and scheduled-agent verification.

---

### Phase 4 — Schema Library Hardening  ✅ REPO-SIDE COMPLETE  _(workspace + real corpus still required for production gate)_

**Goal:** promotion gate fully wired, inheritance resolves, 50+ golden docs per type from real (anonymised) documents.

| Deliverable | Status |
|---|---|
| `schema_test_harness.py` as Workflow task (resource YAML exists) | ✅ Built |
| Admin Schema Manager shows test results before promotion | ✅ Built (`schema_prompts.py`) |
| Schema promotion gate: new version → auto-test → activate on pass | ✅ Logic built; needs workspace run to verify end-to-end |
| Schema inheritance tables + V-migration | ✅ Built (`V008__create_schema_library_tables.sql`) |
| `schema_changelog` auto-populated | ✅ Built in test harness |
| FS golden test suite ≥ 20 docs per type | ✅ Built with synthetic tests |
| FS golden corpus ≥ 50 aggregate labeled tests | ✅ Built: 80 synthetic tests across 4 FS document types |
| Schema asset coverage gate | ✅ Built (`scripts/validate_schema_assets.py`, `test_schema_asset_coverage.py`) |
| Production golden suite ≥ 50 real/anonymized docs per type | 🔄 External design-partner collection required |

**Remaining production blocker:** production-grade accuracy claims require real/anonymized documents. Unblock by engaging Phase 6 design partners early.

**Phase gate:** Engineer updates prompt in Admin app, test harness runs, result displayed, version promoted — ⏳ needs workspace + real golden docs.

---

### Phase 5 — Second Vertical + Marketplace Prep  ✅ REPO-SIDE COMPLETE

**Goal:** second vertical live; field rep can demo in < 45 minutes without engineering support.

| Deliverable | Owner | Notes |
|---|---|---|
| Healthcare schema bundle (EOB, clinical note, lab report, prior auth) | Domain expert + engineer | ✅ Complete repo bundle: prompt, validation rules, thresholds, routing, and 5 goldens per type |
| `src/agents/healthcare/eob_reconciliation.py` | Agent library engineer | ✅ Built |
| Legal schema bundle | Domain expert + engineer | 🔄 Partial: NDA/MSA and SOW have 5 tests each; court/regulatory have assets but no tests |
| Tier gating in bootstrap | Engineer | 🔄 Needs live license/key verification |
| `README.md` + `RUNME.py` — Databricks solution accelerator format | Engineer + marketing | ✅ Files exist; fresh-workspace install not verified |
| `docs/` — quickstart, configuration, schema authoring, troubleshooting | Technical writer | ✅ Core docs plus field-rep demo and Marketplace listing draft |
| Demo workspace — anonymised sample documents | Solutions engineer | ✅ Synthetic demo manifest built (`demo/healthcare/README.md`); live workspace still pending |

**Phase gate:** Field rep runs full accelerator end-to-end in prospect workspace in < 45 min, no engineering support. ⏳ Requires Databricks CLI/workspace deployment and Marketplace/demo account setup.

---

### Phase 6 — Design Partners + Marketplace Launch  ⏳ NOT STARTED

**Goal:** first $2,500/month MRR via Marketplace; Databricks co-sell activated.

| Deliverable | Owner | Target |
|---|---|---|
| 3 design-partner bank deployments (Enterprise tier) | Solutions engineer | Week 19 |
| Golden test doc collection from design partners (unblocks Phase 4 gate) | Solutions engineer | Week 19 |
| Databricks Marketplace ISV registration | Legal / Finance | **Start now** — 2–4 week process |
| Community tier public listing | Engineering + marketing | Week 20 |
| Starter/Professional private listing | Sales | Week 21 |
| Databricks AI Accelerator Program application | CEO | **Submit now** — takes 4–6 weeks |
| Co-sell profile in Partner Solutions Catalog | Sales | Week 22 |
| Data + AI Summit talk/demo stage slot | Marketing | **Apply now** — deadline-driven |

**Phase gate:** First $2,500 MRR collected via Marketplace. One Databricks field rep has co-sold into an active deal.

---

## 7. Testing Strategy

### Three test levels

| Level | Scope | Runs when | Databricks needed |
|---|---|---|---|
| **Unit** | Pure Python logic: schema inheritance, confidence routing, app components | Every PR | No |
| **Integration** | Autoloader → Bronze → Silver, Lakebase lifecycle, schema registry load | Merge to main | Dev workspace |
| **End-to-end** | Full document flow (upload → COMPLETE → Genie answer), duplicate guard, review flow | Release to staging | Staging workspace |

### Unit tests  _(pytest, no Databricks credential needed)_  ✅ Passing locally

```
tests/unit/                          ✅ 131 tests across 6 files
├── test_schema_inheritance.py    ✅  30 tests — resolve_prompt() EXTENDS/SPECIALISES chain
├── test_confidence_routing.py    ✅  35 tests — per-doc threshold routing + field gates
├── test_lakebase_helpers.py      ✅  28 tests — lb_query/exec/returning, mock pool
├── test_onboarding_state.py      ✅  35 tests — state machine + JSON persistence
├── test_check_readiness.py       ✅  prerequisite validation checks
└── test_schema_asset_coverage.py ✅  Phase 4/5 schema asset gate
```

```bash
pytest tests/unit/ -v --cov=src --cov=apps/lib --cov-report=xml
```

Fresh local run on 2026-06-05:

```text
python3 -m pytest tests/unit -q
131 passed
```

Current status: package/module layout and onboarding source path are fixed; unit tests are green locally.

### Integration tests  _(dev workspace required)_

```
tests/integration/
└── test_lakebase_lifecycle.py    ✅  22 tests (@pytest.mark.integration, real psycopg2)
                                      — full document_registry state transitions
                                      — ON CONFLICT upsert, constraint violations
                                      — rolled-back transactions per test

⏳ Still needed:
    test_bronze_pipeline.py       — fixture PDF → Bronze table row within 2 min
    test_silver_extraction.py     — mortgage PDF → extracted fields match expected
    test_genie_seed_question.py   — Genie returns non-empty for seed question
```

### End-to-end tests  _(staging workspace required)_

```
tests/e2e/
└── smoke_test.py                 ✅  8 steps: upload → COMPLETE → Silver assert → Genie answer

⏳ Still needed:
    test_kyc_review_flow.py       — upload → REVIEW → correction → COMPLETE
    test_duplicate_guard.py       — same PDF uploaded twice → second deduped
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
  ✅ All resource files exist (databricks.yml, 19 job YAMLs, 4 app YAMLs, 3 pipeline YAMLs)
  ❌ Local readiness check fails: missing apps/onboarding/app.py and apps/onboarding/app.yaml
  ❌ databricks bundle validate not run locally: Databricks CLI unavailable
  ☐  bundle deploy in a clean workspace: < 5 minutes        [needs workspace test]
  ☐  full bootstrap sequence: < 10 minutes                   [needs workspace test]
  ☐  smoke test: < 3 minutes                                 [needs workspace test]

Pipeline
  ✅ All 4 DLT extractor tables written with correct column types
  ✅ DLT expectations configured (expect_or_fail / expect_or_drop / expect)
  ✅ Schema prompts written and aligned to URLA/BSA/FinCEN standards
  ☐  p95 document processing time: < 5 minutes               [needs workspace test]
  ☐  schema test harness: ≥ 0.85 for all FS doc types        [needs workspace run + representative corpus]
  ☐  quarantine rate on representative corpus: < 5%           [needs workspace test]
  ☐  duplicate guard: second upload = deduped, zero reprocessing [needs workspace test]

Applications
  ✅ 5 app surfaces written (onboarding, onboarding-web, portal, review, admin)
  ✅ DAB onboarding resource points to existing apps/onboarding/
  ✅ onboarding-web build/lint pass locally
  ✅ Real DatabricksAPI implemented (all 15 provision steps wired)
  ✅ Shared library complete: 7 modules + 5 Streamlit components
  ☐  onboarding wizard: completes in < 4 min user interaction [needs UX walkthrough]
  ☐  Portal accessible via Apps URL after deploy              [needs workspace test]
  ☐  upload → COMPLETE visible without workspace access       [needs UX walkthrough]
  ☐  Genie: 10/10 seed questions answered correctly           [needs workspace test]

Observability
  ✅ OTel instruments defined (5 metrics across all 3 apps)
  ✅ Lakehouse Monitoring setup script written
  ✅ platform_health Gold view defined
  ☐  platform_health populated within 1h of first document    [needs workspace test]
  ☐  drift alert fires on injected confidence drop            [needs workspace test]
  ☐  OTel upload counter visible in backend                   [needs OTel endpoint config]

Agents
  ✅ MortgageRiskMonitorAgent written (daily DTI/LTV/score + Claude briefing)
  ✅ KYCRefreshAgent written (weekly + priority routing)
  ✅ AMLPatternAgent written (cross-reference + HIGH alert)
  ✅ ContractExpiryAgent written (Phase 5 item done early)
  ☐  MortgageRiskAgent correctly flags seeded high-DTI document [needs workspace test]
  ☐  KYCRefreshAgent correctly identifies overdue profiles    [needs workspace test]

Tests
  ✅ 131 unit tests passing locally
  ✅ 22 integration tests written (test_lakebase_lifecycle)
  ✅ E2E smoke_test.py written (8-step full flow)
  ☐  test_kyc_review_flow.py                                  [still needed]
  ☐  test_duplicate_guard.py                                  [still needed]
  ☐  test_genie_seed_question.py                              [still needed]

Marketplace
  ✅ README.md + RUNME.py entry point exists
  ✅ Marketplace listing draft exists (`docs/marketplace-listing.md`)
  ✅ Healthcare field-rep demo runbook exists (`docs/field-rep-demo.md`)
  ☐  Community tier tested in 3 fresh workspaces              [Phase 5]
  ☐  ISV vendor account active on Databricks Marketplace      [start now — 2–4 weeks]
  ☐  Databricks AI Accelerator Program application submitted  [start now — 4–6 weeks]
  ☐  Co-sell profile live in Partner Solutions Catalog        [Phase 6]
  ☐  First paying customer on Starter tier                    [Phase 6]
```

### What to do next (priority order)

1. **Install/configure Databricks CLI** — run `databricks bundle validate --target dev`.
2. **Deploy to a dev workspace** — run `databricks bundle deploy --target dev` + all bootstrap jobs. This validates the pipeline in a real environment and is the blocker for Phases 0–3 gates.
3. **Run field-rep demo in a live workspace** — use `docs/field-rep-demo.md` with the Healthcare bundle.
4. **Expand real golden corpus** — FS has 20 synthetic docs per type; production Phase 4 accuracy claims still need real/anonymized 50+ docs per type from design partners.
5. **Start ISV Marketplace registration** — 2–4 week process; use `docs/marketplace-listing.md` as the first listing draft.
6. **Submit AI Accelerator Program application** — $250K credits, requires working demo.
7. **Complete remaining Legal goldens** — optional Enterprise packaging hardening; Professional Healthcare package is ready repo-side.

---

*This plan is the build contract. Phase gates are non-negotiable. Local repository gates now pass, and Phases 4–5 are complete for repo assets. Clean workspace Databricks deployment, Marketplace registration, and real design-partner corpora remain before production launch.*
