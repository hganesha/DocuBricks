# DocuBricks Onboarding — Architecture & Design Specification

> Designed as Jony Ive would: one thought per screen, reduction to essence, no decoration that doesn't carry meaning.
> Architected as Karpathy would: explicit state machine, deterministic provisioning, no hidden complexity.

---

## Philosophy

The onboarding has one job: get a user from zero to "first document processed" with the minimum number of decisions. Every question we ask costs attention. Every validation we defer costs trust. Every provisioning step we expose costs confidence.

**Design constraints:**
- One primary action per screen. Never two.
- No jargon until the user has signaled expertise.
- Every field is either pre-filled, auto-detected, or mandatory. Never optional-but-confusing.
- The happy path must take under 4 minutes. We measure this.
- Errors surface where they are fixable, not at the end.

---

## Information Architecture

Five decisions the user makes. In this order. No skipping.

```
1. PROJECT       What are you building, in what environment?
2. VERTICAL      Which industry schema set?
3. WORKSPACE     Where is your Databricks?
4. RESOURCES     What to create vs what to reuse?
5. REVIEW        Is this right? (then: deploy)
```

Three states the system moves through after the user commits:

```
DEPLOYING        Provisioning in sequence with live progress
FIRST DOC        The moment of first value — process one document
COMPLETE         Handed off to the main portal
```

---

## Screen-by-Screen Design

### Screen 0 — Welcome

The logo. A sentence. A button. Nothing else.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                                                                     │
│                                                                     │
│                              ◈                                      │
│                                                                     │
│                         DocuBricks                                  │
│                                                                     │
│             Document intelligence, natively on Databricks.          │
│             Built for regulated industries.                          │
│                                                                     │
│                                                                     │
│                       ┌───────────────┐                             │
│                       │  Get started  │                             │
│                       └───────────────┘                             │
│                                                                     │
│                                                                     │
│                                          v0.1 · FS vertical         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Copy notes:**
- "Natively on Databricks" is the differentiator. Say it first.
- Version + vertical label sets expectations without a wall of text.
- No taglines, no feature lists, no screenshots. The product will show itself.

---

### Screen 1 — Project

```
┌─────────────────────────────────────────────────────────────────────┐
│  ① Project  ── ② Vertical  ── ③ Workspace  ── ④ Resources          │
│  ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                                                                     │
│   What are you building?                                            │
│                                                                     │
│   Project name                                                      │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ e.g.  Acme Bank Document Intelligence                     │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│   Environment                                                       │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│   │ ● Production │  │ ○ Staging    │  │ ○ Development│            │
│   └──────────────┘  └──────────────┘  └──────────────┘            │
│   Production resources use liquid clustering, 90-day retention,    │
│   and row-level security. Development uses smaller compute.        │
│                                                                     │
│   Owner email                                                       │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │  (auto-filled from Databricks SSO if available)           │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│                                                                     │
│                                              [  Continue  →  ]     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Fields:**
| Field | Type | Validation | Default |
|---|---|---|---|
| `project_name` | text | non-empty, < 80 chars, alphanum + spaces | — |
| `environment` | enum | `production \| staging \| development` | `production` |
| `owner_email` | email | valid email format | SSO identity if detectable |

**Environment semantics (communicated inline, not in docs):**

| Setting | Production | Staging | Development |
|---|---|---|---|
| Delta log retention | 90d | 30d | 7d |
| Compute | Serverless | Serverless | Serverless (min) |
| RLS enforced | Yes | Yes | No |
| MLflow eval | Yes | Yes | No |

---

### Screen 2 — Vertical

```
┌─────────────────────────────────────────────────────────────────────┐
│  ① Project  ── ② Vertical  ── ③ Workspace  ── ④ Resources          │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Which industry?                                                   │
│                                                                     │
│   ┌──────────────────────────┐  ┌──────────────────────────┐      │
│   │                          │  │                          │      │
│   │   Financial Services  ●  │  │   Healthcare       soon  │      │
│   │                          │  │                          │      │
│   │   Mortgage · KYC/CDD     │  │   Clinical notes · EOB   │      │
│   │   AML SAR · Invoice       │  │   Lab reports · Auth     │      │
│   │   Trade confirmation      │  │                          │      │
│   │                          │  │                          │      │
│   │   4 document types        │  │   5 document types       │      │
│   │   30+ schema fields       │  │   Available Q3 2026      │      │
│   │                          │  │                          │      │
│   └──────────────────────────┘  └──────────────────────────┘      │
│                                                                     │
│   ┌──────────────────────────┐  ┌──────────────────────────┐      │
│   │                          │  │                          │      │
│   │   Legal            soon  │  │   Insurance        soon  │      │
│   │                          │  │                          │      │
│   │   NDA · Contracts        │  │   Claims · Policy        │      │
│   │   IP filings · Court      │  │   Underwriting · Loss    │      │
│   │                          │  │                          │      │
│   │   Available Q3 2026      │  │   Available Q4 2026      │      │
│   │                          │  │                          │      │
│   └──────────────────────────┘  └──────────────────────────┘      │
│                                                                     │
│   Need another vertical?  →  Join the waitlist                     │
│                                                                     │
│                                              [  Continue  →  ]     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Interaction design:**
- Clicking "soon" cards expands a tooltip: "Join the waitlist to be first when this vertical ships." Not disabled — engaging.
- "Financial Services" card is subtly highlighted (left border accent, not a gimmick color). It's the only selectable one in v0.1.
- Document types listed are the actual schema types, not marketing copy. Engineers reading this recognize what they're deploying.

