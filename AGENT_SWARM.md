# DocuBricks — Agent Swarm Design

> Parallel AI agent execution plan for building the platform. Each agent owns a strict, non-overlapping file set. No agent may write outside its ownership boundary. Waves gate on the previous wave completing all contracts.

---

## Dependency Graph

```
                         ┌─────────────────────────┐
                         │   WAVE 0 — FOUNDATION   │
                         │   (sequential, done by  │
                         │    coordinator first)    │
                         │                         │
                         │  • databricks.yml       │
                         │  • migrations/ V001-V007 │
                         │  • directory scaffold   │
                         │  • .env.example         │
                         │  • contracts/wave0.json │
                         └────────────┬────────────┘
                                      │ contract: wave0.json
                    ┌─────────────────┼──────────────────┐
                    ▼                 ▼                   ▼
          ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐
          │  PIPELINE    │  │   SCHEMA BUNDLE  │  │   APP LIB        │
          │  AGENT       │  │   AGENT          │  │   AGENT          │
          │              │  │                  │  │                  │
          │  src/        │  │  schemas/fs/     │  │  apps/lib/       │
          │  pipelines/  │  │  (prompts,       │  │  (auth, genie,   │
          │  Bronze →    │  │   rules,         │  │   lakebase,      │
          │  Silver →    │  │   thresholds,    │  │   otel, theme,   │
          │  Gold DLT    │  │   model routing) │  │   components/)   │
          └──────┬───────┘  └────────┬─────────┘  └───────┬──────────┘
                 │ wave1_pipeline    │ wave1_schema         │ wave1_applib
                 └──────────────────┼──────────────────────┘
                          ┌─────────┴──────────┐
                          │   WAVE 2 — fires when ALL wave1 contracts exist
                          │   Split into two concurrent fan-outs:
                          └───────────┬────────────────────────────┐
                                      │                            │
              ┌───────────────────────┼────────────────┐           │
              ▼                       ▼                ▼           ▼
    ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ ┌──────────────┐
    │ MORTGAGE         │  │ KYC              │  │ AML SAR      │ │ INVOICE      │
    │ EXTRACTOR        │  │ EXTRACTOR        │  │ EXTRACTOR    │ │ EXTRACTOR    │
    │ AGENT            │  │ AGENT            │  │ AGENT        │ │ AGENT        │
    │                  │  │                  │  │              │ │              │
    │ silver/          │  │ silver/          │  │ silver/      │ │ silver/      │
    │ extractors/      │  │ extractors/      │  │ extractors/  │ │ extractors/  │
    │ mortgage_*.py    │  │ kyc_*.py         │  │ aml_sar.py   │ │ invoice.py   │
    └──────────────────┘  └──────────────────┘  └──────────────┘ └──────────────┘

              ┌───────────────────────┬──────────────────┬──────────────────┐
              ▼                       ▼                  ▼                  ▼
    ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
    │ PORTAL           │  │ REVIEW UI        │  │ ADMIN        │  │ ONBOARDING       │
    │ AGENT            │  │ AGENT            │  │ AGENT        │  │ AGENT            │
    │                  │  │                  │  │              │  │                  │
    │ apps/portal/     │  │ apps/review/     │  │ apps/admin/  │  │ Wire real API    │
    │ (Streamlit)      │  │ (Streamlit)      │  │ (Streamlit)  │  │ into existing    │
    │                  │  │                  │  │              │  │ React app        │
    └──────────────────┘  └──────────────────┘  └──────────────┘  └──────────────────┘
                                      │
                        ┌─────────────┴──────────────────┐
                        │   WAVE 3 — fires when ALL wave2 contracts exist
                        └───────────────┬────────────────┘
                    ┌───────────────────┼───────────────────────┐
                    ▼                   ▼                        ▼
          ┌──────────────────┐ ┌─────────────────┐  ┌──────────────────────┐
          │  INTELLIGENCE    │ │  AGENT LIBRARY  │  │  OBSERVABILITY       │
          │  AGENT           │ │  AGENT          │  │  AGENT               │
          │                  │ │                 │  │                      │
          │  setup_genie.py  │ │  agents/fs/     │  │  OTel in apps/lib    │
          │  setup_vs.py     │ │  agents/hc/     │  │  setup_monitoring.py │
          │  Gold views      │ │  agents/legal/  │  │  platform_health     │
          └──────────────────┘ └─────────────────┘  └──────────────────────┘
                                      │
                        ┌─────────────┴──────────────────┐
                        │   WAVE 4 — INTEGRATION (sequential)
                        │   Test Agent + DevOps Agent
                        └────────────────────────────────┘
```

---

## Agent Roster & File Ownership

File ownership is **strict**. An agent that writes outside its boundary causes a conflict and must be rolled back.

