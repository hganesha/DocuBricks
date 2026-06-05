"""
Ops Task — Schema promotion gate / test harness.
Tests a candidate prompt version against golden test cases.
Promotes the version if avg field accuracy >= 0.85; otherwise records failure.
Run after inserting a new prompt version into schema_registry.extraction_prompts.

Usage (spark.conf or CLI args):
  document_type      = mortgage_application | kyc_cdd_form | aml_sar | invoice
  candidate_version  = v2 (or any version string, e.g. "v2")

Exit code 1 on failure so Databricks Workflow marks task FAILED.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config — prefer spark.conf, fall back to env vars / sys.argv
# ---------------------------------------------------------------------------

def _conf(key: str, env_var: str, default: str = "") -> str:
    try:
        val = spark.conf.get(key, default)  # noqa: F821
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(env_var, default)


CATALOG           = _conf("catalog_name",       "CATALOG_NAME",       "docubricks_prod")
SECRET_SCOPE      = _conf("secret_scope",        "SECRET_SCOPE",       "docubricks-prod")
DOCUMENT_TYPE     = _conf("document_type",       "DOCUMENT_TYPE",      "")
CANDIDATE_VERSION = _conf("candidate_version",   "CANDIDATE_VERSION",  "")
ACCURACY_THRESHOLD = float(_conf("accuracy_threshold", "ACCURACY_THRESHOLD", "0.85"))
MAX_TEST_CASES    = int(_conf("max_test_cases",  "MAX_TEST_CASES",      "50"))

# Fallback to positional argv for non-Databricks invocation
if not DOCUMENT_TYPE and len(sys.argv) > 1:
    DOCUMENT_TYPE = sys.argv[1]
if not CANDIDATE_VERSION and len(sys.argv) > 2:
    CANDIDATE_VERSION = sys.argv[2]

SREG = f"`{CATALOG}`.`schema_registry`"
EVAL = f"`{CATALOG}`.`eval`"

PROMOTION_THRESHOLD = ACCURACY_THRESHOLD  # alias for clarity in prints

# MLflow
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

def validate_args() -> None:
    errors = []
    if not DOCUMENT_TYPE:
        errors.append(
            "document_type is required "
            "(spark.conf 'document_type', env DOCUMENT_TYPE, or sys.argv[1])"
        )
    if not CANDIDATE_VERSION:
        errors.append(
            "candidate_version is required "
            "(spark.conf 'candidate_version', env CANDIDATE_VERSION, or sys.argv[2])"
        )
    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# DB connection (Lakebase)
# ---------------------------------------------------------------------------

def get_lakebase_conn():
    try:
        conn_string = dbutils.secrets.get(SECRET_SCOPE, "lakebase-conn-string")  # noqa: F821
    except Exception:
        conn_string = os.environ.get("LAKEBASE_CONN", "")
    if not conn_string:
        raise RuntimeError("LAKEBASE_CONN is not set.")
    import psycopg2
    conn = psycopg2.connect(conn_string)
    conn.autocommit = False
    return conn


# ---------------------------------------------------------------------------
# Load candidate prompt (from Delta via Spark)
# ---------------------------------------------------------------------------

def load_candidate_prompt(doc_type: str, version: str) -> str:
    df = spark.sql(f"""  # noqa: F821
        SELECT prompt_text
        FROM {SREG}.extraction_prompts
        WHERE doc_type = '{doc_type}'
          AND version  = '{version}'
        LIMIT 1
    """)
    rows = df.collect()
    if not rows:
        raise ValueError(
            f"No prompt found for doc_type='{doc_type}' version='{version}' "
            f"in {SREG}.extraction_prompts"
        )
    return rows[0]["prompt_text"]


# ---------------------------------------------------------------------------
# Load golden test cases (from eval.ground_truth Delta table)
# ---------------------------------------------------------------------------

def load_golden_test_cases(doc_type: str, limit: int = 50) -> list[dict]:
    df = spark.sql(f"""  # noqa: F821
        SELECT document_id, parsed_text, expected_json
        FROM {EVAL}.ground_truth
        WHERE doc_type = '{doc_type}'
        LIMIT {limit}
    """)
    rows = df.collect()
    if not rows:
        raise ValueError(
            f"No golden test cases found in {EVAL}.ground_truth for doc_type='{doc_type}'. "
            "Load labeled documents before running promotion."
        )
    return [
        {
            "document_id": r["document_id"],
            "parsed_text": r["parsed_text"],
            "expected_json": (
                json.loads(r["expected_json"])
                if isinstance(r["expected_json"], str)
                else r["expected_json"]
            ),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Extraction via ai_query (Databricks SQL AI function)
# ---------------------------------------------------------------------------

def ai_extract(parsed_text: str, prompt: str) -> dict:
    """
    Call Databricks ai_query() to extract structured fields.
    Returns parsed JSON dict; returns {} on failure.
    """
    # Safety: escape single quotes and truncate very long inputs
    safe_text   = parsed_text.replace("'", "''")[:8000]
    safe_prompt = prompt.replace("'", "''")[:4000]

    df = spark.sql(f"""  # noqa: F821
        SELECT ai_query(
            'databricks-dbrx-instruct',
            CONCAT(
                '{safe_prompt}',
                '\\n\\nDocument text:\\n',
                '{safe_text}',
                '\\n\\nRespond with valid JSON only. No markdown, no explanation.'
            )
        ) AS result
    """)
    row = df.collect()[0]
    raw = (row["result"] or "").strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else ""
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# Field accuracy computation
# ---------------------------------------------------------------------------

def compute_field_accuracy(predicted: dict, expected: dict) -> float:
    """
    Fraction of expected fields that match the predicted output.
    Numeric values compared within 0.001 tolerance.
    String values compared case-insensitively after stripping whitespace.
    Returns 0.0 if expected is empty.
    """
    if not expected:
        return 0.0

    matches = 0
    for key, exp_val in expected.items():
        pred_val = predicted.get(key)
        if pred_val is None:
            continue
        # Try numeric comparison
        try:
            if abs(float(str(pred_val)) - float(str(exp_val))) < 0.001:
                matches += 1
                continue
        except (ValueError, TypeError):
            pass
        # String comparison
        if str(pred_val).strip().lower() == str(exp_val).strip().lower():
            matches += 1

    return matches / len(expected)


# ---------------------------------------------------------------------------
# Schema version promotion (Delta via Spark)
# ---------------------------------------------------------------------------

def promote_version(doc_type: str, candidate_version: str) -> None:
    """Deactivate all other versions; activate the candidate."""
    spark.sql(f"""  # noqa: F821
        UPDATE {SREG}.extraction_prompts
        SET    is_active = false
        WHERE  doc_type = '{doc_type}'
          AND  version  != '{candidate_version}'
          AND  is_active = true
    """)
    spark.sql(f"""  # noqa: F821
        UPDATE {SREG}.extraction_prompts
        SET    is_active = true
        WHERE  doc_type = '{doc_type}'
          AND  version  = '{candidate_version}'
    """)


# ---------------------------------------------------------------------------
# Changelog persistence (Lakebase)
# ---------------------------------------------------------------------------

def insert_changelog(
    cursor,
    doc_type: str,
    version: str,
    change_type: str,
    test_accuracy: float | None,
    test_cases_run: int,
    change_reason: str,
) -> None:
    changelog_id = str(uuid.uuid4())
    cursor.execute(
        """
        INSERT INTO schema_changelog
            (changelog_id, doc_type, version, change_type, changed_by,
             change_reason, test_accuracy, test_cases_run, changed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """,
        (
            changelog_id,
            doc_type,
            version,
            change_type,
            "schema_test_harness",
            change_reason,
            test_accuracy,
            test_cases_run,
        ),
    )


# ---------------------------------------------------------------------------
# MLflow logging
# ---------------------------------------------------------------------------

def log_to_mlflow(
    doc_type: str,
    version: str,
    avg_accuracy: float,
    test_cases_run: int,
    passed: bool,
    per_case: list[tuple[str, float]],
) -> str:
    if not MLFLOW_AVAILABLE:
        print("  [WARN] mlflow not installed — skipping MLflow logging.")
        return ""
    try:
        experiment_name = f"/docubricks/schema_promotion/{doc_type}"
        mlflow.set_experiment(experiment_name)
        run_name = (
            f"promotion_{doc_type}_{version}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        )
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_param("document_type",     doc_type)
            mlflow.log_param("candidate_version", version)
            mlflow.log_param("accuracy_threshold", ACCURACY_THRESHOLD)
            mlflow.log_metric("avg_field_accuracy", avg_accuracy)
            mlflow.log_metric("test_cases_run",     test_cases_run)
            mlflow.log_metric("promoted",           int(passed))
            for case_id, acc in per_case:
                mlflow.log_metric(f"accuracy_{case_id[:32]}", acc)
        print(f"  MLflow run_id: {run.info.run_id}")
        return run.info.run_id
    except Exception as exc:
        print(f"  [WARN] MLflow logging failed: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_test_harness(document_type: str, candidate_version: str) -> bool:
    """Core logic. Returns True if promotion passed."""

    print(f"[1/5] Loading candidate prompt ({document_type} {candidate_version})...")
    prompt = load_candidate_prompt(document_type, candidate_version)
    print(f"  Prompt loaded ({len(prompt)} chars).")

    print(f"\n[2/5] Loading golden test cases (limit={MAX_TEST_CASES})...")
    test_cases = load_golden_test_cases(document_type, limit=MAX_TEST_CASES)
    print(f"  Loaded {len(test_cases)} test case(s).")
    if len(test_cases) < 5:
        raise ValueError(
            f"Only {len(test_cases)} test cases available for {document_type}. "
            "Minimum 5 required for meaningful evaluation."
        )

    print(f"\n[3/5] Running extraction on {len(test_cases)} test case(s)...")
    per_case_results: list[tuple[str, float]] = []
    extraction_errors: list[str] = []

    for i, tc in enumerate(test_cases, 1):
        doc_id       = tc["document_id"]
        parsed_text  = tc["parsed_text"]
        expected     = tc["expected_json"]

        try:
            predicted = ai_extract(parsed_text, prompt)
            accuracy  = compute_field_accuracy(predicted, expected)
            per_case_results.append((doc_id, accuracy))
            icon = "PASS" if accuracy >= ACCURACY_THRESHOLD else "WARN"
            print(
                f"  [{icon}] [{i:02d}/{len(test_cases):02d}] {doc_id[:16]}... "
                f"accuracy={accuracy:.3f} "
                f"expected_fields={len(expected)} extracted={len(predicted)}"
            )
        except Exception as exc:
            print(f"  [FAIL] [{i:02d}/{len(test_cases):02d}] {doc_id[:16]}...: {exc}",
                  file=sys.stderr)
            per_case_results.append((doc_id, 0.0))
            extraction_errors.append(f"{doc_id}: {exc}")

    avg_accuracy = (
        sum(a for _, a in per_case_results) / len(per_case_results)
        if per_case_results else 0.0
    )
    passed = avg_accuracy >= ACCURACY_THRESHOLD

    print(f"\n[4/5] Results:")
    print(f"  Test cases run     : {len(test_cases)}")
    print(f"  Avg field accuracy : {avg_accuracy:.4f}")
    print(f"  Threshold          : {ACCURACY_THRESHOLD}")
    print(f"  Decision           : {'PROMOTE' if passed else 'REJECT'}")

    print(f"\n[5/5] Logging to MLflow and persisting decision...")
    run_id = log_to_mlflow(
        document_type, candidate_version, avg_accuracy,
        len(test_cases), passed, per_case_results
    )

    # Persist to Lakebase changelog
    lb_conn   = get_lakebase_conn()
    lb_cursor = lb_conn.cursor()
    try:
        if passed:
            # Promote in Delta (schema_registry is a UC Delta table)
            promote_version(document_type, candidate_version)
            insert_changelog(
                lb_cursor,
                doc_type=document_type,
                version=candidate_version,
                change_type="PROMOTION_SUCCEEDED",
                test_accuracy=round(avg_accuracy, 4),
                test_cases_run=len(test_cases),
                change_reason=(
                    f"Auto-promoted: avg_accuracy={avg_accuracy:.4f} "
                    f">= threshold={ACCURACY_THRESHOLD}"
                ),
            )
            lb_conn.commit()
            print(f"  [OK] Version '{candidate_version}' promoted to active for {document_type}.")
        else:
            insert_changelog(
                lb_cursor,
                doc_type=document_type,
                version=candidate_version,
                change_type="PROMOTION_FAILED",
                test_accuracy=round(avg_accuracy, 4),
                test_cases_run=len(test_cases),
                change_reason=(
                    f"Gate failed: avg_accuracy={avg_accuracy:.4f} "
                    f"< threshold={ACCURACY_THRESHOLD}"
                ),
            )
            lb_conn.commit()
    finally:
        lb_cursor.close()
        lb_conn.close()

    return passed


def main() -> None:
    validate_args()

    run_ts = datetime.now(timezone.utc).isoformat()
    print("=" * 60)
    print("Ops Task — Schema Promotion Test Harness")
    print(f"  Run time           : {run_ts}")
    print(f"  Document type      : {DOCUMENT_TYPE}")
    print(f"  Candidate version  : {CANDIDATE_VERSION}")
    print(f"  Accuracy threshold : {ACCURACY_THRESHOLD}")
    print(f"  Max test cases     : {MAX_TEST_CASES}")
    print(f"  Catalog            : {CATALOG}")
    print("=" * 60)

    passed = run_test_harness(DOCUMENT_TYPE, CANDIDATE_VERSION)

    print("\n" + "=" * 60)
    if passed:
        print(f"RESULT: PROMOTED — '{CANDIDATE_VERSION}' is now active for {DOCUMENT_TYPE}.")
        print("Schema promotion test harness complete.")
    else:
        print(f"RESULT: REJECTED — '{CANDIDATE_VERSION}' did NOT meet accuracy threshold.")
        print(f"Required >= {ACCURACY_THRESHOLD:.0%}. Check schema_changelog for details.")
        print("Fix the prompt and re-submit.")
    print("=" * 60)

    if not passed:
        sys.exit(1)


main()