---

### Screen 3 — Workspace

```
┌─────────────────────────────────────────────────────────────────────┐
│  ① Project  ── ② Vertical  ── ③ Workspace  ── ④ Resources          │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Connect your Databricks workspace.                                │
│                                                                     │
│   Workspace URL                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ https://adb-1234567890123456.7.azuredatabricks.net        │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│   Personal access token                                             │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ dapi••••••••••••••••••••••••••••••••••••••••            │    │
│   └───────────────────────────────────────────────────────────┘    │
│   How to create a token  ↗                                         │
│                                                                     │
│                                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │  Verify connection                                        │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│                          ← waiting for verification                 │
│                                                                     │
│   ─────────────────────────────────────────────────────────────    │
│                                                                     │
│   Your token is never stored. It is used once to provision         │
│   a service principal, then discarded. All subsequent access       │
│   uses the service principal credential, scoped to DocuBricks.     │
│                                                                     │
│                                              [  Continue  →  ]     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**After successful verification:**

```
│   ✓  Connected                                                      │
│      Azure · West US 2 · Premium plan · Unity Catalog enabled       │
│                                                                     │
│      Detected: docubricks_prod catalog (existing)                   │
│      Detected: No existing DocuBricks deployment                    │
```

**After failure:**

```
│   ✗  Could not connect                                              │
│      The token may be expired, or Unity Catalog may not be         │
│      enabled on this workspace. Check workspace settings.           │
│      Learn more  ↗                                                  │
```

**Validation logic (sequential, fail fast):**
1. URL format check (client-side, instant)
2. `GET /api/2.0/clusters/spark-versions` — basic connectivity
3. `GET /api/2.1/unity-catalog/metastores` — UC enabled?
4. `GET /api/2.0/workspace/get-status?path=/` — workspace accessible?
5. `GET /api/2.0/preview/scim/v2/Me` — resolve user identity
6. Check existing DocuBricks deployment (catalog `docubricks_prod` exists?)

Each step takes ~300ms. Total verification: ~2 seconds. Show a subtle progress animation, not a spinner — the user should feel the system working, not waiting.

---

### Screen 4 — Resources

```
┌─────────────────────────────────────────────────────────────────────┐
│  ① Project  ── ② Vertical  ── ③ Workspace  ── ④ Resources          │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Resources.                                                        │
│   We pre-fill what we detected. Change anything you need.          │
│                                                                     │
│   Unity Catalog                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ ◉ Use existing     docubricks_prod              ▾         │    │
│   │ ○ Create new       docubricks_{project_slug}              │    │
│   └───────────────────────────────────────────────────────────┘    │
│   Schemas (bronze, silver, gold, schema_registry, eval)            │
│   will be created inside this catalog.                             │
│                                                                     │
│   Compute                                                           │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ ◉ Serverless (recommended)                                │    │
│   │   No cluster management. Auto-scales to zero.             │    │
│   │ ○ Existing cluster  (advanced)                            │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│   Operational Database                                              │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ ◉ Create Lakebase  (managed PostgreSQL, free tier)        │    │
│   │   docubricks-{project_slug}.lakebase.databricks.com       │    │
│   │ ○ Connect existing PostgreSQL  (advanced)                 │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│   Genie Workspace                                                   │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ ◉ Create  "DocuBricks FS — {project_name}"                │    │
│   │ ○ Use existing  (enter space ID)                          │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│                                              [  Continue  →  ]     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Decision logic for pre-fills:**
- If `docubricks_prod` catalog detected → default to "use existing"
- If no catalog detected → default to "create new" with slug derived from `project_name`
- Serverless is always the default for compute. Experts who need clusters know to change it.
- Lakebase creation is always the default. No prior PostgreSQL connection is assumed.

