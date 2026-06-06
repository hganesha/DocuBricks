# ◈ DocuBricks

**Document intelligence, natively on Databricks. Built for regulated industries.**

[![Open in Databricks](https://databricks.com/wp-content/uploads/2021/10/databricks-solution-accelerator-badge.svg)](https://databricks.com/solutions/accelerators/docubricks)
[![Apache 2.0 License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Databricks CLI](https://img.shields.io/badge/Databricks%20CLI-%E2%89%A50.221-orange)](https://docs.databricks.com/dev-tools/cli/index.html)

---

## What this accelerator does

DocuBricks turns unstructured documents — mortgage applications, KYC/CDD forms, AML SARs, Explanation of Benefits, prior authorisations, and more — into structured, queryable Delta tables using Databricks Delta Live Tables and Foundation Model APIs. It ships with vertical-specific extraction agents that continuously monitor Silver tables, apply regulatory business logic, and route flagged items into a Lakebase-backed review queue for human-in-the-loop decisioning. Every extraction, confidence score, and agent action is audited end-to-end so your compliance team has a complete lineage trail.

## Supported Verticals

| Phase | Vertical | Status |
|-------|----------|--------|
| Phase 1 | Financial Services (mortgage, KYC/CDD, AML SAR, invoice) | Generally Available |
| Phase 2 | Healthcare (EOB/CMS-1500, prior authorisation) | Preview |
| Phase 2 | Legal (contracts, NDAs, court filings) | Preview |
| Roadmap | Insurance, Manufacturing, Real Estate | Coming Soon |

## Architecture Overview

DocuBricks is a three-layer Lakehouse architecture. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

```
┌──────────────────────────────────────────────────────────────────┐
│  Layer 1 — Ingestion (Bronze)                                    │
│  Autoloader watches Unity Catalog Volumes per tenant/vertical.   │
│  Documents are SHA-256 fingerprinted and quarantined if corrupt. │
├──────────────────────────────────────────────────────────────────┤
│  Layer 2 — Extraction (Silver)                                   │
│  DLT streaming pipeline: parse → classify → route → extract.    │
│  Foundation Model API (Claude / DBRX) runs per-vertical prompts  │
│  with configurable confidence thresholds and validation rules.   │
├──────────────────────────────────────────────────────────────────┤
│  Layer 3 — Intelligence (Gold + Agents)                          │
│  Gold tables aggregate KPIs, compliance summaries, and alerts.   │
│  Scheduled agents apply domain logic and write to Lakebase       │
│  review_queue. Genie answers natural-language questions.         │
└──────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- [ ] Databricks workspace with Unity Catalog enabled
- [ ] Foundation Model API enabled (workspace settings → Model Serving → Enable Foundation Model APIs)
- [ ] Lakebase instance provisioned (workspace settings → Lakebase → Create instance)
- [ ] Databricks CLI >= 0.221 installed locally (`databricks --version`)

## Quick Install

```bash
git clone https://github.com/your-org/docubricks.git
cp .env.example .env          # fill in DATABRICKS_HOST and DATABRICKS_TOKEN
databricks bundle deploy --target dev
```

After deployment, run the bootstrap job from the Databricks UI or via:

```bash
databricks jobs run-now --job-name "DocuBricks — Bootstrap [dev]"
```

## Or Use the Setup Wizard

For a guided installation experience, open the DocuBricks Onboarding App directly in your workspace after deployment:

```
https://<your-workspace>.azuredatabricks.net/apps/docubricks-onboarding
```

The wizard walks you through secret configuration, vertical selection, first-document upload, and smoke testing in under 10 minutes.

## Schema Bundles

| Vertical | Document Types | Regulatory Alignment |
|----------|---------------|---------------------|
| Financial Services | Mortgage Application, KYC/CDD Form, AML SAR, Invoice | CFPB Reg B, FinCEN BSA/AML, SOX |
| Healthcare | EOB / CMS-1500, Prior Authorisation | HIPAA, CMS billing rules |
| Legal | Contracts, NDAs, Court Filings | GDPR Art. 30, e-SIGN Act |
| Insurance | Policy Applications, Claims | NAIC Model Laws |
| Manufacturing | Purchase Orders, Quality Records | ISO 9001, IATF 16949 |
| Real Estate | Leases, Title, Property Management | RESPA, local recording rules |

## Pricing Tiers

| Tier | Price | Included |
|------|-------|----------|
| Community | Free | 1 vertical, 1 tenant, community support, Apache 2.0 |
| Starter | $2,500 / month | 2 verticals, 5 tenants, schema customisation, email support |
| Professional | $8,500 / month | All verticals, unlimited tenants, agents, Genie, SLA support |
| Enterprise | Custom | Private deployment, custom schema authoring, dedicated CSM |

> Community tier is licensed under Apache 2.0. Starter, Professional, and Enterprise tiers are governed by the DocuBricks Commercial License. See [LICENSE](LICENSE) for details.

## Documentation

| Guide | Description |
|-------|-------------|
| [Quick Start](docs/quickstart.md) | Deploy and run your first document end-to-end |
| [Configuration](docs/configuration.md) | All variables, secrets, and environment settings |
| [Schema Authoring](docs/schema-authoring.md) | Add new document types or customise extraction prompts |
| [Troubleshooting](docs/troubleshooting.md) | Operational runbook for common issues |
| [Architecture](ARCHITECTURE.md) | Full system design and design decisions |

## License

Community tier: [Apache License 2.0](LICENSE).
Paid tiers (Starter, Professional, Enterprise): DocuBricks Commercial License — contact sales@docubricks.io.
