# DocuBricks — Schema Architecture v2: Implementation Plan

**Status:** Draft · June 2026  
**Companion:** `docs/schema-architecture-v2.md`  
**Scope:** Sequenced plan to migrate to v2 schema architecture with zero pipeline downtime

---

## Pre-read: What the code audit found

Before planning migrations, the code audit found three **pre-existing bugs** unrelated to v2 that must be fixed first. These are in the currently-deployed code and affect production behaviour silently.

### Bug 1 — `load_field_thresholds()` silently loads nothing

`src/bootstrap/setup_schema_registry.py:408–411`:

```python
# Current code — handles flat {field: float} dict
thresholds = [
    {"field_name": k, "min_confidence": v}
    for k, v in data.items()
    if isinstance(v, (int, float))   # ← filters OUT nested objects
]
```

Every deployed `field_thresholds.json` uses nested objects `{"field_name": {"min_confidence": 0.92, ...}}`. The `isinstance(v, (int, float))` guard silently drops all of them. **The `field_confidence_thresholds` table in the schema registry is empty for all schemas.** Confidence threshold enforcement at extraction time is not happening.

### Bug 2 — `load_model_routing()` reads the wrong key for half the schemas

`src/bootstrap/setup_schema_registry.py:448`:

```python
model_endpoint = escape_sql_string(str(data.get("model_endpoint", data.get("model", ""))))
```

Schemas using `preferred_model` (invoice, kyc_cdd_form, aml_sar, mortgage_application, all four healthcare schemas) load an empty string into `schema_model_routing.model_endpoint`. Those schemas have no model configured in the registry.

### Bug 3 — `build_extraction_stream()` ignores model routing entirely

`src/pipelines/silver/extractors/_base.py:518`:

```python
.withColumn("extraction_model", lit("databricks-dbrx-instruct"))
```

Every extraction record is tagged `dbrx-instruct` regardless of what `model_routing.json` says. The DLT pipeline does not read the `schema_model_routing` table at extraction time — it is populated but never consulted.

---

## Backward compatibility map

The following table classifies every v2 change by its impact on existing code before any changes are made to that code.

| Change | Files affected | Runtime impact today | Safe to ship independently? |
|---|---|---|---|
| Fix Bug 1 (field thresholds loader) | `setup_schema_registry.py` | Silent data loss fixed | Yes — purely additive fix |
| Fix Bug 2 (model routing loader) | `setup_schema_registry.py` | Empty endpoints fixed | Yes |
| Fix Bug 3 (extraction model column) | `_base.py` | Audit column gains correct value | Yes — column already exists |
| Normalize `model_routing.json` keys → `primary` | All 22 bundle JSON files, `setup_schema_registry.py` | Breaks loader until both ship together | Must be atomic PR |
| Fix `schema_version` strings | All 18 `fields.json` | No runtime consumer reads this key today | Safe independently |
| Add `default_threshold` to `field_thresholds.json` | 22 bundle JSON files | No runtime consumer reads this key today | Safe independently |
| Add `rule_type`/`fields` to `validation_rules.json` | 22 bundle JSON files | No runtime consumer reads these keys | Safe independently |
| Standardize golden test format + add tests | `golden_tests/` directories | Only consumed by `schema_test_harness.py` | Safe if harness updated first |
| Common field library + `$ref` | New files + `fields.json` edits | No consumer resolves `$ref` today | Must ship lib resolver first |
| Retire bundle-local `prompt_v1.txt` | 22 bundle text files, `validate_schema_assets.py` | `REQUIRED_SCHEMA_FILES` check breaks | Must update validator first |
| New CI lint checks | `validate_schema_assets.py` | No impact — new gates only | Safe independently |

---

## Phase 0 — Fix pre-existing bugs (Week 1)

These are correctness fixes to existing code. They do not change any schema file. They must ship before any schema file changes so the registry loads correctly once migrations run.

### 0-A: Fix `load_field_thresholds()` to handle nested object format

