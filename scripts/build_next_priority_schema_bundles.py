#!/usr/bin/env python3
"""Generate the next priority registry-ready schema bundles."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_ROOT = REPO_ROOT / "Schemas"


COMMON_ROUTING = {
    "model_endpoint": "databricks-claude-sonnet",
    "fallback_endpoint": "databricks-meta-llama-3-70b-instruct",
    "max_tokens": 6144,
    "temperature": 0.0,
}


SCHEMAS = [
    {
        "vertical": "fs",
        "family": "regulatory_exams_audit",
        "doc_type": "third_party_risk_assessment",
        "display_name": "Third-party Risk Assessment",
        "schema_version": "risk_third_party_risk_assessment_v1",
        "specialist": "vendor risk and third-party risk management",
        "fields": [
            ("assessment_date", "date YYYY-MM-DD", "Date the assessment was completed."),
            ("vendor_name", "string", "Legal or operating name of the vendor."),
            ("vendor_service_description", "string", "Description of products or services provided."),
            ("business_owner", "string", "Internal owner or relationship manager."),
            ("criticality_tier", "string", "Critical, high, medium, low, or other tier."),
            ("inherent_risk_rating", "string", "Inherent risk before controls."),
            ("residual_risk_rating", "string", "Residual risk after controls."),
            ("data_access_level", "string", "Customer data, confidential data, payment data, PHI, none, or other."),
            ("customer_impact", "boolean", "Whether vendor failure could materially affect customers."),
            ("outsourcing_indicator", "boolean", "Whether this is an outsourcing or material service provider."),
            ("subcontractors", "array<string>", "Named material subcontractors or fourth parties."),
            ("soc_report_type", "string", "SOC 1, SOC 2, bridge letter, none, or other."),
            ("soc_report_date", "date YYYY-MM-DD", "Date or period end of SOC report."),
            ("information_security_rating", "string", "Information security control rating."),
            ("business_continuity_rating", "string", "BCP/DR control rating."),
            ("financial_condition_rating", "string", "Financial strength or viability rating."),
            ("regulatory_compliance_rating", "string", "Compliance control rating."),
            ("open_issues", "array<string>", "Open issues, findings, or remediation items."),
            ("remediation_due_date", "date YYYY-MM-DD", "Due date for remediation if stated."),
            ("approval_status", "string", "Approved, conditionally approved, rejected, pending, or other."),
            ("approver_name", "string", "Approver, committee, or risk officer."),
            ("next_review_date", "date YYYY-MM-DD", "Next periodic review date."),
        ],
        "required": ["vendor_name", "assessment_date"],
        "thresholds": ["vendor_name", "criticality_tier", "residual_risk_rating", "approval_status"],
        "golden_text": "THIRD-PARTY RISK ASSESSMENT\nAssessment Date: 2026-04-12\nVendor: ClearPay Data Services LLC\nService: hosted payment dispute workflow and evidence repository\nBusiness Owner: Nora Singh\nCriticality: High\nInherent Risk: High\nResidual Risk: Medium\nData Access: customer PII and payment dispute records\nCustomer Impact: Yes\nOutsourcing: Yes\nMaterial Subcontractors: NorthCloud Hosting; Sentinel SOC Services\nSOC Report: SOC 2 Type II, period ended 2026-02-28\nInformation Security Rating: Satisfactory\nBusiness Continuity Rating: Needs Improvement\nFinancial Condition Rating: Stable\nRegulatory Compliance Rating: Satisfactory\nOpen Issues: update incident response contact list; complete DR test evidence\nRemediation Due Date: 2026-06-30\nApproval Status: Conditionally Approved\nApprover: Third Party Risk Committee\nNext Review Date: 2027-04-12",
        "expected": {
            "assessment_date": "2026-04-12",
            "vendor_name": "ClearPay Data Services LLC",
            "vendor_service_description": "hosted payment dispute workflow and evidence repository",
            "business_owner": "Nora Singh",
            "criticality_tier": "High",
            "inherent_risk_rating": "High",
            "residual_risk_rating": "Medium",
            "data_access_level": "customer PII and payment dispute records",
            "customer_impact": True,
            "outsourcing_indicator": True,
            "subcontractors": ["NorthCloud Hosting", "Sentinel SOC Services"],
            "soc_report_type": "SOC 2 Type II",
            "soc_report_date": "2026-02-28",
            "information_security_rating": "Satisfactory",
            "business_continuity_rating": "Needs Improvement",
            "financial_condition_rating": "Stable",
            "regulatory_compliance_rating": "Satisfactory",
            "open_issues": ["update incident response contact list", "complete DR test evidence"],
            "remediation_due_date": "2026-06-30",
            "approval_status": "Conditionally Approved",
            "approver_name": "Third Party Risk Committee",
            "next_review_date": "2027-04-12",
        },
    },
    {
        "vertical": "fs",
        "family": "regulatory_exams_audit",
        "doc_type": "issue_management_record",
        "display_name": "Issue Management Record",
        "schema_version": "risk_issue_management_record_v1",
        "specialist": "regulatory exam and issue management",
        "fields": [
            ("issue_id", "string", "Internal issue, MRA, MRIA, or audit finding identifier."),
            ("source_type", "string", "Regulatory exam, internal audit, compliance testing, self-identified, or other."),
            ("source_name", "string", "Regulator, audit group, testing program, or source."),
            ("issue_title", "string", "Short issue title."),
            ("issue_description", "string", "Detailed issue or finding description."),
            ("risk_domain", "string", "Compliance, credit, operational, model, cyber, liquidity, or other domain."),
            ("severity", "string", "Critical, high, medium, low, MRA, MRIA, or other severity."),
            ("status", "string", "Open, in progress, pending validation, closed, overdue, or other."),
            ("owner_name", "string", "Accountable issue owner."),
            ("business_unit", "string", "Business unit responsible for remediation."),
            ("opened_date", "date YYYY-MM-DD", "Date issue was opened."),
            ("target_completion_date", "date YYYY-MM-DD", "Committed remediation target date."),
            ("actual_completion_date", "date YYYY-MM-DD", "Actual completion date if closed."),
            ("corrective_action_plan", "string", "Summary of remediation plan."),
            ("milestones", "array<string>", "Key milestones or deliverables."),
            ("evidence_required", "array<string>", "Evidence expected for closure."),
            ("validation_owner", "string", "Independent validation owner or function."),
            ("validation_status", "string", "Not started, in progress, passed, failed, or other."),
            ("regulatory_commitment", "boolean", "Whether issue is tied to a regulatory commitment."),
            ("days_overdue", "integer", "Days overdue if stated."),
        ],
        "required": ["issue_id", "issue_title", "status"],
        "thresholds": ["issue_id", "issue_title", "severity", "target_completion_date", "status"],
        "golden_text": "ISSUE MANAGEMENT RECORD\nIssue ID: MRA-2026-014\nSource Type: Regulatory exam\nSource: OCC Commercial Credit Exam\nTitle: Weak evidence of covenant monitoring follow-up\nDescription: Examiners found inconsistent tracking of borrower covenant exceptions and delayed escalation of waiver requests.\nRisk Domain: Credit Risk\nSeverity: MRA\nStatus: In Progress\nOwner: Marcus Hale\nBusiness Unit: Commercial Banking Credit Administration\nOpened Date: 2026-01-18\nTarget Completion Date: 2026-09-30\nCorrective Action Plan: implement centralized covenant exception workflow, monthly aging report, and second-line validation.\nMilestones: workflow design by 2026-03-31; production deployment by 2026-06-30; validation package by 2026-09-15\nEvidence Required: policy update; workflow screenshots; sample exception report; validation memo\nValidation Owner: Credit Risk Review\nValidation Status: Not Started\nRegulatory Commitment: Yes\nDays Overdue: 0",
        "expected": {
            "issue_id": "MRA-2026-014",
            "source_type": "Regulatory exam",
            "source_name": "OCC Commercial Credit Exam",
            "issue_title": "Weak evidence of covenant monitoring follow-up",
            "issue_description": "Examiners found inconsistent tracking of borrower covenant exceptions and delayed escalation of waiver requests.",
            "risk_domain": "Credit Risk",
            "severity": "MRA",
            "status": "In Progress",
            "owner_name": "Marcus Hale",
            "business_unit": "Commercial Banking Credit Administration",
            "opened_date": "2026-01-18",
            "target_completion_date": "2026-09-30",
            "actual_completion_date": None,
            "corrective_action_plan": "implement centralized covenant exception workflow, monthly aging report, and second-line validation",
            "milestones": ["workflow design by 2026-03-31", "production deployment by 2026-06-30", "validation package by 2026-09-15"],
            "evidence_required": ["policy update", "workflow screenshots", "sample exception report", "validation memo"],
            "validation_owner": "Credit Risk Review",
            "validation_status": "Not Started",
            "regulatory_commitment": True,
            "days_overdue": 0,
        },
    },
    {
        "vertical": "fs",
        "family": "wealth_brokerage_investment",
        "doc_type": "trust_account_opening_package",
        "display_name": "Trust Account Opening Package",
        "schema_version": "fs_trust_account_opening_package_v1",
        "specialist": "trust and fiduciary account onboarding",
        "fields": [
            ("application_date", "date YYYY-MM-DD", "Date the account package was completed."),
            ("trust_name", "string", "Legal name of trust or estate."),
            ("trust_type", "string", "Revocable, irrevocable, testamentary, estate, charitable, special needs, or other."),
            ("trust_tax_id_masked", "string", "Masked trust EIN or tax identifier."),
            ("jurisdiction", "string", "Governing state or country."),
            ("grantor_names", "array<string>", "Grantors, settlors, or decedent names."),
            ("trustee_names", "array<string>", "Trustees or personal representatives."),
            ("authorized_signer_names", "array<string>", "Authorized account signers."),
            ("beneficiary_names", "array<string>", "Named beneficiaries when present."),
            ("fiduciary_powers", "array<string>", "Investment, distribution, borrowing, pledge, or other powers."),
            ("investment_objective", "string", "Investment objective or account purpose."),
            ("risk_tolerance", "string", "Conservative, moderate, aggressive, or stated risk profile."),
            ("source_of_funds", "string", "Source of initial funding."),
            ("initial_deposit_amount", "number", "Initial deposit or transfer amount."),
            ("account_type_requested", "string", "Trust brokerage, fiduciary checking, estate account, managed account, or other."),
            ("tax_certification_status", "string", "W-9, W-8, exempt, missing, or other tax certification status."),
            ("beneficial_ownership_required", "boolean", "Whether beneficial ownership certification is required or referenced."),
            ("document_checklist", "array<string>", "Documents received or required."),
            ("approval_status", "string", "Approved, pending, rejected, conditional, or other."),
            ("relationship_manager_name", "string", "Advisor, banker, or relationship manager."),
        ],
        "required": ["trust_name", "trustee_names"],
        "thresholds": ["trust_name", "trust_tax_id_masked", "trustee_names", "initial_deposit_amount"],
        "golden_text": "TRUST ACCOUNT OPENING PACKAGE\nApplication Date: 2026-05-04\nTrust Name: The Eleanor Park Revocable Trust dated May 1, 2021\nTrust Type: Revocable Trust\nTax ID: XX-XXX4412\nGoverning Law: California\nGrantor: Eleanor Park\nTrustees: Eleanor Park; Samuel Park\nAuthorized Signers: Eleanor Park; Samuel Park\nBeneficiaries: Samuel Park; Mina Park\nFiduciary Powers: invest assets; open brokerage accounts; make distributions; pledge assets only with trustee consent\nInvestment Objective: balanced income and growth\nRisk Tolerance: Moderate\nSource of Funds: transfer from existing brokerage account\nInitial Deposit: $1,250,000\nAccount Requested: Trust brokerage managed account\nTax Certification: W-9 received\nBeneficial Ownership Certification Required: No\nDocuments: trust certification; trustee IDs; W-9; investment profile\nApproval Status: Approved\nRelationship Manager: Dana Ortiz",
        "expected": {
            "application_date": "2026-05-04",
            "trust_name": "The Eleanor Park Revocable Trust dated May 1, 2021",
            "trust_type": "Revocable Trust",
            "trust_tax_id_masked": "XX-XXX4412",
            "jurisdiction": "California",
            "grantor_names": ["Eleanor Park"],
            "trustee_names": ["Eleanor Park", "Samuel Park"],
            "authorized_signer_names": ["Eleanor Park", "Samuel Park"],
            "beneficiary_names": ["Samuel Park", "Mina Park"],
            "fiduciary_powers": ["invest assets", "open brokerage accounts", "make distributions", "pledge assets only with trustee consent"],
            "investment_objective": "balanced income and growth",
            "risk_tolerance": "Moderate",
            "source_of_funds": "transfer from existing brokerage account",
            "initial_deposit_amount": 1250000.0,
            "account_type_requested": "Trust brokerage managed account",
            "tax_certification_status": "W-9 received",
            "beneficial_ownership_required": False,
            "document_checklist": ["trust certification", "trustee IDs", "W-9", "investment profile"],
            "approval_status": "Approved",
            "relationship_manager_name": "Dana Ortiz",
        },
    },
    {
        "vertical": "fs",
        "family": "payments_fintech",
        "doc_type": "merchant_onboarding_application",
        "display_name": "Merchant Onboarding Application",
        "schema_version": "fs_merchant_onboarding_application_v1",
        "specialist": "merchant acquiring and payment risk onboarding",
        "fields": [
            ("application_date", "date YYYY-MM-DD", "Date the merchant application was submitted."),
            ("merchant_legal_name", "string", "Merchant legal entity name."),
            ("merchant_dba_name", "string", "Doing-business-as name."),
            ("merchant_tax_id_masked", "string", "Masked EIN or tax identifier."),
            ("merchant_category_code", "string", "MCC if stated."),
            ("business_type", "string", "Retail, ecommerce, restaurant, marketplace, services, or other."),
            ("website_url", "string", "Merchant website or app URL."),
            ("processing_channels", "array<string>", "Card-present, ecommerce, mobile, keyed, ACH, or other channels."),
            ("estimated_monthly_volume", "number", "Estimated monthly processing volume."),
            ("average_ticket_amount", "number", "Average transaction amount."),
            ("high_ticket_amount", "number", "Highest expected transaction amount."),
            ("refund_policy", "string", "Refund, cancellation, or return policy summary."),
            ("chargeback_history", "string", "Prior chargeback history or ratio."),
            ("reserve_required", "boolean", "Whether reserve or holdback is required."),
            ("reserve_terms", "string", "Reserve amount, percentage, or duration."),
            ("beneficial_owner_names", "array<string>", "Beneficial owners listed in application."),
            ("principal_signer_name", "string", "Principal or authorized signer."),
            ("risk_rating", "string", "Merchant risk rating."),
            ("underwriting_decision", "string", "Approved, declined, conditional, pending, or other."),
            ("approval_conditions", "array<string>", "Underwriting conditions."),
        ],
        "required": ["merchant_legal_name", "estimated_monthly_volume"],
        "thresholds": ["merchant_legal_name", "merchant_tax_id_masked", "estimated_monthly_volume", "underwriting_decision"],
        "golden_text": "MERCHANT ONBOARDING APPLICATION\nApplication Date: 2026-03-22\nLegal Name: Lakeside Outdoor Gear LLC\nDBA: LakesideGear.com\nEIN: XX-XXX9201\nMCC: 5941 Sporting Goods Stores\nBusiness Type: Ecommerce retailer\nWebsite: https://lakesidegear.example\nProcessing Channels: ecommerce; mobile wallet; keyed phone orders\nEstimated Monthly Volume: $850,000\nAverage Ticket: $115.00\nHigh Ticket: $2,500.00\nRefund Policy: 30-day returns for unused goods\nChargeback History: prior processor reported 0.65% chargeback ratio\nReserve Required: Yes\nReserve Terms: 5% rolling reserve for 180 days\nBeneficial Owners: Priya Raman; Cole Bennett\nPrincipal Signer: Priya Raman\nRisk Rating: Medium\nUnderwriting Decision: Approved with conditions\nConditions: rolling reserve agreement; website terms update; proof of inventory financing",
        "expected": {
            "application_date": "2026-03-22",
            "merchant_legal_name": "Lakeside Outdoor Gear LLC",
            "merchant_dba_name": "LakesideGear.com",
            "merchant_tax_id_masked": "XX-XXX9201",
            "merchant_category_code": "5941",
            "business_type": "Ecommerce retailer",
            "website_url": "https://lakesidegear.example",
            "processing_channels": ["ecommerce", "mobile wallet", "keyed phone orders"],
            "estimated_monthly_volume": 850000.0,
            "average_ticket_amount": 115.0,
            "high_ticket_amount": 2500.0,
            "refund_policy": "30-day returns for unused goods",
            "chargeback_history": "prior processor reported 0.65% chargeback ratio",
            "reserve_required": True,
            "reserve_terms": "5% rolling reserve for 180 days",
            "beneficial_owner_names": ["Priya Raman", "Cole Bennett"],
            "principal_signer_name": "Priya Raman",
            "risk_rating": "Medium",
            "underwriting_decision": "Approved with conditions",
            "approval_conditions": ["rolling reserve agreement", "website terms update", "proof of inventory financing"],
        },
    },
    {
        "vertical": "fs",
        "family": "commercial_lending",
        "doc_type": "syndicated_credit_agreement",
        "display_name": "Syndicated Credit Agreement",
        "schema_version": "fs_syndicated_credit_agreement_v1",
        "specialist": "syndicated loan and private credit deal documentation",
        "fields": [
            ("agreement_date", "date YYYY-MM-DD", "Date of credit agreement or amendment."),
            ("borrower_name", "string", "Borrower legal name."),
            ("administrative_agent_name", "string", "Administrative agent or collateral agent."),
            ("lead_arranger_names", "array<string>", "Lead arrangers, bookrunners, or private credit sponsors."),
            ("lender_names", "array<string>", "Named lenders or lender groups."),
            ("facility_type", "string", "Revolver, term loan A, term loan B, delayed draw, unitranche, or other."),
            ("total_commitment_amount", "number", "Total commitments across all tranches."),
            ("tranches", "array<object>", "Tranche entries with name, amount, maturity, pricing, and currency when present."),
            ("maturity_date", "date YYYY-MM-DD", "Final maturity date."),
            ("pricing_grid", "string", "Pricing grid or spread mechanics."),
            ("benchmark_rate", "string", "SOFR, base rate, prime, EURIBOR, or other benchmark."),
            ("commitment_fee", "number", "Unused commitment fee percentage if stated."),
            ("collateral_summary", "string", "Collateral or security package summary."),
            ("guarantor_names", "array<string>", "Guarantors or loan parties."),
            ("financial_covenants", "array<string>", "Financial covenants."),
            ("negative_covenants", "array<string>", "Negative covenants."),
            ("mandatory_prepayment_events", "array<string>", "Asset sale, debt issuance, excess cash flow, or other prepayment triggers."),
            ("assignment_minimum_amount", "number", "Minimum assignment amount if stated."),
            ("required_lender_threshold", "string", "Required lender voting threshold."),
            ("governing_law", "string", "Governing law jurisdiction."),
        ],
        "required": ["borrower_name", "administrative_agent_name", "total_commitment_amount"],
        "thresholds": ["borrower_name", "administrative_agent_name", "total_commitment_amount", "tranches"],
        "golden_text": "SYNDICATED CREDIT AGREEMENT dated June 1, 2026. Borrower: Northstar Components Holdings Inc. Administrative Agent and Collateral Agent: Atlantic Bank, N.A. Lead Arrangers: Atlantic Bank Securities; Blue Ridge Private Credit. Lenders: Atlantic Bank, N.A.; Blue Ridge Direct Lending Fund; Harbor Credit Partners. Facilities: $75,000,000 revolving credit facility and $225,000,000 term loan. Total Commitments: $300,000,000. Tranche A Revolver: $75,000,000, maturity June 1, 2031, SOFR plus 2.25%. Term Loan: $225,000,000, maturity June 1, 2032, SOFR plus 4.75%. Pricing Grid: leverage-based grid. Benchmark: Term SOFR. Commitment Fee: 0.35%. Collateral: substantially all assets of borrower and domestic subsidiaries. Guarantors: Northstar Components LLC; Northstar Distribution LLC. Financial Covenants: maximum first lien leverage ratio 4.50x; minimum fixed charge coverage ratio 1.10x. Negative Covenants: debt, liens, restricted payments, investments, asset sales. Mandatory Prepayments: asset sales; debt issuance; excess cash flow. Minimum Assignment Amount: $5,000,000. Required Lenders: more than 50% of commitments. Governing Law: New York.",
        "expected": {
            "agreement_date": "2026-06-01",
            "borrower_name": "Northstar Components Holdings Inc.",
            "administrative_agent_name": "Atlantic Bank, N.A.",
            "lead_arranger_names": ["Atlantic Bank Securities", "Blue Ridge Private Credit"],
            "lender_names": ["Atlantic Bank, N.A.", "Blue Ridge Direct Lending Fund", "Harbor Credit Partners"],
            "facility_type": "revolving credit facility and term loan",
            "total_commitment_amount": 300000000.0,
            "tranches": [
                {"name": "Tranche A Revolver", "amount": 75000000.0, "maturity": "2031-06-01", "pricing": "SOFR plus 2.25%"},
                {"name": "Term Loan", "amount": 225000000.0, "maturity": "2032-06-01", "pricing": "SOFR plus 4.75%"},
            ],
            "maturity_date": "2032-06-01",
            "pricing_grid": "leverage-based grid",
            "benchmark_rate": "Term SOFR",
            "commitment_fee": 0.35,
            "collateral_summary": "substantially all assets of borrower and domestic subsidiaries",
            "guarantor_names": ["Northstar Components LLC", "Northstar Distribution LLC"],
            "financial_covenants": ["maximum first lien leverage ratio 4.50x", "minimum fixed charge coverage ratio 1.10x"],
            "negative_covenants": ["debt", "liens", "restricted payments", "investments", "asset sales"],
            "mandatory_prepayment_events": ["asset sales", "debt issuance", "excess cash flow"],
            "assignment_minimum_amount": 5000000.0,
            "required_lender_threshold": "more than 50% of commitments",
            "governing_law": "New York",
        },
    },
    {
        "vertical": "legal",
        "family": "litigation_disputes",
        "doc_type": "litigation_case_file",
        "display_name": "Litigation Case File",
        "schema_version": "legal_litigation_case_file_v1",
        "specialist": "litigation matter and case file intake",
        "fields": [
            ("matter_id", "string", "Internal matter or case file identifier."),
            ("case_name", "string", "Case caption or matter name."),
            ("court_name", "string", "Court, arbitration forum, or tribunal."),
            ("case_number", "string", "Court docket or arbitration number."),
            ("case_type", "string", "Commercial, employment, collections, bankruptcy, class action, arbitration, or other."),
            ("plaintiff_names", "array<string>", "Plaintiffs, claimants, or petitioners."),
            ("defendant_names", "array<string>", "Defendants, respondents, or opposing parties."),
            ("client_role", "string", "Plaintiff, defendant, third party, creditor, debtor, witness, or other."),
            ("lead_counsel_name", "string", "Lead internal or external counsel."),
            ("law_firm", "string", "Outside counsel firm if present."),
            ("filing_date", "date YYYY-MM-DD", "Initial filing or demand date."),
            ("next_deadline_date", "date YYYY-MM-DD", "Next upcoming deadline."),
            ("next_deadline_description", "string", "Description of next deadline."),
            ("claims_or_causes", "array<string>", "Claims, causes of action, or legal theories."),
            ("key_motions", "array<string>", "Key pending or decided motions."),
            ("discovery_status", "string", "Discovery phase or status."),
            ("hearing_dates", "array<string>", "Upcoming hearing, mediation, trial, or conference dates."),
            ("settlement_status", "string", "Settlement posture or demand status."),
            ("exposure_amount", "number", "Claimed damages, reserve, or exposure amount."),
            ("case_status", "string", "Open, stayed, settled, judgment, closed, appealed, or other."),
        ],
        "required": ["case_name", "case_status"],
        "thresholds": ["case_name", "case_number", "next_deadline_date", "exposure_amount"],
        "golden_text": "LITIGATION CASE FILE SUMMARY\nMatter ID: LIT-2026-087\nCase: Apex Supply Co. v. Meridian Bank, N.A.\nCourt: Superior Court of California, County of Los Angeles\nCase No.: 26STCV10482\nCase Type: Commercial contract dispute\nPlaintiffs: Apex Supply Co.\nDefendants: Meridian Bank, N.A.; Meridian Commercial Finance LLC\nClient Role: Defendant\nLead Counsel: Andrea Wolfe\nLaw Firm: Wolfe & Kim LLP\nInitial Filing Date: 2026-02-11\nNext Deadline: July 15, 2026 - opposition to motion for preliminary injunction\nClaims: breach of contract; negligent misrepresentation; unfair business practices\nKey Motions: motion for preliminary injunction pending; demurrer filed\nDiscovery Status: written discovery served, document production in progress\nHearings: 2026-07-29 preliminary injunction hearing; 2026-09-04 case management conference\nSettlement Status: mediation scheduled, no demand accepted\nExposure: $8,500,000\nCase Status: Open",
        "expected": {
            "matter_id": "LIT-2026-087",
            "case_name": "Apex Supply Co. v. Meridian Bank, N.A.",
            "court_name": "Superior Court of California, County of Los Angeles",
            "case_number": "26STCV10482",
            "case_type": "Commercial contract dispute",
            "plaintiff_names": ["Apex Supply Co."],
            "defendant_names": ["Meridian Bank, N.A.", "Meridian Commercial Finance LLC"],
            "client_role": "Defendant",
            "lead_counsel_name": "Andrea Wolfe",
            "law_firm": "Wolfe & Kim LLP",
            "filing_date": "2026-02-11",
            "next_deadline_date": "2026-07-15",
            "next_deadline_description": "opposition to motion for preliminary injunction",
            "claims_or_causes": ["breach of contract", "negligent misrepresentation", "unfair business practices"],
            "key_motions": ["motion for preliminary injunction pending", "demurrer filed"],
            "discovery_status": "written discovery served, document production in progress",
            "hearing_dates": ["2026-07-29 preliminary injunction hearing", "2026-09-04 case management conference"],
            "settlement_status": "mediation scheduled, no demand accepted",
            "exposure_amount": 8500000.0,
            "case_status": "Open",
        },
    },
    {
        "vertical": "fs",
        "family": "regulatory_reporting",
        "doc_type": "regulatory_reporting_package",
        "display_name": "Regulatory Reporting Package",
        "schema_version": "risk_regulatory_reporting_package_v1",
        "specialist": "bank regulatory reporting and attestation packages",
        "fields": [
            ("report_name", "string", "Name of report package or filing."),
            ("report_type", "string", "Call Report, HMDA, CRA, SAR, CTR, CECL, CCAR, DFAST, liquidity, or other."),
            ("reporting_period_end_date", "date YYYY-MM-DD", "Reporting period end date."),
            ("institution_name", "string", "Reporting institution legal name."),
            ("institution_identifier", "string", "RSSD, FDIC certificate, LEI, NMLS, or other identifier."),
            ("regulator_name", "string", "Regulator or filing recipient."),
            ("submission_due_date", "date YYYY-MM-DD", "Submission due date."),
            ("submission_date", "date YYYY-MM-DD", "Actual submission date if filed."),
            ("filing_status", "string", "Draft, filed, accepted, rejected, amended, or other."),
            ("preparer_name", "string", "Report preparer or owner."),
            ("approver_name", "string", "Approver or certifying officer."),
            ("attestation_required", "boolean", "Whether certification or attestation is required."),
            ("key_metrics", "array<object>", "Material report metrics with name, value, and unit if present."),
            ("exceptions", "array<string>", "Known exceptions, edits, or validation issues."),
            ("amendment_indicator", "boolean", "Whether package is an amendment or resubmission."),
            ("amendment_reason", "string", "Reason for amendment or resubmission."),
            ("evidence_documents", "array<string>", "Supporting schedules, reconciliations, or evidence."),
            ("control_signoffs", "array<string>", "Control owners or signoff records."),
        ],
        "required": ["report_name", "report_type", "reporting_period_end_date"],
        "thresholds": ["report_name", "report_type", "reporting_period_end_date", "filing_status"],
        "golden_text": "REGULATORY REPORTING PACKAGE\nReport Name: Q1 2026 Consolidated Reports of Condition and Income\nReport Type: Call Report\nReporting Period End: 2026-03-31\nInstitution: Meridian Bank, N.A.\nRSSD ID: 1234567\nRegulator: FFIEC / OCC\nSubmission Due Date: 2026-04-30\nSubmission Date: 2026-04-28\nFiling Status: Accepted\nPreparer: Luis Romero\nApprover: Karen Blake, Chief Financial Officer\nAttestation Required: Yes\nKey Metrics: Total Assets $18,420,000,000; Tier 1 Capital Ratio 11.2%; Total Loans $12,750,000,000\nExceptions: Schedule RC-C commercial loan reconciliation variance resolved; edit check E-212 cleared\nAmendment: No\nEvidence: trial balance reconciliation; loan system tie-out; CFO certification; edit check report\nControl Signoffs: Financial Reporting Control FR-12; Regulatory Reporting Manager review; CFO certification",
        "expected": {
            "report_name": "Q1 2026 Consolidated Reports of Condition and Income",
            "report_type": "Call Report",
            "reporting_period_end_date": "2026-03-31",
            "institution_name": "Meridian Bank, N.A.",
            "institution_identifier": "1234567",
            "regulator_name": "FFIEC / OCC",
            "submission_due_date": "2026-04-30",
            "submission_date": "2026-04-28",
            "filing_status": "Accepted",
            "preparer_name": "Luis Romero",
            "approver_name": "Karen Blake, Chief Financial Officer",
            "attestation_required": True,
            "key_metrics": [
                {"name": "Total Assets", "value": 18420000000.0, "unit": "USD"},
                {"name": "Tier 1 Capital Ratio", "value": 11.2, "unit": "percent"},
                {"name": "Total Loans", "value": 12750000000.0, "unit": "USD"},
            ],
            "exceptions": ["Schedule RC-C commercial loan reconciliation variance resolved", "edit check E-212 cleared"],
            "amendment_indicator": False,
            "amendment_reason": None,
            "evidence_documents": ["trial balance reconciliation", "loan system tie-out", "CFO certification", "edit check report"],
            "control_signoffs": ["Financial Reporting Control FR-12", "Regulatory Reporting Manager review", "CFO certification"],
        },
    },
]


def prompt_text(schema: dict) -> str:
    field_lines = "\n".join(
        f"- {name} ({field_type}): {description}"
        for name, field_type, description in schema["fields"]
    )
    output_fields = ",\n    ".join(f'"{name}": null' for name, _, _ in schema["fields"])
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
    "schema_version": "{schema['schema_version']}",
    "extraction_timestamp": "ISO8601",
    "avg_confidence": 0.0,
    "low_confidence_fields": [],
    "missing_fields": []
  }}
}}
"""


