# DocuBricks — Schema Authoring Guide

This guide explains how to add a new document type to DocuBricks or customise an existing extraction schema. It covers the anatomy of a schema bundle, how to write prompts and validation rules, model routing, golden tests, and the schema promotion gate.

---

## Schema Bundle Anatomy

Every document type is defined by a **schema bundle** — a directory of required schema assets stored in `Schemas/<vertical>/<document_type>/`.

```
Schemas/
  schema_catalog.json        ← inventory of available and future document types
  prompt_catalog.json        ← prompt inventory tied to available schema entries
  prompts/
    fs/
      mortgage_application/
        prompt_v1.txt        ← centralized prompt copy for registry/runtime use
  fs/
    mortgage_application/
      fields.json                 ← machine-readable field schema
      prompt_v1.txt               ← bundle-local prompt copy for compatibility
      validation_rules.json       ← field-level validation rules and severities
      field_thresholds.json       ← per-field confidence thresholds
      model_routing.json          ← which model to use and fallback chain
      golden_tests/
        test_001.json             ← golden test case (input + expected output)
        test_002.json
        ...
```

All components must be present before the schema promotion gate will pass for an `available` schema.

`fields.json` is the canonical machine-readable field inventory. Prompts should reference or mirror it, but field definitions should not live only in prompt prose.

`prompt_catalog.json` is the canonical prompt inventory. It ties each `available` `schema_catalog.json` entry to:

- a centralized prompt under `Schemas/prompts/<vertical>/<document_type>/prompt_v1.txt`
- the corresponding `fields.json`
- validation, threshold, and model routing assets
- a SHA-256 checksum for stale prompt detection

The bundle-local `prompt_v1.txt` files are retained for compatibility with existing bootstrap and runtime loaders. New automation should prefer `prompt_catalog.json` for prompt discovery.

### Field Schema Format

```json
{
  "document_type": "mortgage_application",
  "vertical": "fs",
  "family": "mortgage_real_estate_finance",
  "schema_version": "MISMO_v3.4_URLA",
  "source_prompt": "prompt_v1.txt",
  "output_contract": {
    "fields_object": "extracted_fields",
    "confidence_object": "confidence",
    "metadata_object": "extraction_metadata"
  },
  "fields": [
    {
      "name": "loan_amount",
      "type": "number",
      "required": true,
      "description": "Requested loan amount as decimal."
    }
  ]
}
```

---

## Writing an Extraction Prompt

The extraction prompt is the single most important tuning lever. A well-written prompt produces high-confidence, well-structured output; a vague prompt produces hallucinations and low confidence scores.

### Template

```
You are a document extraction specialist. Extract the following fields from the
{DOCUMENT_TYPE} document provided.

Return ONLY a valid JSON object with the keys listed below. Do not include
explanatory text, markdown fences, or any content outside the JSON object.

If a field is not present in the document, return null for that field.
Do not infer or estimate values — only extract what is explicitly stated.

Fields to extract:
- field_name_1 (type: string) — description of what this field contains
- field_name_2 (type: number) — description, units if applicable
- field_name_3 (type: array<string>) — description, e.g. ["CPT-99213", "CPT-85025"]
...

Document text:
{DOCUMENT_TEXT}
```

### Tips

**Be explicit about types.** Specify `string`, `number`, `boolean`, `array<string>`, or `date (ISO 8601)` for every field. Ambiguous types cause parsing errors downstream.

**Name arrays explicitly.** For fields like `procedure_codes`, write: `array of strings, each a CPT or ICD-10 code, e.g. ["CPT-99213"]`. Unguided array fields produce inconsistent formats.

**Use "null if not present".** Never ask the model to guess. Validation rules catch missing required fields; you do not need the model to fill in defaults.

**Avoid negatives in the instruction.** Instead of "Do not include the patient's date of birth," write "Extract only the fields listed below." Negatives increase the chance of the model fixating on the prohibited field.

**Include 1–2 in-prompt examples** for fields that have irregular formats in your document population (e.g. non-standard date formats, currency strings with symbols). In-prompt examples reduce variance significantly.

**Token budget.** Keep prompts under 1,500 tokens (excluding `{DOCUMENT_TEXT}`). Long prompts slow throughput on high-volume workloads. If your document type has more than 30 fields, split it into two extraction passes.

---

## Validation Rule Severity Levels