### Wave 0 — Foundation (Coordinator)
**Owner:** Main coordinator (not a subagent)
**Files owned:**
```
databricks.yml
databricks.dev.yml
.env.example
resources/                    (empty YAML stubs — content added by agents)
migrations/V001__create_document_registry.sql
migrations/V002__create_processing_jobs.sql
migrations/V003__create_review_queue.sql
migrations/V004__create_reprocessing_queue.sql
migrations/V005__create_extraction_audit.sql
migrations/V006__create_monitoring_alerts.sql
migrations/V007__create_tenant_registry.sql
.contracts/wave0.json
```

### Wave 1 Agents

| Agent | Files owned | Reads from |
|---|---|---|
| **PipelineAgent** | `src/pipelines/**`, `resources/pipelines/*.yml` | `contracts/wave0.json` |
| **SchemaAgent** | `schemas/fs/**` | `contracts/wave0.json` |
| **AppLibAgent** | `apps/lib/**` | `contracts/wave0.json` |

### Wave 2 Agents

| Agent | Files owned | Reads from |
|---|---|---|
| **MortgageExtractorAgent** | `src/pipelines/silver/extractors/mortgage_application.py` | `contracts/wave1_pipeline.json`, `contracts/wave1_schema.json` |
| **KYCExtractorAgent** | `src/pipelines/silver/extractors/kyc_cdd_form.py` | same |
| **AMLSARExtractorAgent** | `src/pipelines/silver/extractors/aml_sar.py` | same |
| **InvoiceExtractorAgent** | `src/pipelines/silver/extractors/invoice.py` | same |
| **PortalAgent** | `apps/portal/**` | `contracts/wave1_applib.json` |
| **ReviewAgent** | `apps/review/**` | `contracts/wave1_applib.json` |
| **AdminAgent** | `apps/admin/**` | `contracts/wave1_applib.json` |
| **OnboardingAgent** | `apps/onboarding-web/src/api/databricks/index.ts` | `contracts/wave1_pipeline.json`, `contracts/wave0.json` |

### Wave 3 Agents

| Agent | Files owned | Reads from |
|---|---|---|
| **IntelligenceAgent** | `src/bootstrap/setup_genie.py`, `src/bootstrap/setup_vector_search.py`, `src/pipelines/gold/*.py` | `contracts/wave2_extractors.json` |
| **AgentLibraryAgent** | `src/agents/**` | `contracts/wave2_extractors.json` |
| **ObservabilityAgent** | `src/bootstrap/setup_monitoring.py`, updates `apps/lib/otel.py` | `contracts/wave2_apps.json` |

### Wave 4 Agents (Integration)

| Agent | Files owned | Reads from |
|---|---|---|
| **TestAgent** | `tests/**` | all wave contracts |
| **DevOpsAgent** | `resources/jobs/**`, `.github/workflows/**`, `src/bootstrap/**` | all wave contracts |

---

## Contract Protocol

Every agent reads the contracts from previous waves before starting and writes its own contract on completion. A contract is a JSON file that documents what was built — file paths, interfaces, function signatures, table names — so downstream agents don't need to re-derive them.

### Contract schema

```json
{
  "wave": 0,
  "agent": "foundation",
  "completed_at": "2026-06-04T10:00:00Z",
  "files_created": ["databricks.yml", "migrations/V001__create_document_registry.sql"],
  "catalog_name": "docubricks_prod",
  "migrations": ["V001", "V002", "V003", "V004", "V005", "V006", "V007"],
  "lakebase_tables": ["document_registry", "processing_jobs", "review_queue",
                       "reprocessing_queue", "extraction_audit", "monitoring_alerts",
                       "tenant_registry"],
  "uc_schemas": ["bronze", "silver", "gold", "schema_registry", "raw_landing", "monitoring", "eval"],
  "interfaces": {}
}
```

### Wave 1 — Pipeline contract

```json
{
  "wave": 1,
  "agent": "pipeline",
  "dlt_tables": {
    "bronze_documents": "docubricks_prod.bronze.bronze_documents",
    "bronze_quarantine": "docubricks_prod.bronze.bronze_quarantine",
    "silver_parsed": "docubricks_prod.silver.silver_parsed",
    "silver_classified": "docubricks_prod.silver.silver_classified"
  },
  "extractor_base_class": "src/pipelines/silver/extractors/_base.py",
  "extractor_interface": {
    "function": "build_extractor_table(document_type: str, schema_prompt_col: str) -> DLT streaming table"
  },
  "gold_refresh_job": "gold_pipeline"
}
```

### Wave 1 — Schema contract

