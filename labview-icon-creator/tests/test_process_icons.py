from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from support import SKILL_ROOT, create_source  # noqa: F401
from scripts.preview_sheet import create_contact_sheet
from scripts.process_icons import ICO_SIZES, PNG_SIZES, process_icon, remove_outer_white


class ProcessIconTests(unittest.TestCase):
    def test_exact_canvases_proportional_centering_and_ico(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = create_source(root / "source.png")
            metadata = process_icon(source, "Add Driver", 1, "a1b2c3d4e5", root, "Driver plus")
            self.assertEqual(metadata["source_dimensions"], [1024, 1024])
            for item, expected in zip(metadata["derived_png_files"], PNG_SIZES):
                with Image.open(root / item["file"]) as image:
                    self.assertEqual(image.size, expected)
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.getpixel((0, 0))[3], 0)
                geometry = item["geometry"]
                source_width, source_height = geometry["source_artwork_size"]
                rendered_width, rendered_height = geometry["rendered_artwork_size"]
                self.assertAlmostEqual(rendered_width / source_width, rendered_height / source_height, delta=0.03)
                self.assertGreaterEqual(geometry["offset"][0], 0)
                self.assertGreaterEqual(geometry["offset"][1], 0)
            with Image.open(root / metadata["ico_file"]) as ico:
                self.assertEqual(ico.format, "ICO")
                self.assertTrue(set(ICO_SIZES).issubset(set(ico.ico.sizes())))
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                process_icon(source, "Add Driver", 1, "a1b2c3d4e5", root)

    def test_non_square_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_source(root / "source.png", (256, 200))
            with self.assertRaisesRegex(ValueError, "must be square"):
                process_icon(root / "source.png", "Driver", 1, "a1b2c3d4e5", root)

    def test_outer_white_becomes_transparent_but_enclosed_white_survives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = create_source(Path(directory) / "source.png")
            with Image.open(path) as image:
                transparent, applied = remove_outer_white(image)
            self.assertTrue(applied)
            self.assertEqual(transparent.getpixel((0, 0))[3], 0)
            self.assertEqual(transparent.getpixel((112, 104))[3], 255)

    def test_contact_sheet_has_native_and_magnified_previews(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = create_source(root / "source.png")
            output = create_contact_sheet([{"source": str(source), "label": "Candidate 1"}], root / "qa.png", 10)
            with Image.open(output) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 1000)
                self.assertGreater(image.height, 200)


if __name__ == "__main__":
    unittest.main()
