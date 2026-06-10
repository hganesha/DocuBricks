#!/usr/bin/env python3
"""Generate oil and gas energy schema bundles."""

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
        "family": "energy_upstream_operations",
        "doc_type": "daily_drilling_report",
        "display_name": "Daily Drilling Report",
        "specialist": "oil and gas drilling operations and daily rig reporting",
        "fields": [
            ("report_date", "date", True, "Date covered by the daily drilling report."),
            ("well_name", "string", True, "Well name and number."),
            ("api_well_number", "string", False, "API well number or other regulatory well identifier."),
            ("operator_name", "string", True, "Operating company."),
            ("rig_name", "string", True, "Rig name or rig number."),
            ("contractor_name", "string", False, "Drilling contractor or rig contractor."),
            ("location", "string", False, "County, state, block, lease, or offshore location."),
            ("measured_depth", "number", True, "Measured depth at report cutoff."),
            ("true_vertical_depth", "number", False, "True vertical depth at report cutoff."),
            ("daily_footage", "number", False, "Footage drilled during the reporting period."),
            ("hole_size", "string", False, "Hole size for current interval."),
            ("mud_weight", "number", False, "Mud weight in pounds per gallon when stated."),
            ("casing_status", "string", False, "Casing, cementing, or liner status."),
            ("operations_summary", "string", True, "Narrative summary of rig operations for the reporting day."),
            ("downtime_hours", "number", False, "Non-productive time or downtime hours."),
            ("safety_incidents", "integer", False, "Count of safety incidents for the day."),
            ("hse_summary", "string", False, "HSE notes or safety summary."),
            ("daily_cost", "number", False, "Estimated or reported daily drilling cost."),
            ("company_representative", "string", False, "Company man, drilling supervisor, or report approver."),
        ],
        "required": ["report_date", "well_name", "operator_name", "rig_name", "measured_depth", "operations_summary"],
        "thresholds": ["report_date", "well_name", "operator_name", "rig_name", "measured_depth", "operations_summary"],
        "golden_text": "DAILY DRILLING REPORT\nReport Date: 2026-05-18\nWell: Wolf Creek 12-7H\nAPI Number: 42-301-44881\nOperator: Prairie Basin Energy LLC\nRig: Frontier Rig 24\nContractor: Frontier Drilling Services\nLocation: Reeves County, Texas\nMeasured Depth: 12480 ft\nTrue Vertical Depth: 9140 ft\nDaily Footage: 610 ft\nHole Size: 8.5 in\nMud Weight: 12.4 ppg\nCasing Status: drilling lateral section, 9-5/8 casing cemented at 9120 ft\nOperations Summary: drilled from 11870 ft to 12480 ft, surveyed, circulated bottoms up, and performed BOP function test\nDowntime Hours: 1.5\nSafety Incidents: 0\nHSE Summary: pre-tour safety meeting completed; no spills or injuries\nDaily Cost: $187500\nCompany Representative: Dana Mills",
        "expected": {
            "report_date": "2026-05-18",
            "well_name": "Wolf Creek 12-7H",
            "api_well_number": "42-301-44881",
            "operator_name": "Prairie Basin Energy LLC",
            "rig_name": "Frontier Rig 24",
            "contractor_name": "Frontier Drilling Services",
            "location": "Reeves County, Texas",
            "measured_depth": 12480.0,
            "true_vertical_depth": 9140.0,
            "daily_footage": 610.0,
            "hole_size": "8.5 in",
            "mud_weight": 12.4,
            "casing_status": "drilling lateral section, 9-5/8 casing cemented at 9120 ft",
            "operations_summary": "drilled from 11870 ft to 12480 ft, surveyed, circulated bottoms up, and performed BOP function test",
            "downtime_hours": 1.5,
            "safety_incidents": 0,
            "hse_summary": "pre-tour safety meeting completed; no spills or injuries",
            "daily_cost": 187500.0,
            "company_representative": "Dana Mills",
        },
    },
    {
        "family": "energy_upstream_operations",
        "doc_type": "well_completion_report",
        "display_name": "Well Completion Report",
        "specialist": "oil and gas well completion and regulatory completion reporting",
        "fields": [
            ("completion_date", "date", True, "Date completion operations finished or report was signed."),
            ("well_name", "string", True, "Well name and number."),
            ("api_well_number", "string", True, "API well number or regulatory well identifier."),
            ("operator_name", "string", True, "Operating company."),
            ("field_name", "string", False, "Field, pool, or reservoir name."),
            ("formation", "string", False, "Producing formation or target zone."),
            ("completion_type", "string", True, "Completion type such as hydraulic fracture, open hole, perforated casing, or recompletion."),
            ("total_depth", "number", False, "Total measured depth."),
            ("perforated_intervals", "array<object>", False, "Perforation intervals with top, bottom, stage, and date when available."),
            ("stimulation_summary", "string", False, "Fracturing, acidizing, stimulation, or treatment summary."),
            ("proppant_volume", "number", False, "Total proppant volume."),
            ("fluid_volume", "number", False, "Total stimulation fluid volume."),
            ("initial_oil_rate_bpd", "number", False, "Initial oil production rate in barrels per day."),
            ("initial_gas_rate_mcfpd", "number", False, "Initial gas production rate in thousand cubic feet per day."),
            ("initial_water_rate_bpd", "number", False, "Initial water production rate in barrels per day."),
            ("choke_size", "string", False, "Initial production test choke size."),
            ("contractors", "array<string>", False, "Completion, cementing, logging, or stimulation contractors."),
            ("regulatory_filing_status", "string", False, "Filed, pending, rejected, amended, or other filing status."),
        ],
        "required": ["completion_date", "well_name", "api_well_number", "operator_name", "completion_type"],
        "thresholds": ["completion_date", "well_name", "api_well_number", "operator_name", "completion_type"],
        "golden_text": "WELL COMPLETION REPORT\nCompletion Date: 2026-06-02\nWell: Wolf Creek 12-7H\nAPI Number: 42-301-44881\nOperator: Prairie Basin Energy LLC\nField: Wolf Creek\nFormation: Wolfcamp B\nCompletion Type: perforated casing hydraulic fracture\nTotal Depth: 20140 ft\nPerforated Intervals: stage 1 top 10210 ft bottom 10480 ft date 2026-05-24; stage 2 top 10490 ft bottom 10765 ft date 2026-05-25\nStimulation Summary: 42-stage slickwater fracture treatment completed without screenout\nProppant Volume: 12800000 lb\nFluid Volume: 315000 bbl\nInitial Oil Rate: 842 BPD\nInitial Gas Rate: 1190 MCFD\nInitial Water Rate: 620 BPD\nChoke Size: 24/64 in\nContractors: HighMesa Pressure Pumping; Basin Wireline; SureCem Cementing\nRegulatory Filing Status: Pending",
        "expected": {
            "completion_date": "2026-06-02",
            "well_name": "Wolf Creek 12-7H",
            "api_well_number": "42-301-44881",
            "operator_name": "Prairie Basin Energy LLC",
            "field_name": "Wolf Creek",
            "formation": "Wolfcamp B",
            "completion_type": "perforated casing hydraulic fracture",
            "total_depth": 20140.0,
            "perforated_intervals": [
                {"stage": "1", "top_depth": 10210, "bottom_depth": 10480, "date": "2026-05-24"},
                {"stage": "2", "top_depth": 10490, "bottom_depth": 10765, "date": "2026-05-25"},
            ],
            "stimulation_summary": "42-stage slickwater fracture treatment completed without screenout",
            "proppant_volume": 12800000.0,
            "fluid_volume": 315000.0,
            "initial_oil_rate_bpd": 842.0,
            "initial_gas_rate_mcfpd": 1190.0,
            "initial_water_rate_bpd": 620.0,
            "choke_size": "24/64 in",
            "contractors": ["HighMesa Pressure Pumping", "Basin Wireline", "SureCem Cementing"],
            "regulatory_filing_status": "Pending",
        },
    },
    {
        "family": "energy_production_operations",
        "doc_type": "production_report",
        "display_name": "Production Report",
        "specialist": "oil and gas production operations and lease reporting",
        "fields": [
            ("production_date", "date", True, "Production date or reporting period end date."),
            ("lease_name", "string", True, "Lease, unit, or facility name."),
            ("operator_name", "string", True, "Operating company."),
            ("well_count", "integer", False, "Number of wells included in the report."),
            ("oil_volume_bbl", "number", True, "Oil production volume in barrels."),
            ("gas_volume_mcf", "number", True, "Gas production volume in thousand cubic feet."),
            ("water_volume_bbl", "number", False, "Produced water volume in barrels."),
            ("ngl_volume_bbl", "number", False, "Natural gas liquids volume in barrels."),
            ("beginning_inventory_bbl", "number", False, "Beginning tank or lease oil inventory."),
            ("ending_inventory_bbl", "number", False, "Ending tank or lease oil inventory."),
            ("sales_volume_bbl", "number", False, "Oil or liquids sales volume."),
            ("flared_gas_mcf", "number", False, "Gas flared volume."),
            ("downtime_hours", "number", False, "Production downtime hours."),
            ("downtime_reason", "string", False, "Reason for downtime or shut-in status."),
            ("purchaser_name", "string", False, "Purchaser, gatherer, or transporter."),
            ("report_preparer", "string", False, "Person or role preparing the report."),
        ],
        "required": ["production_date", "lease_name", "operator_name", "oil_volume_bbl", "gas_volume_mcf"],
        "thresholds": ["production_date", "lease_name", "operator_name", "oil_volume_bbl", "gas_volume_mcf"],
        "golden_text": "PRODUCTION REPORT\nProduction Date: 2026-05-31\nLease/Unit: Wolf Creek Unit\nOperator: Prairie Basin Energy LLC\nWell Count: 14\nOil Produced: 18420 bbl\nGas Produced: 28650 mcf\nWater Produced: 12110 bbl\nNGL Produced: 0 bbl\nBeginning Inventory: 5120 bbl\nEnding Inventory: 4875 bbl\nSales Volume: 18665 bbl\nFlared Gas: 42 mcf\nDowntime Hours: 9.0\nDowntime Reason: compressor maintenance on central facility\nPurchaser: Red River Crude Marketing\nPrepared By: Luis Ortega",
        "expected": {
            "production_date": "2026-05-31",
            "lease_name": "Wolf Creek Unit",
            "operator_name": "Prairie Basin Energy LLC",
            "well_count": 14,
            "oil_volume_bbl": 18420.0,
            "gas_volume_mcf": 28650.0,
            "water_volume_bbl": 12110.0,
            "ngl_volume_bbl": 0.0,
            "beginning_inventory_bbl": 5120.0,
            "ending_inventory_bbl": 4875.0,
            "sales_volume_bbl": 18665.0,
            "flared_gas_mcf": 42.0,
            "downtime_hours": 9.0,
            "downtime_reason": "compressor maintenance on central facility",
            "purchaser_name": "Red River Crude Marketing",
            "report_preparer": "Luis Ortega",
        },
    },
    {
        "family": "energy_field_services",
        "doc_type": "field_ticket",
        "display_name": "Field Ticket",
        "specialist": "oilfield service tickets, field labor, equipment, and materials",
        "fields": [
            ("ticket_number", "string", True, "Field ticket number."),
            ("service_date", "date", True, "Date service was performed."),
            ("operator_name", "string", True, "Customer or operating company."),
            ("service_company_name", "string", True, "Service provider issuing the ticket."),
            ("well_name", "string", False, "Well, pad, lease, or facility serviced."),
            ("location", "string", False, "Service location."),
            ("job_type", "string", True, "Type of service performed."),
            ("job_description", "string", False, "Narrative description of the work performed."),
            ("labor_lines", "array<object>", False, "Labor charges with role, hours, rate, and amount."),
            ("equipment_lines", "array<object>", False, "Equipment charges with unit, hours, rate, and amount."),
            ("material_lines", "array<object>", False, "Material charges with item, quantity, unit price, and amount."),
            ("subtotal_amount", "number", False, "Subtotal before tax or fees."),
            ("tax_amount", "number", False, "Tax amount."),
            ("total_amount", "number", True, "Total field ticket amount."),
            ("customer_representative", "string", False, "Customer approver or company representative."),
            ("service_supervisor", "string", False, "Service company supervisor."),
            ("approval_status", "string", False, "Signed, pending, disputed, rejected, or other approval status."),
        ],
        "required": ["ticket_number", "service_date", "operator_name", "service_company_name", "job_type", "total_amount"],
        "thresholds": ["ticket_number", "service_date", "operator_name", "service_company_name", "job_type", "total_amount"],
        "golden_text": "FIELD TICKET\nTicket Number: FT-778244\nService Date: 2026-05-19\nCustomer: Prairie Basin Energy LLC\nService Company: HighMesa Pressure Pumping\nWell: Wolf Creek 12-7H\nLocation: Reeves County, Texas\nJob Type: pump down support\nJob Description: provided pump down pumps, operators, and chemical additive for wireline perforating stages\nLabor: pump operator 12 hr rate 95 amount 1140; field supervisor 12 hr rate 125 amount 1500\nEquipment: pump unit PU-19 12 hr rate 450 amount 5400; blender BL-4 12 hr rate 375 amount 4500\nMaterials: friction reducer 180 gal unit price 18.50 amount 3330\nSubtotal: $15870.00\nTax: $0.00\nTotal: $15870.00\nCustomer Representative: Dana Mills\nService Supervisor: Caleb Nguyen\nApproval Status: Signed",
        "expected": {
            "ticket_number": "FT-778244",
            "service_date": "2026-05-19",
            "operator_name": "Prairie Basin Energy LLC",
            "service_company_name": "HighMesa Pressure Pumping",
            "well_name": "Wolf Creek 12-7H",
            "location": "Reeves County, Texas",
            "job_type": "pump down support",
            "job_description": "provided pump down pumps, operators, and chemical additive for wireline perforating stages",
            "labor_lines": [
                {"role": "pump operator", "hours": 12, "rate": 95, "amount": 1140},
                {"role": "field supervisor", "hours": 12, "rate": 125, "amount": 1500},
            ],
            "equipment_lines": [
                {"unit": "pump unit PU-19", "hours": 12, "rate": 450, "amount": 5400},
                {"unit": "blender BL-4", "hours": 12, "rate": 375, "amount": 4500},
            ],
            "material_lines": [
                {"item": "friction reducer", "quantity": 180, "unit": "gal", "unit_price": 18.5, "amount": 3330},
            ],
            "subtotal_amount": 15870.0,
            "tax_amount": 0.0,
            "total_amount": 15870.0,
            "customer_representative": "Dana Mills",
            "service_supervisor": "Caleb Nguyen",
            "approval_status": "Signed",
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
    "schema_version": "energy_{schema['doc_type']}_v1",
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
        "vertical": "energy",
        "family": schema["family"],
        "schema_version": f"energy_{schema['doc_type']}_v1",
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
        bundle = SCHEMAS_ROOT / "energy" / schema["doc_type"]
        prompt_path = PROMPT_ROOT / "energy" / schema["doc_type"] / "prompt_v1.txt"
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
            f"{schema['display_name']} documents combine upstream operations, "
            "production accounting, field services, HSE, and lease control context."
        )
        (bundle / "model_routing.json").write_text(
            json.dumps(routing, indent=2) + "\n",
            encoding="utf-8",
        )
        (bundle / "golden_tests" / "test_001.json").write_text(
            json.dumps(golden_test(schema), indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Wrote {len(SCHEMAS)} energy schema bundles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
