from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from support import SKILL_ROOT, create_source  # noqa: F401
from scripts.manifest import build_manifest, write_manifest
from scripts.process_icons import process_icon


class ManifestTests(unittest.TestCase):
    def test_manifest_lists_only_accepted_files_with_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            accepted = process_icon(create_source(root / "source.png"), "Add Driver", 1, "a1b2c3d4e5", root, "Driver plus")
            rejected = {"qa_status": "FAIL", "source_file": "missing.png"}
            document = build_manifest("run-1", "add a driver", "Add Driver", [accepted, rejected], root)
            self.assertEqual(len(document["options"]), 1)
            option = document["options"][0]
            self.assertEqual(option["salt"], "a1b2c3d4e5")
            self.assertEqual(len(option["sha256"]), 5)
            source_path = root / option["source_file"]
            self.assertEqual(option["sha256"][option["source_file"]], hashlib.sha256(source_path.read_bytes()).hexdigest())
            destination = write_manifest(root / "manifest.json", "run-1", "add a driver", "Add Driver", [accepted], root)
            self.assertEqual(json.loads(destination.read_text())["options"][0]["qa_status"], "PASS")

    def test_duplicate_option_salts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = process_icon(create_source(root / "one.png"), "Driver", 1, "a1b2c3d4e5", root)
            second = process_icon(create_source(root / "two.png", variant=2), "Driver", 2, "a1b2c3d4e5", root)
            with self.assertRaisesRegex(ValueError, "unique salts"):
                build_manifest("run", "driver", "Driver", [first, second], root)


if __name__ == "__main__":
    unittest.main()
