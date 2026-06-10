#!/usr/bin/env python3
"""Generate manufacturing quality and supply chain schema bundles."""

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
        "family": "procurement_supply_chain",
        "doc_type": "purchase_order",
        "display_name": "Purchase Order",
        "specialist": "manufacturing procurement and purchase order operations",
        "fields": [
            ("purchase_order_number", "string", True, "Purchase order number."),
            ("po_date", "date", True, "Date the purchase order was issued."),
            ("buyer_name", "string", True, "Buying legal entity or plant."),
            ("supplier_name", "string", True, "Supplier or vendor name."),
            ("ship_to_location", "string", False, "Ship-to plant, warehouse, or address."),
            ("requested_delivery_date", "date", False, "Requested delivery date."),
            ("currency", "string", False, "Currency code."),
            ("payment_terms", "string", False, "Payment terms."),
            ("incoterms", "string", False, "Incoterms or freight terms."),
            ("line_items", "array<object>", True, "PO line items with part, description, quantity, unit price, and due date."),
            ("subtotal_amount", "number", False, "Subtotal amount."),
            ("tax_amount", "number", False, "Tax amount."),
            ("total_amount", "number", True, "Total purchase order amount."),
            ("buyer_contact_name", "string", False, "Buyer contact or purchasing agent."),
            ("approval_status", "string", False, "Approved, pending, revised, closed, cancelled, or other status."),
        ],
        "required": ["purchase_order_number", "po_date", "buyer_name", "supplier_name", "line_items", "total_amount"],
        "thresholds": ["purchase_order_number", "supplier_name", "line_items", "total_amount"],
        "golden_text": "PURCHASE ORDER\nPO Number: PO-4500129841\nPO Date: 2026-04-03\nBuyer: Prairie Ridge Manufacturing LLC - Des Moines Plant\nSupplier: Apex Alloy Supply Inc.\nShip To: 4100 Foundry Road, Des Moines, IA 50309\nRequested Delivery: 2026-04-24\nCurrency: USD\nPayment Terms: Net 45\nIncoterms: FOB Origin\nLine Items: 1) Part AL-6061-BAR, Aluminum bar stock, qty 1200 LB, unit price $4.25, due 2026-04-24; 2) Part ST-4140-PLT, Steel plate, qty 80 EA, unit price $185.00, due 2026-04-28\nSubtotal: $19,900.00\nTax: $0.00\nTotal: $19,900.00\nBuyer Contact: Lena Ortiz\nApproval Status: Approved",
        "expected": {
            "purchase_order_number": "PO-4500129841",
            "po_date": "2026-04-03",
            "buyer_name": "Prairie Ridge Manufacturing LLC - Des Moines Plant",
            "supplier_name": "Apex Alloy Supply Inc.",
            "ship_to_location": "4100 Foundry Road, Des Moines, IA 50309",
            "requested_delivery_date": "2026-04-24",
            "currency": "USD",
            "payment_terms": "Net 45",
            "incoterms": "FOB Origin",
            "line_items": [
                {"part_number": "AL-6061-BAR", "description": "Aluminum bar stock", "quantity": 1200, "unit": "LB", "unit_price": 4.25, "due_date": "2026-04-24"},
                {"part_number": "ST-4140-PLT", "description": "Steel plate", "quantity": 80, "unit": "EA", "unit_price": 185.0, "due_date": "2026-04-28"},
            ],
            "subtotal_amount": 19900.0,
            "tax_amount": 0.0,
            "total_amount": 19900.0,
            "buyer_contact_name": "Lena Ortiz",
            "approval_status": "Approved",
        },
    },
    {
        "family": "procurement_supply_chain",
        "doc_type": "bill_of_materials",
        "display_name": "Bill of Materials",
        "specialist": "manufacturing bill of materials and product structure control",
        "fields": [
            ("bom_number", "string", True, "BOM number or identifier."),
            ("bom_revision", "string", True, "BOM revision level."),
            ("parent_part_number", "string", True, "Parent assembly or finished good part number."),
            ("parent_part_description", "string", False, "Parent part description."),
            ("effective_date", "date", False, "BOM effective date."),
            ("plant_or_site", "string", False, "Plant, site, or manufacturing location."),
            ("engineering_change_order", "string", False, "Related engineering change order."),
            ("component_items", "array<object>", True, "Component list with part number, quantity, unit, revision, and scrap factor."),
            ("approved_by", "string", False, "Approver name or function."),
            ("approval_date", "date", False, "Approval date."),
            ("bom_status", "string", False, "Released, draft, obsolete, pending, or other status."),
        ],
        "required": ["bom_number", "bom_revision", "parent_part_number", "component_items"],
        "thresholds": ["bom_number", "bom_revision", "parent_part_number", "component_items"],
        "golden_text": "BILL OF MATERIALS\nBOM Number: BOM-FG-2207\nRevision: C\nParent Part: FG-2207 Hydraulic Lift Assembly\nEffective Date: 2026-05-01\nPlant: Des Moines Assembly Cell 4\nEngineering Change Order: ECO-2026-117\nComponents: 10 HYD-CYL-45 cylinder rev B qty 1 EA scrap 0%; 20 BRKT-2207-L bracket left rev C qty 1 EA scrap 1%; 30 BRKT-2207-R bracket right rev C qty 1 EA scrap 1%; 40 BOLT-M12-35 zinc bolt rev A qty 8 EA scrap 2%\nApproved By: Mateo Singh, Manufacturing Engineering\nApproval Date: 2026-04-22\nStatus: Released",
        "expected": {
            "bom_number": "BOM-FG-2207",
            "bom_revision": "C",
            "parent_part_number": "FG-2207",
            "parent_part_description": "Hydraulic Lift Assembly",
            "effective_date": "2026-05-01",
            "plant_or_site": "Des Moines Assembly Cell 4",
            "engineering_change_order": "ECO-2026-117",
            "component_items": [
                {"line": "10", "part_number": "HYD-CYL-45", "description": "cylinder", "revision": "B", "quantity": 1, "unit": "EA", "scrap_factor_percent": 0},
                {"line": "20", "part_number": "BRKT-2207-L", "description": "bracket left", "revision": "C", "quantity": 1, "unit": "EA", "scrap_factor_percent": 1},
                {"line": "30", "part_number": "BRKT-2207-R", "description": "bracket right", "revision": "C", "quantity": 1, "unit": "EA", "scrap_factor_percent": 1},
                {"line": "40", "part_number": "BOLT-M12-35", "description": "zinc bolt", "revision": "A", "quantity": 8, "unit": "EA", "scrap_factor_percent": 2},
            ],
            "approved_by": "Mateo Singh, Manufacturing Engineering",
            "approval_date": "2026-04-22",
            "bom_status": "Released",
        },
    },
    {
        "family": "procurement_supply_chain",
        "doc_type": "receiving_report",
        "display_name": "Receiving Report",
        "specialist": "manufacturing receiving and inventory control",
        "fields": [
            ("receiving_report_number", "string", True, "Receiving report or goods receipt number."),
            ("receipt_date", "date", True, "Date goods were received."),
            ("purchase_order_number", "string", True, "Related purchase order number."),
            ("supplier_name", "string", True, "Supplier name."),
            ("packing_slip_number", "string", False, "Supplier packing slip number."),
            ("carrier_name", "string", False, "Carrier or freight provider."),
            ("received_by", "string", False, "Receiving employee or function."),
            ("line_items_received", "array<object>", True, "Received line items with part, quantity ordered, quantity received, and disposition."),
            ("shortage_or_overage", "string", False, "Shortage, overage, or mismatch summary."),
            ("inspection_required", "boolean", False, "Whether quality inspection is required."),
            ("hold_status", "string", False, "Released, on hold, rejected, pending inspection, or other status."),
        ],
        "required": ["receiving_report_number", "receipt_date", "purchase_order_number", "supplier_name", "line_items_received"],
        "thresholds": ["receiving_report_number", "purchase_order_number", "supplier_name", "line_items_received"],
        "golden_text": "RECEIVING REPORT\nReceipt Number: RR-2026-008144\nReceipt Date: 2026-04-24\nPO Number: PO-4500129841\nSupplier: Apex Alloy Supply Inc.\nPacking Slip: PS-778201\nCarrier: Midwest Freight Lines\nReceived By: Jordan Kim\nLines Received: AL-6061-BAR ordered 1200 LB received 1192 LB disposition pending inspection; ST-4140-PLT ordered 80 EA received 80 EA disposition accepted\nShortage/Overage: aluminum bar stock short 8 LB\nInspection Required: Yes\nHold Status: Pending inspection",
        "expected": {
            "receiving_report_number": "RR-2026-008144",
            "receipt_date": "2026-04-24",
            "purchase_order_number": "PO-4500129841",
            "supplier_name": "Apex Alloy Supply Inc.",
            "packing_slip_number": "PS-778201",
            "carrier_name": "Midwest Freight Lines",
            "received_by": "Jordan Kim",
            "line_items_received": [
                {"part_number": "AL-6061-BAR", "quantity_ordered": 1200, "quantity_received": 1192, "unit": "LB", "disposition": "pending inspection"},
                {"part_number": "ST-4140-PLT", "quantity_ordered": 80, "quantity_received": 80, "unit": "EA", "disposition": "accepted"},
            ],
            "shortage_or_overage": "aluminum bar stock short 8 LB",
            "inspection_required": True,
            "hold_status": "Pending inspection",
        },
    },
    {
        "family": "procurement_supply_chain",
        "doc_type": "supplier_scorecard",
        "display_name": "Supplier Scorecard",
        "specialist": "supplier performance and quality management",
        "fields": [
            ("scorecard_period", "string", True, "Reporting period."),
            ("supplier_name", "string", True, "Supplier name."),
            ("supplier_id", "string", False, "Supplier identifier."),
            ("commodity_category", "string", False, "Commodity, material group, or category."),
            ("on_time_delivery_rate", "number", True, "On-time delivery rate percentage."),
            ("quality_ppm", "number", True, "Defective parts per million or quality PPM."),
            ("nonconformance_count", "integer", False, "Number of nonconformances."),
            ("cost_variance_percent", "number", False, "Cost variance percentage."),
            ("responsiveness_rating", "string", False, "Responsiveness rating."),
            ("overall_score", "number", True, "Overall score."),
            ("supplier_tier", "string", False, "Preferred, approved, conditional, probation, disqualified, or other tier."),
            ("corrective_actions_open", "array<string>", False, "Open corrective actions."),
            ("review_owner", "string", False, "Owner of supplier review."),
            ("next_review_date", "date", False, "Next review date."),
        ],
        "required": ["scorecard_period", "supplier_name", "on_time_delivery_rate", "quality_ppm", "overall_score"],
        "thresholds": ["supplier_name", "on_time_delivery_rate", "quality_ppm", "overall_score"],
        "golden_text": "SUPPLIER SCORECARD\nPeriod: Q2 2026\nSupplier: Apex Alloy Supply Inc.\nSupplier ID: SUP-10442\nCommodity: Raw metals\nOn-Time Delivery: 92.4%\nQuality PPM: 185\nNonconformances: 3\nCost Variance: 1.8%\nResponsiveness: Satisfactory\nOverall Score: 86.5\nSupplier Tier: Approved - watch\nOpen Corrective Actions: SCAR-2026-014 late certificate submissions; SCAR-2026-021 aluminum dimensional variance\nReview Owner: Lena Ortiz\nNext Review Date: 2026-10-15",
        "expected": {
            "scorecard_period": "Q2 2026",
            "supplier_name": "Apex Alloy Supply Inc.",
            "supplier_id": "SUP-10442",
            "commodity_category": "Raw metals",
            "on_time_delivery_rate": 92.4,
            "quality_ppm": 185.0,
            "nonconformance_count": 3,
            "cost_variance_percent": 1.8,
            "responsiveness_rating": "Satisfactory",
            "overall_score": 86.5,
            "supplier_tier": "Approved - watch",
            "corrective_actions_open": ["SCAR-2026-014 late certificate submissions", "SCAR-2026-021 aluminum dimensional variance"],
            "review_owner": "Lena Ortiz",
            "next_review_date": "2026-10-15",
        },
    },
    {
        "family": "manufacturing_quality",
        "doc_type": "quality_inspection_report",
        "display_name": "Quality Inspection Report",
        "specialist": "manufacturing quality inspection and release",
        "fields": [
            ("inspection_report_number", "string", True, "Inspection report number."),
            ("inspection_date", "date", True, "Inspection date."),
            ("part_number", "string", True, "Part number inspected."),
            ("part_revision", "string", False, "Part revision."),
            ("lot_number", "string", True, "Lot, batch, or serial group inspected."),
            ("supplier_or_work_center", "string", False, "Supplier, work center, or production cell."),
            ("sample_size", "integer", False, "Sample size inspected."),
            ("inspection_characteristics", "array<object>", True, "Measured characteristics with specification, result, and disposition."),
            ("defect_count", "integer", False, "Count of defects found."),
            ("overall_disposition", "string", True, "Accepted, rejected, rework, use-as-is, or other disposition."),
            ("inspector_name", "string", False, "Inspector name."),
            ("approval_name", "string", False, "Quality approver name."),
        ],
        "required": ["inspection_report_number", "inspection_date", "part_number", "lot_number", "inspection_characteristics", "overall_disposition"],
        "thresholds": ["inspection_report_number", "part_number", "lot_number", "overall_disposition"],
        "golden_text": "QUALITY INSPECTION REPORT\nReport Number: QIR-2026-5510\nInspection Date: 2026-04-25\nPart Number: AL-6061-BAR\nRevision: A\nLot Number: LOT-AAS-042426-7\nSupplier/Work Center: Apex Alloy Supply Inc.\nSample Size: 32\nCharacteristics: outside diameter spec 1.250 +/- 0.005 in result pass; surface finish spec 63 Ra result pass; material cert match spec required result pass\nDefect Count: 0\nOverall Disposition: Accepted\nInspector: Priya Menon\nQuality Approval: Carlos Rivera",
        "expected": {
            "inspection_report_number": "QIR-2026-5510",
            "inspection_date": "2026-04-25",
            "part_number": "AL-6061-BAR",
            "part_revision": "A",
            "lot_number": "LOT-AAS-042426-7",
            "supplier_or_work_center": "Apex Alloy Supply Inc.",
            "sample_size": 32,
            "inspection_characteristics": [
                {"characteristic": "outside diameter", "specification": "1.250 +/- 0.005 in", "result": "pass"},
                {"characteristic": "surface finish", "specification": "63 Ra", "result": "pass"},
                {"characteristic": "material cert match", "specification": "required", "result": "pass"},
            ],
            "defect_count": 0,
            "overall_disposition": "Accepted",
            "inspector_name": "Priya Menon",
            "approval_name": "Carlos Rivera",
        },
    },
    {
        "family": "manufacturing_quality",
        "doc_type": "certificate_of_analysis",
        "display_name": "Certificate of Analysis",
        "specialist": "material certification and certificate of analysis review",
        "fields": [
            ("certificate_number", "string", True, "Certificate of analysis number."),
            ("certificate_date", "date", True, "Certificate date."),
            ("supplier_name", "string", True, "Supplier or manufacturer."),
            ("material_name", "string", True, "Material or product name."),
            ("part_or_material_number", "string", False, "Part, material, or item number."),
            ("lot_number", "string", True, "Lot, batch, heat, or serial number."),
            ("specification_standard", "string", False, "Specification or standard referenced."),
            ("test_results", "array<object>", True, "Test results with analyte or characteristic, method, result, unit, and limit."),
            ("manufacture_date", "date", False, "Manufacture date."),
            ("expiration_date", "date", False, "Expiration or retest date."),
            ("authorized_signer", "string", False, "Authorized signer."),
            ("coa_disposition", "string", False, "Conforms, accepted, rejected, or other disposition."),
        ],
        "required": ["certificate_number", "certificate_date", "supplier_name", "material_name", "lot_number", "test_results"],
        "thresholds": ["certificate_number", "supplier_name", "lot_number", "test_results"],
        "golden_text": "CERTIFICATE OF ANALYSIS\nCertificate Number: COA-778201-A\nCertificate Date: 2026-04-22\nSupplier: Apex Alloy Supply Inc.\nMaterial: 6061-T6 Aluminum Bar Stock\nMaterial Number: AL-6061-BAR\nLot/Heat: LOT-AAS-042426-7\nSpecification: ASTM B221\nResults: Si method ASTM E1251 result 0.62 percent limit 0.40-0.80; Mg method ASTM E1251 result 1.02 percent limit 0.80-1.20; Tensile Strength method ASTM E8 result 45 ksi limit min 42 ksi\nManufacture Date: 2026-04-18\nExpiration/Retest: 2028-04-18\nAuthorized Signer: N. Patel, Quality Manager\nDisposition: Conforms",
        "expected": {
            "certificate_number": "COA-778201-A",
            "certificate_date": "2026-04-22",
            "supplier_name": "Apex Alloy Supply Inc.",
            "material_name": "6061-T6 Aluminum Bar Stock",
            "part_or_material_number": "AL-6061-BAR",
            "lot_number": "LOT-AAS-042426-7",
            "specification_standard": "ASTM B221",
            "test_results": [
                {"characteristic": "Si", "method": "ASTM E1251", "result": 0.62, "unit": "percent", "limit": "0.40-0.80"},
                {"characteristic": "Mg", "method": "ASTM E1251", "result": 1.02, "unit": "percent", "limit": "0.80-1.20"},
                {"characteristic": "Tensile Strength", "method": "ASTM E8", "result": 45, "unit": "ksi", "limit": "min 42 ksi"},
            ],
            "manufacture_date": "2026-04-18",
            "expiration_date": "2028-04-18",
            "authorized_signer": "N. Patel, Quality Manager",
            "coa_disposition": "Conforms",
        },
    },
    {
        "family": "manufacturing_quality",
        "doc_type": "nonconformance_report",
        "display_name": "Nonconformance Report",
        "specialist": "manufacturing nonconformance and material review board workflows",
        "fields": [
            ("ncr_number", "string", True, "Nonconformance report number."),
            ("ncr_date", "date", True, "Date the nonconformance was opened."),
            ("part_number", "string", True, "Affected part number."),
            ("lot_number", "string", False, "Affected lot, batch, serial, or work order."),
            ("supplier_or_work_center", "string", False, "Supplier or internal work center."),
            ("nonconformance_description", "string", True, "Description of nonconformance."),
            ("detected_by", "string", False, "Person, station, inspection, or process that detected the issue."),
            ("quantity_affected", "number", False, "Quantity affected."),
            ("containment_actions", "array<string>", False, "Containment actions taken."),
            ("root_cause_summary", "string", False, "Root cause summary if known."),
            ("disposition", "string", True, "Scrap, rework, repair, use-as-is, return to supplier, or other disposition."),
            ("mrb_owner", "string", False, "Material review board owner or approver."),
            ("closure_date", "date", False, "Closure date."),
            ("status", "string", False, "Open, in review, closed, overdue, or other status."),
        ],
        "required": ["ncr_number", "ncr_date", "part_number", "nonconformance_description", "disposition"],
        "thresholds": ["ncr_number", "part_number", "nonconformance_description", "disposition"],
        "golden_text": "NONCONFORMANCE REPORT\nNCR Number: NCR-2026-0338\nOpened Date: 2026-05-02\nPart Number: BRKT-2207-L\nLot Number: LOT-PRM-050126-2\nSupplier/Work Center: Press Cell 2\nDescription: mounting hole diameter measured 0.018 inch oversize on sampled brackets\nDetected By: final inspection station QI-4\nQuantity Affected: 46\nContainment Actions: quarantined lot; stopped press cell; notified production supervisor\nRoot Cause: worn punch tooling exceeded preventive maintenance interval\nDisposition: Rework\nMRB Owner: Carlos Rivera\nClosure Date: 2026-05-06\nStatus: Closed",
        "expected": {
            "ncr_number": "NCR-2026-0338",
            "ncr_date": "2026-05-02",
            "part_number": "BRKT-2207-L",
            "lot_number": "LOT-PRM-050126-2",
            "supplier_or_work_center": "Press Cell 2",
            "nonconformance_description": "mounting hole diameter measured 0.018 inch oversize on sampled brackets",
            "detected_by": "final inspection station QI-4",
            "quantity_affected": 46,
            "containment_actions": ["quarantined lot", "stopped press cell", "notified production supervisor"],
            "root_cause_summary": "worn punch tooling exceeded preventive maintenance interval",
            "disposition": "Rework",
            "mrb_owner": "Carlos Rivera",
            "closure_date": "2026-05-06",
            "status": "Closed",
        },
    },
    {
        "family": "manufacturing_quality",
        "doc_type": "corrective_preventive_action",
        "display_name": "Corrective Preventive Action",
        "specialist": "CAPA and manufacturing quality remediation",
        "fields": [
            ("capa_number", "string", True, "CAPA number."),
            ("opened_date", "date", True, "Date CAPA was opened."),
            ("source_type", "string", False, "Audit, NCR, customer complaint, supplier issue, trend, or other source."),
            ("source_reference", "string", False, "Source record identifier."),
            ("problem_statement", "string", True, "Problem statement."),
            ("risk_level", "string", False, "Risk level or severity."),
            ("root_cause", "string", True, "Root cause."),
            ("corrective_actions", "array<string>", False, "Corrective actions."),
            ("preventive_actions", "array<string>", False, "Preventive actions."),
            ("owner_name", "string", True, "CAPA owner."),
            ("target_completion_date", "date", True, "Target completion date."),
            ("effectiveness_check_plan", "string", False, "Effectiveness check plan."),
            ("effectiveness_due_date", "date", False, "Effectiveness check due date."),
            ("capa_status", "string", False, "Open, implemented, pending effectiveness, closed, overdue, or other status."),
            ("closure_date", "date", False, "Closure date."),
        ],
        "required": ["capa_number", "opened_date", "problem_statement", "root_cause", "owner_name", "target_completion_date"],
        "thresholds": ["capa_number", "problem_statement", "root_cause", "owner_name", "target_completion_date"],
        "golden_text": "CORRECTIVE PREVENTIVE ACTION\nCAPA Number: CAPA-2026-019\nOpened Date: 2026-05-07\nSource Type: Nonconformance trend\nSource Reference: NCR-2026-0338; NCR-2026-0341\nProblem Statement: repeated oversize mounting holes on BRKT-2207 bracket family\nRisk Level: Medium\nRoot Cause: punch tooling preventive maintenance interval not aligned with actual wear rate\nCorrective Actions: replace punch tooling; rework affected lots; update inspection sampling for next 5 lots\nPreventive Actions: reduce PM interval from 20,000 to 12,000 cycles; add tooling wear check to setup checklist; train press operators\nOwner: Mateo Singh\nTarget Completion Date: 2026-06-15\nEffectiveness Check Plan: verify zero repeat NCRs for three consecutive production lots\nEffectiveness Due Date: 2026-08-15\nStatus: Pending effectiveness\nClosure Date:",
        "expected": {
            "capa_number": "CAPA-2026-019",
            "opened_date": "2026-05-07",
            "source_type": "Nonconformance trend",
            "source_reference": "NCR-2026-0338; NCR-2026-0341",
            "problem_statement": "repeated oversize mounting holes on BRKT-2207 bracket family",
            "risk_level": "Medium",
            "root_cause": "punch tooling preventive maintenance interval not aligned with actual wear rate",
            "corrective_actions": ["replace punch tooling", "rework affected lots", "update inspection sampling for next 5 lots"],
            "preventive_actions": ["reduce PM interval from 20,000 to 12,000 cycles", "add tooling wear check to setup checklist", "train press operators"],
            "owner_name": "Mateo Singh",
            "target_completion_date": "2026-06-15",
            "effectiveness_check_plan": "verify zero repeat NCRs for three consecutive production lots",
            "effectiveness_due_date": "2026-08-15",
            "capa_status": "Pending effectiveness",
            "closure_date": None,
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
    "schema_version": "manufacturing_{schema['doc_type']}_v1",
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
        "vertical": "manufacturing",
        "family": schema["family"],
        "schema_version": f"manufacturing_{schema['doc_type']}_v1",
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
        bundle = SCHEMAS_ROOT / "manufacturing" / schema["doc_type"]
        prompt_path = PROMPT_ROOT / "manufacturing" / schema["doc_type"] / "prompt_v1.txt"
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
            f"{schema['display_name']} documents combine manufacturing, "
            "quality, supplier, material, and operational control context."
        )
        (bundle / "model_routing.json").write_text(
            json.dumps(routing, indent=2) + "\n",
            encoding="utf-8",
        )
        (bundle / "golden_tests" / "test_001.json").write_text(
            json.dumps(golden_test(schema), indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Wrote {len(SCHEMAS)} manufacturing schema bundles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
