"""
apps/lib/schema_sections.py
-----------------------------
Section registry for the human-in-the-loop Review UI.

Maps document_type → ordered section groupings + per-field display metadata.
Consumed by field_editor to render tab-organised, type-aware inputs.

display_type values
-------------------
text      : single-line text_input (default)
textarea  : multi-line text_area (addresses, narratives)
date      : date_input  → stored/returned as ISO-8601 string "YYYY-MM-DD"
integer   : number_input step=1
currency  : number_input with "$" label prefix
percent   : number_input with "%" label suffix (value stored as raw %, e.g. 6.5)
decimal   : generic float number_input
boolean   : checkbox (accepts bool or "true"/"false"/"yes"/"no" strings)
table     : st.data_editor — value is a JSON-encoded list of dicts
"""
from __future__ import annotations

# ── Registry ───────────────────────────────────────────────────────────────────
# Each entry: {
#   "sections":   [{id, label, fields: [str, ...]}, ...],
#   "field_meta": {field_name: {display_type, ...}}
# }
# A table entry also carries:
#   "table_columns": [{"name": str, "type": text|decimal|currency|integer}, ...]

SECTION_REGISTRY: dict[str, dict] = {

    # ── Invoice ───────────────────────────────────────────────────────────────
    "invoice": {
        "sections": [
            {
                "id": "header",
                "label": "Header",
                "fields": [
                    "invoice_number", "invoice_date", "due_date",
                    "purchase_order_number", "payment_terms", "currency",
                ],
            },
            {
                "id": "vendor",
                "label": "Vendor",
                "fields": ["vendor_name", "vendor_tax_id_masked", "vendor_address"],
            },
            {
                "id": "customer",
                "label": "Customer",
                "fields": ["customer_name", "customer_address"],
            },
            {
                "id": "amounts",
                "label": "Amounts",
                "fields": [
                    "subtotal", "tax_amount", "shipping_amount",
                    "discount_amount", "total_amount", "amount_due",
                ],
            },
            {
                "id": "line_items",
                "label": "Line Items",
                "fields": ["line_item_count", "line_items"],
            },
        ],
        "field_meta": {
            "invoice_date":     {"display_type": "date"},
            "due_date":         {"display_type": "date"},
            "vendor_address":   {"display_type": "textarea"},
            "customer_address": {"display_type": "textarea"},
            "subtotal":         {"display_type": "currency"},
            "tax_amount":       {"display_type": "currency"},
            "shipping_amount":  {"display_type": "currency"},
            "discount_amount":  {"display_type": "currency"},
            "total_amount":     {"display_type": "currency"},
            "amount_due":       {"display_type": "currency"},
            "payment_terms":    {"display_type": "integer"},
            "line_item_count":  {"display_type": "integer"},
            "line_items": {
                "display_type": "table",
                "table_columns": [
                    {"name": "description", "type": "text"},
                    {"name": "quantity",    "type": "decimal"},
                    {"name": "unit_price",  "type": "currency"},
                    {"name": "amount",      "type": "currency"},
                ],
            },
        },
    },

    # ── Mortgage Application ──────────────────────────────────────────────────
    "mortgage_application": {
        "sections": [
            {
                "id": "loan_info",
                "label": "Loan Info",
                "fields": [
                    "loan_purpose", "loan_type", "lien_priority", "mortgage_type",
                    "loan_amount", "loan_term_months", "interest_rate_percent",
                    "amortization_type",
                ],
            },
            {
                "id": "property",
                "label": "Property",
                "fields": [
                    "occupancy_type", "property_street", "property_city",
                    "property_state", "property_zip", "property_county",
                    "property_type", "number_of_units", "year_built",
                    "purchase_price", "estimated_value",
                ],
            },
            {
                "id": "borrower",
                "label": "Borrower",
                "fields": [
                    "borrower_first_name", "borrower_middle_name", "borrower_last_name",
                    "borrower_suffix", "borrower_ssn_masked", "borrower_dob",
                    "borrower_marital_status", "borrower_dependents_count",
                    "borrower_citizenship", "borrower_phone", "borrower_email",
                ],
            },
            {
                "id": "coborrower",
                "label": "Co-Borrower",
                "fields": [
                    "coborrower_first_name", "coborrower_last_name",
                    "coborrower_ssn_masked", "coborrower_dob",
                ],
            },
            {
                "id": "employment",
                "label": "Employment",
                "fields": [
                    "employer_name", "employer_address", "employer_phone",
                    "position_title", "employment_start_date", "years_on_job",
                    "self_employed",
                ],
            },
            {
                "id": "income",
                "label": "Income",
                "fields": [
                    "base_monthly_income", "overtime_monthly_income",
                    "bonus_monthly_income", "commission_monthly_income",
                    "other_monthly_income", "total_monthly_income",
                ],
            },
            {
                "id": "housing_expense",
                "label": "Housing Expense",
                "fields": [
                    "present_housing_payment", "proposed_principal_interest",
                    "proposed_taxes", "proposed_insurance", "proposed_hoa_dues",
                    "proposed_total_housing_payment",
                ],
            },
            {
                "id": "assets",
                "label": "Assets",
                "fields": [
                    "total_assets", "checking_savings_balance",
                    "retirement_assets", "down_payment_amount", "down_payment_source",
                ],
            },
            {
                "id": "liabilities",
                "label": "Liabilities",
                "fields": [
                    "total_monthly_debt_payments", "auto_loan_payment",
                    "student_loan_payment", "credit_card_payment",
                    "other_debt_payments", "borrowed_down_payment",
                    "debt_to_income_ratio", "housing_expense_ratio",
                    "ltv_percent", "cltv_percent",
                ],
            },
            {
                "id": "declarations",
                "label": "Declarations",
                "fields": [
                    "outstanding_judgments", "bankruptcy", "foreclosure",
                    "party_to_lawsuit", "delinquent_on_debt", "intent_to_occupy",
                ],
            },
            {
                "id": "monitoring",
                "label": "Monitoring",
                "fields": [
                    "ethnicity_hispanic", "race_white", "race_black", "race_asian",
                    "sex_male", "sex_female", "monitoring_info_not_provided",
                ],
            },
            {
                "id": "origination",
                "label": "Origination",
                "fields": [
                    "application_date", "loan_officer_name", "lender_name", "nmls_id",
                ],
            },
        ],
        "field_meta": {
            # Loan
            "loan_amount":                  {"display_type": "currency"},
            "loan_term_months":             {"display_type": "integer"},
            "interest_rate_percent":        {"display_type": "percent"},
            # Property
            "purchase_price":               {"display_type": "currency"},
            "estimated_value":              {"display_type": "currency"},
            # Employment
            "employment_start_date":        {"display_type": "date"},
            "self_employed":                {"display_type": "boolean"},
            # Income
            "base_monthly_income":          {"display_type": "currency"},
            "overtime_monthly_income":      {"display_type": "currency"},
            "bonus_monthly_income":         {"display_type": "currency"},
            "commission_monthly_income":    {"display_type": "currency"},
            "other_monthly_income":         {"display_type": "currency"},
            "total_monthly_income":         {"display_type": "currency"},
            # Housing
            "present_housing_payment":          {"display_type": "currency"},
            "proposed_taxes":                   {"display_type": "currency"},
            "proposed_total_housing_payment":   {"display_type": "currency"},
            # Assets
            "total_assets":                 {"display_type": "currency"},
            "checking_savings_balance":     {"display_type": "currency"},
            "retirement_assets":            {"display_type": "currency"},
            "down_payment_amount":          {"display_type": "currency"},
            # Liabilities
            "total_monthly_debt_payments":  {"display_type": "currency"},
            "auto_loan_payment":            {"display_type": "currency"},
            "student_loan_payment":         {"display_type": "currency"},
            "credit_card_payment":          {"display_type": "currency"},
            "other_debt_payments":          {"display_type": "currency"},
            "borrowed_down_payment":        {"display_type": "currency"},
            "debt_to_income_ratio":         {"display_type": "percent"},
            "housing_expense_ratio":        {"display_type": "percent"},
            "ltv_percent":                  {"display_type": "percent"},
            "cltv_percent":                 {"display_type": "percent"},
            # Origination
            "application_date":             {"display_type": "date"},
            # Borrower
            "borrower_dependents_count":    {"display_type": "integer"},
        },
    },

    # ── KYC / CDD Form ────────────────────────────────────────────────────────
    "kyc_cdd_form": {
        "sections": [
            {
                "id": "identity",
                "label": "Identity",
                "fields": [
                    "customer_name", "customer_type", "date_of_birth", "tax_id_masked",
                    "id_document_type", "id_document_number_masked", "id_expiration_date",
                ],
            },
            {
                "id": "contact",
                "label": "Contact & Address",
                "fields": [
                    "address_line1", "city", "state", "postal_code",
                    "country", "phone", "email",
                ],
            },
            {
                "id": "compliance",
                "label": "Compliance",
                "fields": [
                    "occupation_or_business", "source_of_funds",
                    "expected_monthly_activity", "risk_rating", "pep_status",
                    "beneficial_owner_name", "beneficial_owner_ownership_percent",
                ],
            },
            {
                "id": "review",
                "label": "Review",
                "fields": ["review_date", "reviewer_name"],
            },
        ],
        "field_meta": {
            "date_of_birth":                        {"display_type": "date"},
            "id_expiration_date":                   {"display_type": "date"},
            "review_date":                          {"display_type": "date"},
            "beneficial_owner_ownership_percent":   {"display_type": "percent"},
        },
    },

    # ── AML / SAR ─────────────────────────────────────────────────────────────
    "aml_sar": {
        "sections": [
            {
                "id": "filing",
                "label": "Filing",
                "fields": [
                    "sar_id", "filing_institution_name", "filing_date",
                    "branch_location", "investigator_name",
                ],
            },
            {
                "id": "subject",
                "label": "Subject",
                "fields": [
                    "subject_name", "subject_tax_id_masked",
                    "subject_address", "subject_account_number_masked",
                ],
            },
            {
                "id": "activity",
                "label": "Suspicious Activity",
                "fields": [
                    "suspicious_activity_type", "activity_start_date",
                    "activity_end_date", "amount_involved", "transaction_count",
                    "currency", "law_enforcement_contacted",
                ],
            },
            {
                "id": "narrative",
                "label": "Narrative",
                "fields": ["narrative_summary"],
            },
        ],
        "field_meta": {
            "filing_date":              {"display_type": "date"},
            "activity_start_date":      {"display_type": "date"},
            "activity_end_date":        {"display_type": "date"},
            "amount_involved":          {"display_type": "currency"},
            "transaction_count":        {"display_type": "integer"},
            "subject_address":          {"display_type": "textarea"},
            "narrative_summary":        {"display_type": "textarea"},
        },
    },

    # ── Collateral Schedule ───────────────────────────────────────────────────
    "collateral_schedule": {
        "sections": [
            {
                "id": "header",
                "label": "Header",
                "fields": [
                    "schedule_date", "borrower_name", "lender_name",
                    "agreement_reference",
                ],
            },
            {
                "id": "collateral_summary",
                "label": "Collateral Summary",
                "fields": [
                    "collateral_category", "collateral_description",
                    "collateral_location", "total_collateral_value",
                    "eligible_collateral_value", "advance_rate_percent",
                    "borrowing_base_amount", "appraisal_date",
                    "valuation_method", "lien_position", "prior_liens_amount",
                ],
            },
            {
                "id": "collateral_items",
                "label": "Collateral Items",
                "fields": ["collateral_items"],
            },
        ],
        "field_meta": {
            "schedule_date":            {"display_type": "date"},
            "appraisal_date":           {"display_type": "date"},
            "total_collateral_value":   {"display_type": "currency"},
            "eligible_collateral_value":{"display_type": "currency"},
            "advance_rate_percent":     {"display_type": "percent"},
            "borrowing_base_amount":    {"display_type": "currency"},
            "prior_liens_amount":       {"display_type": "currency"},
            "collateral_description":   {"display_type": "textarea"},
            "collateral_items": {
                "display_type": "table",
                "table_columns": [
                    {"name": "item_description",    "type": "text"},
                    {"name": "serial_or_id",        "type": "text"},
                    {"name": "appraised_value",     "type": "currency"},
                    {"name": "condition",           "type": "text"},
                ],
            },
        },
    },
}


# ── Public API ─────────────────────────────────────────────────────────────────

def get_schema_meta(doc_type: str) -> dict:
    """
    Return {sections, field_meta} for doc_type.
    Returns empty-sections dict for unknown types (renders flat, backward-compat).
    """
    return SECTION_REGISTRY.get(doc_type, {"sections": [], "field_meta": {}})
