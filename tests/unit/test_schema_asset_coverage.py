from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.validate_schema_assets import validate_schema_assets


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

    def test_reports_missing_healthcare_assets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = validate_schema_assets(root)

        self.assertFalse(result.ok)
        self.assertIn(
            "Schemas/fs golden corpus has 0 cases; expected at least 50",
            result.missing,
        )


if __name__ == "__main__":
    unittest.main()

