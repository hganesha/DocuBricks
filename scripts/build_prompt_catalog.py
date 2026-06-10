#!/usr/bin/env python3
"""Build a centralized prompt library and prompt catalog tied to schemas."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_ROOT = REPO_ROOT / "Schemas"
SCHEMA_CATALOG_PATH = SCHEMAS_ROOT / "schema_catalog.json"
PROMPT_ROOT = SCHEMAS_ROOT / "prompts"
PROMPT_CATALOG_PATH = SCHEMAS_ROOT / "prompt_catalog.json"


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _read_schema_catalog() -> dict[str, Any]:
    return json.loads(SCHEMA_CATALOG_PATH.read_text(encoding="utf-8"))


def _prompt_entry(entry: dict[str, Any]) -> dict[str, Any]:
    vertical = str(entry["vertical"])
    doc_type = str(entry["doc_type"])
    centralized_prompt_path = PROMPT_ROOT / vertical / doc_type / "prompt_v1.txt"
    source_prompt_path = SCHEMAS_ROOT / vertical / doc_type / "prompt_v1.txt"
    if centralized_prompt_path.exists():
        prompt_text = centralized_prompt_path.read_text(encoding="utf-8")
        source_bundle_prompt_path = None
    else:
        prompt_text = source_prompt_path.read_text(encoding="utf-8")
        centralized_prompt_path.parent.mkdir(parents=True, exist_ok=True)
        centralized_prompt_path.write_text(prompt_text, encoding="utf-8")
        source_bundle_prompt_path = _relative(source_prompt_path)

    prompt_entry = {
        "prompt_id": f"{vertical}.{doc_type}.v1",
        "doc_type": doc_type,
        "schema_catalog_doc_type": doc_type,
        "vertical": vertical,
        "family": entry.get("family"),
        "availability": entry.get("availability"),
        "prompt_version": "v1",
        "prompt_path": _relative(centralized_prompt_path),
        "field_schema_path": _relative(SCHEMAS_ROOT / vertical / doc_type / "fields.json"),
        "validation_rules_path": _relative(SCHEMAS_ROOT / vertical / doc_type / "validation_rules.json"),
        "field_thresholds_path": _relative(SCHEMAS_ROOT / vertical / doc_type / "field_thresholds.json"),
        "model_routing_path": _relative(SCHEMAS_ROOT / vertical / doc_type / "model_routing.json"),
        "sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
    }
    if source_bundle_prompt_path is not None:
        prompt_entry["source_bundle_prompt_path"] = source_bundle_prompt_path
    return prompt_entry


def build_prompt_catalog() -> dict[str, Any]:
    schema_catalog = _read_schema_catalog()
    prompts = [
        _prompt_entry(entry)
        for entry in schema_catalog.get("document_types", [])
        if entry.get("availability") == "available"
    ]
    prompts.sort(key=lambda item: (str(item["vertical"]), str(item["doc_type"])))

    return {
        "prompt_catalog_version": schema_catalog.get("schema_catalog_version"),
        "schema_catalog_path": _relative(SCHEMA_CATALOG_PATH),
        "schema_catalog_version": schema_catalog.get("schema_catalog_version"),
        "prompt_root": _relative(PROMPT_ROOT),
        "prompts": prompts,
    }


def main() -> int:
    catalog = build_prompt_catalog()
    PROMPT_CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(catalog['prompts'])} prompts to {_relative(PROMPT_ROOT)}")
    print(f"Wrote prompt catalog to {_relative(PROMPT_CATALOG_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
