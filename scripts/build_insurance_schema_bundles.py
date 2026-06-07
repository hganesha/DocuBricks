#!/usr/bin/env python3
"""Generate insurance claims and policy operations schema bundles."""

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
        "vertical": "insurance",
        "family": "insurance_underwriting",
        "doc_type": "insurance_policy_application",
        "display_name": "Insurance Policy Application",
        "schema_version": "insurance_policy_application_v1",
        "specialist": "insurance underwriting intake",
        "fields": [
            ("application_date", "date YYYY-MM-DD", "Date the application was completed or submitted."),
            ("applicant_name", "string", "Named applicant or proposed insured."),
            ("applicant_entity_type", "string", "Individual, corporation, LLC, trust, or other legal form."),
            ("mailing_address", "string", "Applicant mailing address."),
            ("policy_type_requested", "string", "Line of business or coverage type requested."),
            ("effective_date_requested", "date YYYY-MM-DD", "Requested policy effective date."),
            ("coverage_limit_requested", "number", "Requested coverage limit or policy amount."),
            ("deductible_requested", "number", "Requested deductible or retention."),
            ("insured_property_or_risk", "string", "Property, operation, person, or risk to be insured."),
            ("prior_carrier_names", "array<string>", "Prior insurance carriers when listed."),
            ("loss_history_summary", "string", "Applicant's stated loss or claims history."),
            ("annual_revenue", "number", "Annual revenue when commercial exposure is stated."),
            ("employee_count", "integer", "Employee count when applicable."),
            ("risk_controls", "array<string>", "Safety, security, compliance, or loss control measures."),
            ("producer_name", "string", "Agent, broker, or producer name."),
            ("underwriting_status", "string", "Submitted, quoted, bound, declined, pending, or other status."),
        ],
        "required": ["applicant_name", "policy_type_requested", "effective_date_requested"],
        "thresholds": ["applicant_name", "policy_type_requested", "coverage_limit_requested", "underwriting_status"],
        "golden_text": "INSURANCE POLICY APPLICATION\nApplication Date: 2026-05-08\nApplicant: Northstar Cold Storage LLC\nEntity Type: LLC\nMailing Address: 1440 River Road, Joliet, IL 60431\nPolicy Type Requested: Commercial property and general liability package\nRequested Effective Date: 2026-07-01\nCoverage Limit Requested: $10,000,000\nDeductible Requested: $25,000\nRisk to be Insured: refrigerated warehouse and distribution operations\nPrior Carriers: Harbor Mutual; Lakeside Specialty\nLoss History: one water damage claim in 2024 for $86,000, closed\nAnnual Revenue: $42,500,000\nEmployees: 118\nRisk Controls: sprinkler system; 24-hour temperature monitoring; visitor log; OSHA safety training\nProducer: Ana Delgado, Summit Risk Advisors\nUnderwriting Status: Submitted",
        "expected": {
            "application_date": "2026-05-08",
            "applicant_name": "Northstar Cold Storage LLC",
            "applicant_entity_type": "LLC",
            "mailing_address": "1440 River Road, Joliet, IL 60431",
            "policy_type_requested": "Commercial property and general liability package",
            "effective_date_requested": "2026-07-01",
            "coverage_limit_requested": 10000000.0,
            "deductible_requested": 25000.0,
            "insured_property_or_risk": "refrigerated warehouse and distribution operations",
            "prior_carrier_names": ["Harbor Mutual", "Lakeside Specialty"],
            "loss_history_summary": "one water damage claim in 2024 for $86,000, closed",
            "annual_revenue": 42500000.0,
            "employee_count": 118,
            "risk_controls": ["sprinkler system", "24-hour temperature monitoring", "visitor log", "OSHA safety training"],
            "producer_name": "Ana Delgado, Summit Risk Advisors",
            "underwriting_status": "Submitted",
        },
    },
    {
        "vertical": "insurance",
        "family": "insurance_collateral_protection",
        "doc_type": "policy_declaration_page",
        "display_name": "Policy Declaration Page",
        "schema_version": "insurance_policy_declaration_page_v1",
        "specialist": "insurance policy declarations and coverage evidence",
        "fields": [
            ("policy_number", "string", "Insurance policy number."),
            ("named_insured", "string", "Named insured on the declaration page."),
            ("carrier_name", "string", "Insurance carrier or underwriting company."),
            ("producer_name", "string", "Agent, broker, or producer name."),
            ("policy_period_start", "date YYYY-MM-DD", "Policy period start date."),
            ("policy_period_end", "date YYYY-MM-DD", "Policy period end date."),
            ("coverage_lines", "array<string>", "Coverage lines shown on the declaration page."),
            ("covered_property_or_risk", "string", "Covered property, vehicle, operation, or risk."),
            ("coverage_limits", "array<object>", "Coverage limit items by line or coverage."),
            ("deductibles", "array<object>", "Deductible items by line or coverage."),
            ("premium_total", "number", "Total policy premium."),
            ("additional_insured_names", "array<string>", "Additional insureds shown on the declarations."),
            ("loss_payee_names", "array<string>", "Loss payees, mortgagees, or lender loss payable parties."),
            ("forms_and_endorsements", "array<string>", "Policy forms and endorsements listed."),
            ("cancellation_notice_days", "integer", "Number of cancellation notice days if stated."),
        ],
        "required": ["policy_number", "named_insured", "carrier_name"],
        "thresholds": ["policy_number", "named_insured", "policy_period_start", "policy_period_end"],
        "golden_text": "POLICY DECLARATION PAGE\nPolicy Number: CPP-7844129-06\nNamed Insured: Northstar Cold Storage LLC\nCarrier: Great Plains Indemnity Company\nProducer: Ana Delgado, Summit Risk Advisors\nPolicy Period: 2026-07-01 to 2027-07-01\nCoverage Lines: Building and Personal Property; Commercial General Liability; Equipment Breakdown\nCovered Risk: refrigerated warehouse at 1440 River Road, Joliet, IL\nCoverage Limits: building $8,500,000; business personal property $2,000,000; general liability $1,000,000 per occurrence\nDeductibles: property $25,000; equipment breakdown $10,000\nTotal Premium: $184,250\nAdditional Insureds: Joliet Logistics Park Owner LLC\nLoss Payees: Prairie Bank NA ISAOA ATIMA\nForms and Endorsements: CP 00 10; CG 20 10; Lender Loss Payable Endorsement\nCancellation Notice: 30 days",
        "expected": {
            "policy_number": "CPP-7844129-06",
            "named_insured": "Northstar Cold Storage LLC",
            "carrier_name": "Great Plains Indemnity Company",
            "producer_name": "Ana Delgado, Summit Risk Advisors",
            "policy_period_start": "2026-07-01",
            "policy_period_end": "2027-07-01",
            "coverage_lines": ["Building and Personal Property", "Commercial General Liability", "Equipment Breakdown"],
            "covered_property_or_risk": "refrigerated warehouse at 1440 River Road, Joliet, IL",
            "coverage_limits": [
                {"coverage": "building", "limit": 8500000.0},
                {"coverage": "business personal property", "limit": 2000000.0},
                {"coverage": "general liability", "limit": 1000000.0, "basis": "per occurrence"},
            ],
            "deductibles": [
                {"coverage": "property", "deductible": 25000.0},
                {"coverage": "equipment breakdown", "deductible": 10000.0},
            ],
            "premium_total": 184250.0,
            "additional_insured_names": ["Joliet Logistics Park Owner LLC"],
            "loss_payee_names": ["Prairie Bank NA ISAOA ATIMA"],
            "forms_and_endorsements": ["CP 00 10", "CG 20 10", "Lender Loss Payable Endorsement"],
            "cancellation_notice_days": 30,
        },
    },
    {
        "vertical": "insurance",
        "family": "insurance_collateral_protection",
        "doc_type": "certificate_of_insurance",
        "display_name": "Certificate of Insurance",
        "schema_version": "insurance_certificate_of_insurance_v1",
        "specialist": "certificate of insurance review",
        "fields": [
            ("certificate_date", "date YYYY-MM-DD", "Date the certificate was issued."),
            ("producer_name", "string", "Insurance producer or agency."),
            ("insured_name", "string", "Insured party named on the certificate."),
            ("certificate_holder_name", "string", "Certificate holder."),
            ("carrier_names", "array<string>", "Insurers affording coverage."),
            ("policy_numbers", "array<string>", "Policy numbers shown on the certificate."),
            ("coverage_lines", "array<string>", "Coverage types listed."),
            ("effective_dates", "array<string>", "Effective dates by coverage line."),
            ("expiration_dates", "array<string>", "Expiration dates by coverage line."),
            ("limits", "array<object>", "Limits by coverage line or limit type."),
            ("additional_insured_indicator", "boolean", "Whether additional insured status is indicated."),
            ("waiver_of_subrogation_indicator", "boolean", "Whether waiver of subrogation is indicated."),
            ("description_of_operations", "string", "Operations, locations, vehicles, or remarks."),
            ("cancellation_notice_text", "string", "Cancellation notice language."),
        ],
        "required": ["insured_name", "certificate_holder_name", "coverage_lines"],
        "thresholds": ["insured_name", "certificate_holder_name", "policy_numbers", "expiration_dates"],
        "golden_text": "CERTIFICATE OF INSURANCE\nCertificate Date: 2026-06-18\nProducer: Summit Risk Advisors\nInsured: Northstar Cold Storage LLC\nCertificate Holder: Prairie Bank NA, 100 Market Street, Chicago, IL\nInsurers: Great Plains Indemnity Company; Midwest Casualty Exchange\nPolicies: CPP-7844129-06; WC-4401287\nCoverage: Commercial General Liability effective 2026-07-01 expires 2027-07-01; Workers Compensation effective 2026-07-01 expires 2027-07-01\nLimits: CGL each occurrence $1,000,000; general aggregate $2,000,000; workers compensation statutory; employers liability $1,000,000\nAdditional Insured: Yes\nWaiver of Subrogation: Yes\nDescription: refrigerated warehouse operations at 1440 River Road; Prairie Bank named as lender loss payee where required by written contract\nCancellation Notice: should any policy be cancelled before expiration, notice will be delivered in accordance with policy provisions",
        "expected": {
            "certificate_date": "2026-06-18",
            "producer_name": "Summit Risk Advisors",
            "insured_name": "Northstar Cold Storage LLC",
            "certificate_holder_name": "Prairie Bank NA, 100 Market Street, Chicago, IL",
            "carrier_names": ["Great Plains Indemnity Company", "Midwest Casualty Exchange"],
            "policy_numbers": ["CPP-7844129-06", "WC-4401287"],
            "coverage_lines": ["Commercial General Liability", "Workers Compensation"],
            "effective_dates": ["2026-07-01", "2026-07-01"],
            "expiration_dates": ["2027-07-01", "2027-07-01"],
            "limits": [
                {"coverage": "CGL", "limit_type": "each occurrence", "limit": 1000000.0},
                {"coverage": "CGL", "limit_type": "general aggregate", "limit": 2000000.0},
                {"coverage": "workers compensation", "limit_type": "statutory", "limit": None},
                {"coverage": "employers liability", "limit_type": "limit", "limit": 1000000.0},
            ],
            "additional_insured_indicator": True,
            "waiver_of_subrogation_indicator": True,
            "description_of_operations": "refrigerated warehouse operations at 1440 River Road; Prairie Bank named as lender loss payee where required by written contract",
            "cancellation_notice_text": "should any policy be cancelled before expiration, notice will be delivered in accordance with policy provisions",
        },
    },
    {
        "vertical": "insurance",
        "family": "insurance_collateral_protection",
        "doc_type": "insurance_claim_file",
        "display_name": "Insurance Claim File",
        "schema_version": "insurance_claim_file_v1",
        "specialist": "insurance claim file triage and monitoring",
        "fields": [
            ("claim_number", "string", "Claim number or file identifier."),
            ("policy_number", "string", "Related policy number."),
            ("insured_name", "string", "Named insured or claimant."),
            ("claimant_name", "string", "Claimant name if different from insured."),
            ("loss_date", "date YYYY-MM-DD", "Date of loss."),
            ("reported_date", "date YYYY-MM-DD", "Date loss was reported."),
            ("loss_location", "string", "Location of loss."),
            ("loss_description", "string", "Description of incident or claimed loss."),
            ("claim_type", "string", "Property, casualty, auto, liability, workers compensation, or other type."),
            ("claim_status", "string", "Open, pending, reserved, closed, denied, litigated, or other status."),
            ("reserve_amount", "number", "Current claim reserve amount."),
            ("paid_amount", "number", "Total amount paid to date."),
            ("adjuster_name", "string", "Assigned adjuster."),
            ("coverage_position", "string", "Coverage accepted, reservation of rights, denied, pending, or other position."),
            ("documents_received", "array<string>", "Documents in claim file."),
            ("next_action_due_date", "date YYYY-MM-DD", "Next diary, review, or action due date."),
        ],
        "required": ["claim_number", "policy_number", "loss_date"],
        "thresholds": ["claim_number", "policy_number", "claim_status", "reserve_amount"],
        "golden_text": "INSURANCE CLAIM FILE\nClaim Number: GL-26-11904\nPolicy Number: CPP-7844129-06\nInsured: Northstar Cold Storage LLC\nClaimant: Metro Produce Distributors Inc.\nLoss Date: 2026-08-14\nReported Date: 2026-08-15\nLoss Location: 1440 River Road, Joliet, IL\nLoss Description: ammonia equipment failure caused spoilage of third-party produce inventory\nClaim Type: Commercial property and liability\nStatus: Open - coverage review\nReserve Amount: $650,000\nPaid Amount: $0\nAdjuster: Leah Chen\nCoverage Position: Reservation of rights pending equipment breakdown review\nDocuments Received: FNOL; refrigeration maintenance logs; inventory spoilage schedule; certificate of insurance\nNext Action Due: 2026-09-01",
        "expected": {
            "claim_number": "GL-26-11904",
            "policy_number": "CPP-7844129-06",
            "insured_name": "Northstar Cold Storage LLC",
            "claimant_name": "Metro Produce Distributors Inc.",
            "loss_date": "2026-08-14",
            "reported_date": "2026-08-15",
            "loss_location": "1440 River Road, Joliet, IL",
            "loss_description": "ammonia equipment failure caused spoilage of third-party produce inventory",
            "claim_type": "Commercial property and liability",
            "claim_status": "Open - coverage review",
            "reserve_amount": 650000.0,
            "paid_amount": 0.0,
            "adjuster_name": "Leah Chen",
            "coverage_position": "Reservation of rights pending equipment breakdown review",
            "documents_received": ["FNOL", "refrigeration maintenance logs", "inventory spoilage schedule", "certificate of insurance"],
            "next_action_due_date": "2026-09-01",
        },
    },
    {
        "vertical": "insurance",
        "family": "insurance_claims",
        "doc_type": "first_notice_of_loss",
        "display_name": "First Notice of Loss",
        "schema_version": "insurance_first_notice_of_loss_v1",
        "specialist": "first notice of loss intake",
        "fields": [
            ("reported_date", "date YYYY-MM-DD", "Date the loss was reported."),
            ("reported_time", "string", "Time the loss was reported if stated."),
            ("reporting_party_name", "string", "Person or entity reporting the loss."),
            ("reporting_party_phone", "string", "Reporter phone number."),
            ("policy_number", "string", "Policy number stated on the notice."),
            ("insured_name", "string", "Named insured."),
            ("loss_date", "date YYYY-MM-DD", "Date of loss."),
            ("loss_time", "string", "Time of loss if stated."),
            ("loss_location", "string", "Location where the loss occurred."),
            ("loss_cause", "string", "Stated cause of loss."),
            ("loss_description", "string", "Narrative description of the loss."),
            ("injury_indicator", "boolean", "Whether injuries are reported."),
            ("police_or_authority_report", "string", "Police, fire, OSHA, or other authority report details."),
            ("estimated_loss_amount", "number", "Estimated loss amount if stated."),
            ("emergency_mitigation_actions", "array<string>", "Emergency actions taken to mitigate loss."),
        ],
        "required": ["reported_date", "policy_number", "loss_date", "loss_description"],
        "thresholds": ["policy_number", "insured_name", "loss_date", "estimated_loss_amount"],
        "golden_text": "FIRST NOTICE OF LOSS\nReported Date: 2026-08-15\nReported Time: 9:35 AM CT\nReported By: Marcus Hale, Operations Director\nPhone: 312-555-0198\nPolicy Number: CPP-7844129-06\nInsured: Northstar Cold Storage LLC\nLoss Date: 2026-08-14\nLoss Time: approximately 11:40 PM\nLoss Location: 1440 River Road, Joliet, IL\nCause of Loss: ammonia refrigeration equipment failure\nDescription: temperature excursion caused spoilage of customer produce inventory in cold room 3\nInjuries Reported: No\nAuthority Report: Fire department incident report JFD-2026-4481\nEstimated Loss: $590,000\nMitigation Actions: isolated cold room 3; transferred unaffected inventory; contacted refrigeration contractor; preserved temperature logs",
        "expected": {
            "reported_date": "2026-08-15",
            "reported_time": "9:35 AM CT",
            "reporting_party_name": "Marcus Hale, Operations Director",
            "reporting_party_phone": "312-555-0198",
            "policy_number": "CPP-7844129-06",
            "insured_name": "Northstar Cold Storage LLC",
            "loss_date": "2026-08-14",
            "loss_time": "approximately 11:40 PM",
            "loss_location": "1440 River Road, Joliet, IL",
            "loss_cause": "ammonia refrigeration equipment failure",
            "loss_description": "temperature excursion caused spoilage of customer produce inventory in cold room 3",
            "injury_indicator": False,
            "police_or_authority_report": "Fire department incident report JFD-2026-4481",
            "estimated_loss_amount": 590000.0,
            "emergency_mitigation_actions": ["isolated cold room 3", "transferred unaffected inventory", "contacted refrigeration contractor", "preserved temperature logs"],
        },
    },
    {
        "vertical": "insurance",
        "family": "insurance_collateral_protection",
        "doc_type": "proof_of_loss",
        "display_name": "Proof of Loss",
        "schema_version": "insurance_proof_of_loss_v1",
        "specialist": "sworn proof of loss review",
        "fields": [
            ("claim_number", "string", "Claim number."),
            ("policy_number", "string", "Policy number."),
            ("insured_name", "string", "Insured submitting proof of loss."),
            ("loss_date", "date YYYY-MM-DD", "Date of loss."),
            ("loss_location", "string", "Location of loss."),
            ("cause_of_loss", "string", "Cause or origin of loss."),
            ("claimed_amount", "number", "Total amount claimed."),
            ("actual_cash_value", "number", "Actual cash value stated."),
            ("replacement_cost_value", "number", "Replacement cost value stated."),
            ("deductible_amount", "number", "Applicable deductible."),
            ("mortgagee_or_loss_payee", "string", "Mortgagee, lienholder, or loss payee."),
            ("other_insurance", "string", "Other insurance disclosed."),
            ("supporting_documents", "array<string>", "Documents supporting the proof of loss."),
            ("signed_date", "date YYYY-MM-DD", "Date signed."),
            ("notary_name", "string", "Notary name if notarized."),
        ],
        "required": ["claim_number", "policy_number", "insured_name", "claimed_amount"],
        "thresholds": ["claim_number", "policy_number", "claimed_amount", "signed_date"],
        "golden_text": "SWORN STATEMENT IN PROOF OF LOSS\nClaim Number: GL-26-11904\nPolicy Number: CPP-7844129-06\nInsured: Northstar Cold Storage LLC\nLoss Date: 2026-08-14\nLoss Location: 1440 River Road, Joliet, Illinois\nCause of Loss: ammonia refrigeration equipment failure and temperature excursion\nAmount Claimed: $612,480\nActual Cash Value: $598,900\nReplacement Cost Value: $612,480\nDeductible: $25,000\nMortgagee/Loss Payee: Prairie Bank NA ISAOA ATIMA\nOther Insurance: none known for spoiled inventory\nSupporting Documents: inventory valuation schedule; temperature logs; contractor invoice; photographs; customer claim notice\nSigned Date: 2026-08-28\nNotary: Denise Palmer, Notary Public",
        "expected": {
            "claim_number": "GL-26-11904",
            "policy_number": "CPP-7844129-06",
            "insured_name": "Northstar Cold Storage LLC",
            "loss_date": "2026-08-14",
            "loss_location": "1440 River Road, Joliet, Illinois",
            "cause_of_loss": "ammonia refrigeration equipment failure and temperature excursion",
            "claimed_amount": 612480.0,
            "actual_cash_value": 598900.0,
            "replacement_cost_value": 612480.0,
            "deductible_amount": 25000.0,
            "mortgagee_or_loss_payee": "Prairie Bank NA ISAOA ATIMA",
            "other_insurance": "none known for spoiled inventory",
            "supporting_documents": ["inventory valuation schedule", "temperature logs", "contractor invoice", "photographs", "customer claim notice"],
            "signed_date": "2026-08-28",
            "notary_name": "Denise Palmer, Notary Public",
        },
    },
    {
        "vertical": "insurance",
        "family": "insurance_claims",
        "doc_type": "claims_adjuster_report",
        "display_name": "Claims Adjuster Report",
        "schema_version": "insurance_claims_adjuster_report_v1",
        "specialist": "claims adjusting and coverage evaluation",
        "fields": [
            ("report_date", "date YYYY-MM-DD", "Date of adjuster report."),
            ("claim_number", "string", "Claim number."),
            ("adjuster_name", "string", "Adjuster name."),
            ("policy_number", "string", "Policy number."),
            ("insured_name", "string", "Named insured."),
            ("loss_date", "date YYYY-MM-DD", "Date of loss."),
            ("inspection_date", "date YYYY-MM-DD", "Date of inspection."),
            ("cause_of_loss_assessment", "string", "Adjuster's cause of loss assessment."),
            ("coverage_analysis", "string", "Coverage analysis or applicable coverage position."),
            ("damage_scope", "array<string>", "Scope of covered or claimed damage."),
            ("estimated_gross_loss", "number", "Gross loss estimate."),
            ("deductible_amount", "number", "Deductible amount."),
            ("recommended_reserve", "number", "Recommended reserve."),
            ("recommended_payment", "number", "Recommended payment."),
            ("salvage_or_subrogation_potential", "string", "Salvage or subrogation potential."),
            ("open_items", "array<string>", "Open information requests or pending items."),
        ],
        "required": ["report_date", "claim_number", "adjuster_name", "coverage_analysis"],
        "thresholds": ["claim_number", "coverage_analysis", "recommended_reserve", "recommended_payment"],
        "golden_text": "CLAIMS ADJUSTER REPORT\nReport Date: 2026-09-03\nClaim Number: GL-26-11904\nAdjuster: Leah Chen\nPolicy Number: CPP-7844129-06\nInsured: Northstar Cold Storage LLC\nLoss Date: 2026-08-14\nInspection Date: 2026-08-19\nCause of Loss Assessment: failed compressor relay caused refrigeration outage and temperature excursion\nCoverage Analysis: equipment breakdown coverage appears triggered; liability for third-party inventory remains under reservation of rights\nDamage Scope: spoiled produce inventory in cold room 3; emergency refrigeration service; sanitation and disposal costs\nEstimated Gross Loss: $612,480\nDeductible: $25,000\nRecommended Reserve: $675,000\nRecommended Payment: $0 pending valuation reconciliation\nSalvage/Subrogation Potential: possible subrogation against refrigeration maintenance contractor\nOpen Items: final inventory valuation; contractor service history; customer ownership records; coverage counsel review",
        "expected": {
            "report_date": "2026-09-03",
            "claim_number": "GL-26-11904",
            "adjuster_name": "Leah Chen",
            "policy_number": "CPP-7844129-06",
            "insured_name": "Northstar Cold Storage LLC",
            "loss_date": "2026-08-14",
            "inspection_date": "2026-08-19",
            "cause_of_loss_assessment": "failed compressor relay caused refrigeration outage and temperature excursion",
            "coverage_analysis": "equipment breakdown coverage appears triggered; liability for third-party inventory remains under reservation of rights",
            "damage_scope": ["spoiled produce inventory in cold room 3", "emergency refrigeration service", "sanitation and disposal costs"],
            "estimated_gross_loss": 612480.0,
            "deductible_amount": 25000.0,
            "recommended_reserve": 675000.0,
            "recommended_payment": 0.0,
            "salvage_or_subrogation_potential": "possible subrogation against refrigeration maintenance contractor",
            "open_items": ["final inventory valuation", "contractor service history", "customer ownership records", "coverage counsel review"],
        },
    },
    {
        "vertical": "insurance",
        "family": "insurance_claims",
        "doc_type": "insurance_claim_denial_letter",
        "display_name": "Insurance Claim Denial Letter",
        "schema_version": "insurance_claim_denial_letter_v1",
        "specialist": "insurance coverage determination and claim denial review",
        "fields": [
            ("letter_date", "date YYYY-MM-DD", "Date of denial letter."),
            ("claim_number", "string", "Claim number."),
            ("policy_number", "string", "Policy number."),
            ("insured_name", "string", "Named insured."),
            ("claimant_name", "string", "Claimant if different from insured."),
            ("loss_date", "date YYYY-MM-DD", "Date of loss."),
            ("coverage_denied", "string", "Coverage, payment, or claim component denied."),
            ("denial_reason", "string", "Reason for denial."),
            ("policy_provisions_cited", "array<string>", "Policy provisions, exclusions, or conditions cited."),
            ("facts_relied_on", "array<string>", "Facts or investigation findings relied on."),
            ("appeal_or_reconsideration_rights", "string", "Appeal, complaint, or reconsideration rights."),
            ("regulatory_notice", "string", "State or regulatory notice language."),
            ("reservation_of_rights_continues", "boolean", "Whether reservation of rights continues for other issues."),
            ("sender_name", "string", "Sender or claims representative."),
            ("sender_title", "string", "Sender title."),
        ],
        "required": ["letter_date", "claim_number", "policy_number", "denial_reason"],
        "thresholds": ["claim_number", "policy_number", "coverage_denied", "denial_reason"],
        "golden_text": "CLAIM DENIAL LETTER\nLetter Date: 2026-10-12\nClaim Number: GL-26-11904\nPolicy Number: CPP-7844129-06\nInsured: Northstar Cold Storage LLC\nClaimant: Metro Produce Distributors Inc.\nLoss Date: 2026-08-14\nCoverage Denied: liability coverage for third-party contractual spoilage claim\nDenial Reason: the claim arises from contractual assumption of liability for customer inventory not otherwise covered by the policy\nPolicy Provisions Cited: Commercial General Liability Coverage Form Section I; Contractual Liability Exclusion; Care Custody or Control Exclusion\nFacts Relied On: warehouse agreement shifts inventory loss risk to Northstar; spoiled goods were in insured's care custody or control; no bodily injury alleged\nAppeal Rights: submit written reconsideration with additional facts within 30 days\nRegulatory Notice: Illinois Department of Insurance complaint rights enclosed\nReservation of Rights Continues: Yes\nSender: Martin Walsh\nTitle: Senior Claims Examiner",
        "expected": {
            "letter_date": "2026-10-12",
            "claim_number": "GL-26-11904",
            "policy_number": "CPP-7844129-06",
            "insured_name": "Northstar Cold Storage LLC",
            "claimant_name": "Metro Produce Distributors Inc.",
            "loss_date": "2026-08-14",
            "coverage_denied": "liability coverage for third-party contractual spoilage claim",
            "denial_reason": "the claim arises from contractual assumption of liability for customer inventory not otherwise covered by the policy",
            "policy_provisions_cited": ["Commercial General Liability Coverage Form Section I", "Contractual Liability Exclusion", "Care Custody or Control Exclusion"],
            "facts_relied_on": ["warehouse agreement shifts inventory loss risk to Northstar", "spoiled goods were in insured's care custody or control", "no bodily injury alleged"],
            "appeal_or_reconsideration_rights": "submit written reconsideration with additional facts within 30 days",
            "regulatory_notice": "Illinois Department of Insurance complaint rights enclosed",
            "reservation_of_rights_continues": True,
            "sender_name": "Martin Walsh",
            "sender_title": "Senior Claims Examiner",
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
        if field_types[name].startswith("array"):
            expression += f" AND JSON_ARRAY_LENGTH({name}) > 0"
        else:
            expression += f" AND LENGTH(TRIM({name})) > 0"
        rules.append(
            {
                "name": f"{name}_present",
                "field_name": name,
                "rule_type": "PRESENCE",
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
                    "field_name": name,
                    "rule_type": "RANGE",
                    "expression": f"{name} IS NULL OR {name} >= 0",
                    "severity": "warn",
                    "description": f"{name} should be non-negative when present.",
                }
            )
    return rules[:10]


def field_thresholds(schema: dict) -> list[dict]:
    return [
        {
            "field_name": name,
            "min_confidence": 0.9 if name in schema["required"] else 0.85,
            "review_threshold": 0.7,
            "quarantine_threshold": 0.5,
            "review_on_breach": True,
            "fail_on_breach": name in schema["required"],
            "regulatory_required": True,
            "description": f"High-impact field for {schema['display_name']} workflow.",
        }
        for name in schema["thresholds"]
    ]


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
        routing["rationale"] = (
            f"{schema['display_name']} documents mix policy, coverage, claim, "
            "party, financial, and regulatory notice context."
        )
        (bundle / "model_routing.json").write_text(
            json.dumps(routing, indent=2) + "\n",
            encoding="utf-8",
        )
        (bundle / "golden_tests" / "test_001.json").write_text(
            json.dumps(golden_test(schema), indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Wrote {len(SCHEMAS)} insurance schema bundles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
