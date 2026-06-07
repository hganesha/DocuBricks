#!/usr/bin/env python3
"""
migrate_model_routing_v2.py

Migrates all model_routing.json files under Schemas/ to the v2 key convention:
  primary          (from model_endpoint or preferred_model)
  fallback_chain   (from fallback_endpoint or fallback_model — wrapped in list)
  max_tokens       (preserved)
  temperature      (preserved)
  timeout_seconds  (added as 30 if missing)
  max_retries      (added as 2 if missing)
  tier_overrides   (added as {} if missing)
  rationale        (preserved)
"""

import json
import pathlib
import subprocess
import sys

SCHEMAS_ROOT = pathlib.Path(__file__).resolve().parent.parent / "Schemas"
KEY_ORDER = [
    "primary",
    "fallback_chain",
    "max_tokens",
    "temperature",
    "timeout_seconds",
    "max_retries",
    "tier_overrides",
    "rationale",
]

# v1 → v2 key renames for the primary model key
PRIMARY_ALIASES = {"model_endpoint", "preferred_model"}
# v1 → v2 key renames for the fallback key
FALLBACK_ALIASES = {"fallback_endpoint", "fallback_model"}


def migrate(path: pathlib.Path) -> dict:
    """Return the migrated dict for a single model_routing.json."""
    with path.open() as fh:
        data = json.load(fh)

    out = {}

    # primary
    for alias in PRIMARY_ALIASES:
        if alias in data:
            out["primary"] = data[alias]
            break
    if "primary" not in out:
        if "primary" in data:
            out["primary"] = data["primary"]
        else:
            raise KeyError(f"{path}: no primary key found in {list(data.keys())}")

    # fallback_chain
    fallback_val = None
    for alias in FALLBACK_ALIASES:
        if alias in data:
            fallback_val = data[alias]
            break
    if fallback_val is None:
        if "fallback_chain" in data:
            # already migrated or already a list
            fallback_val = data["fallback_chain"]
            if not isinstance(fallback_val, list):
                fallback_val = [fallback_val]
        else:
            fallback_val = []
    else:
        fallback_val = [fallback_val]
    out["fallback_chain"] = fallback_val

    # preserved keys
    out["max_tokens"] = data["max_tokens"]
    out["temperature"] = data["temperature"]

    # new keys (add if missing)
    out["timeout_seconds"] = data.get("timeout_seconds", 30)
    out["max_retries"] = data.get("max_retries", 2)
    out["tier_overrides"] = data.get("tier_overrides", {})

    out["rationale"] = data["rationale"]

    return out


def main():
    files = sorted(
        SCHEMAS_ROOT.rglob("model_routing.json")
    )
    # exclude anything under a prompts/ directory
    files = [f for f in files if "prompts" not in f.parts]

    migrated = 0
    errors = 0

    for path in files:
        try:
            new_data = migrate(path)
            # Write back with 2-space indent; ensure trailing newline
            content = json.dumps(new_data, indent=2) + "\n"
            path.write_text(content, encoding="utf-8")
            print(f"  OK  {path.relative_to(SCHEMAS_ROOT.parent)}")
            migrated += 1
        except Exception as exc:
            print(f"  ERR {path.relative_to(SCHEMAS_ROOT.parent)}: {exc}", file=sys.stderr)
            errors += 1

    print(f"\nDone: {migrated} migrated, {errors} errors.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
