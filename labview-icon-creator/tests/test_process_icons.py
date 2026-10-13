from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from support import SKILL_ROOT, create_source  # noqa: F401
from scripts.workspace import temporary_directory
from scripts.preview_sheet import create_contact_sheet, validate_source_paths
from scripts.process_icons import (ICO_SIZES, PNG_SIZES, apply_background, create_ico, fit_artwork,
                                   normalize_master, open_source, process_icon, publish_staged_files, remove_outer_white)


class ProcessIconTests(unittest.TestCase):
    def test_each_ico_frame_has_exact_corners_and_matches_reviewed_render(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            # High-contrast geometry close to the source edge reproduces the
            # conditions where resizing an opaque master rings into corners.
            from PIL import ImageDraw
            source = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
            ImageDraw.Draw(source).rectangle((2, 2, 900, 800), fill=(0, 40, 100, 255))
            source.save(root / "source.png")
            master = normalize_master(open_source(root / "source.png"))
            for background in ("white", "transparent"):
                ico_path = root / f"{background}.ico"
                create_ico(master, ico_path, background)
                with Image.open(ico_path) as ico:
                    self.assertEqual(set(ico.ico.sizes()), set(ICO_SIZES))
                    for size in ICO_SIZES:
                        decoded = ico.ico.getimage(size).convert("RGBA")
                        expected = apply_background(fit_artwork(master, size)[0], background).convert("RGBA")
                        self.assertEqual(decoded.tobytes(), expected.tobytes())
                        for point in ((0, 0), (size[0]-1, 0), (0, size[1]-1), (size[0]-1, size[1]-1)):
                            if background == "white":
                                self.assertEqual(decoded.getpixel(point), (255, 255, 255, 255))
                            else:
                                self.assertEqual(decoded.getpixel(point)[3], 0)

    def test_explicit_staging_root_and_collision_preserve_existing_files(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            output = root / "output"
            stage = root / "stage"
            output.mkdir()
            process_icon(create_source(root / "source.png"), "Staged", 1, "a1b2c3d4e5", output,
                         staging_root=stage)
            self.assertEqual(list(stage.iterdir()), [])
            with self.assertRaisesRegex(ValueError, "outside"):
                process_icon(root / "source.png", "Wrong Stage", 1, "b1b2c3d4e5", output,
                             staging_root=output / "stage")
            (stage / "existing.txt").write_text("new")
            (output / "existing.txt").write_text("previous")
            with self.assertRaises(FileExistsError):
                publish_staged_files(stage, output, ["existing.txt"])
            self.assertEqual((output / "existing.txt").read_text(), "previous")

    def test_exact_canvases_proportional_centering_and_ico(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            source = create_source(root / "source.png")
            metadata = process_icon(source, "Add Driver", 1, "a1b2c3d4e5", root, "Driver plus")
            self.assertEqual(metadata["source_dimensions"], [1024, 1024])
            self.assertEqual(metadata["background_mode"], "white")
            for item, expected in zip(metadata["derived_png_files"], PNG_SIZES):
                with Image.open(root / item["file"]) as image:
                    self.assertEqual(image.size, expected)
                    self.assertEqual(image.mode, "RGB")
                    self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
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

    def test_transparent_background_is_available_when_requested(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            metadata = process_icon(
                create_source(root / "source.png"),
                "Add Driver",
                1,
                "a1b2c3d4e5",
                root,
                background_mode="transparent",
            )
            self.assertEqual(metadata["background_mode"], "transparent")
            for filename in [metadata["source_file"], *(item["file"] for item in metadata["derived_png_files"])]:
                with Image.open(root / filename) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_white_background_is_applied_after_resampling_for_antialiasing(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            source = root / "source.png"
            image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            from PIL import ImageDraw
            ImageDraw.Draw(image).ellipse((36, 36, 220, 220), fill="black")
            image.save(source)
            metadata = process_icon(source, "Smooth Edge", 1, "a1b2c3d4e5", root)
            smallest = root / metadata["derived_png_files"][-1]["file"]
            with Image.open(smallest) as reduced:
                grayscale_edges = [pixel[0] for pixel in getattr(reduced, "get_flattened_data", reduced.getdata)()
                                   if pixel[0] == pixel[1] == pixel[2]]
            self.assertTrue(any(0 < value < 255 for value in grayscale_edges))

    def test_non_square_source_is_rejected(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            create_source(root / "source.png", (256, 200))
            with self.assertRaisesRegex(ValueError, "must be square"):
                process_icon(root / "source.png", "Driver", 1, "a1b2c3d4e5", root)

    def test_outer_white_becomes_transparent_but_enclosed_white_survives(self) -> None:
        with temporary_directory() as directory:
            path = create_source(Path(directory) / "source.png")
            with Image.open(path) as image:
                transparent, applied = remove_outer_white(image)
            self.assertTrue(applied)
            self.assertEqual(transparent.getpixel((0, 0))[3], 0)
            self.assertEqual(transparent.getpixel((112, 104))[3], 255)

    def test_contact_sheet_has_native_and_magnified_previews(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            source = create_source(root / "source.png")
            output = create_contact_sheet([{"source": str(source), "label": "Candidate 1"}], root / "qa.png", 10)
            with Image.open(output) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 1000)
                self.assertGreater(image.height, 200)

    def test_processing_stages_outside_output_directory(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            real_temporary_directory = temporary_directory
            with patch("scripts.process_icons.temporary_directory") as factory:
                factory.side_effect = lambda *args, **kwargs: real_temporary_directory(*args, **kwargs)
                process_icon(create_source(root / "source.png"), "Staged", 1, "a1b2c3d4e5", root)
            self.assertNotIn("dir", factory.call_args.kwargs)

    def test_staged_validation_failure_publishes_nothing(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            with patch(
                "scripts.validate_icon_assets.validate_option_assets",
                return_value=[{"rule_id": "PROCESS-GEOMETRY-001", "result": "FAIL"}],
            ), patch("scripts.validate_icon_assets.has_failures", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "PROCESS-GEOMETRY-001"):
                    process_icon(create_source(root / "source.png"), "Rejected", 1, "a1b2c3d4e5", root)
            self.assertEqual(list(root.glob("Rejected option *")), [])

    def test_partial_publication_rolls_back_created_files(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            staging = root / "staging"
            output = root / "output"
            staging.mkdir()
            output.mkdir()
            names = ["one.txt", "two.txt", "three.txt"]
            for name in names:
                (staging / name).write_text(name, encoding="utf-8")
            real_open = Path.open
            calls = 0

            def fail_on_second_open(path: Path, *args, **kwargs):
                nonlocal calls
                if path.parent == output:
                    calls += 1
                    if calls == 2:
                        raise OSError("simulated publication failure")
                return real_open(path, *args, **kwargs)

            with patch.object(Path, "open", new=fail_on_second_open):
                with self.assertRaisesRegex(OSError, "simulated publication failure"):
                    publish_staged_files(staging, output, names)
            self.assertEqual(list(output.iterdir()), [])

    def test_preview_sources_must_be_explicit_existing_distinct_files(self) -> None:
        with temporary_directory() as directory:
            source = create_source(Path(directory) / "source.png")
            self.assertEqual(validate_source_paths([source]), [source.resolve()])
            with self.assertRaisesRegex(ValueError, "does not exist"):
                validate_source_paths([Path(directory) / "missing.png"])
            with self.assertRaisesRegex(ValueError, "distinct"):
                validate_source_paths([source, source])

if __name__ == "__main__":
    unittest.main()