def validation_rules(schema: dict) -> list[dict]:
    rules: list[dict] = []
    field_types = {name: field_type for name, field_type, _ in schema["fields"]}
    for name in schema["required"]:
        expression = f"{name} IS NOT NULL"
        if not field_types[name].startswith("array"):
            expression += f" AND LENGTH(TRIM({name})) > 0"
        else:
            expression += f" AND JSON_ARRAY_LENGTH({name}) > 0"
        rules.append(
            {
                "name": f"{name}_present",
                "expression": expression,
                "severity": "fail",
                "description": f"{name} is required for {schema['display_name']} extraction.",
            }
        )
    for name, field_type, _ in schema["fields"]:
        if field_type == "number":
            rules.append(
                {
                    "name": f"{name}_non_negative",
                    "expression": f"{name} IS NULL OR {name} >= 0",
                    "severity": "warn",
                    "description": f"{name} should be non-negative when present.",
                }
            )
    return rules[:8]


def field_thresholds(schema: dict) -> dict:
    thresholds = {}
    for name in schema["thresholds"]:
        thresholds[name] = {
            "min_confidence": 0.9 if name in schema["required"] else 0.85,
            "review_on_breach": True,
            "fail_on_breach": name in schema["required"],
            "regulatory_required": schema["vertical"] == "risk_compliance",
            "description": f"High-impact field for {schema['display_name']} workflow.",
        }
    return thresholds


