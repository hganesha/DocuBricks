#!/usr/bin/env python3
"""
migrate_add_default_threshold.py

Inserts "default_threshold": 0.75 as the first key in every
field_thresholds.json file under Schemas/ (excluding prompts/ and common/).

Safe to re-run: files that already have default_threshold are skipped.
"""

import json
import subprocess
import sys
from pathlib import Path

SCHEMAS_ROOT = Path(__file__).resolve().parent.parent / "Schemas"
DEFAULT_THRESHOLD_VALUE = 0.75
DEFAULT_THRESHOLD_KEY = "default_threshold"


def find_threshold_files():
    result = subprocess.run(
        [
            "find",
            str(SCHEMAS_ROOT),
            "-name",
            "field_thresholds.json",
            "-not",
            "-path",
            "*/prompts/*",
            "-not",
            "-path",
            "*/common/*",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    paths = [Path(p) for p in result.stdout.strip().splitlines() if p]
    return sorted(paths)


def process_file(path: Path) -> str:
    """Return 'updated', 'skipped', or 'incompatible'."""
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        # Array-format files use a different schema; cannot add a top-level key.
        print(f"  [skip-array-format] {path.relative_to(SCHEMAS_ROOT.parent)}")
        return "incompatible"

    if DEFAULT_THRESHOLD_KEY in data:
        print(f"  [skip]    {path.relative_to(SCHEMAS_ROOT.parent)}")
        return "skipped"

    # Rebuild dict with default_threshold first
    updated = {DEFAULT_THRESHOLD_KEY: DEFAULT_THRESHOLD_VALUE, **data}

    with path.open("w", encoding="utf-8") as fh:
        json.dump(updated, fh, indent=2)
        fh.write("\n")  # trailing newline

    print(f"  [updated] {path.relative_to(SCHEMAS_ROOT.parent)}")
    return "updated"


def main():
    files = find_threshold_files()
    if not files:
        print("No field_thresholds.json files found. Nothing to do.")
        sys.exit(0)

    print(f"Found {len(files)} field_thresholds.json file(s).\n")

    updated_count = 0
    skipped_count = 0
    incompatible_count = 0
    for path in files:
        result = process_file(path)
        if result == "updated":
            updated_count += 1
        elif result == "skipped":
            skipped_count += 1
        else:
            incompatible_count += 1

    print(
        f"\nDone. Files updated: {updated_count}"
        f"  |  Files skipped (already had key): {skipped_count}"
        f"  |  Skipped (array-format, incompatible): {incompatible_count}"
    )


if __name__ == "__main__":
    main()
