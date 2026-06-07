#!/usr/bin/env python3
"""
migrate_schema_version.py
Normalise the schema_version field in every fields.json to the canonical
  {vertical}_{document_type}_v{N}
format. v0 values are promoted to v1. External-standard strings are moved to
a new external_standard key immediately after schema_version.

Run from anywhere:
    python3 scripts/migrate_schema_version.py
"""

import json
import re
import sys
from pathlib import Path

SCHEMAS_ROOT = Path(__file__).resolve().parent.parent / "Schemas"

# External-standard values whose original string should be preserved in a
# separate key.  Key = old schema_version value, Value = external_standard label.
EXTERNAL_STANDARDS: dict[str, str] = {
    "MISMO_v3.4_URLA": "MISMO_v3.4_URLA",
}


def canonical_version(current: str, vertical: str, doc_type: str) -> tuple[str, str | None]:
    """
    Returns (new_schema_version, external_standard_or_None).
    """
    expected_prefix = f"{vertical}_{doc_type}_v"
    # Already in correct format?
    if re.fullmatch(rf"{re.escape(expected_prefix)}\d+", current):
        return current, None

    # Capture external standard if applicable.
    ext = EXTERNAL_STANDARDS.get(current)

    # Determine version number.
    # External standards always map to v1 (their embedded version numbers refer
    # to the standard itself, not our schema version).
    # Otherwise: promote v0 → v1, keep v1+.
    if ext is not None:
        version_num = 1
    else:
        v_match = re.search(r"v(\d+)", current, re.IGNORECASE)
        version_num = 1
        if v_match:
            n = int(v_match.group(1))
            version_num = max(n, 1)   # v0 → v1

    new_sv = f"{expected_prefix}{version_num}"
    return new_sv, ext


def migrate_file(path: Path) -> dict | None:
    """
    Migrates one fields.json.  Returns a dict with before/after info if changed,
    or None if the file was already correct.
    """
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    vertical = data.get("vertical", "")
    doc_type = data.get("document_type", "")
    old_sv = data.get("schema_version", "")

    if not vertical or not doc_type:
        print(f"  SKIP (missing vertical/document_type): {path}", file=sys.stderr)
        return None

    new_sv, ext_std = canonical_version(old_sv, vertical, doc_type)

    if new_sv == old_sv and ext_std is None:
        return None  # Nothing to do.

    # ------------------------------------------------------------------ #
    # Rebuild the ordered dict preserving key order; insert external_standard
    # immediately after schema_version when needed.
    # ------------------------------------------------------------------ #
    new_data: dict = {}
    for key, value in data.items():
        if key == "schema_version":
            new_data["schema_version"] = new_sv
            if ext_std is not None:
                new_data["external_standard"] = ext_std
        else:
            new_data[key] = value

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(new_data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    return {
        "file": str(path.relative_to(SCHEMAS_ROOT.parent)),
        "before": old_sv,
        "after": new_sv,
        "external_standard": ext_std,
    }


def main() -> None:
    files = sorted(
        p for p in SCHEMAS_ROOT.rglob("fields.json")
        if "prompts" not in p.parts and "common" not in p.parts
    )

    changes: list[dict] = []
    for path in files:
        result = migrate_file(path)
        if result:
            changes.append(result)

    if not changes:
        print("All schema_version values are already canonical. Nothing to do.")
        return

    # ------------------------------------------------------------------ #
    # Print before/after table
    # ------------------------------------------------------------------ #
    col_file  = max(len(c["file"]) for c in changes)
    col_before = max(len(c["before"]) for c in changes)
    col_after  = max(len(c["after"]) for c in changes)

    header = (
        f"{'File':<{col_file}}  {'Before':<{col_before}}  {'After':<{col_after}}  {'external_standard'}"
    )
    print(header)
    print("-" * len(header))
    for c in changes:
        ext = c["external_standard"] or ""
        print(f"{c['file']:<{col_file}}  {c['before']:<{col_before}}  {c['after']:<{col_after}}  {ext}")

    print(f"\n{len(changes)} file(s) updated.")


if __name__ == "__main__":
    main()
