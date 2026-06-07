"""
Bootstrap Job 02 — Schema Registry loader.
Loads extraction prompts, validation rules, field thresholds, and model routing
from schemas/fs/{doc_type}/ into Delta tables in the schema_registry UC schema.
Idempotent: inserts use ON CONFLICT DO NOTHING / MERGE.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _conf(key: str, env_var: str, default: str = "") -> str:
    try:
        val = spark.conf.get(key, default)  # noqa: F821
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(env_var, default)


CATALOG      = _conf("catalog_name",  "CATALOG_NAME",  "docubricks_prod")
SECRET_SCOPE = _conf("secret_scope",  "SECRET_SCOPE",  "docubricks-prod")
TIER         = _conf("tier",          "SCHEMA_TIER",   "community")
REPO_ROOT    = Path(os.environ.get("REPO_ROOT", "/Workspace/Repos/docubricks/DocuBricks"))

# ---------------------------------------------------------------------------
# Tier-based schema bundle selection
# ---------------------------------------------------------------------------
# community    — FS only (mortgage, KYC, AML SAR, invoice)
# starter      — FS full (7 doc types: + trade_confirmation, 10k_filing, kyc_edd)
# professional — FS + Healthcare (EOB, clinical note, lab report, prior auth)
#              — FS + Legal    (NDA/MSA, SOW, regulatory submission, court filing)
# enterprise   — All verticals + commercial lending expansion + all doc types

COMMERCIAL_LENDING_DOC_TYPES = [
    "commercial_loan_application",
    "commercial_credit_memo",
    "loan_agreement",
    "syndicated_credit_agreement",
    "covenant_compliance_certificate",
    "collateral_schedule",
    "ucc_financing_statement",
    "guaranty_agreement",
    "security_agreement",
]

PAYMENTS_DOC_TYPES = [
    "merchant_onboarding_application",
]

WEALTH_DOC_TYPES = [
    "trust_account_opening_package",
]

RISK_COMPLIANCE_DOC_TYPES = [
    "third_party_risk_assessment",
    "issue_management_record",
    "regulatory_reporting_package",
]

INSURANCE_DOC_TYPES = [
    "insurance_policy_application",
    "policy_declaration_page",
    "certificate_of_insurance",
    "insurance_claim_file",
    "first_notice_of_loss",
    "proof_of_loss",
    "claims_adjuster_report",
    "insurance_claim_denial_letter",
]

TIER_SCHEMA_MAP: dict[str, dict[str, list[str]]] = {
    "community": {
        "fs": ["mortgage_application", "kyc_cdd_form", "aml_sar", "invoice"],
    },
    "starter": {
        "fs": ["mortgage_application", "kyc_cdd_form", "aml_sar", "invoice"],
    },
    "professional": {
        "fs":         ["mortgage_application", "kyc_cdd_form", "aml_sar", "invoice"],
        "healthcare": ["eob_cms1500", "clinical_note_soap", "lab_report", "prior_auth"],
        "legal":      ["nda_msa", "sow", "regulatory_submission", "court_filing"],
    },
    "enterprise": {
        "fs":         [
            "mortgage_application",
            "kyc_cdd_form",
            "aml_sar",
            "invoice",
            *COMMERCIAL_LENDING_DOC_TYPES,
            *PAYMENTS_DOC_TYPES,
            *WEALTH_DOC_TYPES,
            *RISK_COMPLIANCE_DOC_TYPES,
        ],
        "healthcare": ["eob_cms1500", "clinical_note_soap", "lab_report", "prior_auth"],
        "legal":      ["nda_msa", "sow", "regulatory_submission", "court_filing", "litigation_case_file"],
        "insurance":  INSURANCE_DOC_TYPES,
    },
}

# Validate tier
_normalised_tier = TIER.lower().strip()
if _normalised_tier not in TIER_SCHEMA_MAP:
    print(f"[WARN] Unknown tier '{TIER}', defaulting to 'community'")
    _normalised_tier = "community"

VERTICAL_DOC_TYPES: dict[str, list[str]] = TIER_SCHEMA_MAP[_normalised_tier]
SREG = f"`{CATALOG}`.`schema_registry`"

# Legacy aliases for FS-only code paths
DOC_TYPES    = VERTICAL_DOC_TYPES.get("fs", [])
SCHEMAS_ROOT = REPO_ROOT / "Schemas" / "fs"   # capital S matches actual directory
VERTICAL     = "fs"

# Regulatory alignment metadata
REGULATORY_ALIGNMENT = {
    "mortgage_application":  "URLA/MISMO v3.x, HMDA, TRID",
    "kyc_cdd_form":          "FinCEN CDD Rule, BSA, FFIEC, NIST SP 800-63-4",
    "aml_sar":               "FinCEN BSA e-Filing, SAR form TD F 90-22.47",
    "invoice":               "Standard AP/AR, GAAP",
    "eob_cms1500":           "ANSI X12 835, CMS-1500 (HCFA), HIPAA 5010",
    "clinical_note_soap":    "HL7 FHIR R4, SNOMED CT, ICD-10-CM",
    "lab_report":            "HL7 FHIR R4, LOINC, CLIA",
    "prior_auth":            "HIPAA 278, AMA/AHA PA standards",
    "nda_msa":               "UCC Article 2, Delaware contract law standards",
    "sow":                   "FAR/DFARS (government), commercial SOW standards",
    "regulatory_submission": "FDA 21 CFR, SEC Reg S-K, FinCEN BSA",
    "court_filing":          "FRCP, PACER, state-specific rules of civil procedure",
    "commercial_loan_application": "ECOA, Reg B, BSA/KYB, internal credit policy",
    "commercial_credit_memo": "Safety and soundness, OCC/FDIC/Fed credit risk management guidance",
    "loan_agreement": "UCC Article 9, commercial lending policy, contract governance",
    "syndicated_credit_agreement": "Syndicated lending, private credit, loan market association-style deal governance",
    "covenant_compliance_certificate": "Credit monitoring, loan agreement covenants, risk rating governance",
    "collateral_schedule": "Secured lending controls, borrowing base monitoring, UCC Article 9",
    "ucc_financing_statement": "UCC Article 9 perfection and lien filing",
    "guaranty_agreement": "Credit support documentation, UCC/common law guaranty enforcement",
    "security_agreement": "UCC Article 9 security interests and collateral attachment",
    "merchant_onboarding_application": "NACHA, card network rules, merchant acquiring, fraud and dispute risk controls",
    "trust_account_opening_package": "Fiduciary account opening, tax certification, suitability, trust authority review",
    "third_party_risk_assessment": "Third-party risk management, outsourcing governance, SOC review, BCP/DR controls",
    "issue_management_record": "Regulatory exam management, MRA/MRIA tracking, audit issue remediation",
    "regulatory_reporting_package": "Call Report, HMDA, CRA, SAR/CTR, CECL, CCAR/DFAST and liquidity reporting",
    "litigation_case_file": "Matter management, court deadlines, discovery, motions, exposure and settlement tracking",
    "insurance_policy_application": "Insurance underwriting intake, risk selection, rating, producer review, and policy issuance controls",
    "policy_declaration_page": "Policy declarations, coverage evidence, loss payee, additional insured, and lender collateral protection controls",
    "certificate_of_insurance": "Certificate of insurance review, coverage evidence, additional insured, waiver of subrogation, and expiration monitoring",
    "insurance_claim_file": "Claim handling, coverage review, reserve monitoring, payment tracking, and claims governance",
    "first_notice_of_loss": "FNOL intake, claims triage, loss reporting, mitigation, and claims handling timelines",
    "proof_of_loss": "Sworn proof of loss, claim valuation, deductible, mortgagee/loss payee, and supporting evidence review",
    "claims_adjuster_report": "Claims adjusting, damage scope, reserve recommendation, coverage analysis, and subrogation review",
    "insurance_claim_denial_letter": "Claims denial, coverage determination, policy provisions, appeal rights, and regulatory notice controls",
}

# ---------------------------------------------------------------------------
# DDL — create schema_registry tables if they don't exist
# ---------------------------------------------------------------------------

TABLES_DDL = f"""
CREATE TABLE IF NOT EXISTS {SREG}.extraction_prompts (
    prompt_id        STRING NOT NULL,
    doc_type         STRING NOT NULL,
    vertical         STRING NOT NULL,
    version          STRING NOT NULL,
    prompt_text      STRING NOT NULL,
    is_active        BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMP NOT NULL,
    created_by       STRING,
    regulatory_ref   STRING,
    CONSTRAINT pk_extraction_prompts PRIMARY KEY (doc_type, version)
)
USING DELTA
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
);