---

### Screen 5 — Review

This is the only screen with no inputs. Reading, not deciding. One button.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   Ready to deploy.                                                  │
│                                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │  Your configuration                                       │    │
│   │                                                           │    │
│   │  Project       Acme Bank Document Intelligence            │    │
│   │  Environment   Production                                 │    │
│   │  Owner         hari@acmebank.com                         │    │
│   │  Vertical      Financial Services (4 document types)     │    │
│   │  Workspace     adb-1234567890.7.azuredatabricks.net      │    │
│   │  Catalog       docubricks_prod (existing)                 │    │
│   │  Compute       Serverless                                 │    │
│   │  Lakebase      New — docubricks-acme.lakebase.net        │    │
│   │  Genie         New — DocuBricks FS — Acme Bank           │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│   What will be created                                              │
│   ─────────────────────                                             │
│                                                                     │
│   Data infrastructure                                               │
│   ○  5 Unity Catalog schemas                                        │
│      bronze · silver · gold · schema_registry · eval               │
│   ○  4 DLT streaming tables (Bronze → Silver)                      │
│   ○  4 Gold materialized views                                      │
│   ○  1 Vector Search index (BGE-large embeddings)                  │
│                                                                     │
│   Document schemas                                                  │
│   ○  Mortgage application  (URLA/MISMO-aligned, 280+ fields)       │
│   ○  KYC / CDD form        (40 canonical domains, bank-grade)      │
│   ○  AML SAR               (FinCEN-aligned)                        │
│   ○  Invoice               (AP/AR workflows)                       │
│                                                                     │
│   Applications                                                      │
│   ○  DocuBricks Portal     (upload · status · Genie chat)          │
│   ○  Review & Correction   (human-in-the-loop queue)               │
│   ○  Admin & Schema Manager                                        │
│                                                                     │
│   Estimated deploy time: 3–4 minutes                               │
│                                                                     │
│                    ← Go back          [  Deploy DocuBricks  ]      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Design notes:**
- "What will be created" uses ○ bullets (not checkmarks yet) — they'll turn to ✓ during deploy.
- Schema descriptions are authoritative: "URLA/MISMO-aligned, 280+ fields" tells a mortgage professional we know their world.
- "Estimated deploy time: 3–4 minutes" sets expectations before the user commits.
- The deploy button is the only interactive element. The back link is visually quiet.

---

### Screen 6 — Deploying

