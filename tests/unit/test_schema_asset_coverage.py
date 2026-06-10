from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import unittest

from scripts.validate_schema_assets import (
    _check_required_fields_have_thresholds,
    validate_schema_assets,
)


class SchemaAssetCoverageTests(unittest.TestCase):
    def test_repo_schema_assets_meet_phase_4_and_5_gate(self):
        result = validate_schema_assets(Path(__file__).resolve().parents[2])

        self.assertTrue(result.ok, "\n".join(result.missing))
        self.assertGreaterEqual(
            sum(
                count
                for name, count in result.golden_counts.items()
                if name.startswith("fs/")
            ),
            50,
        )
        for doc_type in (
            "eob_cms1500",
            "clinical_note_soap",
            "lab_report",
            "prior_auth",
        ):
            self.assertGreaterEqual(result.golden_counts[f"healthcare/{doc_type}"], 5)
        for doc_type in (
            "commercial_loan_application",
            "commercial_credit_memo",
            "loan_agreement",
            "covenant_compliance_certificate",
            "collateral_schedule",
            "ucc_financing_statement",
            "guaranty_agreement",
            "security_agreement",
        ):
            self.assertGreaterEqual(result.golden_counts[f"fs/{doc_type}"], 1)
        for name in (
            "fs/third_party_risk_assessment",
            "fs/issue_management_record",
            "fs/trust_account_opening_package",
            "fs/merchant_onboarding_application",
            "fs/syndicated_credit_agreement",
            "legal/litigation_case_file",
            "fs/regulatory_reporting_package",
        ):
            self.assertGreaterEqual(result.golden_counts[name], 1)
        for doc_type in (
            "insurance_policy_application",
            "policy_declaration_page",
            "certificate_of_insurance",
            "insurance_claim_file",
            "first_notice_of_loss",
            "proof_of_loss",
            "claims_adjuster_report",
            "insurance_claim_denial_letter",
        ):
            self.assertGreaterEqual(result.golden_counts[f"insurance/{doc_type}"], 1)
        for doc_type in (
            "purchase_order",
            "bill_of_materials",
            "receiving_report",
            "supplier_scorecard",
            "quality_inspection_report",
            "certificate_of_analysis",
            "nonconformance_report",
            "corrective_preventive_action",
        ):
            self.assertGreaterEqual(result.golden_counts[f"manufacturing/{doc_type}"], 1)
        for doc_type in (
            "lease_agreement",
            "purchase_agreement",
            "closing_statement",
            "deed",
            "real_estate_transactions_title_commitment",
            "property_management_agreement",
            "rent_roll",
            "tenant_estoppel_certificate",
        ):
            self.assertGreaterEqual(result.golden_counts[f"real_estate/{doc_type}"], 1)
        for doc_type in (
            "daily_drilling_report",
            "well_completion_report",
            "production_report",
            "field_ticket",
        ):
            self.assertGreaterEqual(result.golden_counts[f"energy/{doc_type}"], 1)

    def test_reports_missing_healthcare_assets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = validate_schema_assets(root)

        self.assertFalse(result.ok)
        self.assertIn(
            "Schemas/fs golden corpus has 0 cases; expected at least 50",
            result.missing,
        )

    def test_schema_catalog_tracks_available_and_future_doc_types(self):
        catalog_path = Path(__file__).resolve().parents[2] / "Schemas" / "schema_catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        entries = catalog["document_types"]
        by_doc_type = {entry["doc_type"]: entry for entry in entries}
        verticals = {entry["vertical"] for entry in entries}

        self.assertEqual(len(entries), len(by_doc_type))
        self.assertGreaterEqual(len(entries), 150)
        self.assertEqual(
            verticals,
            {
                "fs",
                "healthcare",
                "legal",
                "insurance",
                "manufacturing",
                "real_estate",
                "energy",
            },
        )
        for entry in entries:
            self.assertIn(entry["availability"], {"available", "future"})

        for doc_type in (
            "commercial_loan_application",
            "commercial_credit_memo",
            "loan_agreement",
            "ucc_financing_statement",
            "security_agreement",
        ):
            self.assertEqual(by_doc_type[doc_type]["availability"], "available")
            self.assertEqual(by_doc_type[doc_type]["family"], "commercial_lending")

        for doc_type in (
            "consumer_security_agreement",
            "personal_loan_application",
            "privacy_notice",
            "chapter_13_filing",
            "bank_statement",
        ):
            self.assertEqual(by_doc_type[doc_type]["availability"], "future")

        for doc_type in (
            "third_party_risk_assessment",
            "issue_management_record",
            "trust_account_opening_package",
            "merchant_onboarding_application",
            "syndicated_credit_agreement",
            "litigation_case_file",
            "regulatory_reporting_package",
        ):
            self.assertEqual(by_doc_type[doc_type]["availability"], "available")

    def test_schema_catalog_has_roadmap_vertical_coverage(self):
        catalog_path = Path(__file__).resolve().parents[2] / "Schemas" / "schema_catalog.json"
        entries = json.loads(catalog_path.read_text(encoding="utf-8"))["document_types"]
        by_doc_type = {entry["doc_type"]: entry for entry in entries}

        for doc_type, vertical in {
            "work_order": "manufacturing",
            "commercial_real_estate_loan_application": "real_estate",
            "authorization_for_expenditure": "energy",
        }.items():
            self.assertIn(doc_type, by_doc_type)
            self.assertEqual(by_doc_type[doc_type]["vertical"], vertical)
            self.assertEqual(by_doc_type[doc_type]["availability"], "future")

    def test_insurance_claims_and_policy_ops_package_is_available(self):
        catalog_path = Path(__file__).resolve().parents[2] / "Schemas" / "schema_catalog.json"
        entries = json.loads(catalog_path.read_text(encoding="utf-8"))["document_types"]
        by_doc_type = {entry["doc_type"]: entry for entry in entries}

        expected = {
            "insurance_policy_application": "insurance_underwriting",
            "policy_declaration_page": "insurance_collateral_protection",
            "certificate_of_insurance": "insurance_collateral_protection",
            "insurance_claim_file": "insurance_collateral_protection",
            "first_notice_of_loss": "insurance_claims",
            "proof_of_loss": "insurance_collateral_protection",
            "claims_adjuster_report": "insurance_claims",
            "insurance_claim_denial_letter": "insurance_claims",
        }

        for doc_type, family in expected.items():
            self.assertIn(doc_type, by_doc_type)
            self.assertEqual(by_doc_type[doc_type]["vertical"], "insurance")
            self.assertEqual(by_doc_type[doc_type]["family"], family)
            self.assertEqual(by_doc_type[doc_type]["availability"], "available")

    def test_manufacturing_quality_and_supply_chain_package_is_available(self):
        catalog_path = Path(__file__).resolve().parents[2] / "Schemas" / "schema_catalog.json"
        entries = json.loads(catalog_path.read_text(encoding="utf-8"))["document_types"]
        by_doc_type = {entry["doc_type"]: entry for entry in entries}

        expected = {
            "purchase_order": "procurement_supply_chain",
            "bill_of_materials": "procurement_supply_chain",
            "receiving_report": "procurement_supply_chain",
            "supplier_scorecard": "procurement_supply_chain",
            "quality_inspection_report": "manufacturing_quality",
            "certificate_of_analysis": "manufacturing_quality",
            "nonconformance_report": "manufacturing_quality",
            "corrective_preventive_action": "manufacturing_quality",
        }

        for doc_type, family in expected.items():
            self.assertIn(doc_type, by_doc_type)
            self.assertEqual(by_doc_type[doc_type]["vertical"], "manufacturing")
            self.assertEqual(by_doc_type[doc_type]["family"], family)
            self.assertEqual(by_doc_type[doc_type]["availability"], "available")

    def test_real_estate_transactions_and_property_management_package_is_available(self):
        catalog_path = Path(__file__).resolve().parents[2] / "Schemas" / "schema_catalog.json"
        entries = json.loads(catalog_path.read_text(encoding="utf-8"))["document_types"]
        by_doc_type = {entry["doc_type"]: entry for entry in entries}

        expected = {
            "lease_agreement": "real_estate_transactions",
            "purchase_agreement": "real_estate_transactions",
            "closing_statement": "real_estate_transactions",
            "deed": "real_estate_transactions",
            "real_estate_transactions_title_commitment": "real_estate_transactions",
            "property_management_agreement": "property_management",
            "rent_roll": "property_management",
            "tenant_estoppel_certificate": "property_management",
        }

        for doc_type, family in expected.items():
            self.assertIn(doc_type, by_doc_type)
            self.assertEqual(by_doc_type[doc_type]["vertical"], "real_estate")
            self.assertEqual(by_doc_type[doc_type]["family"], family)
            self.assertEqual(by_doc_type[doc_type]["availability"], "available")

    def test_energy_upstream_operations_package_is_available(self):
        catalog_path = Path(__file__).resolve().parents[2] / "Schemas" / "schema_catalog.json"
        entries = json.loads(catalog_path.read_text(encoding="utf-8"))["document_types"]
        by_doc_type = {entry["doc_type"]: entry for entry in entries}

        expected = {
            "daily_drilling_report": "energy_upstream_operations",
            "well_completion_report": "energy_upstream_operations",
            "production_report": "energy_production_operations",
            "field_ticket": "energy_field_services",
        }

        for doc_type, family in expected.items():
            self.assertIn(doc_type, by_doc_type)
            self.assertEqual(by_doc_type[doc_type]["vertical"], "energy")
            self.assertEqual(by_doc_type[doc_type]["family"], family)
            self.assertEqual(by_doc_type[doc_type]["availability"], "available")

    def test_required_threshold_check_reports_legacy_array_format(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            fields_path = root / "fields.json"
            thresholds_path = root / "field_thresholds.json"
            fields_path.write_text(
                json.dumps(
                    {
                        "fields": [
                            {
                                "name": "purchase_order_number",
                                "type": "string",
                                "required": True,
                                "description": "PO number.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            thresholds_path.write_text("[]", encoding="utf-8")

            missing: list[str] = []
            _check_required_fields_have_thresholds(fields_path, thresholds_path, missing)

        self.assertEqual(
            missing,
            [
                f"{thresholds_path}: field_thresholds.json uses legacy array format; "
                "required field coverage cannot be evaluated"
            ],
        )

    def test_schema_catalog_has_broad_healthcare_industry_coverage(self):
        catalog_path = Path(__file__).resolve().parents[2] / "Schemas" / "schema_catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        healthcare_entries = [
            entry for entry in catalog["document_types"] if entry["vertical"] == "healthcare"
        ]
        by_doc_type = {entry["doc_type"]: entry for entry in healthcare_entries}
        families = {entry["family"] for entry in healthcare_entries}

        self.assertGreaterEqual(len(healthcare_entries), 80)
        for family in (
            "healthcare_claims",
            "clinical_documents",
            "healthcare_authorization",
            "revenue_cycle",
            "pharmacy",
            "imaging_diagnostics",
            "care_management",
            "patient_access",
            "quality_reporting",
            "provider_network",
        ):
            self.assertIn(family, families)

        for doc_type in (
            "ub_04_claim",
            "remittance_advice_835",
            "medical_record_request",
            "discharge_summary",
            "radiology_report",
            "pathology_report",
            "prescription",
            "medication_prior_authorization",
            "referral_authorization",
            "appeal_grievance_case",
            "hcc_risk_adjustment_chart",
            "hedis_quality_measure_packet",
            "provider_contract",
            "credentialing_application",
            "cms_star_ratings_evidence",
        ):
            self.assertIn(doc_type, by_doc_type)
            self.assertEqual(by_doc_type[doc_type]["availability"], "future")

    def test_available_schema_bundles_have_machine_readable_field_schemas(self):
        root = Path(__file__).resolve().parents[2]
        catalog = json.loads((root / "Schemas" / "schema_catalog.json").read_text(encoding="utf-8"))

        for entry in catalog["document_types"]:
            if entry["availability"] != "available":
                continue
            path = root / "Schemas" / entry["vertical"] / entry["doc_type"] / "fields.json"
            self.assertTrue(path.exists(), f"Missing field schema: {path}")

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["document_type"], entry["doc_type"])
            self.assertEqual(data["vertical"], entry["vertical"])
            self.assertIsInstance(data["fields"], list)
            self.assertGreater(len(data["fields"]), 0)

            seen_names = set()
            for field in data["fields"]:
                self.assertIn("name", field)
                self.assertIn("type", field)
                self.assertIn("required", field)
                self.assertIn("description", field)
                self.assertIsInstance(field["required"], bool)
                self.assertNotIn(field["name"], seen_names)
                seen_names.add(field["name"])

    def test_available_schema_bundles_have_sections_and_nested_array_contracts(self):
        root = Path(__file__).resolve().parents[2]
        catalog = json.loads((root / "Schemas" / "schema_catalog.json").read_text(encoding="utf-8"))

        for entry in catalog["document_types"]:
            if entry["availability"] != "available":
                continue
            path = root / "Schemas" / entry["vertical"] / entry["doc_type"] / "fields.json"
            data = json.loads(path.read_text(encoding="utf-8"))

            sections = data.get("sections")
            self.assertIsInstance(sections, list, f"Missing sections in {path}")
            self.assertGreater(len(sections), 0, f"Empty sections in {path}")
            section_ids = {section.get("id") for section in sections}
            self.assertNotIn(None, section_ids, f"Section missing id in {path}")

            checklist = data.get("completeness_checklist")
            self.assertIsInstance(checklist, list, f"Missing completeness_checklist in {path}")
            self.assertGreater(len(checklist), 0, f"Empty completeness_checklist in {path}")

            for field in data["fields"]:
                self.assertIn("section", field, f"{path}: {field['name']} missing section")
                self.assertIn(field["section"], section_ids)
                self.assertIn("category", field, f"{path}: {field['name']} missing category")
                if field["type"] == "array<object>":
                    item_schema = field.get("item_schema")
                    self.assertIsInstance(item_schema, list, f"{path}: {field['name']} missing item_schema")
                    self.assertGreater(len(item_schema), 0, f"{path}: {field['name']} empty item_schema")
                    for item_field in item_schema:
                        self.assertIn("name", item_field)
                        self.assertIn("type", item_field)
                        self.assertIn("description", item_field)

    def test_high_value_list_fields_have_domain_item_details(self):
        root = Path(__file__).resolve().parents[2]

        expectations = {
            ("fs", "collateral_schedule", "collateral_items"): {
                "asset_id",
                "asset_type",
                "asset_description",
                "value_amount",
                "lien_position",
                "perfection_status",
            },
            ("real_estate", "rent_roll", "tenant_entries"): {
                "unit_or_suite",
                "tenant_name",
                "lease_start_date",
                "lease_end_date",
                "monthly_rent_amount",
                "arrears_amount",
            },
            ("manufacturing", "purchase_order", "line_items"): {
                "line_number",
                "part_number",
                "description",
                "quantity",
                "unit_price",
                "due_date",
            },
            ("energy", "field_ticket", "equipment_lines"): {
                "equipment_id",
                "equipment_type",
                "description",
                "hours",
                "rate",
                "amount",
            },
        }

        for (vertical, doc_type, field_name), expected_names in expectations.items():
            path = root / "Schemas" / vertical / doc_type / "fields.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            field = next(item for item in data["fields"] if item["name"] == field_name)
            item_names = {item["name"] for item in field["item_schema"]}
            self.assertTrue(
                expected_names <= item_names,
                f"{path}: {field_name} missing item details {sorted(expected_names - item_names)}",
            )

    def test_prompt_catalog_tracks_centralized_prompts_for_available_schemas(self):
        root = Path(__file__).resolve().parents[2]
        schema_catalog = json.loads((root / "Schemas" / "schema_catalog.json").read_text(encoding="utf-8"))
        available = {
            entry["doc_type"]: entry
            for entry in schema_catalog["document_types"]
            if entry["availability"] == "available"
        }

        prompt_catalog_path = root / "Schemas" / "prompt_catalog.json"
        self.assertTrue(prompt_catalog_path.exists(), "Missing prompt catalog")
        prompt_catalog = json.loads(prompt_catalog_path.read_text(encoding="utf-8"))
        entries = prompt_catalog["prompts"]
        by_doc_type = {entry["doc_type"]: entry for entry in entries}

        self.assertEqual(set(available), set(by_doc_type))
        for doc_type, schema_entry in available.items():
            prompt_entry = by_doc_type[doc_type]
            self.assertEqual(prompt_entry["vertical"], schema_entry["vertical"])
            self.assertEqual(prompt_entry["schema_catalog_doc_type"], doc_type)
            self.assertEqual(prompt_entry["availability"], "available")

            prompt_path = root / prompt_entry["prompt_path"]
            self.assertTrue(prompt_path.exists(), f"Missing centralized prompt: {prompt_path}")
            self.assertTrue(prompt_entry["field_schema_path"].endswith("/fields.json"))
            self.assertTrue((root / prompt_entry["field_schema_path"]).exists())
            prompt_text = prompt_path.read_text(encoding="utf-8")
            self.assertEqual(
                hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
                prompt_entry["sha256"],
            )


if __name__ == "__main__":
    unittest.main()
