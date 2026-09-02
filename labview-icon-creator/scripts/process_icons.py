#!/usr/bin/env python3
"""Create exact PNG derivatives and a multi-resolution ICO from an accepted source."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw

try:
    from .naming import generate_salt, ico_filename, png_filename, sanitize_summary_name
except ImportError:  # Direct script execution.
    from naming import generate_salt, ico_filename, png_filename, sanitize_summary_name

MASTER_SIZE = (1024, 1024)
PNG_SIZES = ((29, 29), (30, 23), (30, 18))
ICO_SIZES = ((16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256))
BACKGROUND_MODES = ("white", "transparent")
DEFAULT_BACKGROUND_MODE = "white"


def open_source(path: str | Path) -> Image.Image:
    source_path = Path(path)
    if not source_path.is_file() or source_path.stat().st_size == 0:
        raise ValueError(f"source is missing or empty: {source_path}")
    with Image.open(source_path) as image:
        image.load()
        if image.format != "PNG":
            raise ValueError(f"accepted source must be PNG, got {image.format!r}")
        if image.width != image.height:
            raise ValueError("source must be square; non-square normalization would distort it")
        return image.convert("RGBA")


def normalize_master(image: Image.Image) -> Image.Image:
    # Processing uses one transparent artwork layer. The selected final
    # background is applied only after each size is resampled.
    transparent, _ = remove_outer_white(image)
    if transparent.size == MASTER_SIZE:
        return transparent
    return transparent.resize(MASTER_SIZE, Image.Resampling.LANCZOS)


def validate_background_mode(background_mode: str) -> str:
    mode = str(background_mode).strip().lower()
    if mode not in BACKGROUND_MODES:
        raise ValueError(f"background mode must be one of: {', '.join(BACKGROUND_MODES)}")
    return mode


def apply_background(image: Image.Image, background_mode: str) -> Image.Image:
    """Apply the final background after resizing to preserve antialiased edges."""

    mode = validate_background_mode(background_mode)
    rgba = image.convert("RGBA")
    if mode == "transparent":
        return rgba
    white = Image.new("RGB", rgba.size, "white")
    white.paste(rgba.convert("RGB"), mask=rgba.getchannel("A"))
    return white


def foreground_bbox(image: Image.Image, tolerance: int = 12) -> tuple[int, int, int, int] | None:
    """Estimate non-background artwork bounds against the top-left background."""

    alpha = image.convert("RGBA").getchannel("A")
    mask = alpha.point(lambda value: 255 if value > tolerance else 0)
    return mask.getbbox()


def fit_artwork(
    master: Image.Image,
    target_size: tuple[int, int],
    margin_pixels: int = 1,
) -> tuple[Image.Image, dict[str, Any]]:
    """Fit detected artwork proportionally into an exact transparent canvas."""

    bbox = foreground_bbox(master)
    if bbox is None:
        raise ValueError("source appears blank")
    artwork = master.crop(bbox)
    available_width = max(1, target_size[0] - 2 * margin_pixels)
    available_height = max(1, target_size[1] - 2 * margin_pixels)
    scale = min(available_width / artwork.width, available_height / artwork.height)
    width = max(1, min(available_width, round(artwork.width * scale)))
    height = max(1, min(available_height, round(artwork.height * scale)))
    resized = artwork.resize((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    offset = ((target_size[0] - width) // 2, (target_size[1] - height) // 2)
    canvas.alpha_composite(resized, offset)
    return canvas, {
        "source_artwork_bbox": list(bbox),
        "source_artwork_size": [artwork.width, artwork.height],
        "rendered_artwork_size": [width, height],
        "canvas_size": list(target_size),
        "scale": scale,
        "offset": list(offset),
    }


def remove_outer_white(image: Image.Image, threshold: int = 238) -> tuple[Image.Image, bool]:
    """Conservatively make only border-connected near-white background transparent."""

    rgba = image.convert("RGBA")
    red, green, blue, original_alpha = rgba.split()
    bright = ImageChops.multiply(
        ImageChops.multiply(red.point(lambda value: 255 if value >= threshold else 0),
                            green.point(lambda value: 255 if value >= threshold else 0)),
        blue.point(lambda value: 255 if value >= threshold else 0),
    )
    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    minimum = ImageChops.darker(ImageChops.darker(red, green), blue)
    neutral = ImageChops.difference(maximum, minimum).point(
        lambda value: 255 if value <= 20 else 0
    )
    candidates = ImageChops.multiply(bright, neutral)
    width, height = candidates.size
    border_values = []
    border_values.extend(candidates.crop((0, 0, width, 1)).getdata())
    border_values.extend(candidates.crop((0, height - 1, width, height)).getdata())
    border_values.extend(candidates.crop((0, 1, 1, height - 1)).getdata())
    border_values.extend(candidates.crop((width - 1, 1, width, height - 1)).getdata())
    if not border_values or sum(value == 255 for value in border_values) / len(border_values) < 0.75:
        return rgba, False

    connected = candidates.copy()
    seed = next(
        (
            (x, y)
            for y in (0, height - 1)
            for x in range(width)
            if connected.getpixel((x, y)) == 255
        ),
        None,
    )
    if seed is None:
        return rgba, False
    ImageDraw.floodfill(connected, seed, 128, border=0)
    connected_mask = connected.point(lambda value: 255 if value == 128 else 0)
    coverage = connected_mask.histogram()[255] / (width * height)
    if not 0.05 <= coverage <= 0.95:
        return rgba, False
    retained_alpha = ImageChops.multiply(original_alpha, ImageChops.invert(connected_mask))
    result = rgba.copy()
    result.putalpha(retained_alpha)
    return result, True


def create_ico(master: Image.Image, destination: Path, background_mode: str) -> None:
    rendered = apply_background(master, background_mode)
    rendered.save(destination, format="ICO", sizes=list(ICO_SIZES), bitmap_format="png")


def process_icon(
    source: str | Path,
    summary_name: str,
    option_number: int,
    salt: str | None = None,
    output_dir: str | Path = ".",
    concept_summary: str = "",
    background_mode: str = DEFAULT_BACKGROUND_MODE,
) -> dict[str, Any]:
    """Process one visually accepted source and return manifest-ready metadata."""

    summary_name = sanitize_summary_name(summary_name)
    background_mode = validate_background_mode(background_mode)
    permanent_salt = salt or generate_salt()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    master_artwork = normalize_master(open_source(source))

    source_name = png_filename(summary_name, option_number, *MASTER_SIZE, permanent_salt)
    png_names = [png_filename(summary_name, option_number, *size, permanent_salt) for size in PNG_SIZES]
    ico_name = ico_filename(summary_name, option_number, permanent_salt)
    final_paths = [output / name for name in [source_name, *png_names, ico_name]]
    existing = [path.name for path in final_paths if path.exists()]
    if existing:
        raise FileExistsError("refusing to overwrite existing deliverables: " + ", ".join(existing))

    derivatives: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="labview-icon-process-", dir=output) as temporary:
        staging = Path(temporary)
        apply_background(master_artwork, background_mode).save(staging / source_name, format="PNG", optimize=True)
        for size, name in zip(PNG_SIZES, png_names):
            derivative, geometry = fit_artwork(master_artwork, size)
            apply_background(derivative, background_mode).save(staging / name, format="PNG", optimize=True)
            derivatives.append({"file": name, "dimensions": list(size), "geometry": geometry})
        create_ico(master_artwork, staging / ico_name, background_mode)

        for name in [source_name, *png_names, ico_name]:
            staged = staging / name
            if not staged.is_file() or staged.stat().st_size == 0:
                raise RuntimeError(f"processing did not create a valid file: {name}")
        metadata = {
            "option_number": option_number,
            "concept_summary": concept_summary,
            "salt": permanent_salt,
            "source_file": source_name,
            "source_dimensions": list(MASTER_SIZE),
            "background_mode": background_mode,
            "derived_png_files": derivatives,
            "ico_file": ico_name,
            "ico_sizes": [list(size) for size in ICO_SIZES],
            "ico_background": f"{background_mode}_background",
            "qa_status": "PASS",
        }
        try:
            from .validate_icon_assets import has_failures, validate_option_assets
        except ImportError:  # Direct script execution.
            from validate_icon_assets import has_failures, validate_option_assets
        staged_checks = validate_option_assets(metadata, staging)
        if has_failures(staged_checks):
            failed_rules = sorted({check["rule_id"] for check in staged_checks if check["result"] == "FAIL"})
            raise RuntimeError("staged asset validation failed: " + ", ".join(failed_rules))
        for name in [source_name, *png_names, ico_name]:
            (staging / name).replace(output / name)

    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="visually accepted source PNG")
    parser.add_argument("--summary-name", required=True)
    parser.add_argument("--option", type=int, required=True)
    parser.add_argument("--salt", help="accepted option's permanent 10-character salt")
    parser.add_argument("--concept-summary", default="")
    parser.add_argument(
        "--background",
        choices=BACKGROUND_MODES,
        default=DEFAULT_BACKGROUND_MODE,
        help="final PNG/ICO background (default: white)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--metadata", type=Path, help="optional JSON metadata destination")
    args = parser.parse_args()

    metadata = process_icon(
        args.source,
        args.summary_name,
        args.option,
        args.salt,
        args.output_dir,
        args.concept_summary,
        args.background,
    )
    encoded = json.dumps(metadata, indent=2)
    if args.metadata:
        args.metadata.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