**File:** `src/bootstrap/setup_schema_registry.py`

Replace the format-detection block (lines 402–411) with one that handles the current nested object format as the primary case and the legacy flat dict as a secondary:

```python
def load_field_thresholds(doc_type: str) -> str:
    path = SCHEMAS_ROOT / doc_type / "field_thresholds.json"
    data = read_json(path)
    if data is None:
        return "skipped"

    thresholds = []
    if isinstance(data, dict):
        if "thresholds" in data:
            # Legacy array format
            thresholds = data["thresholds"]
        else:
            for field_name, value in data.items():
                if field_name == "default_threshold":
                    continue  # catalog-level default, not a per-field row
                if isinstance(value, dict):
                    # Current nested object format
                    thresholds.append({
                        "field_name":   field_name,
                        "min_confidence": value.get("min_confidence", 0.70),
                        "review_threshold":    value.get("review_threshold", 0.60),
                        "quarantine_threshold": value.get("quarantine_threshold", 0.40),
                    })
                elif isinstance(value, (int, float)):
                    # Legacy flat float format
                    thresholds.append({"field_name": field_name, "min_confidence": value})
    else:
        thresholds = data
    # ... rest of load loop unchanged
```

**Backward compatibility:** The DB schema for `field_confidence_thresholds` is unchanged. The fix only affects which rows get inserted. Safe to deploy standalone and re-run bootstrap for all doc types.

---

### 0-B: Fix `load_model_routing()` to handle all key variants

**File:** `src/bootstrap/setup_schema_registry.py`

Replace lines 448–449 with a helper that checks all three in-use variants:

```python
def _get_model_routing_keys(data: dict) -> tuple[str, str]:
    """Return (primary_model, fallback_model) from any current key convention."""
    primary = (
        data.get("primary")           # v2 target key
        or data.get("model_endpoint") # most FS schemas
        or data.get("preferred_model") # some FS + all healthcare schemas
        or data.get("primary_model")  # documented but unused
        or data.get("model", "")
    )
    fallback_raw = (
        data.get("fallback_chain")     # v2 target key (array)
        or data.get("fallback_endpoint") # most FS schemas
        or data.get("fallback_model")   # some FS + all healthcare
        or data.get("fallback", "")
    )
    # fallback_chain is an array in v2; take first element
    fallback = fallback_raw[0] if isinstance(fallback_raw, list) else fallback_raw
    return str(primary), str(fallback)

model_endpoint, fallback = _get_model_routing_keys(data)
```

**Backward compatibility:** The DB columns `model_endpoint` and `fallback_endpoint` are unchanged. Only the values written into them are corrected.

---

### 0-C: Wire `extraction_model` from the schema registry

**File:** `src/pipelines/silver/extractors/_base.py`

The `build_extraction_stream()` function hardcodes `dbrx-instruct`. Replace with a lookup from the registry table that was populated by the bootstrap:

```python
# Before: hardcoded
.withColumn("extraction_model", lit("databricks-dbrx-instruct"))

# After: read from schema_model_routing loaded at job start
schema_model = _get_schema_model(catalog_name, document_type)
...
.withColumn("extraction_model", lit(schema_model))
```

Add helper:
```python
def _get_schema_model(catalog_name: str, document_type: str) -> str:
    """Read primary model for this document_type from schema_model_routing."""
    try:
        row = (
            spark.table(f"{catalog_name}.schema_registry.schema_model_routing")
            .filter(
                (col("doc_type") == document_type) & (col("is_active") == True)
            )
            .first()
        )
        if row and row["model_endpoint"]:
            return row["model_endpoint"]
    except Exception as exc:
        logger.warning("Could not read schema_model_routing for %s: %s", document_type, exc)
    return "databricks-claude-sonnet"  # safe default
```

**Backward compatibility:** Column name `extraction_model` is unchanged. The value changes from the wrong constant to the correct per-schema value. Downstream Gold aggregations that read `extraction_model` will start seeing correct values. No schema change required.

---

