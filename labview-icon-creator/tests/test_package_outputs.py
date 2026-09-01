from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import SKILL_ROOT, create_source  # noqa: F401
from scripts.manifest import write_manifest
from scripts.process_icons import process_icon
from scripts.validate_icon_assets import has_failures, validate_package


class PackageOutputTests(unittest.TestCase):
    def test_five_options_produce_exactly_25_icon_files_without_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = []
            for number in range(1, 6):
                source = create_source(root / f"candidate-{number}.png", variant=number)
                options.append(process_icon(source, "Driver Manager", number, f"salt{number:06d}", root, f"Concept {number}"))
                source.unlink()
            checks = validate_package(options, root)
            self.assertFalse(has_failures(checks))
            write_manifest(root / "manifest.json", "run-5", "driver manager", "Driver Manager", options, root)
            icon_files = list(root.glob("Driver Manager option *"))
            self.assertEqual(len(icon_files), 25)
            self.assertEqual(len(list(root.glob("*.png"))), 20)
            self.assertEqual(len(list(root.glob("*.ico"))), 5)
            self.assertTrue((root / "manifest.json").is_file())
            self.assertFalse(list(root.glob("*.zip")))


if __name__ == "__main__":
    unittest.main()
