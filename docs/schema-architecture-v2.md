# DocuBricks — Schema Architecture v2

**Status:** Proposal · June 2026  
**Scope:** Schema catalog, field definitions, extraction prompts, model routing, validation, golden tests, versioning, and CI gate  
**Replaces:** `docs/schema-authoring.md` (keep as legacy reference until migration complete)

---

## Executive Summary

The current schema layer has solid foundations — catalog inventory, per-bundle JSON assets, prompt catalog with checksums, and a promotion gate — but has accumulated inconsistencies that will compound as the library grows toward 477 schemas across 6 verticals. This document audits what is broken and defines a clean, versioned, and reusable target architecture.

The design principle is: **every schema bundle should be self-describing, diff-friendly, and deployable through a standard CI gate with no manual steps.**

---

## Current State Audit

### 1. `model_routing.json` — three conflicting key schemas

Across 22 deployed schema bundles, three different key conventions are in active use:

| Convention | Files using it | Problem |
|---|---|---|
| `model_endpoint` / `fallback_endpoint` | 13 FS schemas | Flat, no chain support |
| `preferred_model` / `fallback_model` | 4 FS schemas, all 4 healthcare | Inconsistent with above |
| `primary_model` / `fallback_chain[]` | Documented in `schema-authoring.md` only | Not used in any actual file |

No file implements `timeout_seconds` or `max_retries` despite both being specified in the docs. The fallback is always a single model, never a chain. Runtime loaders must currently handle three different key names for the same concept.

### 2. `schema_version` — no enforced convention

| Schema | schema_version |
|---|---|
| `fs/aml_sar` | `FS_AML_SAR_v0` |
| `fs/collateral_schedule` | `fs_collateral_schedule_v1` |
| `fs/issue_management_record` | `risk_issue_management_record_v1` |
| `fs/mortgage_application` | `MISMO_v3.4_URLA` |

Four different naming conventions in 18 schemas. `v0` vs `v1` carries no semantic meaning. Two schemas use `risk_` prefix instead of `fs_`. Mortgage uses an external standard reference as the version. This makes programmatic version comparison impossible.

### 3. `field_thresholds.json` — schema diverges from docs

The docs specify a `default_threshold` + `field_thresholds` nested structure. Every actual file uses a flat per-field object — richer than the docs, but different. There is no `default_threshold` in any file, so the runtime cannot apply a fallback for unspecified fields without hardcoding a value.

### 4. `validation_rules.json` — SQL-expression rules vs type-rule convention

The docs show a declarative `{field, rule, expected_type}` format. The actual files use a SQL-expression string (`"expression": "borrower_name IS NOT NULL AND ..."`) — more powerful, but entirely undocumented. Cross-field rules are possible in expressions but there are no examples and no tests for them.

### 5. Golden tests — 1 test per schema, two format variants

Every schema bundle has exactly one golden test. The docs require 5 for dev, 20 for production. The actual test format (`parsed_text` / `expected_json`) differs from the documented format (`input.document_text` / `expected_output` / `tolerance` / `tags`). A test without tags cannot be selectively run by class (happy-path vs edge-case vs degraded).

### 6. Redundant prompt copies

`prompt_catalog.json` is the registry of record (with SHA-256 checksums). Bundle-local `prompt_v1.txt` files are described as "compatibility copies." With 27 entries today, two copies of every prompt mean divergence is inevitable. The SHA-256 only covers the centralized copy.

### 7. No shared field library

Fields like `borrower_name`, `governing_law`, `lender_name`, `tax_id_masked`, and `patient_mrn` appear in dozens of schemas with slightly varying descriptions. There is no `$ref` mechanism, so a correction to a shared field must be applied manually across every schema that uses it.

### 8. No lint or schema validation in CI

