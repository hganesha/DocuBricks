#!/usr/bin/env python3
"""Generate real estate transactions and property management schema bundles."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_ROOT = REPO_ROOT / "Schemas"
PROMPT_ROOT = SCHEMAS_ROOT / "prompts"


COMMON_ROUTING = {
    "primary": "databricks-claude-sonnet",
    "fallback_chain": ["databricks-meta-llama-3-70b-instruct"],
    "max_tokens": 6144,
    "temperature": 0.0,
    "timeout_seconds": 30,
    "max_retries": 2,
    "tier_overrides": {},
}


SCHEMAS = [
    {
        "family": "real_estate_transactions",
        "doc_type": "lease_agreement",
        "display_name": "Lease Agreement",
        "specialist": "real estate leasing and lease abstraction",
        "fields": [
            ("lease_date", "date", True, "Date the lease was executed or made effective."),
            ("landlord_name", "string", True, "Landlord or lessor legal name."),
            ("tenant_name", "string", True, "Tenant or lessee legal name."),
            ("property_address", "string", True, "Leased property address or premises."),
            ("premises_description", "string", False, "Description of leased premises, suite, floor, or rentable area."),
            ("lease_start_date", "date", True, "Lease commencement date."),
            ("lease_end_date", "date", True, "Lease expiration date."),
            ("base_rent_amount", "number", True, "Base rent amount for the stated period."),
            ("rent_frequency", "string", False, "Monthly, annual, weekly, or other rent frequency."),
            ("security_deposit_amount", "number", False, "Security deposit amount."),
            ("renewal_options", "array<string>", False, "Renewal options, extension rights, or option terms."),
            ("use_clause", "string", False, "Permitted use clause."),
            ("cam_or_operating_expense_terms", "string", False, "CAM, operating expense, tax, or insurance reimbursement terms."),
            ("guarantor_names", "array<string>", False, "Lease guarantors."),
            ("assignment_subletting_terms", "string", False, "Assignment or subletting restrictions."),
            ("governing_law", "string", False, "Governing state or jurisdiction."),
        ],
        "required": ["lease_date", "landlord_name", "tenant_name", "property_address", "lease_start_date", "lease_end_date", "base_rent_amount"],
        "thresholds": ["landlord_name", "tenant_name", "property_address", "lease_start_date", "lease_end_date", "base_rent_amount"],
        "golden_text": "LEASE AGREEMENT\nLease Date: 2026-07-01\nLandlord: Lakeshore Industrial Owner LLC\nTenant: Northstar Cold Storage LLC\nProperty: 1440 River Road, Joliet, IL 60431\nPremises: Suite 200, approximately 85,000 rentable square feet of refrigerated warehouse space\nCommencement Date: 2026-08-01\nExpiration Date: 2031-07-31\nBase Rent: $74,375.00 per month\nSecurity Deposit: $148,750.00\nRenewal Options: one 5-year renewal at fair market rent\nPermitted Use: refrigerated warehousing, distribution, and ancillary office use\nCAM/Operating Expenses: tenant pays pro rata share of taxes, insurance, utilities, and common area maintenance\nGuarantors: Northstar Holdings Inc.\nAssignment/Subletting: landlord consent required, not to be unreasonably withheld\nGoverning Law: Illinois",
        "expected": {
            "lease_date": "2026-07-01",
            "landlord_name": "Lakeshore Industrial Owner LLC",
            "tenant_name": "Northstar Cold Storage LLC",
            "property_address": "1440 River Road, Joliet, IL 60431",
            "premises_description": "Suite 200, approximately 85,000 rentable square feet of refrigerated warehouse space",
            "lease_start_date": "2026-08-01",
            "lease_end_date": "2031-07-31",
            "base_rent_amount": 74375.0,
            "rent_frequency": "monthly",
            "security_deposit_amount": 148750.0,
            "renewal_options": ["one 5-year renewal at fair market rent"],
            "use_clause": "refrigerated warehousing, distribution, and ancillary office use",
            "cam_or_operating_expense_terms": "tenant pays pro rata share of taxes, insurance, utilities, and common area maintenance",
            "guarantor_names": ["Northstar Holdings Inc."],
            "assignment_subletting_terms": "landlord consent required, not to be unreasonably withheld",
            "governing_law": "Illinois",
        },
    },
    {
        "family": "real_estate_transactions",
        "doc_type": "purchase_agreement",
        "display_name": "Purchase Agreement",
        "specialist": "real estate acquisition and sale contract review",
        "fields": [
            ("agreement_date", "date", True, "Date of purchase agreement."),
            ("buyer_name", "string", True, "Buyer or purchaser legal name."),
            ("seller_name", "string", True, "Seller legal name."),
            ("property_address", "string", True, "Property address."),
            ("legal_description", "string", False, "Legal description or parcel description."),
            ("purchase_price", "number", True, "Purchase price."),
            ("earnest_money_deposit", "number", False, "Earnest money deposit amount."),
            ("closing_date", "date", False, "Scheduled closing date."),
            ("due_diligence_deadline", "date", False, "Inspection or due diligence deadline."),
            ("financing_contingency", "boolean", False, "Whether financing contingency is stated."),
            ("inspection_contingency", "boolean", False, "Whether inspection contingency is stated."),
            ("title_company_name", "string", False, "Escrow agent or title company."),
            ("included_personal_property", "array<string>", False, "Personal property included in sale."),
            ("special_conditions", "array<string>", False, "Special conditions or seller obligations."),
            ("governing_law", "string", False, "Governing state or jurisdiction."),
        ],
        "required": ["agreement_date", "buyer_name", "seller_name", "property_address", "purchase_price"],
        "thresholds": ["buyer_name", "seller_name", "property_address", "purchase_price", "closing_date"],
        "golden_text": "REAL ESTATE PURCHASE AGREEMENT\nAgreement Date: 2026-06-15\nBuyer: Harborview Capital Partners LLC\nSeller: Maple Ridge Office Owner LP\nProperty: 8200 West Park Avenue, Denver, CO 80221\nLegal Description: Lot 4, Block 2, Maple Ridge Business Park, Adams County, Colorado\nPurchase Price: $18,750,000\nEarnest Money Deposit: $500,000\nScheduled Closing Date: 2026-09-30\nDue Diligence Deadline: 2026-07-31\nFinancing Contingency: Yes\nInspection Contingency: Yes\nTitle Company/Escrow Agent: Front Range Title Company\nIncluded Personal Property: lobby furniture; building maintenance equipment; security cameras\nSpecial Conditions: seller to deliver tenant estoppels for 80% of leased area; seller to cure open roof permit before closing\nGoverning Law: Colorado",
        "expected": {
            "agreement_date": "2026-06-15",
            "buyer_name": "Harborview Capital Partners LLC",
            "seller_name": "Maple Ridge Office Owner LP",
            "property_address": "8200 West Park Avenue, Denver, CO 80221",
            "legal_description": "Lot 4, Block 2, Maple Ridge Business Park, Adams County, Colorado",
            "purchase_price": 18750000.0,
            "earnest_money_deposit": 500000.0,
            "closing_date": "2026-09-30",
            "due_diligence_deadline": "2026-07-31",
            "financing_contingency": True,
            "inspection_contingency": True,
            "title_company_name": "Front Range Title Company",
            "included_personal_property": ["lobby furniture", "building maintenance equipment", "security cameras"],
            "special_conditions": ["seller to deliver tenant estoppels for 80% of leased area", "seller to cure open roof permit before closing"],
            "governing_law": "Colorado",
        },
    },
    {
        "family": "real_estate_transactions",
        "doc_type": "closing_statement",
        "display_name": "Closing Statement",
        "specialist": "real estate settlement and closing statement review",
        "fields": [
            ("closing_statement_date", "date", True, "Closing statement date."),
            ("property_address", "string", True, "Property address."),
            ("buyer_name", "string", True, "Buyer name."),
            ("seller_name", "string", True, "Seller name."),
            ("settlement_agent_name", "string", False, "Settlement agent, title company, or escrow officer."),
            ("closing_date", "date", True, "Closing date."),
            ("purchase_price", "number", True, "Purchase price."),
            ("loan_amount", "number", False, "Loan proceeds or loan amount."),
            ("buyer_cash_to_close", "number", False, "Buyer cash to close."),
            ("seller_proceeds", "number", False, "Seller net proceeds."),
            ("prorations", "array<object>", False, "Tax, rent, utility, CAM, or other prorations."),
            ("title_charges", "array<object>", False, "Title, escrow, recording, transfer tax, or settlement charges."),
            ("payoffs", "array<object>", False, "Mortgage, lien, or other payoff items."),
            ("recording_reference", "string", False, "Recording information if stated."),
        ],
        "required": ["closing_statement_date", "property_address", "buyer_name", "seller_name", "closing_date", "purchase_price"],
        "thresholds": ["property_address", "buyer_name", "seller_name", "closing_date", "purchase_price"],
        "golden_text": "CLOSING STATEMENT\nStatement Date: 2026-09-30\nProperty: 8200 West Park Avenue, Denver, CO 80221\nBuyer: Harborview Capital Partners LLC\nSeller: Maple Ridge Office Owner LP\nSettlement Agent: Front Range Title Company\nClosing Date: 2026-09-30\nPurchase Price: $18,750,000\nLoan Amount: $12,500,000\nBuyer Cash to Close: $6,925,430.22\nSeller Net Proceeds: $17,904,112.80\nProrations: county taxes credit to buyer $38,450.18; September rent credit to seller $72,000.00; CAM reconciliation debit to seller $14,200.00\nTitle/Settlement Charges: owner's title policy $42,500; escrow fee $8,750; recording fees $1,240; transfer tax $187,500\nPayoffs: First Western Bank loan payoff $612,480.22; mechanic lien release $22,000\nRecording Reference: Reception No. 20260930008912",
        "expected": {
            "closing_statement_date": "2026-09-30",
            "property_address": "8200 West Park Avenue, Denver, CO 80221",
            "buyer_name": "Harborview Capital Partners LLC",
            "seller_name": "Maple Ridge Office Owner LP",
            "settlement_agent_name": "Front Range Title Company",
            "closing_date": "2026-09-30",
            "purchase_price": 18750000.0,
            "loan_amount": 12500000.0,
            "buyer_cash_to_close": 6925430.22,
            "seller_proceeds": 17904112.8,
            "prorations": [
                {"item": "county taxes", "party_credited": "buyer", "amount": 38450.18},
                {"item": "September rent", "party_credited": "seller", "amount": 72000.0},
                {"item": "CAM reconciliation", "party_debited": "seller", "amount": 14200.0},
            ],
            "title_charges": [
                {"item": "owner's title policy", "amount": 42500.0},
                {"item": "escrow fee", "amount": 8750.0},
                {"item": "recording fees", "amount": 1240.0},
                {"item": "transfer tax", "amount": 187500.0},
            ],
            "payoffs": [
                {"payee": "First Western Bank", "amount": 612480.22},
                {"payee": "mechanic lien release", "amount": 22000.0},
            ],
            "recording_reference": "Reception No. 20260930008912",
        },
    },
    {
        "family": "real_estate_transactions",
        "doc_type": "deed",
        "display_name": "Deed",
        "specialist": "real estate deed and conveyance review",
        "fields": [
            ("deed_date", "date", True, "Date of deed."),
            ("deed_type", "string", True, "Warranty deed, special warranty deed, quitclaim deed, grant deed, or other type."),
            ("grantor_names", "array<string>", True, "Grantor names."),
            ("grantee_names", "array<string>", True, "Grantee names."),
            ("property_address", "string", False, "Property address."),
            ("legal_description", "string", True, "Legal description of conveyed property."),
            ("consideration_amount", "number", False, "Stated consideration amount."),
            ("county", "string", False, "County of property or recording."),
            ("state", "string", False, "State of property or recording."),
            ("recording_date", "date", False, "Recording date."),
            ("recording_number", "string", False, "Instrument, book/page, reception, or recording number."),
            ("notary_name", "string", False, "Notary name."),
            ("transfer_tax_amount", "number", False, "Transfer tax or documentary stamp amount."),
        ],
        "required": ["deed_date", "deed_type", "grantor_names", "grantee_names", "legal_description"],
        "thresholds": ["deed_type", "grantor_names", "grantee_names", "legal_description", "recording_number"],
        "golden_text": "SPECIAL WARRANTY DEED\nDeed Date: 2026-09-30\nGrantor: Maple Ridge Office Owner LP, a Delaware limited partnership\nGrantee: Harborview Capital Partners LLC, a Colorado limited liability company\nProperty Address: 8200 West Park Avenue, Denver, CO 80221\nLegal Description: Lot 4, Block 2, Maple Ridge Business Park, Adams County, Colorado\nConsideration: $18,750,000\nCounty: Adams\nState: Colorado\nRecorded: 2026-10-01\nReception Number: 20261001004418\nNotary: Vivian Brooks\nTransfer Tax: $187,500",
        "expected": {
            "deed_date": "2026-09-30",
            "deed_type": "Special Warranty Deed",
            "grantor_names": ["Maple Ridge Office Owner LP"],
            "grantee_names": ["Harborview Capital Partners LLC"],
            "property_address": "8200 West Park Avenue, Denver, CO 80221",
            "legal_description": "Lot 4, Block 2, Maple Ridge Business Park, Adams County, Colorado",
            "consideration_amount": 18750000.0,
            "county": "Adams",
            "state": "Colorado",
            "recording_date": "2026-10-01",
            "recording_number": "20261001004418",
            "notary_name": "Vivian Brooks",
            "transfer_tax_amount": 187500.0,
        },
    },
    {
        "family": "real_estate_transactions",
        "doc_type": "real_estate_transactions_title_commitment",
        "display_name": "Title Commitment",
        "specialist": "real estate title commitment and exception review",
        "fields": [
            ("commitment_number", "string", True, "Title commitment number."),
            ("commitment_date", "date", True, "Title commitment date."),
            ("title_company_name", "string", True, "Title insurer, agent, or issuing office."),
            ("proposed_insured", "string", False, "Proposed insured owner, lender, or policyholder."),
            ("property_address", "string", True, "Property address."),
            ("legal_description", "string", True, "Legal description."),
            ("vesting_owner", "string", False, "Current vested owner."),
            ("estate_or_interest", "string", False, "Estate or interest in land."),
            ("policy_amount", "number", False, "Proposed title policy amount."),
            ("requirements", "array<string>", False, "Schedule B-I requirements."),
            ("exceptions", "array<string>", False, "Schedule B-II exceptions."),
            ("tax_parcel_number", "string", False, "Tax parcel or assessor number."),
            ("effective_time", "string", False, "Effective date and time of title search."),
        ],
        "required": ["commitment_number", "commitment_date", "title_company_name", "property_address", "legal_description"],
        "thresholds": ["commitment_number", "title_company_name", "property_address", "legal_description", "exceptions"],
        "golden_text": "TITLE COMMITMENT\nCommitment Number: FRT-26-883104\nCommitment Date: 2026-08-20\nTitle Company: Front Range Title Company as agent for Mountain States Title Insurance Company\nProposed Insured: Harborview Capital Partners LLC and Prairie Bank NA\nProperty: 8200 West Park Avenue, Denver, CO 80221\nLegal Description: Lot 4, Block 2, Maple Ridge Business Park, Adams County, Colorado\nVesting Owner: Maple Ridge Office Owner LP\nEstate or Interest: Fee simple\nPolicy Amount: $18,750,000\nSchedule B-I Requirements: record special warranty deed; payoff First Western Bank deed of trust; obtain owner affidavit; release mechanic lien\nSchedule B-II Exceptions: easement recorded at Reception No. 1998123401; mineral reservation in Book 221 Page 14; current year property taxes not yet due; tenant rights under unrecorded leases\nTax Parcel: 0182511204004\nEffective Time: 2026-08-18 at 8:00 AM",
        "expected": {
            "commitment_number": "FRT-26-883104",
            "commitment_date": "2026-08-20",
            "title_company_name": "Front Range Title Company as agent for Mountain States Title Insurance Company",
            "proposed_insured": "Harborview Capital Partners LLC and Prairie Bank NA",
            "property_address": "8200 West Park Avenue, Denver, CO 80221",
            "legal_description": "Lot 4, Block 2, Maple Ridge Business Park, Adams County, Colorado",
            "vesting_owner": "Maple Ridge Office Owner LP",
            "estate_or_interest": "Fee simple",
            "policy_amount": 18750000.0,
            "requirements": ["record special warranty deed", "payoff First Western Bank deed of trust", "obtain owner affidavit", "release mechanic lien"],
            "exceptions": ["easement recorded at Reception No. 1998123401", "mineral reservation in Book 221 Page 14", "current year property taxes not yet due", "tenant rights under unrecorded leases"],
            "tax_parcel_number": "0182511204004",
            "effective_time": "2026-08-18 at 8:00 AM",
        },
    },
    {
        "family": "property_management",
        "doc_type": "property_management_agreement",
        "display_name": "Property Management Agreement",
        "specialist": "property management contract and operating authority review",
        "fields": [
            ("agreement_date", "date", True, "Date of property management agreement."),
            ("owner_name", "string", True, "Property owner legal name."),
            ("manager_name", "string", True, "Property manager legal name."),
            ("property_name", "string", False, "Property name."),
            ("property_address", "string", True, "Managed property address."),
            ("management_start_date", "date", True, "Management start date."),
            ("management_end_date", "date", False, "Management expiration date or initial term end."),
            ("management_fee_terms", "string", True, "Management fee percentage, amount, or formula."),
            ("leasing_fee_terms", "string", False, "Leasing fee or commission terms."),
            ("authority_to_collect_rent", "boolean", False, "Whether manager is authorized to collect rent."),
            ("bank_account_control", "string", False, "Operating account, trust account, or cash management terms."),
            ("termination_notice_days", "integer", False, "Termination notice period in days."),
            ("insurance_requirements", "array<string>", False, "Insurance requirements."),
            ("reporting_requirements", "array<string>", False, "Owner reporting requirements."),
            ("governing_law", "string", False, "Governing state or jurisdiction."),
        ],
        "required": ["agreement_date", "owner_name", "manager_name", "property_address", "management_start_date", "management_fee_terms"],
        "thresholds": ["owner_name", "manager_name", "property_address", "management_fee_terms", "termination_notice_days"],
        "golden_text": "PROPERTY MANAGEMENT AGREEMENT\nAgreement Date: 2026-10-01\nOwner: Harborview Capital Partners LLC\nManager: Summit Property Services Inc.\nProperty Name: Maple Ridge Office Center\nProperty Address: 8200 West Park Avenue, Denver, CO 80221\nManagement Start Date: 2026-10-01\nInitial Term End: 2028-09-30\nManagement Fee: 3.0% of gross collected revenue, payable monthly\nLeasing Fee: 4.0% of base rent for new leases and 2.0% for renewals\nAuthority to Collect Rent: Yes\nBank Account Control: manager to maintain separate operating account in owner's name with monthly reconciliations\nTermination Notice: 60 days\nInsurance Requirements: commercial general liability; crime coverage; workers compensation; errors and omissions\nReporting Requirements: monthly operating statement; rent roll; delinquency report; annual budget\nGoverning Law: Colorado",
        "expected": {
            "agreement_date": "2026-10-01",
            "owner_name": "Harborview Capital Partners LLC",
            "manager_name": "Summit Property Services Inc.",
            "property_name": "Maple Ridge Office Center",
            "property_address": "8200 West Park Avenue, Denver, CO 80221",
            "management_start_date": "2026-10-01",
            "management_end_date": "2028-09-30",
            "management_fee_terms": "3.0% of gross collected revenue, payable monthly",
            "leasing_fee_terms": "4.0% of base rent for new leases and 2.0% for renewals",
            "authority_to_collect_rent": True,
            "bank_account_control": "manager to maintain separate operating account in owner's name with monthly reconciliations",
            "termination_notice_days": 60,
            "insurance_requirements": ["commercial general liability", "crime coverage", "workers compensation", "errors and omissions"],
            "reporting_requirements": ["monthly operating statement", "rent roll", "delinquency report", "annual budget"],
            "governing_law": "Colorado",
        },
    },
    {
        "family": "property_management",
        "doc_type": "rent_roll",
        "display_name": "Rent Roll",
        "specialist": "property management rent roll and lease revenue review",
        "fields": [
            ("rent_roll_date", "date", True, "Date of rent roll."),
            ("property_name", "string", False, "Property name."),
            ("property_address", "string", True, "Property address."),
            ("owner_name", "string", False, "Owner name."),
            ("total_units_or_suites", "integer", False, "Total units or suites."),
            ("occupied_units_or_suites", "integer", False, "Occupied units or suites."),
            ("occupancy_rate", "number", False, "Occupancy rate percentage."),
            ("tenant_entries", "array<object>", True, "Tenant rows with unit, tenant, lease dates, area, rent, and arrears."),
            ("monthly_scheduled_rent", "number", True, "Total monthly scheduled rent."),
            ("delinquent_amount", "number", False, "Total delinquent or past due amount."),
            ("vacant_units", "array<string>", False, "Vacant units or suites."),
            ("report_preparer", "string", False, "Preparer or property manager."),
        ],
        "required": ["rent_roll_date", "property_address", "tenant_entries", "monthly_scheduled_rent"],
        "thresholds": ["rent_roll_date", "property_address", "tenant_entries", "monthly_scheduled_rent"],
        "golden_text": "RENT ROLL\nRent Roll Date: 2026-10-31\nProperty: Maple Ridge Office Center\nAddress: 8200 West Park Avenue, Denver, CO 80221\nOwner: Harborview Capital Partners LLC\nTotal Suites: 12\nOccupied Suites: 10\nOccupancy: 83.3%\nTenants: Suite 100 Alpine Dental lease 2024-01-01 to 2029-12-31 area 8,500 SF monthly rent $18,700 arrears $0; Suite 210 Peak Analytics lease 2025-06-01 to 2028-05-31 area 12,200 SF monthly rent $27,450 arrears $4,200; Suite 300 Front Range Design lease 2023-09-01 to 2026-08-31 area 6,000 SF monthly rent $13,500 arrears $0\nMonthly Scheduled Rent: $214,850\nTotal Delinquent: $4,200\nVacant Suites: 410; 520\nPrepared By: Summit Property Services Inc.",
        "expected": {
            "rent_roll_date": "2026-10-31",
            "property_name": "Maple Ridge Office Center",
            "property_address": "8200 West Park Avenue, Denver, CO 80221",
            "owner_name": "Harborview Capital Partners LLC",
            "total_units_or_suites": 12,
            "occupied_units_or_suites": 10,
            "occupancy_rate": 83.3,
            "tenant_entries": [
                {"suite": "100", "tenant_name": "Alpine Dental", "lease_start_date": "2024-01-01", "lease_end_date": "2029-12-31", "area_sq_ft": 8500, "monthly_rent": 18700.0, "arrears": 0.0},
                {"suite": "210", "tenant_name": "Peak Analytics", "lease_start_date": "2025-06-01", "lease_end_date": "2028-05-31", "area_sq_ft": 12200, "monthly_rent": 27450.0, "arrears": 4200.0},
                {"suite": "300", "tenant_name": "Front Range Design", "lease_start_date": "2023-09-01", "lease_end_date": "2026-08-31", "area_sq_ft": 6000, "monthly_rent": 13500.0, "arrears": 0.0},
            ],
            "monthly_scheduled_rent": 214850.0,
            "delinquent_amount": 4200.0,
            "vacant_units": ["410", "520"],
            "report_preparer": "Summit Property Services Inc.",
        },
    },
    {
        "family": "property_management",
        "doc_type": "tenant_estoppel_certificate",
        "display_name": "Tenant Estoppel Certificate",
        "specialist": "tenant estoppel and lease diligence review",
        "fields": [
            ("certificate_date", "date", True, "Tenant estoppel certificate date."),
            ("tenant_name", "string", True, "Tenant name."),
            ("landlord_name", "string", False, "Landlord name stated by tenant."),
            ("property_address", "string", True, "Property address."),
            ("premises_description", "string", False, "Suite, unit, floor, or premises description."),
            ("lease_date", "date", False, "Lease date."),
            ("lease_start_date", "date", False, "Lease commencement date."),
            ("lease_end_date", "date", True, "Lease expiration date."),
            ("current_monthly_rent", "number", True, "Current monthly rent."),
            ("security_deposit_amount", "number", False, "Security deposit amount."),
            ("defaults_claimed", "boolean", True, "Whether tenant claims landlord or tenant defaults."),
            ("offsets_or_claims", "string", False, "Offsets, defenses, claims, or concessions asserted."),
            ("renewal_options", "array<string>", False, "Renewal or expansion options stated."),
            ("tenant_signer_name", "string", True, "Tenant signer name."),
            ("tenant_signer_title", "string", False, "Tenant signer title."),
        ],
        "required": ["certificate_date", "tenant_name", "property_address", "lease_end_date", "current_monthly_rent", "defaults_claimed", "tenant_signer_name"],
        "thresholds": ["tenant_name", "property_address", "lease_end_date", "current_monthly_rent", "defaults_claimed", "tenant_signer_name"],
        "golden_text": "TENANT ESTOPPEL CERTIFICATE\nCertificate Date: 2026-09-10\nTenant: Peak Analytics Inc.\nLandlord: Maple Ridge Office Owner LP\nProperty: 8200 West Park Avenue, Denver, CO 80221\nPremises: Suite 210, approximately 12,200 rentable square feet\nLease Date: 2025-05-12\nCommencement Date: 2025-06-01\nExpiration Date: 2028-05-31\nCurrent Monthly Rent: $27,450\nSecurity Deposit: $27,450\nDefaults Claimed: No\nOffsets/Claims: none\nRenewal Options: one 3-year renewal at 95% of fair market rent\nSigned By: Rachel Lin\nTitle: Chief Operating Officer",
        "expected": {
            "certificate_date": "2026-09-10",
            "tenant_name": "Peak Analytics Inc.",
            "landlord_name": "Maple Ridge Office Owner LP",
            "property_address": "8200 West Park Avenue, Denver, CO 80221",
            "premises_description": "Suite 210, approximately 12,200 rentable square feet",
            "lease_date": "2025-05-12",
            "lease_start_date": "2025-06-01",
            "lease_end_date": "2028-05-31",
            "current_monthly_rent": 27450.0,
            "security_deposit_amount": 27450.0,
            "defaults_claimed": False,
            "offsets_or_claims": "none",
            "renewal_options": ["one 3-year renewal at 95% of fair market rent"],
            "tenant_signer_name": "Rachel Lin",
            "tenant_signer_title": "Chief Operating Officer",
        },
    },
]


def prompt_text(schema: dict) -> str:
    field_lines = "\n".join(
        f"- {name} ({field_type}): {description}"
        for name, field_type, _required, description in schema["fields"]
    )
    output_fields = ",\n    ".join(f'"{name}": null' for name, *_ in schema["fields"])
    return f"""You are a document extraction specialist for {schema['specialist']}. Extract structured fields from a {schema['display_name']} document.