This screen auto-progresses. No user input. Pure feedback.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                                                                     │
│   Deploying DocuBricks.                                             │
│                                                                     │
│                                                                     │
│   ✓  Connected to workspace                                         │
│   ✓  Created Unity Catalog schemas                        2s       │
│   ✓  Uploaded extraction schemas (4 document types)      8s       │
│   ✓  Deployed DLT pipeline                               12s      │
│   ●  Provisioning Lakebase...                            ░░░░░░░   │
│   ○  Running database migrations                                    │
│   ○  Creating Genie workspace                                       │
│   ○  Seeding Genie with 20 seed questions                          │
│   ○  Creating Vector Search index                                  │
│   ○  Deploying DocuBricks Portal                                   │
│   ○  Deploying Review & Correction UI                              │
│   ○  Deploying Admin console                                       │
│   ○  Processing sample document                                     │
│                                                                     │
│                                                                     │
│   Lakebase is warming up. This is the longest step.                │
│                                                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Interaction design:**
- ✓ (completed) · ● (in progress with spinner) · ○ (pending)
- Elapsed time shown next to completed steps — builds confidence that progress is real.
- The current step has a one-sentence explanation: "Lakebase is warming up. This is the longest step." Users don't need to wonder why something takes longer than the rest.
- The screen does not show a percentage bar. Fake progress breeds distrust. Real step completion is honest.

**Error during deployment:**
```
│   ✓  Connected to workspace                                         │
│   ✓  Created Unity Catalog schemas                                  │
│   ✗  Uploaded extraction schemas                                    │
│      Error: Permission denied on catalog docubricks_prod            │
│      The token needs USAGE + CREATE on this catalog.               │
│                                                                     │
│      Grant permissions ↗ (opens Databricks catalog explorer)      │
│                                                                     │
│      [ Retry from here ]          [ Start over ]                   │
```

**Error design principle:** tell the user what failed, why, and where to fix it. "Retry from here" resumes from the failed step, not from the beginning — provisioning is idempotent.

---

### Screen 7 — First Document

The deploy succeeded. Don't send them to a dashboard. Give them a moment.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                                                                     │
│                              ✓                                      │
│                                                                     │
│                     DocuBricks is ready.                            │
│                                                                     │
│             Process your first document to see the                  │
│             full pipeline in action.                                │
│                                                                     │
│                                                                     │
│          ┌──────────────────────────────────────────────┐          │
│          │                                              │          │
│          │            Drop a PDF here                   │          │
│          │                                              │          │
│          └──────────────────────────────────────────────┘          │
│                                                                     │
│          Or use a pre-loaded sample:                                │
│                                                                     │
│          ○  Sample KYC form (HSBC format, redacted)                │
│          ○  Sample mortgage application (Fannie Mae URLA)           │
│          ○  Sample AML SAR                                          │
│                                                                     │
│          [ Process sample ]          [ Upload my own ]             │
│                                                                     │
│                                                                     │
│          Skip  →  Go to Portal                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this screen exists:** The first document processed is the moment the product becomes real. It takes 15–30 seconds. The user watches their document move through Bronze → Silver → Gold, sees the extracted fields appear, sees the confidence scores. That experience cannot be replicated by reading docs. We make it zero-friction and put it on the path.

---

## State Machine Architecture

```
State enum:
  WELCOME → PROJECT → VERTICAL → WORKSPACE → RESOURCES → REVIEW
  → DEPLOYING → FIRST_DOC → COMPLETE

Transitions are strictly linear.
Every state persists its collected data before transitioning.
Returning users resume from their last complete state.
```

### State Object Schema