### Phase 0 PR checklist

```
[ ] 0-A: load_field_thresholds() nested object fix
[ ] 0-B: load_model_routing() multi-key fix + _get_model_routing_keys helper
[ ] 0-C: build_extraction_stream() reads model from registry
[ ] Re-run bootstrap for all 22 doc types to populate correct values
[ ] test_confidence_routing.py passes
[ ] Manual verify: field_confidence_thresholds has rows for all doc types
```

---

## Phase 1 — Normalize schema JSON files (Weeks 2–3)

All schema file changes in this phase. No pipeline code changes. The Phase 0 fixes ensure the registry loader handles both old and new key names, so the two changes can be sequenced independently.

### 1-A: Normalize `model_routing.json` key convention

Write a migration script (`scripts/migrate_model_routing_v2.py`) that transforms every bundle's `model_routing.json` in one pass:

```python
RENAME = {
    "model_endpoint":  "primary",
    "preferred_model": "primary",
    "primary_model":   "primary",
    "fallback_endpoint": lambda v: ("fallback_chain", [v]),
    "fallback_model":    lambda v: ("fallback_chain", [v]),
}
NEW_KEYS = {"timeout_seconds": 30, "max_retries": 2}
```

The script:
1. Renames keys per the map above
2. Adds `timeout_seconds` and `max_retries` with defaults
3. Preserves `max_tokens`, `temperature`, `rationale`
4. Adds an empty `tier_overrides: {}` stub for dev teams to fill in

The Phase 0-B loader already reads `primary`, so these files will load correctly after the rename. The loader also retains its multi-key fallback for any schema bundles not yet migrated (safe during migration window).

**One PR per vertical** is recommended (`schema(fs): normalize model_routing keys`, `schema(healthcare): normalize model_routing keys`) for reviewability.

---

### 1-B: Fix `schema_version` strings

Migration script (`scripts/migrate_schema_version.py`) rewrites the `schema_version` field in every `fields.json` to `{vertical}_{doc_type}_v1`. For schemas currently at `v0` (aml_sar, invoice, kyc_cdd_form) this becomes their first clean version. Schemas using external standard references (mortgage_application: `MISMO_v3.4_URLA`) get a new `external_standard` key added alongside the normalized `schema_version`.

No runtime code reads `schema_version` today. This change only affects the lint gate added in Phase 3.

---

### 1-C: Add `default_threshold` to `field_thresholds.json`

One-liner script that prepends `"default_threshold": 0.75` to every `field_thresholds.json` that lacks it. The Phase 0-A loader already skips this key when iterating fields, so no loader change needed.

---

### 1-D: Add `rule_type` and `fields` array to `validation_rules.json`

Each rule gets a `rule_type` inferred from its expression:
- Contains `IS NOT NULL` or `LENGTH` → `presence`
- Contains `>=` or `<=` with single field → `range`
- References two different field names → `cross_field`
- Contains `ARRAY_LENGTH` or `JSON_ARRAY_LENGTH` → `array`

A migration script can infer type mechanically. The `fields` array lists field names parsed from the expression. No runtime code reads these keys today.

---

### Phase 1 PR checklist

```
[ ] 1-A migration script written and dry-run passes (no file changes)
[ ] 1-A applied to fs vertical — PR schema(fs): normalize model_routing keys
[ ] 1-A applied to healthcare vertical — PR schema(healthcare): normalize model_routing keys
[ ] 1-B schema_version normalization applied to all verticals
[ ] 1-C default_threshold added to all field_thresholds.json
[ ] 1-D rule_type + fields added to all validation_rules.json
[ ] Re-run bootstrap to refresh registry values
[ ] validate_schema_assets.py still passes (no new checks yet)
```

---

## Phase 2 — Expand golden test coverage (Weeks 3–6)

The current state: 1 test per schema. The test suite at `tests/unit/test_schema_asset_coverage.py` already requires ≥5 per healthcare type and ≥50 total for FS — **these assertions are currently failing**. Phase 2 brings coverage to passing.