`validation_rules.json` defines per-field rules with one of three severity levels.

```json
{
  "rules": [
    {
      "field": "billed_amount",
      "rule": "type_check",
      "expected_type": "number",
      "severity": "fail"
    },
    {
      "field": "procedure_codes",
      "rule": "non_empty_array",
      "severity": "drop"
    },
    {
      "field": "rendering_provider_npi",
      "rule": "regex",
      "pattern": "^[0-9]{10}$",
      "severity": "warn"
    }
  ]
}
```

| Severity | Behaviour | When to use |
|----------|-----------|-------------|
| `fail` | Record is rejected entirely. Moved to `bronze_quarantine`. Pipeline increments the `failed` counter in `extraction_metrics_daily`. | Use for fields that are structurally essential — without them the document cannot be processed at all. Example: missing `document_id` or an unparseable primary key. |
| `drop` | Record is silently excluded from Silver output. Not quarantined; not flagged for review. | Use for fields whose absence means the record is irrelevant to your use case but not erroneous. Example: an invoice without a line-item table is simply not actionable. |
| `warn` | Record proceeds to Silver but a warning flag is set in `silver_parsed.validation_warnings` (a JSON array). The record appears in the review queue with low priority. | Use for fields that are important but whose absence or format deviation is recoverable. Example: NPI number in wrong format — the record is still usable but should be checked. |

**Rule of thumb:** Start with `warn` for every rule during development. Promote to `drop` or `fail` only after reviewing a week of production data and confirming the rule fires correctly.

---

## Field Confidence Thresholds

`field_thresholds.json` sets the minimum extraction confidence score required for each field to be accepted. Scores below the threshold cause the field to be set to `null` and a low-confidence flag added.

```json
{
  "default_threshold": 0.65,
  "field_thresholds": {
    "patient_member_id":      0.90,
    "billed_amount":          0.85,
    "procedure_codes":        0.80,
    "rendering_provider_npi": 0.70,
    "service_date":           0.75,
    "diagnosis_codes":        0.70
  }
}
```

### How to set thresholds

Start with the `default_threshold` of `0.65` for all fields. Then raise thresholds for:

- **Regulatory fields** — fields that feed compliance reports or trigger regulatory actions. These should be >= 0.85. For HIPAA-sensitive PHI fields, use >= 0.90.
- **Join keys** — fields used to join documents across tables (e.g. `patient_member_id`, `document_id`). Incorrect join keys cause silent data corruption; use >= 0.90.
- **Amount fields** — currency amounts that feed financial calculations. Use >= 0.85.

Lower thresholds (< 0.65) are only appropriate for free-text descriptive fields (e.g. `notes`, `comments`) where any extracted value is better than null.

### Regulatory considerations

For HIPAA-regulated fields, CMS requires that automated billing determinations be reviewable. If a field with a threshold below 0.85 feeds an automated decision, add a `warn` validation rule to ensure those records enter the review queue for human verification.

---

## Model Routing

`model_routing.json` tells the extraction pipeline which LLM to use for this document type and defines a fallback chain.

```json
{
  "primary_model": "databricks-claude-sonnet",
  "fallback_chain": [
    "databricks-meta-llama-3-70b-instruct",
    "databricks-dbrx-instruct"
  ],
  "timeout_seconds": 30,
  "max_retries": 2
}
```

### When to use each model

| Model | Use case |
|-------|----------|
| `databricks-claude-sonnet` | Default for all document types. Best accuracy on complex multi-field extraction, long documents, and regulatory language. Use for anything in regulated industries. |
| `databricks-meta-llama-3-70b-instruct` | Good fallback for structured forms with well-defined fields. Lower cost per token; appropriate for high-volume, low-complexity extractions (e.g. standardised invoices). |
| `databricks-dbrx-instruct` | Last-resort fallback. Fastest and cheapest. Use only when latency is critical and document structure is highly regular. Not recommended for clinical or legal documents. |
| External Claude (via `ANTHROPIC_API_KEY`) | Use when you need Claude Opus or a model version not yet available in Databricks FMApi. Requires the `ANTHROPIC_API_KEY` secret. Only available in `professional` and `enterprise` tiers. |
| External Gemini | Not currently supported in the base accelerator. Contact `support@docubricks.io` for the Gemini routing plugin. |

Set `timeout_seconds` to at least `20` for documents longer than 5 pages. Long PDFs require more tokens and the model call takes longer.