```python
@dataclass
class OnboardingState:
    onboarding_id: str          # UUID, created at WELCOME
    state: str                  # current enum value
    started_at: str             # ISO 8601
    updated_at: str
    config: OnboardingConfig
    deploy_log: list[DeployStep]  # populated during DEPLOYING

@dataclass
class OnboardingConfig:
    project: ProjectConfig
    vertical: str               # 'fs' | 'healthcare' | 'legal' | 'insurance'
    workspace: WorkspaceConfig
    resources: ResourceConfig

@dataclass
class ProjectConfig:
    name: str
    slug: str                   # auto-generated: lowercase, hyphens
    environment: str            # 'production' | 'staging' | 'development'
    owner_email: str

@dataclass
class WorkspaceConfig:
    host: str                   # e.g. https://adb-xxxx.azuredatabricks.net
    cloud: str                  # 'azure' | 'aws' | 'gcp' (auto-detected)
    region: str                 # auto-detected from workspace
    plan: str                   # 'premium' | 'standard' (detected)
    service_principal_id: str   # created during DEPLOYING, not before
    # token is NEVER stored — used once, discarded

@dataclass
class ResourceConfig:
    catalog_mode: str           # 'existing' | 'create'
    catalog_name: str
    compute_mode: str           # 'serverless' | 'existing_cluster'
    cluster_id: str | None
    lakebase_mode: str          # 'create' | 'existing'
    lakebase_conn_str: str | None  # None until created
    genie_mode: str             # 'create' | 'existing'
    genie_space_id: str | None  # None until created
    genie_name: str

@dataclass
class DeployStep:
    key: str                    # e.g. 'create_catalog_schemas'
    label: str                  # e.g. 'Created Unity Catalog schemas'
    status: str                 # 'pending' | 'running' | 'complete' | 'failed'
    started_at: str | None
    elapsed_ms: int | None
    error: str | None
```

### State Persistence

During onboarding (before Lakebase exists), state is persisted to a local JSON file in the app's writable directory. After Lakebase is provisioned, it migrates to Lakebase and the file is deleted.

```
~/.docubricks/onboarding_{onboarding_id}.json   (during setup)
↓  migrated after step 'provision_lakebase' completes
lakebase: onboarding_sessions table              (durable)
```

This means: if the browser closes mid-deployment, reopening the onboarding app resumes from the last completed step.

---

## Provisioning Sequence

Each step is **idempotent**. Running it twice produces the same result. This makes "Retry from here" safe.

```python
DEPLOY_STEPS = [
    # Step key                  Label shown in UI
    "verify_workspace",         # Verify workspace access
    "create_service_principal", # Create DocuBricks service principal
    "grant_sp_permissions",     # Grant SP permissions on catalog
    "create_uc_schemas",        # Create Unity Catalog schemas
    "upload_schema_registry",   # Upload extraction prompts (4 document types)
    "create_dlt_pipeline",      # Deploy DLT pipeline
    "provision_lakebase",       # Create Lakebase + run migrations  [longest step]
    "migrate_state_to_lakebase",# Move onboarding state to Lakebase
    "create_genie_workspace",   # Create Genie space + seed questions
    "create_vector_index",      # Create Vector Search index
    "deploy_portal_app",        # Deploy DocuBricks Portal app
    "deploy_review_app",        # Deploy Review & Correction app
    "deploy_admin_app",         # Deploy Admin console app
    "write_secrets",            # Write all connection strings to secret scope
    "run_health_check",         # Verify all components respond
]
```

### Idempotency Pattern

```python
def provision_step(step_key: str, fn: Callable, *args, **kwargs):
    step = get_step(step_key)

    if step.status == 'complete':
        return  # already done; skip

    mark_running(step_key)
    try:
        result = fn(*args, **kwargs)
        mark_complete(step_key, result)
    except ProvisioningError as e:
        mark_failed(step_key, str(e))
        raise  # surface to UI

# Every step function is written to handle pre-existing state:
def create_uc_schemas(config: OnboardingConfig):
    for schema in ['bronze', 'silver', 'gold', 'schema_registry', 'eval']:
        spark.sql(f"""
            CREATE SCHEMA IF NOT EXISTS {config.resources.catalog_name}.{schema}
        """)
    # IF NOT EXISTS = idempotent
```

### Service Principal Creation (Security Design)

The user's PAT token is used for exactly one thing: creating a service principal. After that:

```
User PAT token
    ↓  used to call  POST /api/2.0/preview/scim/v2/ServicePrincipals
    ↓  used to call  POST /api/2.0/tokens/create  (for SP)
    → discarded from memory (never written to disk or Lakebase)

Service principal credentials
    → stored in Databricks Secret Scope  (docubricks-{slug})
    → all subsequent API calls use the SP token
    → SP has minimum required permissions (not workspace-admin)
```

