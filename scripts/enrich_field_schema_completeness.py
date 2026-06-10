#!/usr/bin/env python3
"""Add sections, field categories, and nested array item schemas to fields.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_ROOT = REPO_ROOT / "Schemas"
CATALOG_PATH = SCHEMAS_ROOT / "schema_catalog.json"


CATEGORY_KEYWORDS = {
    "identity": (
        "name",
        "party",
        "borrower",
        "lender",
        "tenant",
        "landlord",
        "buyer",
        "seller",
        "supplier",
        "customer",
        "operator",
        "insured",
        "claimant",
        "provider",
        "patient",
        "owner",
        "manager",
        "grantor",
        "grantee",
        "signer",
        "approver",
    ),
    "financial": (
        "amount",
        "price",
        "rent",
        "revenue",
        "cost",
        "fee",
        "premium",
        "payment",
        "proceeds",
        "deposit",
        "value",
        "rate",
        "balance",
        "subtotal",
        "tax",
        "total",
        "loan",
        "cash",
        "reserve",
        "arrears",
        "delinquent",
    ),
    "temporal": ("date", "time", "period", "term", "deadline", "due", "maturity", "expiration", "start", "end"),
    "regulatory": ("regulatory", "compliance", "filing", "policy", "coverage", "covenant", "lien", "perfection", "notice"),
    "operational": (
        "status",
        "summary",
        "description",
        "items",
        "entries",
        "lines",
        "actions",
        "documents",
        "requirements",
        "exceptions",
        "equipment",
        "materials",
        "operations",
        "production",
        "inspection",
        "component",
        "collateral",
    ),
}


SECTION_BY_KEYWORD = (
    ("parties", ("name", "party", "borrower", "lender", "tenant", "landlord", "buyer", "seller", "supplier", "customer", "operator", "insured", "claimant", "owner", "manager", "grantor", "grantee")),
    ("property_or_asset", ("property", "premises", "collateral", "asset", "well", "lease_or_well", "location", "address", "legal_description", "part_number", "material", "lot_number")),
    ("dates_and_terms", ("date", "period", "term", "deadline", "due", "maturity", "expiration", "start", "end", "renewal", "notice_days")),
    ("financials", ("amount", "price", "rent", "fee", "premium", "cost", "value", "rate", "payment", "proceeds", "deposit", "tax", "total", "subtotal", "loan", "cash", "reserve", "arrears")),
    ("line_items", ("items", "entries", "lines", "component", "materials", "documents", "requirements", "exceptions", "actions", "payoffs", "prorations", "charges")),
    ("risk_and_compliance", ("status", "rating", "risk", "coverage", "policy", "lien", "perfection", "regulatory", "compliance", "approval", "disposition", "default")),
)


ITEM_SCHEMA_OVERRIDES: dict[tuple[str, str, str], list[dict[str, Any]]] = {
    ("fs", "collateral_schedule", "collateral_items"): [
        {"name": "asset_id", "type": "string", "description": "Unique asset, collateral, VIN, serial, parcel, or internal identifier."},
        {"name": "asset_type", "type": "string", "description": "Collateral type such as equipment, inventory, receivable, vehicle, real estate, cash, or securities."},
        {"name": "asset_description", "type": "string", "description": "Specific asset or collateral description."},
        {"name": "owner_name", "type": "string", "description": "Owner or pledgor of the asset."},
        {"name": "location", "type": "string", "description": "Physical or custodial location of the asset."},
        {"name": "value_amount", "type": "number", "description": "Stated value for the asset."},
        {"name": "valuation_date", "type": "date", "description": "Date of valuation or appraisal."},
        {"name": "lien_position", "type": "string", "description": "Lien priority for the asset."},
        {"name": "perfection_status", "type": "string", "description": "Perfected, unperfected, pending, expired, or unknown perfection status."},
        {"name": "insurance_status", "type": "string", "description": "Insurance coverage status if stated."},
    ],
    ("real_estate", "rent_roll", "tenant_entries"): [
        {"name": "unit_or_suite", "type": "string", "description": "Unit, suite, space, or apartment identifier."},
        {"name": "tenant_name", "type": "string", "description": "Tenant name."},
        {"name": "lease_start_date", "type": "date", "description": "Lease start date."},
        {"name": "lease_end_date", "type": "date", "description": "Lease end date."},
        {"name": "area_sq_ft", "type": "number", "description": "Leased area in square feet."},
        {"name": "monthly_rent_amount", "type": "number", "description": "Monthly rent amount."},
        {"name": "arrears_amount", "type": "number", "description": "Past-due or delinquent amount."},
        {"name": "security_deposit_amount", "type": "number", "description": "Security deposit amount if stated."},
    ],
    ("manufacturing", "purchase_order", "line_items"): [
        {"name": "line_number", "type": "string", "description": "Purchase order line number."},
        {"name": "part_number", "type": "string", "description": "Part, SKU, item, or material number."},
        {"name": "description", "type": "string", "description": "Line item description."},
        {"name": "quantity", "type": "number", "description": "Ordered quantity."},
        {"name": "unit", "type": "string", "description": "Unit of measure."},
        {"name": "unit_price", "type": "number", "description": "Unit price."},
        {"name": "extended_amount", "type": "number", "description": "Line extended amount."},
        {"name": "due_date", "type": "date", "description": "Line requested or promised due date."},
    ],
    ("energy", "field_ticket", "equipment_lines"): [
        {"name": "equipment_id", "type": "string", "description": "Equipment unit, serial, or asset identifier."},
        {"name": "equipment_type", "type": "string", "description": "Equipment type."},
        {"name": "description", "type": "string", "description": "Equipment or service line description."},
        {"name": "hours", "type": "number", "description": "Billable equipment hours."},
        {"name": "rate", "type": "number", "description": "Billing rate."},
        {"name": "amount", "type": "number", "description": "Line amount."},
    ],
}


GENERIC_ITEM_SCHEMAS: dict[str, list[dict[str, str]]] = {
    "line_items": [
        {"name": "line_number", "type": "string", "description": "Line number."},
        {"name": "description", "type": "string", "description": "Line description."},
        {"name": "quantity", "type": "number", "description": "Quantity."},
        {"name": "unit_amount", "type": "number", "description": "Unit amount or price."},
        {"name": "total_amount", "type": "number", "description": "Line total amount."},
    ],
    "tenant_entries": ITEM_SCHEMA_OVERRIDES[("real_estate", "rent_roll", "tenant_entries")],
    "component_items": [
        {"name": "line_number", "type": "string", "description": "BOM line number."},
        {"name": "part_number", "type": "string", "description": "Component part number."},
        {"name": "description", "type": "string", "description": "Component description."},
        {"name": "revision", "type": "string", "description": "Component revision."},
        {"name": "quantity", "type": "number", "description": "Component quantity."},
        {"name": "unit", "type": "string", "description": "Unit of measure."},
    ],
    "test_results": [
        {"name": "characteristic", "type": "string", "description": "Tested analyte or characteristic."},
        {"name": "method", "type": "string", "description": "Test method."},
        {"name": "result", "type": "string", "description": "Reported result."},
        {"name": "unit", "type": "string", "description": "Result unit."},
        {"name": "limit", "type": "string", "description": "Specification limit."},
    ],
    "inspection_characteristics": [
        {"name": "characteristic", "type": "string", "description": "Inspected characteristic."},
        {"name": "specification", "type": "string", "description": "Specification or tolerance."},
        {"name": "measured_value", "type": "string", "description": "Measured value."},
        {"name": "result", "type": "string", "description": "Pass, fail, accepted, rejected, or other result."},
    ],
    "prorations": [
        {"name": "item", "type": "string", "description": "Proration item."},
        {"name": "party_credited", "type": "string", "description": "Credited party."},
        {"name": "party_debited", "type": "string", "description": "Debited party."},
        {"name": "amount", "type": "number", "description": "Proration amount."},
    ],
    "title_charges": [
        {"name": "item", "type": "string", "description": "Title or settlement charge item."},
        {"name": "amount", "type": "number", "description": "Charge amount."},
        {"name": "paid_by", "type": "string", "description": "Party responsible for charge."},
    ],
    "payoffs": [
        {"name": "payee", "type": "string", "description": "Payoff recipient."},
        {"name": "amount", "type": "number", "description": "Payoff amount."},
        {"name": "reference", "type": "string", "description": "Loan, lien, or account reference."},
    ],
    "materials": [
        {"name": "item", "type": "string", "description": "Material or consumable item."},
        {"name": "quantity", "type": "number", "description": "Quantity."},
        {"name": "unit", "type": "string", "description": "Unit of measure."},
        {"name": "unit_price", "type": "number", "description": "Unit price."},
        {"name": "amount", "type": "number", "description": "Material amount."},
    ],
    "equipment_lines": ITEM_SCHEMA_OVERRIDES[("energy", "field_ticket", "equipment_lines")],
}


def _infer_category(name: str, field_type: str) -> str:
    lowered = name.lower()
    if field_type.startswith("array"):
        return "array"
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "descriptive"


def _infer_section(name: str) -> str:
    lowered = name.lower()
    for section, keywords in SECTION_BY_KEYWORD:
        if any(keyword in lowered for keyword in keywords):
            return section
    return "document_details"


def _section_title(section_id: str) -> str:
    return section_id.replace("_", " ").title()


def _item_schema(vertical: str, doc_type: str, field_name: str) -> list[dict[str, Any]]:
    override = ITEM_SCHEMA_OVERRIDES.get((vertical, doc_type, field_name))
    if override is not None:
        return override
    if field_name in GENERIC_ITEM_SCHEMAS:
        return GENERIC_ITEM_SCHEMAS[field_name]
    singular = field_name.removesuffix("s").removesuffix("_items").removesuffix("_entries")
    return [
        {"name": f"{singular}_type", "type": "string", "description": f"Type or class for {field_name} item."},
        {"name": f"{singular}_description", "type": "string", "description": f"Description for {field_name} item."},
        {"name": "amount", "type": "number", "description": "Amount or value when stated."},
        {"name": "date", "type": "date", "description": "Relevant item date when stated."},
        {"name": "status", "type": "string", "description": "Item status or disposition when stated."},
    ]


def _checklist(data: dict[str, Any]) -> list[dict[str, Any]]:
    fields = data.get("fields", [])
    required = [field["name"] for field in fields if field.get("required") is True]
    array_objects = [field["name"] for field in fields if field.get("type") == "array<object>"]
    sections = [section["id"] for section in data.get("sections", [])]
    return [
        {
            "id": "required_fields_present",
            "description": "All required fields are present or explicitly null with low confidence when absent.",
            "fields": required,
        },
        {
            "id": "section_coverage_reviewed",
            "description": "Each declared section was reviewed for extractable evidence.",
            "sections": sections,
        },
        {
            "id": "nested_lists_normalized",
            "description": "Object array fields use their item_schema for consistent nested extraction.",
            "fields": array_objects,
        },
    ]


def enrich_schema(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    vertical = str(data["vertical"])
    doc_type = str(data["document_type"])
    used_sections: dict[str, set[str]] = {}
    changed = False

    for field in data.get("fields", []):
        name = str(field["name"])
        field_type = str(field["type"])
        if field_type == "array" and isinstance(field.get("items"), dict):
            field_type = "array<object>"
            field["type"] = field_type
            field.pop("items", None)
            changed = True
        section = str(field.get("section") or _infer_section(name))
        category = str(field.get("category") or _infer_category(name, field_type))
        if field.get("section") != section:
            field["section"] = section
            changed = True
        if field.get("category") != category:
            field["category"] = category
            changed = True
        used_sections.setdefault(section, set()).add(name)
        if field_type == "array<object>" and not field.get("item_schema"):
            field["item_schema"] = _item_schema(vertical, doc_type, name)
            changed = True

    sections = [
        {
            "id": section_id,
            "title": _section_title(section_id),
            "description": f"{_section_title(section_id)} fields extracted from the document.",
            "fields": sorted(field_names),
        }
        for section_id, field_names in sorted(used_sections.items())
    ]
    if data.get("sections") != sections:
        data["sections"] = sections
        changed = True

    checklist = _checklist(data)
    if data.get("completeness_checklist") != checklist:
        data["completeness_checklist"] = checklist
        changed = True

    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return changed


def available_field_paths() -> list[Path]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    paths = []
    for entry in catalog.get("document_types", []):
        if entry.get("availability") != "available":
            continue
        paths.append(SCHEMAS_ROOT / str(entry["vertical"]) / str(entry["doc_type"]) / "fields.json")
    return paths


def main() -> int:
    changed = 0
    for path in available_field_paths():
        if enrich_schema(path):
            print(f"updated {path.relative_to(REPO_ROOT)}")
            changed += 1
    print(f"Enriched {changed} field schema files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
