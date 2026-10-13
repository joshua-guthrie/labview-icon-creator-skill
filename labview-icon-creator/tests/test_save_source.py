from __future__ import annotations

import base64
import unittest
from pathlib import Path

from PIL import Image

from support import create_source
from scripts.save_source import decode_payload, save_source
from scripts.workspace import temporary_directory


class SourceTransportTests(unittest.TestCase):
    def test_local_and_stdin_payload_routes_preserve_identical_source_bytes(self):
        with temporary_directory() as folder:
            root = Path(folder)
            source = create_source(root / "original.png")
            payload = "data:image/png;base64," + base64.b64encode(source.read_bytes()).decode("ascii")
            local = save_source(root / "local.png", source=source)
            stdin = save_source(root / "stdin.png", payload=payload)
            self.assertEqual(local["sha256"], stdin["sha256"])
            self.assertEqual((root / "stdin.png").read_bytes(), source.read_bytes())
            with self.assertRaises(FileExistsError):
                save_source(root / "stdin.png", payload=payload)

    def test_malformed_transport_is_rejected_before_source_publication(self):
        for payload in ("data:image/jpeg;base64,abcd", "data:image/png;base64,???"):
            with self.assertRaises(ValueError):
                decode_payload(payload)
        with temporary_directory() as folder:
            root = Path(folder)
            payload = "data:image/png;base64," + base64.b64encode(b"corrupt").decode()
            with self.assertRaises(OSError):
                save_source(root / "bad.png", payload=payload)
            self.assertFalse((root / "bad.png").exists())

    def test_nonsquare_and_nonpng_sources_are_rejected(self):
        with temporary_directory() as folder:
            root = Path(folder)
            create_source(root / "wide.png", size=(256, 200))
            Image.new("RGB", (30, 30)).save(root / "photo.jpg")
            for source in (root / "wide.png", root / "photo.jpg"):
                with self.assertRaisesRegex(ValueError, "square PNG"):
                    save_source(root / "candidate.png", source=source)
            self.assertFalse((root / "candidate.png").exists())


if __name__ == "__main__":
    unittest.main()