---

## Golden Test Format

Golden tests are the ground truth used by the schema promotion gate. Each test case is a JSON file with an input document excerpt and the expected extraction output.

```json
{
  "test_id": "eob_cms1500_001",
  "document_type": "eob_cms1500",
  "vertical": "healthcare",
  "input": {
    "document_text": "EXPLANATION OF BENEFITS\nMember ID: MBR-123456\nService Date: 2026-03-15\nProcedure: CPT-99213 Office Visit\nBilled Amount: $175.00\nApproved Amount: $142.50\nPatient Responsibility: $32.50"
  },
  "expected_output": {
    "patient_member_id": "MBR-123456",
    "service_date": "2026-03-15",
    "procedure_codes": ["CPT-99213"],
    "billed_amount": 175.00,
    "approved_amount": 142.50,
    "patient_responsibility": 32.50
  },
  "tolerance": {
    "billed_amount": 0.01,
    "approved_amount": 0.01,
    "patient_responsibility": 0.01
  },
  "tags": ["happy_path", "standard_eob"]
}
```

### Minimum test counts

| Environment | Minimum golden tests | Recommended |
|-------------|---------------------|-------------|
| Development | 5 | 10 |
| Staging | 10 | 20 |
| Production | 20 | 50 |

Tests should cover:
- **Happy path** — clean, well-formed documents
- **Missing optional fields** — documents where optional fields are absent
- **Edge cases** — multi-procedure codes, unusual date formats, currency with symbols
- **Near-threshold amounts** — values close to business rule thresholds (e.g. amounts near $1 and $100 for EOB variance rules)
- **Degraded input** — OCR artefacts, handwritten annotations (for scanned documents)

---

## Schema Promotion Gate

The promotion gate is the automated check that must pass before a schema bundle can be deployed to staging or production. It runs the golden tests and reports a pass rate.

### Running the gate

```bash
# Run against the dev catalog
databricks jobs run-now \
  --job-name "DocuBricks — Schema Promotion Gate [dev]" \
  --job-parameters '{"document_type": "eob_cms1500", "vertical": "healthcare"}'
```

Or from within a notebook:

```python
%run ./tests/schema_promotion_gate {
  "document_type": "eob_cms1500",
  "catalog_name": "docubricks_dev"
}
```

### Interpreting the output

```
Schema Promotion Gate — eob_cms1500
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests run:       20
Tests passed:    18
Tests failed:    2
Pass rate:       0.90

PASSED (threshold: 0.85)

Failed tests:
  eob_cms1500_014 — procedure_codes: expected ["CPT-99213","CPT-85025"], got ["CPT-99213"]
  eob_cms1500_017 — billed_amount: expected 1250.00, got null (confidence 0.61 < threshold 0.85)
```

- **Pass threshold is 0.85** for staging promotion and production promotion.
- A pass rate below 0.85 blocks deployment. Investigate the failing tests (see [Troubleshooting — Issue 9](troubleshooting.md#9-schema-test-harness-failing-with-085)).
- The promotion gate result is written to `docubricks_prod.eval.promotion_gate_runs` for audit.

---

## Adding a New Vertical

Adding a completely new vertical (e.g. Real Estate, Manufacturing) is a 5-step process described in full in ARCHITECTURE.md §16. Summary:

1. **Define the vertical slug** — a lowercase identifier (e.g. `real_estate`). Add it to the `supported_verticals` list in your `.env` and to the `vertical` variable enum in `databricks.yml`.

2. **Author schema bundles** — create `schema_registry/<vertical>/<document_type>/` directories with all 5 required files (prompt, validation_rules, field_thresholds, model_routing, golden_tests). Write at least 5 golden tests per document type.

3. **Register the extractor** — add a new Silver extractor notebook at `src/pipelines/silver/extractors/<vertical>_<document_type>.py` using `build_silver_table` from `_base.py`. Add it to the `processing_pipeline` library list in `databricks.yml`.

4. **Run the schema promotion gate** — achieve >= 0.85 pass rate on golden tests in the dev environment before proceeding.

5. **Enable in `databricks.yml`** — add the vertical slug to the `vertical` variable's allowed values and create a target-specific override if needed. Deploy to staging for integration testing, then promote to prod.

Each step should be a separate pull request so that schema bundle changes are reviewable independently of infrastructure changes.
