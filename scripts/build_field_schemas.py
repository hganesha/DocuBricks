#!/usr/bin/env python3
"""Generate machine-readable fields.json files for available schema bundles."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_ROOT = REPO_ROOT / "Schemas"
CATALOG_PATH = SCHEMAS_ROOT / "schema_catalog.json"


FIELD_LINE_RE = re.compile(
    r"^\s*-\s+(?P<name>[a-z][a-z0-9_]*)(?:\s*\((?P<type_hint>[^)]*)\))?\s*(?::|--|—|-)?\s*(?P<description>.*)$"
)
SCHEMA_VERSION_RE = re.compile(r'"schema_version"\s*:\s*"(?P<version>[^"]+)"')


TYPE_HINTS = (
    ("array<object>", ("array<object>", "array of objects", "array<object")),
    ("array<string>", ("array<string>", "array of strings", "array<string>")),
    ("array<number>", ("array<number>", "array of numbers", "array<number>")),
    ("boolean", ("boolean", "bool")),
    ("integer", ("integer", "int")),
    ("number", ("number", "decimal", "amount", "percent", "ratio", "double", "float")),
    ("date", ("date", "yyyy-mm-dd", "iso 8601")),
    ("string", ("string", "text")),
)


def _titleize(name: str) -> str:
    return name.replace("_", " ").capitalize()


def _infer_type(name: str, type_hint: str, description: str) -> str:
    explicit = type_hint.lower()
    if explicit:
        if "array" in explicit and "object" in explicit:
            return "array<object>"
        if "array" in explicit and "number" in explicit:
            return "array<number>"
        if "array" in explicit:
            return "array<string>"
        if "boolean" in explicit or "bool" in explicit:
            return "boolean"
        if "integer" in explicit or explicit == "int":
            return "integer"
        if "number" in explicit or "decimal" in explicit or "float" in explicit:
            return "number"
        if "date" in explicit:
            return "date"
        if "string" in explicit or "text" in explicit:
            return "string"

    lowered_description = description.lower()
    if "array<object>" in lowered_description or "array of objects" in lowered_description:
        return "array<object>"
    if "array<number>" in lowered_description or "array of numbers" in lowered_description:
        return "array<number>"
    if "array<string>" in lowered_description or "array of strings" in lowered_description:
        return "array<string>"
    if lowered_description.startswith("array of ") or " array of " in lowered_description:
        return "array<string>"

    if name.endswith("_date") or name in {"filing_date", "application_date", "memo_date"}:
        return "date"
    if (
        name.endswith("_id")
        or name.endswith("_number")
        or name.endswith("_code")
        or name.endswith("_codes")
        or name.endswith("_phone")
        or "tax_id" in name
        or "ssn" in name
        or "npi" in name
        or name in {"currency", "bar_number", "case_number", "claim_number", "group_number"}
    ):
        if name.endswith("_codes"):
            return "array<string>"
        return "string"
    if name.endswith("_names") or name.endswith("_codes") or name.endswith("_requirements"):
        return "array<string>"
    if name.endswith("_items"):
        return "array<object>"
    if (
        name.startswith("is_")
        or name.startswith("has_")
        or name.endswith("_indicator")
        or name.endswith("_present")
        or name.endswith("_required")
        or name.endswith("_declared")
        or name.endswith("_waiver")
        or name.endswith("_clause")
        or name in {"self_employed", "auto_renew", "jury_demand", "existing_bank_relationship"}
    ):
        return "boolean"
    if name.endswith("_count") or name.endswith("_months") or name == "pages":
        return "integer"
    if any(
        token in name
        for token in (
            "amount",
            "balance",
            "revenue",
            "assets",
            "liabilities",
            "worth",
            "price",
            "value",
            "rate",
            "percent",
            "ratio",
            "income",
            "payment",
            "subtotal",
            "tax",
            "shipping",
            "discount",
            "ltv",
            "cltv",
            "dscr",
            "leverage",
            "liquidity",
        )
    ):
        return "number"
    return "string"


def _parse_prompt_fields(prompt_text: str) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    in_fields_section = False

    for raw_line in prompt_text.splitlines():
        line = raw_line.strip()
        upper = line.upper()
        if "FIELDS TO EXTRACT" in upper or line == "Fields to extract:":
            in_fields_section = True
            continue
        if in_fields_section and (
            "CONFIDENCE SCORING" in upper
            or "EDGE CASES" in upper
            or "OUTPUT FORMAT" in upper
            or line.startswith("{")
        ):
            break
        if not in_fields_section:
            continue

        match = FIELD_LINE_RE.match(raw_line)
        if not match:
            continue
        name = match.group("name")
        if name in seen:
            continue
        seen.add(name)
        type_hint = (match.group("type_hint") or "").strip()
        description = (match.group("description") or "").strip()
        description = description.lstrip("—-: ").strip()
        if not description:
            description = _titleize(name)
        fields.append(
            {
                "name": name,
                "type": _infer_type(name, type_hint, description),
                "required": False,
                "description": description,
            }
        )

    return fields


def _required_fields_from_rules(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        rules = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    if isinstance(rules, dict):
        rules = rules.get("rules", [rules])
    if not isinstance(rules, list):
        return set()

    required: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        severity = str(rule.get("severity", "")).lower()
        if severity not in {"fail", "drop", "error"}:
            continue
        expression = str(rule.get("expression", rule.get("rule_expression", "")))
        for field_name in re.findall(r"\b([a-z][a-z0-9_]*)\s+IS\s+NOT\s+NULL\b", expression):
            required.add(field_name)
    return required


def _schema_version(prompt_text: str, doc_type: str) -> str:
    match = SCHEMA_VERSION_RE.search(prompt_text)
    if match:
        return match.group("version")
    return f"{doc_type}_v1"


def _available_catalog_entries() -> list[dict[str, Any]]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return [
        entry
        for entry in catalog.get("document_types", [])
        if entry.get("availability") == "available"
    ]


def build_field_schema(entry: dict[str, Any]) -> dict[str, Any]:
    doc_type = str(entry["doc_type"])
    vertical = str(entry["vertical"])
    bundle_path = SCHEMAS_ROOT / vertical / doc_type
    prompt_path = SCHEMAS_ROOT / "prompts" / vertical / doc_type / "prompt_v1.txt"
    if not prompt_path.exists():
        prompt_path = bundle_path / "prompt_v1.txt"
    prompt_text = prompt_path.read_text(encoding="utf-8")

    fields = _parse_prompt_fields(prompt_text)
    required = _required_fields_from_rules(bundle_path / "validation_rules.json")
    for field in fields:
        field["required"] = field["name"] in required

    return {
        "document_type": doc_type,
        "vertical": vertical,
        "family": entry.get("family"),
        "schema_version": _schema_version(prompt_text, doc_type),
        "source_prompt": "prompt_v1.txt",
        "output_contract": {
            "fields_object": "extracted_fields",
            "confidence_object": "confidence",
            "metadata_object": "extraction_metadata",
        },
        "fields": fields,
    }


def main() -> int:
    written = 0
    for entry in _available_catalog_entries():
        bundle_path = SCHEMAS_ROOT / str(entry["vertical"]) / str(entry["doc_type"])
        if not (bundle_path / "prompt_v1.txt").exists():
            continue
        field_schema = build_field_schema(entry)
        if not field_schema["fields"]:
            raise ValueError(f"No fields parsed for {bundle_path}")
        (bundle_path / "fields.json").write_text(
            json.dumps(field_schema, indent=2) + "\n",
            encoding="utf-8",
        )
        written += 1
    print(f"Wrote {written} field schema files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