Return exactly one JSON object with "extracted_fields", "confidence", and "extraction_metadata". For every listed field, return a value and a matching confidence score from 0.0 to 1.0. If a field is absent, return null and confidence 0.0. Do not infer facts that are not stated.

Fields to extract:
{field_lines}

Confidence scoring:
- 1.0: Explicit labeled field with no ambiguity.
- 0.90-0.99: Clearly present with minor normalization.
- 0.75-0.89: Present but requires reading across nearby context.
- 0.60-0.74: Ambiguous or partially legible.
- 0.0: Missing or not reliable.

Output format:
{{
  "extracted_fields": {{
    {output_fields}
  }},
  "confidence": {{}},
  "extraction_metadata": {{
    "document_type": "{schema['doc_type']}",
    "schema_version": "real_estate_{schema['doc_type']}_v1",
    "extraction_timestamp": "ISO8601",
    "avg_confidence": 0.0,
    "low_confidence_fields": [],
    "missing_fields": []
  }}
}}
"""


def fields_json(schema: dict) -> dict:
    return {
        "document_type": schema["doc_type"],
        "vertical": "real_estate",
        "family": schema["family"],
        "schema_version": f"real_estate_{schema['doc_type']}_v1",
        "fields": [
            {
                "name": name,
                "type": field_type,
                "required": required,
                "description": description,
            }
            for name, field_type, required, description in schema["fields"]
        ],
    }


def validation_rules(schema: dict) -> list[dict]:
    rules = []
    field_types = {name: field_type for name, field_type, _required, _desc in schema["fields"]}
    for name in schema["required"]:
        expression = f"{name} IS NOT NULL"
        if field_types[name].startswith("array"):
            expression += f" AND JSON_ARRAY_LENGTH({name}) > 0"
            rule_type = "array"
        else:
            expression += f" AND LENGTH(TRIM({name})) > 0"
            rule_type = "presence"
        rules.append(
            {
                "name": f"{name}_present",
                "rule_type": rule_type,
                "fields": [name],
                "expression": expression,
                "severity": "fail",
                "description": f"{name} is required for {schema['display_name']} extraction.",
            }
        )
    for name, field_type, _required, _desc in schema["fields"]:
        if field_type in {"number", "integer"}:
            rules.append(
                {
                    "name": f"{name}_non_negative",
                    "rule_type": "range",
                    "fields": [name],
                    "expression": f"{name} IS NULL OR {name} >= 0",
                    "severity": "warn",
                    "description": f"{name} should be non-negative when present.",
                }
            )
    return rules[:10]


def field_thresholds(schema: dict) -> dict:
    thresholds = {"default_threshold": 0.75}
    required = set(schema["required"])
    for name in [*schema["thresholds"], *(name for name in schema["required"] if name not in schema["thresholds"])]:
        thresholds[name] = {
            "min_confidence": 0.9 if name in required else 0.85,
            "review_on_breach": True,
            "fail_on_breach": name in required,
            "regulatory_required": name in required,
            "description": f"High-impact field for {schema['display_name']} workflow.",
        }
    return thresholds


def golden_test(schema: dict) -> dict:
    return {
        "test_case_id": f"{schema['doc_type']}_001",
        "document_type": schema["doc_type"],
        "description": f"Seed golden test for {schema['display_name']}",
        "tags": ["happy_path", schema["family"], "seed"],
        "parsed_text": schema["golden_text"],
        "expected_json": schema["expected"],
        "expected_avg_confidence": 0.92,
    }


def main() -> int:
    for schema in SCHEMAS:
        bundle = SCHEMAS_ROOT / "real_estate" / schema["doc_type"]
        prompt_path = PROMPT_ROOT / "real_estate" / schema["doc_type"] / "prompt_v1.txt"
        (bundle / "golden_tests").mkdir(parents=True, exist_ok=True)
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt_text(schema), encoding="utf-8")
        (bundle / "fields.json").write_text(
            json.dumps(fields_json(schema), indent=2) + "\n",
            encoding="utf-8",
        )
        (bundle / "validation_rules.json").write_text(
            json.dumps(validation_rules(schema), indent=2) + "\n",
            encoding="utf-8",
        )
        (bundle / "field_thresholds.json").write_text(
            json.dumps(field_thresholds(schema), indent=2) + "\n",
            encoding="utf-8",
        )
        routing = dict(COMMON_ROUTING)
        routing["rationale"] = (
            f"{schema['display_name']} documents combine real estate parties, "
            "property, title, lease, financial, and operating context."
        )
        (bundle / "model_routing.json").write_text(
            json.dumps(routing, indent=2) + "\n",
            encoding="utf-8",
        )
        (bundle / "golden_tests" / "test_001.json").write_text(
            json.dumps(golden_test(schema), indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Wrote {len(SCHEMAS)} real estate schema bundles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