SP permissions granted:
- `USE CATALOG` on `{catalog_name}`
- `CREATE SCHEMA`, `CREATE TABLE`, `CREATE VOLUME` on `{catalog_name}`
- `CAN USE` on the Serverless SQL warehouse
- `CAN MANAGE RUN` on the DLT pipeline job (once created)
- `CAN QUERY` on the Foundation Model API endpoints

No admin-level permissions. Fail loud if any grant fails — don't proceed with insufficient permissions.

---

## Visual Design System

### Typography

Two weights. No more.

```
Headings       Inter 600   24px   letter-spacing: -0.02em
Body           Inter 400   15px   line-height: 1.6
Captions       Inter 400   13px   color: #6b7280  (gray-500)
Monospace      JetBrains Mono 400  13px  (URLs, IDs, connection strings)
```

### Color

One accent. Everything else is gray.

```
Background     #ffffff
Surface        #f9fafb   (cards, inputs)
Border         #e5e7eb
Text primary   #111827
Text secondary #6b7280
Accent         #5B21B6   (Databricks purple — one color, used sparingly)
Success        #059669
Error          #DC2626
Progress       #5B21B6   (same as accent)
```

### Spacing

8px base unit. All spacing is a multiple of 8.

```
Screen padding     48px (6×8)
Section gap        32px (4×8)
Field gap          16px (2×8)
Inline gap         8px  (1×8)
```

### Progress Bar

Linear. Top of screen. Fills based on `(current_step / total_steps)`. Not animated past the current position — no false progress.

```
Height: 3px
Color:  #5B21B6
No border-radius — straight line, decisive
```

### Step Indicators (Deploy screen)

```
○  pending     color: #e5e7eb  (gray ring)
●  running     color: #5B21B6  (filled, subtle pulse animation)
✓  complete    color: #059669  (green check)
✗  failed      color: #DC2626  (red cross)
```

### Cards (Vertical selection)

```css
/* Selected card */
border: 2px solid #5B21B6;
background: #F5F3FF;  /* purple-50 */
box-shadow: none;

/* Unselected card */
border: 1px solid #e5e7eb;
background: #ffffff;
cursor: pointer;

/* Soon card */
border: 1px solid #e5e7eb;
background: #f9fafb;
opacity: 0.7;
cursor: default;  /* not pointer */
```

No hover animations that feel frivolous. A subtle `border-color` transition (150ms ease) is sufficient.

---

## Implementation Architecture

### Stack

```
Runtime:    Databricks Apps (Streamlit)
Language:   Python 3.11
State:      JSON file → Lakebase (migrated during deploy)
Validation: Pydantic models
API calls:  httpx (async where Streamlit supports it)
```

### File Structure

```
apps/onboarding/
  app.py                    # entry point, state machine router
  app.yaml                  # Databricks Apps manifest
  requirements.txt

  screens/
    welcome.py
    project.py
    vertical.py
    workspace.py
    resources.py
    review.py
    deploying.py
    first_doc.py

  core/
    state.py                # OnboardingState, persistence
    models.py               # Pydantic config models
    provisioner.py          # DEPLOY_STEPS executor
    validators.py           # per-screen validation functions

  steps/
    verify_workspace.py
    create_service_principal.py
    create_uc_schemas.py
    upload_schema_registry.py
    create_dlt_pipeline.py
    provision_lakebase.py
    create_genie_workspace.py
    create_vector_index.py
    deploy_apps.py
    write_secrets.py
    run_health_check.py

  assets/
    sample_kyc.pdf          # redacted KYC form for "first document" screen
    sample_mortgage.pdf     # redacted URLA form
    sample_aml_sar.pdf
```

### State Machine Router (`app.py`)

