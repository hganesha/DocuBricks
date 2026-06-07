#!/usr/bin/env python3
"""
migrate_validation_rules_v2.py
-------------------------------
Enrich every validation_rules.json under Schemas/ by adding two new keys to
each rule object: `rule_type` and `fields`.

Run from any directory:
    python scripts/migrate_validation_rules_v2.py

Idempotent: rules that already have BOTH `rule_type` and `fields` are skipped.

Key-order in each rule object:
    name -> rule_type -> fields -> expression -> severity -> description
    (any extra keys are preserved at the end)
"""

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_ROOT = REPO_ROOT / "Schemas"

FIND_EXCLUDE = {"prompts", "common"}

# SQL keywords / function names that must NOT be treated as field names
SQL_KEYWORDS = frozenset({
    "not", "null", "and", "or", "is", "true", "false",
    "trim", "length", "json_array_length", "array_length", "array_size",
    "in", "like", "rlike", "regexp", "select", "from", "where",
    "case", "when", "then", "else", "end", "cast", "as",
    "between", "exists", "coalesce", "ifnull", "isnull",
    "date", "timestamp", "interval",
})

# ---------------------------------------------------------------------------
# Rule-type inference
# ---------------------------------------------------------------------------

def infer_rule_type(expression: str) -> str:
    """
    Infer a rule_type string from the SQL expression.

    Priority (first match wins):
        1. array     – JSON_ARRAY_LENGTH / ARRAY_LENGTH / ARRAY_SIZE
        2. format    – REGEXP / RLIKE / LIKE
        3. range     – >= / <= on a numeric literal (not cross-field)
        4. cross_field – comparison that references two+ distinct field names
        5. presence  – IS NOT NULL / LENGTH(
        6. presence  – safe default
    """
    expr_upper = expression.upper()

    # 1. array functions
    if re.search(r'\b(JSON_ARRAY_LENGTH|ARRAY_LENGTH|ARRAY_SIZE)\b', expr_upper):
        return "array"

    # 2. format patterns
    if re.search(r'\b(REGEXP|RLIKE|LIKE)\b', expr_upper):
        return "format"

    # 3. range – numeric bound comparison (>= or <= with a number literal)
    #    We match patterns like:  field >= 0  /  field <= 100  /  field > 0
    #    Exclude expressions that compare two field names against each other.
    has_numeric_comparison = bool(
        re.search(r'[A-Za-z_][A-Za-z0-9_]*\s*(>=|<=|>|<)\s*[\d.]+', expression)
        or re.search(r'[\d.]+\s*(>=|<=|>|<)\s*[A-Za-z_][A-Za-z0-9_]*', expression)
    )
    if has_numeric_comparison:
        # Check whether the expression also compares two field names (cross-field)
        # e.g.  maturity_date > agreement_date
        field_vs_field = bool(
            re.search(
                r'[a-z][a-z0-9_]+\s*(>=|<=|>|<)\s*[a-z][a-z0-9_]+',
                expression,
            )
        )
        if not field_vs_field:
            return "range"

    # 4. cross-field – two or more distinct field names on either side of a comparison
    #    Heuristic: look for   identifier <op> identifier   where both sides are
    #    lowercase identifiers (not keywords / numbers).
    cross_field_match = re.findall(
        r'\b([a-z][a-z0-9_]+)\s*(>=|<=|>|<|=)\s*([a-z][a-z0-9_]+)\b',
        expression,
    )
    cf_pairs = [
        (lhs, rhs)
        for lhs, _op, rhs in cross_field_match
        if lhs not in SQL_KEYWORDS and rhs not in SQL_KEYWORDS and lhs != rhs
    ]
    if cf_pairs:
        return "cross_field"

    # 5. presence
    if re.search(r'\bIS\s+(NOT\s+)?NULL\b', expr_upper) or re.search(
        r'\bLENGTH\s*\(', expr_upper
    ):
        return "presence"

    # 6. safe default
    return "presence"


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def extract_fields(expression: str) -> list:
    """
    Extract field names referenced in the SQL expression.

    A token is treated as a field name when:
      - It is a lowercase identifier [a-z][a-z0-9_]*
      - It is NOT in SQL_KEYWORDS
      - It appears in a recognisable field-referencing pattern:
          * before IS NULL / IS NOT NULL
          * inside TRIM( ... ) or LENGTH( ... )
          * in a direct comparison:  field <op> literal  or  literal <op> field
          * standalone IS NOT NULL / IS NULL check

    Returns unique names in first-appearance order.
    """
    seen: dict = {}  # name -> order_index

    def record(name: str):
        lname = name.lower()
        if lname not in SQL_KEYWORDS and lname not in seen:
            seen[lname] = len(seen)

    # Pattern 1: field IS [NOT] NULL
    for m in re.finditer(
        r'\b([a-z][a-z0-9_]+)\s+IS\s+(?:NOT\s+)?NULL\b', expression, re.IGNORECASE
    ):
        record(m.group(1).lower())

    # Pattern 2: inside TRIM(field) or LENGTH(field) — capture direct identifier arg
    for m in re.finditer(
        r'\b(?:TRIM|LENGTH)\s*\(\s*([a-z][a-z0-9_]+)\s*\)', expression, re.IGNORECASE
    ):
        record(m.group(1).lower())

    # Pattern 3: field <comparison_op> numeric_literal  (range rules)
    for m in re.finditer(
        r'\b([a-z][a-z0-9_]+)\s*(?:>=|<=|>|<|=)\s*[\d.]+', expression
    ):
        record(m.group(1).lower())

    # Pattern 4: numeric_literal <comparison_op> field
    for m in re.finditer(
        r'[\d.]+\s*(?:>=|<=|>|<|=)\s*([a-z][a-z0-9_]+)\b', expression
    ):
        record(m.group(1).lower())

    # Pattern 5: cross-field comparisons  field1 <op> field2
    for m in re.finditer(
        r'\b([a-z][a-z0-9_]+)\s*(?:>=|<=|>|<|=)\s*([a-z][a-z0-9_]+)\b', expression
    ):
        record(m.group(1).lower())
        record(m.group(2).lower())

    # Sort by first-appearance order
    return sorted(seen.keys(), key=lambda k: seen[k])