def golden_test(schema: dict) -> dict:
    return {
        "test_case_id": f"{schema['doc_type']}_001",
        "document_type": schema["doc_type"],
        "description": f"Seed golden test for {schema['display_name']}",
        "parsed_text": schema["golden_text"],
        "expected_json": schema["expected"],
        "expected_avg_confidence": 0.92,
    }


def main() -> int:
    for schema in SCHEMAS:
        bundle = SCHEMAS_ROOT / schema["vertical"] / schema["doc_type"]
        (bundle / "golden_tests").mkdir(parents=True, exist_ok=True)
        (bundle / "prompt_v1.txt").write_text(prompt_text(schema), encoding="utf-8")
        (bundle / "validation_rules.json").write_text(
            json.dumps(validation_rules(schema), indent=2) + "\n",
            encoding="utf-8",
        )
        (bundle / "field_thresholds.json").write_text(
            json.dumps(field_thresholds(schema), indent=2) + "\n",
            encoding="utf-8",
        )
        routing = dict(COMMON_ROUTING)
        routing["rationale"] = f"{schema['display_name']} documents combine structured fields and narrative risk/legal/compliance context."
        (bundle / "model_routing.json").write_text(
            json.dumps(routing, indent=2) + "\n",
            encoding="utf-8",
        )
        (bundle / "golden_tests" / "test_001.json").write_text(
            json.dumps(golden_test(schema), indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Wrote {len(SCHEMAS)} next-priority schema bundles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
