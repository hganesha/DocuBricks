#!/usr/bin/env python3
"""Validate schema asset coverage required for Phase 4 and Phase 5."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


FS_DOC_TYPES = (
    "mortgage_application",
    "kyc_cdd_form",
    "aml_sar",
    "invoice",
)

COMMERCIAL_LENDING_DOC_TYPES = (
    "commercial_loan_application",
    "commercial_credit_memo",
    "loan_agreement",
    "covenant_compliance_certificate",
    "collateral_schedule",
    "ucc_financing_statement",
    "guaranty_agreement",
    "security_agreement",
)

HEALTHCARE_DOC_TYPES = (
    "eob_cms1500",
    "clinical_note_soap",
    "lab_report",
    "prior_auth",
)

REQUIRED_SCHEMA_FILES = (
    "prompt_v1.txt",
    "validation_rules.json",
    "field_thresholds.json",
    "model_routing.json",
)


@dataclass(frozen=True)
class SchemaCoverageResult:
    ok: bool
    golden_counts: dict[str, int]
    missing: tuple[str, ...]
    warnings: tuple[str, ...]


def _count_goldens(path: Path) -> int:
    golden_dir = path / "golden_tests"
    return len(tuple(golden_dir.glob("test_*.json"))) if golden_dir.exists() else 0


def _validate_json(path: Path, missing: list[str]) -> None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        missing.append(f"{path}: invalid JSON ({exc})")


def _validate_schema_catalog(path: Path, missing: list[str]) -> None:
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        missing.append(f"{path}: invalid JSON ({exc})")
        return

    entries = catalog.get("document_types")
    if not isinstance(entries, list):
        missing.append(f"{path}: document_types must be a list")
        return

    seen: set[str] = set()
    required_fields = {
        "vertical",
        "family",
        "doc_type",
        "display_name",
        "availability",
    }
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            missing.append(f"{path}: document_types[{index}] must be an object")
            continue
        missing_fields = sorted(required_fields - set(entry))
        if missing_fields:
            missing.append(
                f"{path}: document_types[{index}] missing fields: {', '.join(missing_fields)}"
            )
        doc_type = str(entry.get("doc_type", ""))
        if doc_type in seen:
            missing.append(f"{path}: duplicate doc_type '{doc_type}'")
        elif doc_type:
            seen.add(doc_type)
        availability = entry.get("availability")
        if availability not in {"available", "future"}:
            missing.append(
                f"{path}: doc_type '{doc_type or index}' has invalid availability '{availability}'"
            )


def _validate_field_schema(
    path: Path,
    missing: list[str],
    *,
    expected_doc_type: str,
    expected_vertical: str,
) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        missing.append(f"{path}: invalid JSON ({exc})")
        return

    if data.get("document_type") != expected_doc_type:
        missing.append(
            f"{path}: document_type '{data.get('document_type')}' does not match '{expected_doc_type}'"
        )
    if data.get("vertical") != expected_vertical:
        missing.append(
            f"{path}: vertical '{data.get('vertical')}' does not match '{expected_vertical}'"
        )

    fields = data.get("fields")
    if not isinstance(fields, list) or not fields:
        missing.append(f"{path}: fields must be a non-empty list")
        return

    seen: set[str] = set()
    required_field_keys = {"name", "type", "required", "description"}
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            missing.append(f"{path}: fields[{index}] must be an object")
            continue
        missing_keys = sorted(required_field_keys - set(field))
        if missing_keys:
            missing.append(
                f"{path}: fields[{index}] missing keys: {', '.join(missing_keys)}"
            )
        name = field.get("name")
        if not isinstance(name, str) or not name:
            missing.append(f"{path}: fields[{index}].name must be a non-empty string")
        elif name in seen:
            missing.append(f"{path}: duplicate field name '{name}'")
        else:
            seen.add(name)
        if not isinstance(field.get("type"), str) or not field.get("type"):
            missing.append(f"{path}: fields[{index}].type must be a non-empty string")
        if not isinstance(field.get("required"), bool):
            missing.append(f"{path}: fields[{index}].required must be a boolean")
        if not isinstance(field.get("description"), str):
            missing.append(f"{path}: fields[{index}].description must be a string")


def _validate_available_field_schemas(schema_root: Path, missing: list[str]) -> None:
    catalog_path = schema_root / "schema_catalog.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return

    for entry in catalog.get("document_types", []):
        if not isinstance(entry, dict) or entry.get("availability") != "available":
            continue
        vertical = str(entry.get("vertical", ""))
        doc_type = str(entry.get("doc_type", ""))
        path = schema_root / vertical / doc_type / "fields.json"
        if not path.exists():
            missing.append(str(path.relative_to(schema_root.parent)))
            continue
        _validate_field_schema(
            path,
            missing,
            expected_doc_type=doc_type,
            expected_vertical=vertical,
        )


def _validate_prompt_catalog(root: Path, schema_root: Path, missing: list[str]) -> None:
    prompt_catalog_path = schema_root / "prompt_catalog.json"
    if not prompt_catalog_path.exists():
        missing.append(str(prompt_catalog_path.relative_to(root)))
        return

    try:
        prompt_catalog = json.loads(prompt_catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        missing.append(f"{prompt_catalog_path}: invalid JSON ({exc})")
        return

    try:
        schema_catalog = json.loads((schema_root / "schema_catalog.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return

    available_entries = {
        str(entry.get("doc_type")): entry
        for entry in schema_catalog.get("document_types", [])
        if isinstance(entry, dict) and entry.get("availability") == "available"
    }
    prompts = prompt_catalog.get("prompts")
    if not isinstance(prompts, list):
        missing.append(f"{prompt_catalog_path}: prompts must be a list")
        return

    by_doc_type: dict[str, dict] = {}
    required_prompt_keys = {
        "prompt_id",
        "doc_type",
        "schema_catalog_doc_type",
        "vertical",
        "availability",
        "prompt_version",
        "prompt_path",
        "field_schema_path",
        "sha256",
    }
    for index, entry in enumerate(prompts):
        if not isinstance(entry, dict):
            missing.append(f"{prompt_catalog_path}: prompts[{index}] must be an object")
            continue
        missing_keys = sorted(required_prompt_keys - set(entry))
        if missing_keys:
            missing.append(
                f"{prompt_catalog_path}: prompts[{index}] missing keys: {', '.join(missing_keys)}"
            )
        doc_type = str(entry.get("doc_type", ""))
        if doc_type in by_doc_type:
            missing.append(f"{prompt_catalog_path}: duplicate prompt doc_type '{doc_type}'")
        elif doc_type:
            by_doc_type[doc_type] = entry

    if set(by_doc_type) != set(available_entries):
        missing_prompts = sorted(set(available_entries) - set(by_doc_type))
        extra_prompts = sorted(set(by_doc_type) - set(available_entries))
        if missing_prompts:
            missing.append(
                f"{prompt_catalog_path}: missing prompts for available schemas: {', '.join(missing_prompts)}"
            )
        if extra_prompts:
            missing.append(
                f"{prompt_catalog_path}: prompts for non-available schemas: {', '.join(extra_prompts)}"
            )

    for doc_type, entry in by_doc_type.items():
        schema_entry = available_entries.get(doc_type)
        if schema_entry is None:
            continue
        if entry.get("schema_catalog_doc_type") != doc_type:
            missing.append(
                f"{prompt_catalog_path}: prompt '{doc_type}' schema_catalog_doc_type mismatch"
            )
        if entry.get("vertical") != schema_entry.get("vertical"):
            missing.append(f"{prompt_catalog_path}: prompt '{doc_type}' vertical mismatch")
        if entry.get("availability") != "available":
            missing.append(f"{prompt_catalog_path}: prompt '{doc_type}' must be available")

        prompt_path = root / str(entry.get("prompt_path", ""))
        if not prompt_path.exists():
            missing.append(str(prompt_path.relative_to(root)))
        else:
            prompt_text = prompt_path.read_text(encoding="utf-8")
            actual_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
            if entry.get("sha256") != actual_hash:
                missing.append(f"{prompt_catalog_path}: prompt '{doc_type}' sha256 mismatch")

        field_schema_path = root / str(entry.get("field_schema_path", ""))
        if not field_schema_path.exists():
            missing.append(str(field_schema_path.relative_to(root)))


def _available_schema_entries(schema_root: Path) -> list[dict]:
    try:
        catalog = json.loads((schema_root / "schema_catalog.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return [
        entry
        for entry in catalog.get("document_types", [])
        if isinstance(entry, dict) and entry.get("availability") == "available"
    ]


def _check_model_routing_v2(path: Path, missing: list[str]) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return  # file-existence errors caught elsewhere
    legacy_keys = {"model_endpoint", "preferred_model", "primary_model",
                   "fallback_endpoint", "fallback_model"}
    found = sorted(legacy_keys & set(data))
    if found:
        missing.append(
            f"{path}: legacy model_routing keys {found!r} — migrate to 'primary'/'fallback_chain'"
        )
    if "primary" not in data:
        missing.append(f"{path}: model_routing.json missing required key 'primary'")
    if "fallback_chain" not in data:
        missing.append(f"{path}: model_routing.json missing required key 'fallback_chain'")
    if not isinstance(data.get("fallback_chain"), list):
        missing.append(f"{path}: model_routing.json 'fallback_chain' must be a JSON array")


def _check_schema_version_format(
    path: Path, vertical: str, doc_type: str, missing: list[str]
) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return
    sv = data.get("schema_version", "")
    expected_prefix = f"{vertical}_{doc_type}_v"
    if not sv.startswith(expected_prefix):
        missing.append(
            f"{path}: schema_version '{sv}' must start with '{expected_prefix}'"
        )


def _check_required_fields_have_thresholds(
    fields_path: Path, thresholds_path: Path, missing: list[str]
) -> None:
    try:
        fields_data = json.loads(fields_path.read_text(encoding="utf-8"))
        threshold_data = json.loads(thresholds_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return
    required_names = {
        f["name"]
        for f in fields_data.get("fields", [])
        if isinstance(f, dict) and f.get("required") is True and "name" in f
    }
    # threshold_data keys are field names; skip the catalog-level "default_threshold"
    threshold_names = set(threshold_data.keys()) - {"default_threshold"}
    uncovered = sorted(required_names - threshold_names)
    for name in uncovered:
        missing.append(
            f"{thresholds_path}: required field '{name}' has no threshold entry"
        )


def _check_default_threshold(path: Path, missing: list[str]) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return
    if isinstance(data, list):
        missing.append(
            f"{path}: field_thresholds.json uses legacy array format — "
            "migrate to keyed object with 'default_threshold'"
        )
        return
    if isinstance(data, dict) and "default_threshold" not in data:
        missing.append(f"{path}: field_thresholds.json missing 'default_threshold' key")


def _check_golden_test_tags(doc_path: Path, warnings: list[str]) -> None:
    golden_dir = doc_path / "golden_tests"
    if not golden_dir.exists():
        return
    for test_file in golden_dir.glob("test_*.json"):
        try:
            data = json.loads(test_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not data.get("tags"):
            warnings.append(f"{test_file}: golden test missing 'tags' field")


def validate_schema_assets(
    root: Path,
    *,
    min_fs_total: int = 50,
    min_healthcare_per_type: int = 5,
    min_commercial_lending_per_type: int = 1,
    min_available_per_type: int = 1,
) -> SchemaCoverageResult:
    schema_root = root / "Schemas"
    missing: list[str] = []
    warnings: list[str] = []
    golden_counts: dict[str, int] = {}

    catalog_path = schema_root / "schema_catalog.json"
    if not catalog_path.exists():
        missing.append(str(catalog_path.relative_to(root)))
    else:
        _validate_schema_catalog(catalog_path, missing)
        _validate_available_field_schemas(schema_root, missing)
        _validate_prompt_catalog(root, schema_root, missing)

    fs_total = 0
    for doc_type in FS_DOC_TYPES:
        doc_path = schema_root / "fs" / doc_type
        for filename in REQUIRED_SCHEMA_FILES:
            path = doc_path / filename
            if not path.exists():
                missing.append(str(path.relative_to(root)))
            elif path.suffix == ".json":
                _validate_json(path, missing)
        count = _count_goldens(doc_path)
        golden_counts[f"fs/{doc_type}"] = count
        fs_total += count

    if fs_total < min_fs_total:
        missing.append(
            f"Schemas/fs golden corpus has {fs_total} cases; expected at least {min_fs_total}"
        )

    for doc_type in HEALTHCARE_DOC_TYPES:
        doc_path = schema_root / "healthcare" / doc_type
        for filename in REQUIRED_SCHEMA_FILES:
            path = doc_path / filename
            if not path.exists():
                missing.append(str(path.relative_to(root)))
            elif path.suffix == ".json":
                _validate_json(path, missing)
        count = _count_goldens(doc_path)
        golden_counts[f"healthcare/{doc_type}"] = count
        if count < min_healthcare_per_type:
            missing.append(
                f"Schemas/healthcare/{doc_type}/golden_tests has {count} cases; "
                f"expected at least {min_healthcare_per_type}"
            )

    for doc_type in COMMERCIAL_LENDING_DOC_TYPES:
        doc_path = schema_root / "fs" / doc_type
        for filename in REQUIRED_SCHEMA_FILES:
            path = doc_path / filename
            if not path.exists():
                missing.append(str(path.relative_to(root)))
            elif path.suffix == ".json":
                _validate_json(path, missing)
        count = _count_goldens(doc_path)
        golden_counts[f"fs/{doc_type}"] = count
        if count < min_commercial_lending_per_type:
            missing.append(
                f"Schemas/fs/{doc_type}/golden_tests has {count} cases; "
                f"expected at least {min_commercial_lending_per_type}"
            )

    for entry in _available_schema_entries(schema_root):
        vertical = str(entry.get("vertical", ""))
        doc_type = str(entry.get("doc_type", ""))
        if not vertical or not doc_type:
            continue
        doc_path = schema_root / vertical / doc_type
        for filename in REQUIRED_SCHEMA_FILES:
            path = doc_path / filename
            if not path.exists():
                missing.append(str(path.relative_to(root)))
            elif path.suffix == ".json":
                _validate_json(path, missing)
        count = _count_goldens(doc_path)
        golden_counts[f"{vertical}/{doc_type}"] = count
        if count < min_available_per_type:
            missing.append(
                f"Schemas/{vertical}/{doc_type}/golden_tests has {count} cases; "
                f"expected at least {min_available_per_type}"
            )
        _check_model_routing_v2(doc_path / "model_routing.json", missing)
        _check_schema_version_format(doc_path / "fields.json", vertical, doc_type, missing)
        _check_required_fields_have_thresholds(
            doc_path / "fields.json", doc_path / "field_thresholds.json", missing
        )
        _check_default_threshold(doc_path / "field_thresholds.json", missing)
        _check_golden_test_tags(doc_path, warnings)

    return SchemaCoverageResult(
        ok=not missing,
        golden_counts=golden_counts,
        missing=tuple(missing),
        warnings=tuple(warnings),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    result = validate_schema_assets(args.root.resolve())
    if result.ok:
        print("Schema asset coverage passed.")
    else:
        print("Schema asset coverage failed.")

    for name, count in sorted(result.golden_counts.items()):
        print(f"{name}: {count} golden tests")
    for item in result.missing:
        print(f"  - {item}")
    for item in result.warnings:
        print(f"[WARN] {item}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
