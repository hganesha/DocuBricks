#!/usr/bin/env python3
"""Validate schema asset coverage required for Phase 4 and Phase 5."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


FS_DOC_TYPES = (
    "mortgage_application",
    "kyc_cdd_form",
    "aml_sar",
    "invoice",
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


def _count_goldens(path: Path) -> int:
    golden_dir = path / "golden_tests"
    return len(tuple(golden_dir.glob("test_*.json"))) if golden_dir.exists() else 0


def _validate_json(path: Path, missing: list[str]) -> None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        missing.append(f"{path}: invalid JSON ({exc})")


def validate_schema_assets(
    root: Path,
    *,
    min_fs_total: int = 50,
    min_healthcare_per_type: int = 5,
) -> SchemaCoverageResult:
    schema_root = root / "Schemas"
    missing: list[str] = []
    golden_counts: dict[str, int] = {}

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

    return SchemaCoverageResult(
        ok=not missing,
        golden_counts=golden_counts,
        missing=tuple(missing),
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

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

