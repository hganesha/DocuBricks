"""
Bootstrap Job 03 — AI/BI Genie workspace provisioning.
Creates a Genie space for the FS vertical, seeds 20 domain questions,
and writes the space_id to Databricks Secret scope.
"""

import json
import os
import sys

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _conf(key: str, env_var: str, default: str = "") -> str:
    try:
        val = spark.conf.get(key, default)  # noqa: F821
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(env_var, default)


CATALOG      = _conf("catalog_name",   "CATALOG_NAME",   "docubricks_prod")
SECRET_SCOPE = _conf("secret_scope",   "SECRET_SCOPE",   "docubricks-prod")
PROJECT_NAME = _conf("project_name",   "PROJECT_NAME",   "DocuBricks")

# Databricks host and PAT
DATABRICKS_HOST = _conf("databricks_host", "DATABRICKS_HOST", "")

def get_token() -> str:
    try:
        return dbutils.secrets.get(SECRET_SCOPE, "databricks-token")  # noqa: F821
    except Exception:
        return os.environ.get("DATABRICKS_TOKEN", "")


# Gold tables that Genie can query (from wave1_pipeline.json)
FS_GOLD_TABLES = [
    f"{CATALOG}.gold.fs_mortgage_portfolio",
    f"{CATALOG}.gold.fs_kyc_compliance_summary",
    f"{CATALOG}.gold.fs_aml_alerts_summary",
    f"{CATALOG}.gold.extraction_metrics_daily",
    f"{CATALOG}.gold.platform_health",
    f"{CATALOG}.gold.agent_activity",
]

# 20 FS-specific Genie seed questions
FS_QUESTIONS = [
    # Mortgage portfolio
    "What is the average loan-to-value ratio for mortgage applications received in the last 30 days?",
    "Which tenants have the highest volume of mortgage applications with debt-to-income ratios above 43%?",
    "Show me the distribution of loan purposes (purchase vs. refinance) by month for the current quarter.",
    "How many mortgage applications have a credit score below 620 and are still in REVIEW status?",
    "What is the average time from document receipt to extraction completion for mortgage applications?",
    # KYC / CDD
    "List all KYC forms where the overall_risk_rating is HIGH and beneficial_ownership_collected is false.",
    "How many customers are flagged as PEP (Politically Exposed Person) by tenant in the last 90 days?",
    "What percentage of KYC forms triggered Enhanced Due Diligence in the past week?",
    "Show me the trend of sanctions screening hits over the last 6 months by vertical.",
    "Which tenants have the most KYC forms currently awaiting periodic refresh review?",
    # AML / SAR
    "What are the top 5 suspicious activity types by transaction volume in the current month?",
    "Show me all AML SARs where transaction_amount exceeds $50,000 filed in the last 7 days.",
    "Which filing institutions submitted the most SARs in Q2, and what was the average narrative length?",
    "Are there any AML SARs with extraction confidence below 0.70 that are not yet in human review?",
    "Compare SAR filing volume this month vs. the same period last year.",
    # Platform health
    "What is the current quarantine rate across all document types in the last 24 hours?",
    "Which document type has the lowest average extraction confidence this week?",
    "Show me all documents stuck in PARSING or EXTRACTING state for more than 30 minutes.",
    "How many documents failed schema validation vs. failed extraction in the past 7 days?",
    "What is the average end-to-end processing time (receipt to COMPLETE status) by document type?",
]

# ---------------------------------------------------------------------------
# Genie API helpers
# ---------------------------------------------------------------------------