The `validate_schema_assets.py` script checks asset presence but does not validate:
- key naming conventions in `model_routing.json`
- `schema_version` format compliance
- whether `field_thresholds.json` covers all `required: true` fields from `fields.json`
- `golden_tests/` minimum count
- `prompt_catalog.json` SHA-256 freshness

---

## Target Architecture

### Guiding principles

1. **One source of truth per concept.** Field definitions live in one place. Prompts live in one place. No sync burden.
2. **Convention over configuration.** Consistent key names mean zero-config runtime loaders.
3. **Diff-friendly.** Every file should produce clean git diffs — keys in a stable order, no generated noise.
4. **Deployable via CI.** The promotion gate is the only deploy mechanism; no manual catalog edits.
5. **Additive versioning.** New schema versions never break consumers of the prior version until an explicit deprecation notice.

---

### Bundle layout (unchanged externally, improved internally)

```
Schemas/
  schema_catalog.json           ← inventory (vertical, family, availability, version)
  prompt_catalog.json           ← single source of truth for all prompts + checksums
  common/
    fields/                     ← shared field definitions (new)
      identity.json
      financial.json
      dates.json
      regulatory.json
  <vertical>/
    <doc_type>/
      fields.json               ← field schema (may $ref common fields)
      prompt_v1.txt             ← REMOVED — prompt_catalog.json is sole source
      validation_rules.json     ← validation rules
      field_thresholds.json     ← confidence thresholds
      model_routing.json        ← routing config (normalized keys)
      golden_tests/
        test_001.json           ← minimum 3 per bundle (5 for staging gate)
        test_002.json
        test_003.json
```

The bundle-local `prompt_v1.txt` files are retired. `prompt_catalog.json` becomes the only prompt source. The runtime loader reads from `prompt_catalog.json`; the CI gate validates its SHA-256 matches the `Schemas/prompts/` copy on every PR.

---

### `fields.json` — enhanced format

#### What changes

- Add `schema_version` with enforced convention (see below).
- Add `category` per field: `identity | financial | regulatory | temporal | descriptive | array`.
- Field `description` minimum length of 15 characters enforced by lint.
- Remove `output_contract` boilerplate (it is the same in every file; move to a global default in `schema_catalog.json`).
- Support `$ref` to `common/fields/<lib>.json#/definitions/<field_name>` for shared fields.

#### Enforced `schema_version` convention

```
{vertical}_{doc_type}_v{N}
```

Examples: `fs_collateral_schedule_v2`, `healthcare_lab_report_v1`, `legal_nda_msa_v1`.

For schemas that implement an external standard, the standard is recorded separately:

```json
"schema_version": "fs_mortgage_application_v2",
"external_standard": "MISMO_v3.4_URLA"
```

#### Example

```json
{
  "document_type": "collateral_schedule",
  "vertical": "fs",
  "family": "commercial_lending",
  "schema_version": "fs_collateral_schedule_v2",
  "fields": [
    {
      "$ref": "common/fields/identity.json#/definitions/borrower_name"
    },
    {
      "name": "collateral_description",
      "type": "string",
      "category": "descriptive",
      "required": true,
      "description": "General description of collateral pledged under the security agreement."
    },
    {
      "name": "total_collateral_value",
      "type": "number",
      "category": "financial",
      "required": false,
      "description": "Total appraised or stated value of all collateral items."
    }
  ]
}
```

---

### `model_routing.json` — normalized

All schemas use a single key schema. The `primary` and `fallback_chain` (array) replace the three current variants. Tier overrides allow dev to use a cheaper model without touching the production config.

```json
{
  "primary": "databricks-claude-sonnet-4",
  "fallback_chain": [
    "databricks-meta-llama-3-70b-instruct"
  ],
  "max_tokens": 4096,
  "temperature": 0.0,
  "timeout_seconds": 30,
  "max_retries": 2,
  "tier_overrides": {
    "dev": {
      "primary": "databricks-dbrx-instruct",
      "max_tokens": 2048
    }
  },
  "rationale": "Collateral schedules contain structured tables, lien positions, and borrowing base calculations that benefit from Sonnet's table-parsing accuracy."
}
```