# ---------------------------------------------------------------------------
# File migration
# ---------------------------------------------------------------------------

def ordered_rule(rule: dict, rule_type: str, fields: list) -> dict:
    """
    Return a new dict with keys in the canonical order:
        name, rule_type, fields, expression, severity, description, <rest>
    """
    canonical_keys = ["name", "rule_type", "fields", "expression", "severity", "description"]
    result = {}
    for k in canonical_keys:
        if k == "rule_type":
            result["rule_type"] = rule_type
        elif k == "fields":
            result["fields"] = fields
        elif k in rule:
            result[k] = rule[k]
    # Any extra keys not in the canonical set
    for k, v in rule.items():
        if k not in result and k not in ("rule_type", "fields"):
            result[k] = v
    return result


def migrate_file(path: Path) -> tuple:
    """
    Read, migrate, and write a single validation_rules.json.

    Returns (changed: bool, rules_migrated: int, rules_skipped: int).
    """
    with open(path, "r", encoding="utf-8") as fh:
        rules = json.load(fh)

    if not isinstance(rules, list):
        print(f"  SKIP (not a list): {path}")
        return False, 0, 0

    new_rules = []
    migrated = 0
    skipped = 0

    for rule in rules:
        if not isinstance(rule, dict):
            new_rules.append(rule)
            continue

        # Already fully migrated (has both rule_type and fields array)?
        if "rule_type" in rule and "fields" in rule:
            # Normalise key order even for already-migrated rules
            new_rules.append(
                ordered_rule(rule, rule.get("rule_type"), rule.get("fields", []))
            )
            skipped += 1
            continue

        expression = rule.get("expression", "")
        rule_type = infer_rule_type(expression)
        fields = extract_fields(expression)

        # If the file used the old single field_name key, incorporate it
        # (do NOT carry it forward — the new format uses `fields` array)
        if not fields and "field_name" in rule:
            fn = rule["field_name"].lower()
            if fn not in SQL_KEYWORDS:
                fields = [fn]

        new_rules.append(ordered_rule(rule, rule_type, fields))
        migrated += 1

    changed = migrated > 0 or (
        # Also write if key order changed even when all were "skipped"
        json.dumps(rules, ensure_ascii=False) != json.dumps(new_rules, ensure_ascii=False)
    )

    if changed:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(new_rules, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    return changed, migrated, skipped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_validation_files() -> list:
    files = []
    for p in SCHEMA_ROOT.rglob("validation_rules.json"):
        # Exclude prompts/ and common/ directories anywhere in path
        parts = set(p.parts)
        if parts & FIND_EXCLUDE:
            continue
        files.append(p)
    return sorted(files)


def main():
    files = find_validation_files()
    if not files:
        print("No validation_rules.json files found.")
        sys.exit(1)

    print(f"Found {len(files)} validation_rules.json files.\n")

    total_changed = 0
    total_migrated = 0
    total_skipped = 0

    for path in files:
        changed, migrated, skipped = migrate_file(path)
        rel = path.relative_to(REPO_ROOT)
        status = "UPDATED" if changed else "no-op "
        print(f"  [{status}]  {rel}  (migrated={migrated}, already-done={skipped})")
        if changed:
            total_changed += 1
        total_migrated += migrated
        total_skipped += skipped

    print(f"\nDone. Files updated: {total_changed}/{len(files)}")
    print(f"Rules migrated: {total_migrated}  |  Rules already complete: {total_skipped}")


if __name__ == "__main__":
    main()
