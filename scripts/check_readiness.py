#!/usr/bin/env python3
"""Check whether the repo has the minimum files needed for Phase 0 work."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReadinessResult:
    present: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing


REQUIRED_PATHS: tuple[str, ...] = (
    "databricks.yml",
    ".env.example",
    ".github/workflows/ci.yml",
    "migrations/V001__create_document_registry.sql",
    "migrations/V002__create_processing_jobs.sql",
    "migrations/V003__create_review_queue.sql",
    "migrations/V004__create_reprocessing_queue.sql",
    "migrations/V005__create_extraction_audit.sql",
    "migrations/V006__create_monitoring_alerts.sql",
    "migrations/V007__create_tenant_registry.sql",
    "src/bootstrap/setup_lakebase.py",
    "src/bootstrap/setup_schema_registry.py",
    "src/bootstrap/setup_unity_catalog.py",
    "src/pipelines/bronze/autoloader_ingest.py",
    "src/pipelines/silver/parse_classify.py",
    "src/pipelines/silver/extract_router.py",
    "src/pipelines/gold/fs_portfolio.py",
    "src/pipelines/gold/platform_health.py",
    "apps/lib/auth.py",
    "apps/lib/databricks_api.py",
    "apps/lib/genie.py",
    "apps/lib/lakebase.py",
    "apps/lib/otel.py",
    "apps/lib/sql_warehouse.py",
    "apps/onboarding/app.py",
    "apps/onboarding/app.yaml",
    "apps/portal/app.py",
    "apps/portal/app.yaml",
    "apps/review/app.py",
    "apps/review/app.yaml",
    "apps/admin/app.py",
    "apps/admin/app.yaml",
)


def check_paths(root: Path, required_paths: tuple[str, ...] = REQUIRED_PATHS) -> ReadinessResult:
    present: list[str] = []
    missing: list[str] = []

    for relative_path in required_paths:
        if (root / relative_path).exists():
            present.append(relative_path)
        else:
            missing.append(relative_path)

    return ReadinessResult(present=tuple(present), missing=tuple(missing))


def print_result(result: ReadinessResult) -> None:
    if result.ok:
        print("DocuBricks readiness check passed.")
        print(f"Present: {len(result.present)} required paths")
        return

    print("DocuBricks readiness check failed.")
    print(f"Present: {len(result.present)} required paths")
    print(f"Missing: {len(result.missing)} required paths")
    for missing_path in result.missing:
        print(f"  - {missing_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to check. Defaults to the current working directory.",
    )
    args = parser.parse_args()

    result = check_paths(args.root.resolve())
    print_result(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