#### Routing model selection guide

| Complexity tier | Primary model | When to use |
|---|---|---|
| **High** | `databricks-claude-sonnet-4` | Long-form legal/financial documents, narrative content, multi-section extraction, regulated fields |
| **Medium** | `databricks-meta-llama-3-70b-instruct` | Moderately structured forms, moderate field count (<30), low regulatory sensitivity |
| **Low** | `databricks-dbrx-instruct` | Highly templated forms, small field count (<15), high volume, latency-sensitive |

New models enter the tier table when benchmarked against golden tests with a pass rate ≥ 0.90. Model identifiers in `model_routing.json` map to Databricks FM API endpoint aliases defined in `databricks.yml` — changing a model deployment requires only updating the alias, not editing every routing file.

---

### `field_thresholds.json` — add default, align with docs

Add `default_threshold` so the runtime has a fallback for fields not explicitly listed. Retain the per-field object format (richer than what the docs described; retroactively adopt it as the standard).

```json
{
  "default_threshold": 0.75,
  "fields": {
    "borrower_name": {
      "min_confidence": 0.92,
      "review_on_breach": true,
      "fail_on_breach": true,
      "regulatory_required": false,
      "description": "Borrower identity links collateral to the credit facility."
    },
    "total_collateral_value": {
      "min_confidence": 0.93,
      "review_on_breach": true,
      "fail_on_breach": false,
      "regulatory_required": false,
      "description": "Collateral value affects borrowing base and exposure coverage."
    }
  }
}
```

**Rule:** Every field with `required: true` in `fields.json` must have an explicit entry in `field_thresholds.json`. The CI gate enforces this.

**Threshold guidance:**

