from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from support import SKILL_ROOT, create_source  # noqa: F401
from scripts.process_icons import process_icon
from scripts.validate_icon_assets import has_failures, measurable_metrics, validate_option_assets, validate_png


class ValidationTests(unittest.TestCase):
    def test_processed_option_passes_technical_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = process_icon(create_source(root / "source.png"), "Add Driver", 1, "a1b2c3d4e5", root)
            checks = validate_option_assets(metadata, root)
            failures = [check for check in checks if check["result"] == "FAIL"]
            self.assertEqual(failures, [])

    def test_blank_and_wrong_dimension_png_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Blank option 1 29x29 a1b2c3d4e5.png"
            Image.new("RGB", (28, 29), "white").save(path)
            checks = validate_png(path, (29, 29))
            failed_rules = {check["rule_id"] for check in checks if check["result"] == "FAIL"}
            self.assertIn("FILE-PNG-003", failed_rules)
            self.assertIn("FILE-PNG-005", failed_rules)
            self.assertIn("NAME-PNG-001", failed_rules)

    def test_metrics_report_margin_occupancy_and_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = create_source(Path(directory) / "source.png")
            with Image.open(path) as image:
                metrics = measurable_metrics(image)
            self.assertGreater(metrics["occupancy"], 0.5)
            self.assertGreater(metrics["minimum_edge_margin_fraction"], 0.1)
            self.assertGreater(metrics["contrast_span"], 20)


if __name__ == "__main__":
    unittest.main()