class GenieClient:
    def __init__(self, host: str, token: str) -> None:
        if not host:
            raise ValueError("DATABRICKS_HOST is not set.")
        if not token:
            raise ValueError("Databricks token is not set.")
        self.base_url = host.rstrip("/")
        self.headers  = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        resp = requests.post(url, headers=self.headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"POST {path} returned {resp.status_code}: {resp.text}"
            )
        return resp.json()

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=self.headers, timeout=30)
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"GET {path} returned {resp.status_code}: {resp.text}"
            )
        return resp.json()

    def list_spaces(self) -> list[dict]:
        try:
            result = self._get("/api/2.0/genie/spaces")
            return result.get("spaces", result.get("items", []))
        except Exception:
            return []

    def create_space(self, name: str, trusted_tables: list[str]) -> dict:
        payload = {
            "display_name": name,
            "trusted_assets": {
                "tables": [
                    {"catalog": t.split(".")[0], "schema": t.split(".")[1], "table": t.split(".")[2]}
                    for t in trusted_tables
                ]
            },
        }
        return self._post("/api/2.0/genie/spaces", payload)

    def add_question(self, space_id: str, question: str) -> dict:
        payload = {"question": question}
        return self._post(f"/api/2.0/genie/spaces/{space_id}/questions", payload)

    def put_secret(self, scope: str, key: str, value: str) -> None:
        try:
            dbutils.secrets.put(scope=scope, key=key, string_value=value)  # noqa: F821
        except Exception as exc:
            print(f"  [WARN] dbutils.secrets.put failed: {exc}. "
                  "Store '{key}' manually in scope '{scope}'.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Bootstrap Job 03 — Genie Workspace Setup")
    print(f"  Catalog      : {CATALOG}")
    print(f"  Secret scope : {SECRET_SCOPE}")
    print(f"  Project      : {PROJECT_NAME}")
    print("=" * 60)

    host  = DATABRICKS_HOST
    token = get_token()

    if not host:
        # Try to derive from spark context
        try:
            host = "https://" + spark.conf.get("spark.databricks.workspaceUrl", "")  # noqa: F821
        except Exception:
            pass

    print(f"\n  Workspace host : {host or '(not set)'}")

    client = GenieClient(host, token)

    # --- FS vertical ---
    vertical     = "fs"
    space_name   = f"DocuBricks FS — {PROJECT_NAME}"
    secret_key   = f"genie-space-id-{vertical}"

    # Check if space already exists
    print(f"\n[1/3] Checking for existing Genie space '{space_name}'...")
    existing_spaces = client.list_spaces()
    existing = next(
        (s for s in existing_spaces if s.get("display_name") == space_name),
        None,
    )

    if existing:
        space_id = existing.get("id") or existing.get("space_id")
        print(f"  Space already exists: id={space_id} — skipping creation.")
    else:
        print(f"  Creating Genie space '{space_name}'...")
        print(f"  Trusted tables:")
        for t in FS_GOLD_TABLES:
            print(f"    {t}")
        result   = client.create_space(space_name, FS_GOLD_TABLES)
        space_id = result.get("id") or result.get("space_id")
        print(f"  [OK] Created space: id={space_id}")

    if not space_id:
        raise RuntimeError("Failed to obtain Genie space_id.")

    # Seed questions
    print(f"\n[2/3] Seeding {len(FS_QUESTIONS)} questions into space {space_id}...")
    q_loaded = 0
    q_errors = 0
    for i, question in enumerate(FS_QUESTIONS, 1):
        try:
            client.add_question(space_id, question)
            print(f"  [OK] Q{i:02d}: {question[:70]}...")
            q_loaded += 1
        except Exception as exc:
            # Questions may already exist — non-fatal
            print(f"  [SKIP] Q{i:02d}: {exc}")
            q_errors += 1

    # Write space_id to secret scope
    print(f"\n[3/3] Writing space_id to secret scope '{SECRET_SCOPE}' key '{secret_key}'...")
    client.put_secret(SECRET_SCOPE, secret_key, space_id)
    print(f"  [OK] Secret stored.")

    # Print Genie URL
    genie_url = f"{host.rstrip('/')}/genie/spaces/{space_id}"
    print(f"\n  Genie space URL: {genie_url}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Vertical         : {vertical}")
    print(f"  Space name       : {space_name}")
    print(f"  Space ID         : {space_id}")
    print(f"  Trusted tables   : {len(FS_GOLD_TABLES)}")
    print(f"  Questions seeded : {q_loaded} / {len(FS_QUESTIONS)}")
    print(f"  Questions skipped: {q_errors}")
    print(f"  Genie URL        : {genie_url}")
    print("=" * 60)
    print("Bootstrap Job 03 complete.")


main()