### Golden test format standardization

All new and existing tests are written in the v2 format with `input.document_text`, `expected_output`, `tolerance`, and `tags`. The `schema_test_harness.py` must be updated to read both formats during the migration window, then the old format retired.

**`src/ops/schema_test_harness.py` changes:**
```python
def _parse_test_case(raw: dict) -> dict:
    """Normalize old and new golden test formats to a common internal dict."""
    if "parsed_text" in raw:
        # Legacy format
        return {
            "input_text":      raw["parsed_text"],
            "expected_output": raw["expected_json"],
            "tolerance":       {},
            "tags":            ["happy_path"],
        }
    else:
        # v2 format
        return {
            "input_text":      raw["input"]["document_text"],
            "expected_output": raw["expected_output"],
            "tolerance":       raw.get("tolerance", {}),
            "tags":            raw.get("tags", []),
        }
```

### Coverage targets by schema tier

| Schema tier | Current tests | Phase 2 target | Notes |
|---|---|---|---|
| FS Phase 1 (mortgage, kyc_cdd, aml_sar, invoice) | 0 (no golden_tests dir) | 5 each | Needed to satisfy `min_fs_total ≥ 50` |
| FS commercial lending (8 schemas) | 1 each | 3 each | Currently fails `min_commercial_lending` |
| FS other available (10 schemas) | 1 each | 3 each | |
| Healthcare (4 schemas) | 1 each | 5 each | Currently failing `min_healthcare_per_type ≥ 5` |

Required tag coverage per tier: `happy_path` for dev gate; add `missing_optional` and `edge_case` for staging gate (Phase 3+).

### `validate_schema_assets.py` update for new format

The validator's `_count_goldens()` function counts files — it does not parse them. No change needed to count. However, the minimum thresholds in `validate_schema_assets()` should be updated to match the new targets:

```python
def validate_schema_assets(
    root: Path,
    *,
    min_fs_total: int = 50,             # unchanged
    min_healthcare_per_type: int = 5,   # unchanged — was already the target
    min_commercial_lending_per_type: int = 3,  # raised from 1
    min_available_per_type: int = 3,           # raised from 1
)
```

---

## Phase 3 — Common field library and new CI checks (Weeks 7–8)

### 3-A: Common field library

Create `Schemas/common/fields/` with the 20 most-reused fields identified across bundles:

```
Schemas/common/fields/
  identity.json       ← borrower_name, lender_name, governing_law, tax_id_masked
  financial.json      ← commitment_amount, interest_rate, maturity_date, currency
  regulatory.json     ← regulatory_alignment, filing_date, jurisdiction
  clinical.json       ← patient_mrn, patient_name, provider_npi, date_of_service
```

Write a **`$ref` resolver** as a standalone utility module (`src/lib/schema_resolver.py`):

```python
def resolve_fields(fields_json_path: Path, common_root: Path) -> list[dict]:
    """
    Load fields from a fields.json, resolving any $ref entries against common_root.
    Returns a flat list of field dicts identical to the pre-$ref format.
    No changes to callers — they receive the same structure as today.
    """
    ...
```

All callers (`setup_schema_registry.py`, `validate_schema_assets.py`, `schema_test_harness.py`) route through `resolve_fields()` instead of `json.loads()` directly. The resolver is transparent — callers see the same flat field list they always have.

**New schemas** use `$ref` for shared fields from day one. **Existing schemas** are migrated opportunistically on the next version bump, not forced in bulk.

### 3-B: New CI lint checks in `validate_schema_assets.py`

Add the following checks, in two severity tiers:

