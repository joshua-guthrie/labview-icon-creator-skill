from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from support import SKILL_ROOT, create_source  # noqa: F401
from scripts.process_icons import process_icon
from scripts.validate_icon_assets import has_failures, measurable_metrics, validate_ico, validate_option_assets, validate_png, validate_proportional_geometry


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

    def test_opaque_background_png_fails_when_transparency_is_declared(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Opaque option 1 29x29 a1b2c3d4e5.png"
            image = Image.new("RGB", (29, 29), "white")
            for x in range(8, 21):
                for y in range(8, 21):
                    image.putpixel((x, y), (20, 90, 180))
            image.save(path)
            checks = validate_png(path, (29, 29), "transparent")
            failed_rules = {check["rule_id"] for check in checks if check["result"] == "FAIL"}
            self.assertIn("FILE-PNG-004", failed_rules)
            self.assertIn("FILE-PNG-008", failed_rules)

    def test_nonwhite_outer_corner_fails_when_white_is_declared(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Tinted option 1 29x29 a1b2c3d4e5.png"
            image = Image.new("RGB", (29, 29), (250, 250, 245))
            for x in range(8, 21):
                for y in range(8, 21):
                    image.putpixel((x, y), (20, 90, 180))
            image.save(path)
            checks = validate_png(path, (29, 29), "white")
            failed_rules = {check["rule_id"] for check in checks if check["result"] == "FAIL"}
            self.assertIn("FILE-PNG-008", failed_rules)

    def test_metrics_report_margin_occupancy_and_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = create_source(Path(directory) / "source.png")
            with Image.open(path) as image:
                metrics = measurable_metrics(image)
            self.assertGreater(metrics["occupancy"], 0.5)
            self.assertGreater(metrics["minimum_edge_margin_fraction"], 0.1)
            self.assertGreater(metrics["contrast_span"], 20)

    def test_malformed_geometry_is_a_structured_failure(self) -> None:
        check = validate_proportional_geometry({
            "source_artwork_size": [100, 100],
            "rendered_artwork_size": [50, 50],
            "canvas_size": [30, 18],
            "offset": [0, 0],
        })
        self.assertEqual(check["rule_id"], "PROCESS-GEOMETRY-001")
        self.assertEqual(check["result"], "FAIL")
        self.assertIn("centered", check["threshold"])

    def test_corrupt_ico_fails_decoding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Corrupt option 1 a1b2c3d4e5.ico"
            path.write_bytes(b"\x00\x00\x01\x00\x01\x00\x00\x00")
            checks = validate_ico(path, "white")
            failed_rules = {check["rule_id"] for check in checks if check["result"] == "FAIL"}
            self.assertIn("FILE-ICO-007", failed_rules)

    def test_incomplete_ico_fails_frame_completeness_and_decoding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Incomplete option 1 a1b2c3d4e5.ico"
            Image.new("RGB", (16, 16), "white").save(path, format="ICO", sizes=[(16, 16)])
            checks = validate_ico(path, "white")
            failed_rules = {check["rule_id"] for check in checks if check["result"] == "FAIL"}
            self.assertIn("FILE-ICO-004", failed_rules)
            self.assertIn("FILE-ICO-005", failed_rules)

if __name__ == "__main__":
    unittest.main()
