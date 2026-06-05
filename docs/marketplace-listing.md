# Databricks Marketplace Listing Draft

## Listing Name

DocuBricks Document AI Accelerator

## Short Description

Deploy governed document ingestion, extraction, human review, and analytics workflows on Databricks with ready-made schema packs for Financial Services and Healthcare.

## Category

Solution Accelerator / Industry Solution

## Target Users

- Data and AI teams building document processing on Databricks.
- Financial Services teams processing mortgage, KYC/CDD, AML SAR, and invoice workflows.
- Healthcare revenue cycle and utilization management teams processing EOB/CMS-1500, clinical notes, lab reports, and prior authorization packets.

## Included Assets

- Databricks Asset Bundle configuration.
- Lakebase and Unity Catalog bootstrap scripts.
- Bronze, Silver, and Gold pipelines.
- Databricks Apps for onboarding, portal, review, and administration.
- Schema registry assets with prompts, validation rules, confidence thresholds, model routing, and golden tests.
- Genie and Vector Search hooks.
- Unit tests and readiness validation scripts.

## Pricing Tiers

- Community: Apache 2.0 starter assets and Financial Services starter schemas.
- Starter: production packaging for Financial Services workflows.
- Professional: Healthcare schema bundle, review workflows, demo workspace assets, and support.
- Enterprise: all verticals, custom schema development, private offer terms, and dedicated enablement.

## Marketplace Readiness Checklist

- Repository package complete for Phase 4 and Phase 5.
- `scripts/check_readiness.py` passes locally.
- `scripts/validate_schema_assets.py` passes locally.
- Unit tests pass locally.
- Databricks CLI authenticated and `databricks bundle validate` passes.
- Demo workspace deployed and validated with sample documents.
- Private offer, commercial license, screenshots, and seller profile submitted in Databricks Marketplace.

## Current External Gates

- Databricks Marketplace seller registration and private offer setup.
- Design-partner approval to use anonymized production-like documents.
- Cross-cloud workspace validation on AWS, Azure, and GCP.

