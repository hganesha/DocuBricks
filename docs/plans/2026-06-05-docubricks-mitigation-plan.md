# DocuBricks Mitigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert the current DocuBricks repo from partial scaffold into a Phase 0 gate-ready accelerator, then reduce the highest Phase 1 and Phase 2 delivery risks.

**Architecture:** Stabilize the repo around the existing Databricks Asset Bundle, Lakebase migration model, DLT pipeline modules, and onboarding web prototype. Avoid expanding product scope until bundle validation, frontend build, CI, and clean workspace bootstrap are reproducible.

**Tech Stack:** Databricks Asset Bundles, Python, SQL migrations, DLT notebooks, React, TypeScript, Vite, ESLint, GitHub Actions.

---

## Current Risk Summary

| Risk | Severity | Evidence | Mitigation |
|---|---:|---|---|
| No phase is gate-complete | Critical | `BUILD_PLAN.md` requires clean workspace gate, docs, and CI green | Make Phase 0 the only active milestone until all Phase 0 checks pass |
| Bundle cannot be validated locally | Critical | `databricks` CLI missing in current environment | Add CLI prerequisite docs and CI bundle validation job |
| Bundle references missing source | Critical | `databricks.yml` references `src/pipelines/gold/platform_health.py` | Add minimal `platform_health.py` or remove resource until implemented |
| Frontend cannot build | High | `npm run build` fails on unused `DBPipelineGetResponse` | Fix TypeScript and lint blockers before app work continues |
| Phase 0 bootstrap code missing | High | `src/bootstrap` has no files | Implement idempotent Lakebase runner and UC/schema registry stubs |
| Planned app directories are empty | High | `apps/portal`, `apps/review`, `apps/admin` have no files | Add deployable stubs or explicitly defer from Phase 0 gate |
| Phase 1 schema bundle incomplete | High | Only mortgage has prompt/rules/tests, and only 5 golden tests | Populate minimum synthetic schema assets for all 4 FS doc types |
| Tests and docs are empty | High | `tests/` and `docs/` have no implementation files except this plan | Add smoke tests, quickstart, configuration, and troubleshooting docs |
| CI absent | High | `.github/workflows` missing | Add CI skeleton for Python smoke checks, frontend build/lint, bundle validate |

---

## Mitigation Strategy

1. Freeze scope to Phase 0 until the repo can pass a deterministic local and CI baseline.
2. Treat missing files referenced by `databricks.yml` as release blockers.
3. Add thin, deployable stubs before feature-complete implementations. A stub must import, validate, and fail loudly with actionable messages.
4. Use synthetic fixtures for Phase 1 test harness until design-partner documents exist.
5. Split readiness into three gates:
   - Local gate: static file checks, Python import checks, frontend build/lint.
   - Bundle gate: `databricks bundle validate`.
   - Clean workspace gate: `databricks bundle deploy --target dev`.

---

## Task 1: Add Repo Readiness Inventory

**Files:**
- Create: `scripts/check_readiness.py`
- Test: `tests/unit/test_check_readiness.py`

**Purpose:** Make missing planned files visible in one command before a developer tries a Databricks deployment.

**Steps:**

1. Create `scripts/check_readiness.py` that checks for:
   - `databricks.yml`
   - `.env.example`
   - all 7 migrations
   - `src/pipelines/gold/platform_health.py`
   - bootstrap scripts required by Phase 0
   - app stubs required by Phase 0
   - `.github/workflows/ci.yml`
2. Write tests for success and missing-file reporting using a temporary directory.
3. Run:
   ```bash
   python -m pytest tests/unit/test_check_readiness.py -v
   ```
4. Add this command to the CI workflow in Task 8.

**Acceptance:** `python scripts/check_readiness.py` exits nonzero with a clear list of missing blockers until later tasks fill them.

---

## Task 2: Fix Immediate Bundle Reference Breakage

