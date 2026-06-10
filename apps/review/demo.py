"""
apps/review/demo.py
-------------------
Standalone local demo of the DocuBricks HiL Review UI.
No Databricks workspace or Lakebase connection required.

Run:
    streamlit run apps/review/demo.py
"""
from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

from lib.theme import apply_docubricks_theme
from lib.components.field_editor import field_editor
from lib.schema_sections import get_schema_meta

st.set_page_config(
    page_title="DocuBricks Review — Demo",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_docubricks_theme()

# ── Mock datasets ──────────────────────────────────────────────────────────────

MOCK_DOCS = {
    "Mortgage Application": {
        "doc_type": "mortgage_application",
        "fields": {
            "loan_purpose": "Purchase",
            "loan_type": "Conventional",
            "lien_priority": "FirstLien",
            "mortgage_type": "FixedRate",
            "loan_amount": 485000.00,
            "loan_term_months": 360,
            "interest_rate_percent": 6.875,
            "amortization_type": "FullyAmortizing",
            "occupancy_type": "PrimaryResidence",
            "property_street": "4821 Maple Grove Drive",
            "property_city": "Austin",
            "property_state": "TX",
            "property_zip": "78745",
            "property_county": "Travis",
            "property_type": "SingleFamily",
            "number_of_units": "1",
            "year_built": "2002",
            "purchase_price": 520000.00,
            "estimated_value": 525000.00,
            "borrower_first_name": "James",
            "borrower_middle_name": "R.",
            "borrower_last_name": "Hartwell",
            "borrower_suffix": "",
            "borrower_ssn_masked": "***-**-4821",
            "borrower_dob": "1982-03-15",
            "borrower_marital_status": "Married",
            "borrower_dependents_count": 2,
            "borrower_citizenship": "US Citizen",
            "borrower_phone": "512-555-0182",
            "borrower_email": "j.hartwell@email.com",
            "coborrower_first_name": "Sarah",
            "coborrower_last_name": "Hartwell",
            "coborrower_ssn_masked": "***-**-6643",
            "coborrower_dob": "1984-07-22",
            "employer_name": "Apex Solutions LLC",
            "employer_address": "1200 Congress Ave, Austin TX 78701",
            "employer_phone": "512-555-0100",
            "position_title": "Senior Engineer",
            "employment_start_date": "2018-04-01",
            "years_on_job": "6",
            "self_employed": False,
            "base_monthly_income": 9200.00,
            "overtime_monthly_income": 0.00,
            "bonus_monthly_income": 800.00,
            "commission_monthly_income": 0.00,
            "other_monthly_income": 350.00,
            "total_monthly_income": 10350.00,
            "present_housing_payment": 1450.00,
            "proposed_principal_interest": "2950.00",
            "proposed_taxes": 520.00,
            "proposed_insurance": "180.00",
            "proposed_hoa_dues": "0.00",
            "proposed_total_housing_payment": 3650.00,
            "total_assets": 142000.00,
            "checking_savings_balance": 62000.00,
            "retirement_assets": 80000.00,
            "down_payment_amount": 35000.00,
            "down_payment_source": "Savings",
            "total_monthly_debt_payments": 820.00,
            "auto_loan_payment": 420.00,
            "student_loan_payment": 280.00,
            "credit_card_payment": 120.00,
            "other_debt_payments": 0.00,
            "borrowed_down_payment": 0.00,
            "debt_to_income_ratio": 44.6,
            "housing_expense_ratio": 35.3,
            "ltv_percent": 93.3,
            "cltv_percent": 93.3,
            "outstanding_judgments": "No",
            "bankruptcy": "No",
            "foreclosure": "No",
            "party_to_lawsuit": "No",
            "delinquent_on_debt": "No",
            "intent_to_occupy": "Yes",
            "ethnicity_hispanic": "Not Hispanic",
            "race_white": "Yes",
            "race_black": "No",
            "race_asian": "No",
            "sex_male": "Yes",
            "sex_female": "No",
            "monitoring_info_not_provided": "No",
            "application_date": "2024-11-12",
            "loan_officer_name": "Patricia Chen",
            "lender_name": "First Community Mortgage",
            "nmls_id": "1847392",
        },
        "confidence_scores": {
            "loan_amount":          0.97,
            "loan_type":            0.99,
            "interest_rate_percent": 0.52,   # LOW — flagged
            "borrower_ssn_masked":  0.91,
            "debt_to_income_ratio": 0.58,    # LOW — flagged
            "ltv_percent":          0.61,    # LOW — flagged
            "employment_start_date": 0.75,   # medium
            "base_monthly_income":  0.88,
            "total_monthly_income": 0.83,    # medium
            "purchase_price":       0.94,
            "down_payment_amount":  0.69,    # medium
        },
    },

    "Invoice": {
        "doc_type": "invoice",
        "fields": {
            "invoice_number":       "INV-2024-08471",
            "invoice_date":         "2024-11-01",
            "due_date":             "2024-11-30",
            "vendor_name":          "Acme Supply Co.",
            "vendor_tax_id_masked": "**-***7842",
            "vendor_address":       "500 Industrial Pkwy\nSuite 200\nDallas, TX 75201",
            "customer_name":        "Hartwell Construction Inc.",
            "customer_address":     "4821 Maple Grove Drive\nAustin, TX 78745",
            "purchase_order_number":"PO-2024-1192",
            "currency":             "USD",
            "subtotal":             12450.00,
            "tax_amount":           1120.50,
            "shipping_amount":      0.00,
            "discount_amount":      250.00,
            "total_amount":         13320.50,
            "amount_due":           13320.50,
            "payment_terms":        30,
            "line_item_count":      3,
            "line_items": json.dumps([
                {"description": "Steel beam 6m I-section",  "quantity": 10, "unit_price": 840.00, "amount": 8400.00},
                {"description": "Galvanized bolts 50pk",    "quantity": 20, "unit_price": 45.00,  "amount": 900.00},
                {"description": "Concrete anchor kit",      "quantity": 15, "unit_price": 220.00, "amount": 3300.00},  # noqa: E501 -- demo data
            ]),
        },
        "confidence_scores": {
            "invoice_number":   0.99,
            "invoice_date":     0.97,
            "due_date":         0.94,
            "vendor_name":      0.98,
            "total_amount":     0.96,
            "tax_amount":       0.55,   # LOW
            "discount_amount":  0.48,   # LOW
            "line_items":       0.81,   # medium
        },
    },

    "KYC / CDD Form": {
        "doc_type": "kyc_cdd_form",
        "fields": {
            "customer_name":                    "Thornfield Capital Advisors LLC",
            "customer_type":                    "Business",
            "date_of_birth":                    None,
            "tax_id_masked":                    "**-***9312",
            "address_line1":                    "1400 Brickell Avenue, Suite 850",
            "city":                             "Miami",
            "state":                            "FL",
            "postal_code":                      "33131",
            "country":                          "USA",
            "phone":                            "305-555-0221",
            "email":                            "compliance@thornfieldcap.com",
            "occupation_or_business":           "Investment Advisory",
            "source_of_funds":                  "Business Revenue",
            "expected_monthly_activity":        "$250,000 – $500,000",
            "risk_rating":                      "Medium",
            "pep_status":                       "No PEP",
            "beneficial_owner_name":            "Marcus Thornfield",
            "beneficial_owner_ownership_percent": 62.0,
            "id_document_type":                 "EIN Certificate",
            "id_document_number_masked":        "**-***9312",
            "id_expiration_date":               None,
            "review_date":                      "2024-11-05",
            "reviewer_name":                    "Alice Morgan",
        },
        "confidence_scores": {
            "customer_name":    0.97,
            "risk_rating":      0.59,   # LOW
            "pep_status":       0.62,   # LOW
            "beneficial_owner_ownership_percent": 0.71,  # medium
            "source_of_funds":  0.78,   # medium
        },
    },
}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-size:20px;font-weight:800;color:#fff;'
        'letter-spacing:-0.5px;padding:4px 0">◈ DocuBricks</div>',
        unsafe_allow_html=True,
    )
    st.caption("Review UI — local demo")
    st.markdown("---")

    selected = st.radio(
        "Document",
        options=list(MOCK_DOCS.keys()),
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption("Signed in as **demo@docubricks.io**")
    st.caption("Tenant: `demo-tenant`")

# ── Load selected doc ──────────────────────────────────────────────────────────
doc        = MOCK_DOCS[selected]
doc_type   = doc["doc_type"]
fields     = doc["fields"]
conf_scores = doc["confidence_scores"]
schema_meta = get_schema_meta(doc_type)

# ── CSS: sticky doc pane + tab styling ────────────────────────────────────────
st.markdown(
    """
    <style>
    [data-testid="column"]:nth-child(1) > div:first-child {
        position: sticky;
        top: 3.5rem;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">'
    f'<span style="font-size:22px;font-weight:800;color:#1A1A2E">Review Queue</span>'
    f'<span style="background:#dbeafe;color:#1d4ed8;border-radius:4px;'
    f'font-size:12px;font-weight:600;padding:3px 10px">'
    f'{doc_type.replace("_"," ").title()}</span>'
    f'<span style="background:#ede9fe;color:#6d28d9;border-radius:4px;'
    f'font-size:12px;font-weight:600;padding:3px 10px">LOW_CONFIDENCE</span>'
    f'</div>',
    unsafe_allow_html=True,
)
st.caption("Document ID: `demo-doc-00001` · SLA: Due in 2h 14m")

# Low-conf summary banner
low_count = sum(1 for v in conf_scores.values() if v < 0.65)
if low_count:
    st.markdown(
        f'<div style="background:#FCE8E6;border-radius:6px;'
        f'padding:6px 12px;margin-bottom:8px;">'
        f'<span style="color:#A32D2D;font-size:12px;font-weight:600">'
        f'⚠ {low_count} field{"s" if low_count != 1 else ""} need attention '
        f'— check the ⚠ Needs Review tab first</span></div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Two-pane layout: doc 55% | fields 45% ─────────────────────────────────────
left_col, right_col = st.columns([55, 45], gap="large")

with left_col:
    st.subheader("Document")
    # Demo: render a styled placeholder since no real PDF is available locally
    st.markdown(
        f"""
        <div style="
            background:#F0F4F9;
            border:2px dashed #D1D9E6;
            border-radius:8px;
            height:620px;
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            color:#6B7280;
            font-size:14px;
            gap:12px;
        ">
            <div style="font-size:48px">📄</div>
            <div style="font-weight:600;color:#374151">{selected}</div>
            <div style="font-size:12px">Source PDF rendered here in production</div>
            <div style="font-size:11px;color:#9CA3AF">
                Databricks Files API → base64 iframe
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right_col:
    st.subheader("Extracted Fields")

    with st.form(key="demo_review_form"):
        with st.container(height=540, border=False):
            corrected = field_editor(
                fields=fields,
                confidence_scores=conf_scores,
                editable=True,
                schema_meta=schema_meta,
            )

        st.markdown("---")
        btn1, btn2, btn3 = st.columns(3)
        approve    = btn1.form_submit_button("✓ Approve as-is",     use_container_width=True, type="primary")
        reprocess  = btn2.form_submit_button("💾 Save & reprocess",  use_container_width=True)
        quarantine = btn3.form_submit_button("🗑 Quarantine",         use_container_width=True)

    if approve:
        st.toast("Document approved!", icon="✅")
    elif reprocess:
        st.toast("Saved — queued for reprocessing.", icon="💾")
        with st.expander("Corrected fields (would write to Lakebase)", expanded=True):
            st.json({k: v for k, v in corrected.items() if not k.startswith("_")})
    elif quarantine:
        st.toast("Document quarantined.", icon="🗑")
