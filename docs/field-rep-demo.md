# DocuBricks Field-Rep Demo

This runbook supports a 20-minute field demo for a Professional-tier healthcare workspace.

## Workspace Assumptions

- Databricks workspace has Unity Catalog, serverless SQL, Vector Search, Genie, and Apps enabled.
- Bundle target is `dev` or `demo`.
- Demo catalog is `docubricks_demo`.
- Schema tier is `professional`.
- Vertical is `healthcare`.

## Demo Flow

1. Launch the onboarding app and create a demo project named `Healthcare Revenue Cycle`.
2. Select the Healthcare vertical and Professional tier.
3. Provision the workspace resources through the onboarding deploy screen.
4. Upload one EOB/CMS-1500 sample and one prior authorization sample.
5. Open the Review app and show field-level confidence, thresholds, and correction capture.
6. Open the Portal app and show processing status, document registry, and Genie questions.
7. Open the Admin app and show schema prompts, accuracy trend hooks, and tenant configuration.

## Talk Track

- Community tier proves the architecture with Financial Services templates.
- Professional tier adds healthcare schemas, review workflows, confidence thresholds, and demo-ready workspace assets.
- Enterprise tier adds all verticals, custom schema bundles, dedicated support, and private Marketplace offer motion.

## Healthcare Demo Questions

- Which claims were denied and need appeal follow-up?
- Which prior authorizations are expiring in the next 30 days?
- Which extracted fields are below review thresholds?
- Which document types are driving the most human review volume?

## Validation Before Demo

Run these checks from the repo root:

```bash
python3 scripts/check_readiness.py
python3 scripts/validate_schema_assets.py
python3 -m pytest tests/unit -q
```

Run `databricks bundle validate` after installing and authenticating the Databricks CLI.