CREATE TABLE IF NOT EXISTS {SREG}.validation_rules (
    rule_id          STRING NOT NULL,
    doc_type         STRING NOT NULL,
    vertical         STRING NOT NULL,
    field_name       STRING NOT NULL,
    rule_type        STRING NOT NULL,
    rule_expression  STRING NOT NULL,
    severity         STRING NOT NULL DEFAULT 'ERROR',
    is_active        BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMP NOT NULL,
    CONSTRAINT pk_validation_rules PRIMARY KEY (rule_id)
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {SREG}.field_confidence_thresholds (
    threshold_id     STRING NOT NULL,
    doc_type         STRING NOT NULL,
    vertical         STRING NOT NULL,
    field_name       STRING NOT NULL,
    min_confidence   DOUBLE NOT NULL,
    review_threshold DOUBLE,
    quarantine_threshold DOUBLE,
    created_at       TIMESTAMP NOT NULL,
    CONSTRAINT pk_field_thresholds PRIMARY KEY (doc_type, field_name)
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {SREG}.schema_model_routing (
    routing_id           STRING NOT NULL,
    doc_type             STRING NOT NULL,
    vertical             STRING NOT NULL,
    model_endpoint       STRING NOT NULL,
    fallback_endpoint    STRING,
    max_tokens           INT,
    temperature          DOUBLE,
    is_active            BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMP NOT NULL,
    CONSTRAINT pk_schema_model_routing PRIMARY KEY (doc_type)
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {SREG}.document_type_labels (
    doc_type         STRING NOT NULL,
    vertical         STRING NOT NULL,
    display_name     STRING NOT NULL,
    regulatory_ref   STRING,
    is_active        BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMP NOT NULL,
    CONSTRAINT pk_document_type_labels PRIMARY KEY (doc_type)
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {SREG}.schema_changelog (
    changelog_id     STRING NOT NULL,
    doc_type         STRING NOT NULL,
    version          STRING NOT NULL,
    change_type      STRING NOT NULL,
    changed_by       STRING,
    change_reason    STRING,
    test_accuracy    DOUBLE,
    test_cases_run   INT,
    changed_at       TIMESTAMP NOT NULL,
    CONSTRAINT pk_schema_changelog PRIMARY KEY (changelog_id)
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

CREATE TABLE IF NOT EXISTS {SREG}.schema_inheritance (
    child_doc_type      STRING  NOT NULL,
    parent_doc_type     TEXT    NOT NULL,
    inheritance_mode    STRING  NOT NULL,
    override_fields     STRING,
    depth               INT     NOT NULL DEFAULT 1,
    created_at          TIMESTAMP NOT NULL,
    CONSTRAINT pk_schema_inheritance PRIMARY KEY (child_doc_type, parent_doc_type)
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');
"""

# Initial inheritance chain seed data (idempotent MERGE)
INHERITANCE_SEED_SQL = f"""
MERGE INTO {SREG}.schema_inheritance AS tgt
USING (
    SELECT 'kyc_edd_form' AS child_doc_type, 'kyc_cdd_form' AS parent_doc_type,
           'EXTENDS' AS inheritance_mode,
           '["sourceOfFunds","sourceOfWealth","eddTriggers","seniorManagementApproval"]' AS override_fields,
           1 AS depth, current_timestamp() AS created_at
    UNION ALL
    SELECT 'aml_sar', 'kyc_cdd_form', 'SPECIALISES',
           '["screening","regulatoryReports","cases","suspiciousActivityType"]',
           1, current_timestamp()
) AS src
ON tgt.child_doc_type = src.child_doc_type
   AND tgt.parent_doc_type = src.parent_doc_type
WHEN NOT MATCHED THEN INSERT *
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_sql(statement: str, label: str = "") -> None:
    try:
        spark.sql(statement)  # noqa: F821
        if label:
            print(f"  [OK] {label}")
    except Exception as exc:
        print(f"  [ERROR] {label}: {exc}", file=sys.stderr)
        raise


def read_file(path: Path) -> str | None:
    if not path.exists():
        print(f"  [WARN] File not found, skipping: {path}")
        return None
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict | list | None:
    text = read_file(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"  [WARN] JSON parse error in {path}: {exc}")
        return None


def escape_sql_string(s: str) -> str:
    """Escape single quotes for SQL string literals."""
    return s.replace("'", "''")


NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

# ---------------------------------------------------------------------------
# Loaders per artifact
# ---------------------------------------------------------------------------

def load_prompt(doc_type: str) -> str:
    path = SCHEMAS_ROOT / doc_type / "prompt_v1.txt"
    text = read_file(path)
    if text is None:
        return "skipped"

    prompt_id = f"{doc_type}__v1"
    escaped   = escape_sql_string(text.strip())
    reg_ref   = escape_sql_string(REGULATORY_ALIGNMENT.get(doc_type, ""))

    run_sql(f"""
        MERGE INTO {SREG}.extraction_prompts AS target
        USING (
            SELECT
                '{prompt_id}'    AS prompt_id,
                '{doc_type}'     AS doc_type,
                '{VERTICAL}'     AS vertical,
                'v1'             AS version,
                '{escaped}'      AS prompt_text,
                true             AS is_active,
                CAST('{NOW}' AS TIMESTAMP) AS created_at,
                'bootstrap'      AS created_by,
                '{reg_ref}'      AS regulatory_ref
        ) AS source
        ON target.doc_type = source.doc_type AND target.version = source.version
        WHEN NOT MATCHED THEN INSERT *
    """, f"INSERT extraction_prompts({doc_type} v1)")
    return "loaded"


def load_validation_rules(doc_type: str) -> str:
    path = SCHEMAS_ROOT / doc_type / "validation_rules.json"
    rules = read_json(path)
    if rules is None:
        return "skipped"

    if isinstance(rules, dict):
        rules = rules.get("rules", [rules])
    if not isinstance(rules, list):
        rules = [rules]

    loaded = 0
    for rule in rules:
        rule_id     = escape_sql_string(str(rule.get("rule_id", f"{doc_type}_{loaded}")))
        field_name  = escape_sql_string(str(rule.get("field_name", "")))
        rule_type   = escape_sql_string(str(rule.get("rule_type", "PRESENCE")))
        rule_expr   = escape_sql_string(str(rule.get("expression", rule.get("rule_expression", ""))))
        severity    = escape_sql_string(str(rule.get("severity", "ERROR")))

        run_sql(f"""
            MERGE INTO {SREG}.validation_rules AS target
            USING (SELECT '{rule_id}' AS rule_id) AS source
            ON target.rule_id = source.rule_id
            WHEN NOT MATCHED THEN INSERT (
                rule_id, doc_type, vertical, field_name, rule_type,
                rule_expression, severity, is_active, created_at
            ) VALUES (
                '{rule_id}', '{doc_type}', '{VERTICAL}', '{field_name}',
                '{rule_type}', '{rule_expr}', '{severity}', true,
                CAST('{NOW}' AS TIMESTAMP)
            )
        """, f"INSERT validation_rules({doc_type}, {rule_id})")
        loaded += 1

    return f"loaded {loaded} rules"


def load_field_thresholds(doc_type: str) -> str:
    path = SCHEMAS_ROOT / doc_type / "field_thresholds.json"
    data = read_json(path)
    if data is None:
        return "skipped"

    if isinstance(data, dict):
        # Might be {"thresholds": [...]} or {"field": threshold_float, ...}
        if "thresholds" in data:
            thresholds = data["thresholds"]
        else:
            # Primary case: nested objects {field_name: {min_confidence: ..., ...}}
            # Legacy case: flat float {field_name: float}
            thresholds = []
            for field_name, value in data.items():
                if field_name == "default_threshold":
                    continue  # catalog-level default, skip
                if isinstance(value, dict):
                    thresholds.append({
                        "field_name":            field_name,
                        "min_confidence":        value.get("min_confidence", 0.70),
                        "review_threshold":      value.get("review_threshold", 0.60),
                        "quarantine_threshold":  value.get("quarantine_threshold", 0.40),
                    })
                elif isinstance(value, (int, float)):
                    # legacy flat float format
                    thresholds.append({"field_name": field_name, "min_confidence": value})
    else:
        thresholds = data

    loaded = 0
    for i, t in enumerate(thresholds):
        field_name        = escape_sql_string(str(t.get("field_name", f"field_{i}")))
        min_conf          = float(t.get("min_confidence", t.get("confidence", 0.70)))
        review_threshold  = t.get("review_threshold",    t.get("review",    0.60))
        quarantine_threshold = t.get("quarantine_threshold", t.get("quarantine", 0.40))
        threshold_id      = f"{doc_type}__{field_name}"

        run_sql(f"""
            MERGE INTO {SREG}.field_confidence_thresholds AS target
            USING (SELECT '{doc_type}' AS doc_type, '{field_name}' AS field_name) AS source
            ON target.doc_type = source.doc_type AND target.field_name = source.field_name
            WHEN NOT MATCHED THEN INSERT (
                threshold_id, doc_type, vertical, field_name,
                min_confidence, review_threshold, quarantine_threshold, created_at
            ) VALUES (
                '{threshold_id}', '{doc_type}', '{VERTICAL}', '{field_name}',
                {min_conf}, {review_threshold}, {quarantine_threshold},
                CAST('{NOW}' AS TIMESTAMP)
            )
        """, f"INSERT field_thresholds({doc_type}, {field_name})")
        loaded += 1

    return f"loaded {loaded} thresholds"


def _get_model_routing_keys(data: dict) -> tuple[str, str]:
    """Return (primary_model, fallback_model) handling all key naming variants."""
    primary = (
        data.get("primary")            # v2 normalized key
        or data.get("model_endpoint")  # most FS schemas
        or data.get("preferred_model") # some FS + all healthcare schemas
        or data.get("primary_model")   # documented but unused variant
        or data.get("model", "")
    )
    fallback_raw = (
        data.get("fallback_chain")      # v2 normalized key (list)
        or data.get("fallback_endpoint") # most FS schemas
        or data.get("fallback_model")    # some FS + all healthcare
        or data.get("fallback", "")
    )
    fallback = fallback_raw[0] if isinstance(fallback_raw, list) else fallback_raw
    return str(primary), str(fallback)


def load_model_routing(doc_type: str) -> str:
    path = SCHEMAS_ROOT / doc_type / "model_routing.json"
    data = read_json(path)
    if data is None:
        return "skipped"

    raw_primary, raw_fallback = _get_model_routing_keys(data)
    model_endpoint  = escape_sql_string(raw_primary)
    fallback        = escape_sql_string(raw_fallback)
    max_tokens      = int(data.get("max_tokens", 4096))
    temperature     = float(data.get("temperature", 0.0))
    routing_id      = f"{doc_type}__routing"

    run_sql(f"""
        MERGE INTO {SREG}.schema_model_routing AS target
        USING (SELECT '{doc_type}' AS doc_type) AS source
        ON target.doc_type = source.doc_type
        WHEN NOT MATCHED THEN INSERT (
            routing_id, doc_type, vertical, model_endpoint, fallback_endpoint,
            max_tokens, temperature, is_active, created_at
        ) VALUES (
            '{routing_id}', '{doc_type}', '{VERTICAL}', '{model_endpoint}',
            '{fallback}', {max_tokens}, {temperature}, true,
            CAST('{NOW}' AS TIMESTAMP)
        )
    """, f"INSERT schema_model_routing({doc_type})")
    return "loaded"


DOC_TYPE_DISPLAY = {
    "mortgage_application": "Mortgage Application",
    "kyc_cdd_form":         "KYC / CDD Form",
    "aml_sar":              "AML Suspicious Activity Report",
    "invoice":              "Invoice",
    "commercial_loan_application":      "Commercial Loan Application",
    "commercial_credit_memo":           "Commercial Credit Memo",
    "loan_agreement":                   "Loan Agreement",
    "syndicated_credit_agreement":      "Syndicated Credit Agreement",
    "covenant_compliance_certificate":  "Covenant Compliance Certificate",
    "collateral_schedule":              "Collateral Schedule",
    "ucc_financing_statement":          "UCC Financing Statement",
    "guaranty_agreement":               "Guaranty Agreement",
    "security_agreement":               "Security Agreement",
    "merchant_onboarding_application":  "Merchant Onboarding Application",
    "trust_account_opening_package":    "Trust Account Opening Package",
    "third_party_risk_assessment":      "Third-Party Risk Assessment",
    "issue_management_record":          "Issue Management Record",
    "regulatory_reporting_package":     "Regulatory Reporting Package",
    "litigation_case_file":             "Litigation Case File",
    "insurance_policy_application":     "Insurance Policy Application",
    "policy_declaration_page":          "Policy Declaration Page",
    "certificate_of_insurance":         "Certificate of Insurance",
    "insurance_claim_file":             "Insurance Claim File",
    "first_notice_of_loss":             "First Notice of Loss",
    "proof_of_loss":                    "Proof of Loss",
    "claims_adjuster_report":           "Claims Adjuster Report",
    "insurance_claim_denial_letter":    "Insurance Claim Denial Letter",
}

def load_document_type_label(doc_type: str) -> str:
    display  = escape_sql_string(DOC_TYPE_DISPLAY.get(doc_type, doc_type))
    reg_ref  = escape_sql_string(REGULATORY_ALIGNMENT.get(doc_type, ""))

    run_sql(f"""
        MERGE INTO {SREG}.document_type_labels AS target
        USING (SELECT '{doc_type}' AS doc_type) AS source
        ON target.doc_type = source.doc_type
        WHEN NOT MATCHED THEN INSERT (
            doc_type, vertical, display_name, regulatory_ref, is_active, created_at
        ) VALUES (
            '{doc_type}', '{VERTICAL}', '{display}', '{reg_ref}', true,
            CAST('{NOW}' AS TIMESTAMP)
        )
    """, f"INSERT document_type_labels({doc_type})")
    return "loaded"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Bootstrap Job 02 — Schema Registry Loader")
    print(f"  Catalog      : {CATALOG}")
    print(f"  Tier         : {_normalised_tier}")
    verticals_list = ", ".join(f"{v}({len(d)} types)" for v, d in VERTICAL_DOC_TYPES.items())
    print(f"  Verticals    : {verticals_list}")
    print("=" * 60)

    # Create tables
    print("\n[1/3] Creating schema_registry tables (IF NOT EXISTS)...")
    for statement in [s.strip() for s in TABLES_DDL.split(";\n\n") if s.strip()]:
        label = statement.split("\n")[0].strip()[:80]
        run_sql(statement + ";", label)

    # Load data per vertical per doc_type
    print("\n[2/3] Loading schema artifacts (all enabled verticals)...")
    summary: dict[str, dict] = {}

    for vertical, doc_types in VERTICAL_DOC_TYPES.items():
        vertical_schemas_root = REPO_ROOT / "Schemas" / vertical
        if not vertical_schemas_root.exists():
            print(f"  [SKIP] Schemas/{vertical}/ not found — skipping vertical")
            continue
        print(f"\n  === {vertical.upper()} ===")

        # Temporarily override module-level SCHEMAS_ROOT for helper functions
        global SCHEMAS_ROOT, VERTICAL
        SCHEMAS_ROOT = vertical_schemas_root
        VERTICAL = vertical

        for doc_type in doc_types:
            print(f"\n  --- {doc_type} ---")
            summary[f"{vertical}/{doc_type}"] = {
                "prompt":       load_prompt(doc_type),
                "rules":        load_validation_rules(doc_type),
                "thresholds":   load_field_thresholds(doc_type),
                "routing":      load_model_routing(doc_type),
                "type_label":   load_document_type_label(doc_type),
            }

    # Seed schema inheritance chain
    print("\n[3/3] Seeding schema inheritance chain...")
    run_sql(INHERITANCE_SEED_SQL, "MERGE schema_inheritance")
    print("  kyc_edd_form EXTENDS kyc_cdd_form  ✓")
    print("  aml_sar SPECIALISES kyc_cdd_form   ✓")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    for doc_type, statuses in summary.items():
        print(f"  {doc_type}:")
        for artifact, status in statuses.items():
            print(f"    {artifact:12s}: {status}")
    print("=" * 60)
    print("Bootstrap Job 02 complete.")


main()
