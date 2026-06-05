from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.check_readiness import check_paths


class CheckReadinessTests(unittest.TestCase):
    def test_reports_missing_paths(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = check_paths(root, ("databricks.yml", "src/bootstrap/setup_lakebase.py"))

        self.assertFalse(result.ok)
        self.assertEqual(result.present, ())
        self.assertEqual(
            result.missing,
            ("databricks.yml", "src/bootstrap/setup_lakebase.py"),
        )

    def test_reports_success_when_all_paths_exist(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src/bootstrap").mkdir(parents=True)
            (root / "databricks.yml").write_text("bundle:\n  name: test\n")
            (root / "src/bootstrap/setup_lakebase.py").write_text("# ok\n")

            result = check_paths(root, ("databricks.yml", "src/bootstrap/setup_lakebase.py"))

        self.assertTrue(result.ok)
        self.assertEqual(
            result.present,
            ("databricks.yml", "src/bootstrap/setup_lakebase.py"),
        )
        self.assertEqual(result.missing, ())


if __name__ == "__main__":
    unittest.main()