```json
{
  "wave": 1,
  "agent": "schema",
  "document_types": ["mortgage_application", "kyc_cdd_form", "aml_sar", "invoice"],
  "schema_paths": {
    "mortgage_application": "schemas/fs/mortgage_application/",
    "kyc_cdd_form":         "schemas/fs/kyc_cdd_form/",
    "aml_sar":              "schemas/fs/aml_sar/",
    "invoice":              "schemas/fs/invoice/"
  },
  "required_files_per_type": ["prompt_v1.txt", "validation_rules.json",
                               "field_thresholds.json", "model_routing.json"],
  "golden_test_count": { "mortgage_application": 20, "kyc_cdd_form": 20,
                         "aml_sar": 20, "invoice": 20 }
}
```

### Wave 1 — App lib contract

```json
{
  "wave": 1,
  "agent": "applib",
  "modules": {
    "auth":           "apps/lib/auth.py",
    "genie":          "apps/lib/genie.py",
    "lakebase":       "apps/lib/lakebase.py",
    "sql_warehouse":  "apps/lib/sql_warehouse.py",
    "databricks_api": "apps/lib/databricks_api.py",
    "otel":           "apps/lib/otel.py",
    "theme":          "apps/lib/theme.py"
  },
  "components": {
    "confidence_badge":  "apps/lib/components/confidence_badge.py",
    "status_tracker":    "apps/lib/components/status_tracker.py",
    "field_editor":      "apps/lib/components/field_editor.py",
    "document_viewer":   "apps/lib/components/document_viewer.py",
    "vertical_selector": "apps/lib/components/vertical_selector.py"
  },
  "key_functions": {
    "lakebase_conn":  "context manager, returns psycopg2 connection",
    "lb_query":       "(sql, params) -> list[dict]",
    "lb_exec":        "(sql, params) -> int (rowcount)",
    "wh_query":       "(sql, params) -> list[dict] via SQL warehouse",
    "ask_genie":      "(space_id, question) -> str",
    "apply_theme":    "() -> None, call once at app entry"
  }
}
```

---

## Synchronization Mechanism

### Signal files

```
.contracts/
  wave0.json                    ← written by coordinator on Wave 0 complete
  wave1_pipeline.json           ← written by PipelineAgent on complete
  wave1_schema.json             ← written by SchemaAgent on complete
  wave1_applib.json             ← written by AppLibAgent on complete
  wave2_extractors.json         ← written when ALL 4 extractor agents complete
  wave2_apps.json               ← written when ALL 4 app agents complete
  wave3_intelligence.json
  wave3_agents.json
  wave3_observability.json
```

### Wave gate rule

- Wave N+1 agents do not start until **all** Wave N contracts exist
- A failed agent writes `wave{N}_{agent}_FAILED.json` with error details
- The coordinator decides whether to retry the agent or unblock the next wave with partial completion (only safe for independent tasks)

### Conflict prevention

Each agent is given its **file ownership list** in the prompt. The agent must:
1. Only `Write` or `Edit` files in its owned list
2. `Read` any file it needs from previous waves (read is always safe)
3. Write its contract file as its **final act** — contract = done signal

---

## Onboarding App Note

The React/Vite onboarding app at `apps/onboarding-web/` is already built. It has:
- All 8 screens implemented (`WelcomeScreen` → `FirstDocScreen`)
- Zustand store with full state machine
- Type definitions exactly matching `ONBOARDING_SPEC.md`
- Mock API (`src/api/mock/`) and `DatabricksAPI` interface

The **OnboardingAgent** in Wave 2 implements the real `src/api/databricks/index.ts` — it doesn't build screens, it wires the real Databricks API calls behind the existing `DatabricksAPI` interface.

---

## Error Handling & Recovery

| Failure scenario | Recovery |
|---|---|
| Agent writes outside ownership boundary | Detected by coordinator file-diff check; agent output discarded; agent re-run with stricter prompt |
| Agent produces syntactically invalid Python/SQL | Contract not written; next-wave agents cannot start; coordinator re-runs agent with failure context |
| Agent times out | Contract not written; coordinator spawns replacement agent with the same brief |
| Two Wave 2 agents produce conflicting imports | Impossible by design — each extractor imports only from `_base.py` and `apps/lib/` (read-only) |
| Wave 3 agent fails | Only affects its own subsystem; other Wave 3 agents proceed; DevOps agent skips failed component |

---

## Execution Timeline (Target)

```
Day 1  AM  Wave 0   coordinator (< 30 min)
Day 1  PM  Wave 1   PipelineAgent + SchemaAgent + AppLibAgent (parallel, ~2h each)
Day 2  AM  Wave 2   8 agents in parallel (~2h each)
Day 2  PM  Wave 3   3 agents in parallel (~2h each)
Day 3  AM  Wave 4   TestAgent + DevOpsAgent (sequential, ~4h total)
Day 3  PM           Integration smoke test in dev workspace
```