| Field category | Recommended floor | Rationale |
|---|---|---|
| Regulatory / compliance keys | ≥ 0.90 | Feed auditable reports |
| Join keys (MRN, member ID, claim#) | ≥ 0.92 | Silent corruption on mismatch |
| Financial amounts | ≥ 0.88 | Downstream calculation errors |
| Temporal fields (dates) | ≥ 0.85 | Timeliness and ordering |
| Descriptive / narrative | ≥ 0.65 | Any value better than null |

---

### `validation_rules.json` — formalize expression syntax, add cross-field rules

Retain the SQL-expression approach (it is more powerful than the declarative format in the docs) but add:
- A `rule_type` discriminator (`presence`, `range`, `format`, `cross_field`, `array`)
- Explicit `fields` array for cross-field rules so static analysis can identify dependencies
- A `tags` array matching test tags so rules can be selectively exercised

```json
[
  {
    "name": "borrower_name_present",
    "rule_type": "presence",
    "fields": ["borrower_name"],
    "expression": "borrower_name IS NOT NULL AND LENGTH(TRIM(borrower_name)) > 0",
    "severity": "fail",
    "tags": ["identity"],
    "description": "Collateral schedule must identify the borrower or collateral owner."
  },
  {
    "name": "borrowing_base_not_exceed_eligible",
    "rule_type": "cross_field",
    "fields": ["borrowing_base_amount", "eligible_collateral_value"],
    "expression": "borrowing_base_amount IS NULL OR eligible_collateral_value IS NULL OR borrowing_base_amount <= eligible_collateral_value",
    "severity": "warn",
    "tags": ["financial", "borrowing_base"],
    "description": "Borrowing base cannot exceed eligible collateral value."
  }
]
```

---

### `golden_tests/` — standardized format, minimum counts enforced

Adopt the documented format with `tolerance` and `tags`. The current format (`parsed_text` / `expected_json`) is merged into `input.document_text` / `expected_output`.

```json
{
  "test_id": "collateral_schedule_001",
  "document_type": "collateral_schedule",
  "vertical": "fs",
  "description": "Equipment collateral with borrowing base — clean scan",
  "tags": ["happy_path", "equipment", "borrowing_base"],
  "input": {
    "document_text": "COLLATERAL SCHEDULE\nSchedule Date: March 15, 2026\n..."
  },
  "expected_output": {
    "borrower_name": "Prairie Ridge Manufacturing LLC",
    "collateral_category": "Equipment",
    "total_collateral_value": 5900000.0,
    "borrowing_base_amount": 4250000.0,
    "lien_position": "First priority"
  },
  "tolerance": {
    "total_collateral_value": 0.01,
    "borrowing_base_amount": 0.01
  },
  "expected_avg_confidence": 0.92
}
```

**Minimum test counts enforced by the CI gate:**

| Gate | Min tests | Required tag coverage |
|---|---|---|
| Dev promotion | 3 | `happy_path` |
| Staging promotion | 5 | `happy_path`, `missing_optional` |
| Production promotion | 10 | `happy_path`, `missing_optional`, `edge_case` |

---

### Common field library

Shared fields live in `Schemas/common/fields/` and are referenced by `$ref`. This eliminates copy-paste across schemas.

**`Schemas/common/fields/identity.json`**
```json
{
  "definitions": {
    "borrower_name": {
      "name": "borrower_name",
      "type": "string",
      "category": "identity",
      "required": true,
      "description": "Legal name of the borrower or obligor as stated in the document."
    },
    "governing_law": {
      "name": "governing_law",
      "type": "string",
      "category": "regulatory",
      "required": false,
      "description": "Governing law jurisdiction stated in the agreement."
    }
  }
}
```

The bundle loader resolves `$ref` pointers at load time, so the runtime schema object is identical to today's flat format. No runtime changes needed.

---

### `schema_catalog.json` — add `output_contract` default

Move the repeated `output_contract` block out of individual `fields.json` files and into `schema_catalog.json` as a catalog-level default. Override at the bundle level only when a schema uses non-standard output keys.

```json
{
  "schema_catalog_version": "2026-06-06",
  "output_contract_default": {
    "fields_object": "extracted_fields",
    "confidence_object": "confidence",
    "metadata_object": "extraction_metadata"
  },
  "document_types": [...]
}
```

---

### `prompt_catalog.json` — sole source of truth

Bundle-local `prompt_v1.txt` files are retired. The prompt catalog entry is the only pointer to the prompt file under `Schemas/prompts/`.

```json
{
  "prompt_id": "fs.collateral_schedule.v2",
  "doc_type": "collateral_schedule",
  "vertical": "fs",
  "schema_version": "fs_collateral_schedule_v2",
  "prompt_path": "Schemas/prompts/fs/collateral_schedule/prompt_v2.txt",
  "sha256": "...",
  "deprecated_versions": [
    { "version": "v1", "deprecated": "2026-06-01", "sunset": "2026-09-01" }
  ]
}
```

Prompt versioning is now explicit. `deprecated_versions` gives consumers a sunset window before a prompt version is removed.

---

## CI Gate — Enhanced Lint Rules

`scripts/validate_schema_assets.py` gains the following checks (fail = blocks PR):

| Check | Severity |
|---|---|
| All `available` catalog entries have all required bundle files | fail |
| `model_routing.json` uses `primary` / `fallback_chain` keys (no `model_endpoint` / `preferred_model`) | fail |
| `schema_version` matches `{vertical}_{doc_type}_v{N}` pattern | fail |
| All `required: true` fields in `fields.json` have entry in `field_thresholds.json` | fail |
| `field_thresholds.json` has `default_threshold` key | fail |
| `golden_tests/` count meets minimum for the schema's promotion tier | fail |
| Every golden test has at least one `tags` entry | warn |
| `prompt_catalog.json` SHA-256 matches file on disk | fail |
| Bundle-local `prompt_v1.txt` does not exist (migration complete check) | warn during migration, fail post-migration |
| `family_display_name` is consistent within a `family` key | warn |
| Cross-field validation rules list all referenced fields in `fields` array | warn |

---

## Migration Path

The migration is designed to be non-breaking. All changes are backward-compatible at the runtime level until the hard cutover dates below.

### Phase 1 — Normalize existing bundles (2 weeks)
- Run a one-time migration script to rename `model_endpoint`→`primary`, `fallback_endpoint`→`fallback_chain[0]`, `preferred_model`→`primary`, `fallback_model`→`fallback_chain[0]` across all 22 deployed bundles.
- Fix `schema_version` strings to follow the new convention.
- Add `default_threshold: 0.75` to every `field_thresholds.json`.
- Add `rule_type` and `fields` array to every validation rule.
- Single PR, reviewed by schema owner.

### Phase 2 — Expand golden test coverage (4 weeks)
- Bring every production schema to ≥ 10 golden tests covering `happy_path`, `missing_optional`, `edge_case`.
- Standardize all golden tests to the new format with `tags` and `tolerance`.
- Enable the CI gate minimum-count check.

### Phase 3 — Common field library (2 weeks)
- Identify the 15–20 most-reused fields across all schemas.
- Author `common/fields/identity.json`, `financial.json`, `temporal.json`, `regulatory.json`.
- Replace inline definitions with `$ref` in new schemas; existing schemas are migrated opportunistically on the next version bump.

### Phase 4 — Prompt catalog consolidation (1 week)
- Remove all bundle-local `prompt_v1.txt` files.
- Update runtime loaders to read exclusively from `prompt_catalog.json`.
- Enable the CI gate check that rejects PRs adding new bundle-local prompt copies.

### Phase 5 — Enable full lint gate (end of migration)
- Flip the migration-period `warn` rules to `fail`.
- All new schemas must be authored against the v2 spec from this point forward.

---

## Version Control Strategy

Schema changes follow a three-tier versioning model:

| Change type | Version impact | Pipeline impact |
|---|---|---|
| Add optional field | Patch — no version bump | Zero — new field silently null in old extractions |
| Add required field | Minor bump `v1→v2` | Existing extractions will not populate the new field until re-extracted |
| Remove or rename field | Major bump `v1→v2`, add to `deprecated_fields` in catalog | Breaking — pipeline must handle null for removed field |
| Change `schema_version` convention | Catalog-level change, all bundles re-versioned at next bump | No runtime impact |
| Change prompt (same fields) | Prompt version bump `prompt_v1→prompt_v2` in `prompt_catalog.json` | Triggers re-evaluation against golden tests before deploy |

**Branch strategy:** Each schema bundle change is a separate PR against `main`. The PR title format is `schema(<vertical>/<doc_type>): <description>` to make catalog changes filterable in git history.

---

## Summary of Changes

| Area | Current | v2 |
|---|---|---|
| `model_routing.json` keys | 3 variants (`model_endpoint`, `preferred_model`, `primary_model`) | 1 canonical: `primary` / `fallback_chain[]` |
| `schema_version` format | 4 ad-hoc formats | `{vertical}_{doc_type}_v{N}` enforced by lint |
| `field_thresholds.json` | No default, undocumented structure | `default_threshold` + documented per-field object |
| Validation rules | Undocumented SQL expression, no cross-field | `rule_type` + `fields` array, cross-field rules supported |
| Golden tests per schema | 1 | 3 / 5 / 10 by tier, enforced by CI gate |
| Prompt location | Two copies (bundle-local + catalog) | One copy under `Schemas/prompts/` via `prompt_catalog.json` |
| Shared fields | Copy-paste across schemas | `common/fields/` library with `$ref` |
| `output_contract` | Repeated in every `fields.json` | Catalog-level default, override only when non-standard |
| CI lint checks | Asset presence only | 10 structural checks, 4 warn + 6 fail |