```python
import streamlit as st
from core.state import load_state, init_state
from screens import welcome, project, vertical, workspace, resources, review, deploying, first_doc

st.set_page_config(
    page_title="DocuBricks Setup",
    page_icon="◈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Load or create session
state = load_state() or init_state()

# Route to current screen — no conditionals in screens themselves
SCREENS = {
    "WELCOME":    welcome.render,
    "PROJECT":    project.render,
    "VERTICAL":   vertical.render,
    "WORKSPACE":  workspace.render,
    "RESOURCES":  resources.render,
    "REVIEW":     review.render,
    "DEPLOYING":  deploying.render,
    "FIRST_DOC":  first_doc.render,
}

render_fn = SCREENS.get(state.state, welcome.render)
render_fn(state)
```

### Screen Contract

Every screen function has the same signature and responsibilities:

```python
def render(state: OnboardingState) -> None:
    # 1. Render the UI
    # 2. On "Continue": validate, update state.config, advance state.state
    # 3. Call save_state(state) before any st.rerun()
    # 4. Never mutate state without saving first
```

### Workspace Validation (`validators.py`)

```python
import httpx

class WorkspaceValidationResult:
    connected: bool
    cloud: str | None       # 'azure' | 'aws' | 'gcp'
    region: str | None
    plan: str | None        # 'premium' | 'standard'
    uc_enabled: bool
    existing_catalog: str | None   # name if docubricks_prod detected
    error: str | None

def validate_workspace(host: str, token: str) -> WorkspaceValidationResult:
    headers = {"Authorization": f"Bearer {token}"}
    client = httpx.Client(timeout=8.0)

    # Step 1: basic connectivity
    try:
        r = client.get(f"{host}/api/2.0/clusters/spark-versions", headers=headers)
        r.raise_for_status()
    except httpx.TimeoutException:
        return WorkspaceValidationResult(connected=False,
            error="Workspace did not respond in 8 seconds. Check the URL.")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return WorkspaceValidationResult(connected=False,
                error="Token is invalid or expired. Generate a new token in Databricks.")
        return WorkspaceValidationResult(connected=False,
            error=f"Workspace returned {e.response.status_code}.")

    # Step 2: Unity Catalog
    r = client.get(f"{host}/api/2.1/unity-catalog/metastores", headers=headers)
    uc_enabled = r.status_code == 200 and len(r.json().get("metastores", [])) > 0

    # Step 3: detect cloud + region from workspace URL
    cloud, region = detect_cloud_region(host)

    # Step 4: detect existing catalog
    existing_catalog = None
    if uc_enabled:
        r = client.get(f"{host}/api/2.1/unity-catalog/catalogs", headers=headers)
        catalogs = [c["name"] for c in r.json().get("catalogs", [])]
        if "docubricks_prod" in catalogs:
            existing_catalog = "docubricks_prod"

    # Step 5: detect plan from cluster policies or features
    plan = detect_plan(host, token, client)

    return WorkspaceValidationResult(
        connected=True,
        cloud=cloud,
        region=region,
        plan=plan,
        uc_enabled=uc_enabled,
        existing_catalog=existing_catalog
    )
```

---

## Provisioner Detail: Key Steps

### `upload_schema_registry`

Uploads extraction prompts for all 4 FS document types to `schema_registry.extraction_prompts`. Prompts are packaged as Python string constants in `steps/schema_prompts/fs/` — they ship with the onboarding app, not fetched from a server.

```python
def upload_schema_registry(config: OnboardingConfig):
    from steps.schema_prompts.fs import (
        MORTGAGE_APPLICATION_PROMPT,
        KYC_CDD_PROMPT,
        AML_SAR_PROMPT,
        INVOICE_PROMPT,
    )
    prompts = [
        ("mortgage_application", "fs", MORTGAGE_APPLICATION_PROMPT),
        ("kyc_cdd_form",         "fs", KYC_CDD_PROMPT),
        ("aml_sar",              "fs", AML_SAR_PROMPT),
        ("invoice",              "fs", INVOICE_PROMPT),
    ]
    for doc_type, vertical, prompt_text in prompts:
        spark.sql(f"""
            INSERT INTO {config.resources.catalog_name}.schema_registry.extraction_prompts
                (document_type, vertical, version, is_active, prompt_text, updated_at)
            VALUES ('{doc_type}', '{vertical}', 1, true, $prompt, NOW())
            ON CONFLICT (document_type, vertical, version) DO NOTHING
        """, prompt=prompt_text)
```