**Files:**
- Create: `src/pipelines/gold/platform_health.py`
- Modify: `databricks.yml`

**Purpose:** Remove the known missing-file blocker in the current bundle.

**Steps:**

1. Add `platform_health.py` as a minimal DLT-compatible module.
2. Include a `gold_platform_health` table or view that can run even when upstream tables are empty.
3. Keep logic narrow: counts, timestamps, and placeholder confidence metrics only.
4. Verify every notebook path in `databricks.yml` exists:
   ```bash
   python scripts/check_readiness.py
   ```
5. When Databricks CLI is installed, run:
   ```bash
   databricks bundle validate
   ```

**Acceptance:** No path referenced from `databricks.yml` points to a missing file.

---

## Task 3: Implement Phase 0 Bootstrap Minimum

**Files:**
- Create: `src/bootstrap/setup_lakebase.py`
- Create: `src/bootstrap/setup_unity_catalog.py`
- Create: `src/bootstrap/setup_schema_registry.py`
- Create: `src/bootstrap/__init__.py`
- Test: `tests/unit/test_setup_lakebase.py`

**Purpose:** Give Phase 0 a real bootstrap path instead of empty directories.

**Steps:**

1. Implement `setup_lakebase.py` with:
   - ordered migration discovery from `migrations/V*.sql`
   - idempotent migration bookkeeping
   - dry-run mode
   - clear failure output with migration filename
2. Write unit tests for migration ordering and dry-run output.
3. Add UC and schema registry scripts as minimal stubs with argument parsing and explicit `NotImplementedError` only for Databricks API actions not yet wired.
4. Run:
   ```bash
   python -m pytest tests/unit/test_setup_lakebase.py -v
   ```

**Acceptance:** Lakebase migration runner can be executed in dry-run mode twice with stable output.

---

## Task 4: Stabilize Frontend Build and Lint

**Files:**
- Modify: `apps/onboarding-web/src/api/databricks/index.ts`
- Modify: `apps/onboarding-web/src/screens/FirstDocScreen.tsx`
- Modify: `apps/onboarding-web/src/screens/DeployingScreen.tsx`

**Purpose:** Stop carrying a broken app baseline.

**Steps:**

1. Remove or use the unused `DBPipelineGetResponse` type.
2. Attach caught errors as `cause` where ESLint requires it.
3. Remove the useless `ucEnabled` assignment.
4. Replace `any` in `FirstDocScreen.tsx` with the existing API interface types.
5. Fix the `useEffect` dependency warning or document why it is intentionally stable.
6. Run:
   ```bash
   npm run build
   npm run lint
   ```

**Acceptance:** Frontend build and lint both pass from `apps/onboarding-web`.

---

## Task 5: Add Deployable App Stubs

**Files:**
- Create: `apps/onboarding/app.yaml`
- Create: `apps/onboarding/app.py`
- Create: `apps/onboarding/requirements.txt`
- Create: `apps/portal/app.yaml`
- Create: `apps/portal/app.py`
- Create: `apps/portal/requirements.txt`
- Create: `apps/review/app.yaml`
- Create: `apps/review/app.py`
- Create: `apps/review/requirements.txt`
- Create: `apps/admin/app.yaml`
- Create: `apps/admin/app.py`
- Create: `apps/admin/requirements.txt`

**Purpose:** Make the app layer deployable enough for Phase 0 while preserving the richer React prototype as a separate artifact.

**Steps:**

1. Add minimal app manifests with explicit resource allowlists.
2. Add Python app entry points that render a health page and import `apps/lib`.
3. Add smoke tests that import each app module.
4. Update `databricks.yml` to include these apps only if the manifest syntax validates.

**Acceptance:** All app entry points import without error, and bundle validation recognizes app resources.

---

## Task 6: Populate Minimum FS Schema Assets