**Hard failures (return code 1):**
```python
def _check_model_routing_keys(path: Path, missing: list[str]) -> None:
    """Reject old key names once migration is complete."""
    data = json.loads(path.read_text())
    for bad_key in ("model_endpoint", "preferred_model", "primary_model",
                    "fallback_endpoint", "fallback_model"):
        if bad_key in data:
            missing.append(f"{path}: legacy key '{bad_key}' — use 'primary'/'fallback_chain'")

def _check_schema_version_format(path: Path, missing: list[str], vertical: str, doc_type: str) -> None:
    """Enforce {vertical}_{doc_type}_v{N} convention."""
    data = json.loads(path.read_text())
    sv = data.get("schema_version", "")
    expected_prefix = f"{vertical}_{doc_type}_v"
    if not sv.startswith(expected_prefix):
        missing.append(f"{path}: schema_version '{sv}' must start with '{expected_prefix}'")

def _check_required_fields_have_thresholds(fields_path: Path, thresholds_path: Path, missing: list[str]) -> None:
    """Every required:true field must have an explicit threshold entry."""
    fields_data = json.loads(fields_path.read_text())
    threshold_data = json.loads(thresholds_path.read_text())
    required_names = {f["name"] for f in fields_data.get("fields", []) if f.get("required")}
    threshold_names = set(threshold_data.keys()) - {"default_threshold"}
    for name in sorted(required_names - threshold_names):
        missing.append(f"{thresholds_path}: required field '{name}' has no threshold entry")
```

**Warnings (logged but do not fail):**
- `family_display_name` consistency within a `family` key across all catalog entries
- Golden tests missing at least one `tags` entry
- Cross-field validation rules not listing all referenced fields in the `fields` array

### 3-C: Update `extract_router.py` to load routes from catalog

Currently `PHASE1_DOCUMENT_TYPES` is a hardcoded list. Replace with a catalog read so adding a new schema bundle does not require editing this file:

```python
# Before: hardcoded list
PHASE1_DOCUMENT_TYPES = ["mortgage_application", "kyc_cdd_form", "aml_sar", "invoice"]

# After: read from schema_catalog.json at pipeline startup
import json
from pathlib import Path

def _load_supported_doc_types() -> list[str]:
    catalog_path = Path("/Workspace/Shared/docubricks/Schemas/schema_catalog.json")
    catalog = json.loads(catalog_path.read_text())
    return [
        e["doc_type"]
        for e in catalog.get("document_types", [])
        if e.get("availability") == "available" and e.get("rollout_status") == "registry_ready"
    ]

SUPPORTED_DOC_TYPES = _load_supported_doc_types()
```

This allows new schema bundles to flow into the pipeline automatically once the catalog marks them `available`, without a code deploy.

**Backward compatibility:** The `silver_route_*` DLT views are still created dynamically per doc type. The existing `PHASE1_DOCUMENT_TYPES` list check is replaced with the catalog-driven `SUPPORTED_DOC_TYPES`. Existing views are unaffected.

---

## Phase 4 — Prompt catalog consolidation (Week 9)

### 4-A: Update `validate_schema_assets.py` — remove `prompt_v1.txt` requirement

Before retiring the bundle-local prompt files, update `REQUIRED_SCHEMA_FILES` in the validator:

```python
# Before
REQUIRED_SCHEMA_FILES = (
    "prompt_v1.txt",
    "validation_rules.json",
    "field_thresholds.json",
    "model_routing.json",
)

# After (prompt_v1.txt removed; fields.json added as explicit required asset)
REQUIRED_SCHEMA_FILES = (
    "fields.json",
    "validation_rules.json",
    "field_thresholds.json",
    "model_routing.json",
)
```

**Ship this change before deleting any prompt files.** The validator runs on every PR; if the files are deleted first the gate will fail.

### 4-B: Add warn check for bundle-local prompt files (migration window)

Add a warning (not failure) that fires if `prompt_v1.txt` exists in a bundle:

```python
def _check_no_bundle_local_prompt(doc_path: Path, warnings: list[str]) -> None:
    legacy = doc_path / "prompt_v1.txt"
    if legacy.exists():
        warnings.append(f"{doc_path}: bundle-local prompt_v1.txt should be removed (use prompt_catalog.json)")
```

### 4-C: Delete bundle-local `prompt_v1.txt` files