### `create_dlt_pipeline`

Uploads the DLT pipeline YAML (parameterized with catalog name and environment settings) via the Pipelines API. Returns the `pipeline_id` stored in config for the portal's "trigger pipeline" functionality.

```python
def create_dlt_pipeline(config: OnboardingConfig) -> str:
    pipeline_config = render_pipeline_config(
        catalog=config.resources.catalog_name,
        environment=config.project.environment,
        serverless=(config.resources.compute_mode == "serverless"),
        vertical=config.vertical,
    )
    r = httpx.post(
        f"{config.workspace.host}/api/2.0/pipelines",
        headers={"Authorization": f"Bearer {get_sp_token(config)}"},
        json=pipeline_config
    )
    r.raise_for_status()
    pipeline_id = r.json()["pipeline_id"]
    store_secret(config, "pipeline-job-id", pipeline_id)
    return pipeline_id
```

### `create_genie_workspace`

Creates a Genie space with pre-seeded questions from `steps/genie_seeds/fs_seeds.py`. The 20 seed questions are the same ones listed in ARCHITECTURE.md §9.1, plus 16 more that were validated against real mortgage/KYC query patterns.

### `run_health_check`

The final step. Makes one request to each deployed app's health endpoint and to the Genie API. If any check fails, the deploy is marked as `DEGRADED` (not `FAILED`) — the apps are deployed; something may need attention. The user sees a yellow warning rather than a red error, with a specific "what to check" message.

---

## Resumability Design

The onboarding can be interrupted at any point:

| Interrupted during | Resume behavior |
|---|---|
| Screens 1–5 | Form data in `st.session_state`; user re-enters on browser refresh |
| DEPLOYING | State file has last completed step; "Retry from here" skips completed steps |
| After COMPLETE | Onboarding app redirects to Portal; re-opening onboarding shows "already configured" with link to Portal |

```python
def load_state() -> OnboardingState | None:
    # Check Lakebase first (post-deploy)
    # Fall back to local JSON file (pre-deploy)
    # Return None if no state found (fresh start)
    ...

def save_state(state: OnboardingState):
    if lakebase_available():
        save_to_lakebase(state)
    else:
        save_to_local_file(state)
```

---

## Accessibility & Performance

**Accessibility:**
- All inputs have explicit `<label>` associations (Streamlit handles this automatically)
- Color is never the only signal — icons accompany status colors
- Tab order follows visual order
- No timed auto-advances — the user controls every transition

**Performance:**
- Workspace validation: < 3 seconds (or show timeout message)
- Screen transitions: < 100ms (Streamlit re-render)
- Deploy progress: real-time via `st.empty()` + polling loop, 1-second refresh
- No blocking calls in the main render path — all I/O in dedicated functions

**Mobile:**
- Not a priority for v0.1. DocuBricks onboarding is done by engineers at a desk.
- Minimum viewport: 1024px wide. Below that: "Please use a desktop browser."

---

## Success Metrics

| Metric | Target | How measured |
|---|---|---|
| Onboarding completion rate | > 70% of users who start | `COMPLETE` / `WELCOME` states in Lakebase |
| Time to first document processed | < 10 minutes | `first_doc_processed_at - started_at` |
| Time to deploy (automated steps) | < 4 minutes | `deploy_log` elapsed times |
| Step error rate | < 5% per step | `FAILED` status count per `step_key` |
| Retry success rate | > 80% | Retried steps that reach `complete` |

The onboarding app writes these to `onboarding_sessions` in Lakebase. The Admin console surfaces them as a funnel dashboard — where do users drop off, which steps fail most often.

---

*This spec governs the onboarding app design and implementation. Any change to the step sequence, screen copy, or provisioning order requires updating this document and the corresponding test fixtures.*