**Files:**
- Create or complete:
  - `Schemas/fs/kyc_cdd_form/prompt_v1.txt`
  - `Schemas/fs/kyc_cdd_form/validation_rules.json`
  - `Schemas/fs/kyc_cdd_form/field_thresholds.json`
  - `Schemas/fs/aml_sar/prompt_v1.txt`
  - `Schemas/fs/aml_sar/validation_rules.json`
  - `Schemas/fs/aml_sar/field_thresholds.json`
  - `Schemas/fs/invoice/prompt_v1.txt`
  - `Schemas/fs/invoice/validation_rules.json`
  - `Schemas/fs/invoice/field_thresholds.json`

**Purpose:** Remove the biggest Phase 1 schema-library gap without waiting for real customer documents.

**Steps:**

1. Use the existing mortgage schema files as the local format.
2. Add minimal fields and thresholds for KYC, AML SAR, and invoice.
3. Add 5 synthetic golden tests per missing doc type as a temporary Phase 1 seed.
4. Mark the target of 20 per type as a Phase 1 hardening task, not Phase 0.

**Acceptance:** Every FS doc type has prompt, validation rules, thresholds, and at least 5 synthetic golden tests.

---

## Task 7: Add Minimum Docs

**Files:**
- Create: `docs/quickstart.md`
- Create: `docs/configuration.md`
- Create: `docs/troubleshooting.md`
- Create: `docs/phase-gates.md`

**Purpose:** Satisfy the documentation part of the Definition of Done for Phase 0.

**Steps:**

1. Document prerequisites:
   - Databricks CLI
   - workspace host/token
   - Unity Catalog permissions
   - Lakebase connection string
2. Document local validation commands.
3. Document clean workspace deploy steps.
4. Document known unsupported areas for Phase 0.

**Acceptance:** A new engineer can run local readiness checks and understand why clean workspace deployment may fail.

---

## Task 8: Add CI Skeleton

**Files:**
- Create: `.github/workflows/ci.yml`

**Purpose:** Prevent regressions in the baseline we just stabilized.

**Steps:**

1. Add Python readiness/test job.
2. Add frontend install/build/lint job under `apps/onboarding-web`.
3. Add optional Databricks bundle validation job that runs only when `DATABRICKS_HOST` and `DATABRICKS_TOKEN` secrets exist.
4. Keep CI short and deterministic.

**Acceptance:** CI can run without Databricks secrets and still validate local repo health.

---

## Task 9: Run Phase 0 Gate

**Files:**
- Modify only if gate failures identify missing resources.

**Purpose:** Convert Phase 0 from "partially present" to "done by definition."

**Steps:**

1. Run local gate:
   ```bash
   python scripts/check_readiness.py
   npm run build
   npm run lint
   ```
2. Install/configure Databricks CLI if not available.
3. Run bundle gate:
   ```bash
   databricks bundle validate
   ```
4. Run clean workspace gate:
   ```bash
   databricks bundle deploy --target dev
   ```
5. Record results in `docs/phase-gates.md`.

**Acceptance:** Phase 0 can be marked complete only after the clean workspace deploy succeeds.

---

## Stop/Go Rules

- Do not start Phase 1 feature work until Task 9 passes.
- Do not expand the onboarding React prototype until `npm run build` and `npm run lint` pass.
- Do not add new Databricks resources without adding them to readiness checks.
- Do not count synthetic golden tests toward Phase 4 launch readiness.
- Do not claim a phase is done without the clean workspace gate output recorded in `docs/phase-gates.md`.

---

## Recommended Execution Order

1. Task 2: fix missing bundle reference.
2. Task 4: fix frontend build/lint.
3. Task 1: add readiness inventory.
4. Task 3: implement Lakebase bootstrap minimum.
5. Task 5: add app stubs.
6. Task 6: populate FS schema minimum.
7. Task 7: add docs.
8. Task 8: add CI.
9. Task 9: run Phase 0 gate.

This order gives fast feedback first, then fills missing scaffolding, then verifies the full gate.