Once 4-A is deployed and CI is green, remove all 22 `prompt_v1.txt` files in a single PR. This PR has no code changes — only file deletions.

### 4-D: Flip warning to failure

After one sprint with no new bundle-local prompts being added, change `_check_no_bundle_local_prompt` from warning to a hard failure in the CI gate.

---

## Phase 5 — Full gate enforcement (Week 10+)

All migration-period warnings become hard failures. The lint gate is the final backstop for any schema bundle reaching `available` in the catalog.

Final `REQUIRED_SCHEMA_FILES`:
```python
REQUIRED_SCHEMA_FILES = (
    "fields.json",
    "validation_rules.json",
    "field_thresholds.json",
    "model_routing.json",
)
```

Final minimum test counts enforced by the gate:

| Gate | Check | Min count |
|---|---|---|
| Any PR touching a schema | `model_routing.json` uses `primary`/`fallback_chain` | — |
| Any PR touching a schema | `schema_version` matches convention | — |
| Dev catalog promotion | `golden_tests/` count | 3 |
| Staging promotion | `golden_tests/` count | 5 |
| Production promotion | `golden_tests/` count | 10 |
| Production promotion | `required:true` fields covered in thresholds | all |
| Production promotion | `default_threshold` present | required |

---

## Execution summary

| Phase | Weeks | PRs | Risk | Backward compat |
|---|---|---|---|---|
| 0 — Bug fixes | 1 | 3 small code PRs | Low — fixes silent failures | Fully compatible |
| 1 — Normalize JSON | 2–3 | 4 schema PRs + 2 migration scripts | Low — no runtime consumers | Compatible after Phase 0 |
| 2 — Golden tests | 3–6 | 1 per schema bundle | Low | Compatible after harness format fix |
| 3 — Common fields + CI | 7–8 | 1 lib PR + 1 CI PR + 1 router PR | Medium — resolver must be tested | Transparent to callers |
| 4 — Prompt consolidation | 9 | 3 small PRs (validator, delete, flip gate) | Low if sequenced | Sequencing is the safety |
| 5 — Full gate | 10+ | 1 gate flip PR | Low | Gate only blocks new schema authors |

**Critical sequencing rules:**
1. Phase 0 must deploy and bootstrap must re-run before Phase 1 PRs merge.
2. Phase 1-A (model_routing normalization) is safe because Phase 0-B added multi-key fallback support.
3. Phase 4-A (remove prompt from REQUIRED_SCHEMA_FILES) must merge before Phase 4-C (delete files).
4. Phase 3-B lint checks are added in warn mode first; promoted to fail only after all existing bundles pass.

---

## Files changed per phase — quick reference

| Phase | Files changed |
|---|---|
| 0-A | `src/bootstrap/setup_schema_registry.py` |
| 0-B | `src/bootstrap/setup_schema_registry.py` |
| 0-C | `src/pipelines/silver/extractors/_base.py` |
| 1-A | All 22 `*/model_routing.json` + `scripts/migrate_model_routing_v2.py` (new) |
| 1-B | All 18 `*/fields.json` + `scripts/migrate_schema_version.py` (new) |
| 1-C | All 22 `*/field_thresholds.json` |
| 1-D | All 22 `*/validation_rules.json` |
| 2 | All `*/golden_tests/*.json` + `src/ops/schema_test_harness.py` + `scripts/validate_schema_assets.py` |
| 3-A | `Schemas/common/fields/*.json` (new) + `src/lib/schema_resolver.py` (new) + callers |
| 3-B | `scripts/validate_schema_assets.py` |
| 3-C | `src/pipelines/silver/extract_router.py` |
| 4-A | `scripts/validate_schema_assets.py` |
| 4-B | `scripts/validate_schema_assets.py` |
| 4-C | Delete all 22 `*/prompt_v1.txt` |
| 4-D | `scripts/validate_schema_assets.py` |
| 5 | `scripts/validate_schema_assets.py` (flip warns to fails) |
