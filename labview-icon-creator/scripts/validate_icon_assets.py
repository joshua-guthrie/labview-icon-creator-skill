#!/usr/bin/env python3
"""Technically validate LabVIEW icon PNG, ICO, naming, and package invariants."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageChops, ImageStat

try:
    from .naming import parse_asset_filename, validate_option_filenames
    from .process_icons import BACKGROUND_MODES, DEFAULT_BACKGROUND_MODE, ICO_SIZES, MASTER_SIZE, PNG_SIZES
except ImportError:  # Direct script execution.
    from naming import parse_asset_filename, validate_option_filenames
    from process_icons import BACKGROUND_MODES, DEFAULT_BACKGROUND_MODE, ICO_SIZES, MASTER_SIZE, PNG_SIZES


def result(
    rule_id: str,
    status: str,
    description: str,
    *,
    measured_value: Any = None,
    threshold: Any = None,
    severity: str = "mandatory",
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "description": description,
        "result": status,
        "measured_value": measured_value,
        "threshold": threshold,
    }


def _foreground_mask(image: Image.Image, tolerance: int = 12) -> Image.Image:
    if "A" in image.getbands():
        return image.getchannel("A").point(lambda value: 255 if value > tolerance else 0)
    rgb = image.convert("RGB")
    background = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    difference = ImageChops.difference(rgb, background).convert("L")
    return difference.point(lambda value: 255 if value > tolerance else 0)


def measurable_metrics(image: Image.Image) -> dict[str, float | list[int] | None]:
    rgba = image.convert("RGBA")
    rgb = rgba.convert("RGB")
    mask = _foreground_mask(image)
    bbox = mask.getbbox()
    if bbox is None:
        return {
            "foreground_fraction": 0.0,
            "occupancy": 0.0,
            "minimum_edge_margin_fraction": None,
            "contrast_span": 0.0,
            "foreground_bbox": None,
        }
    histogram = mask.histogram()
    foreground_fraction = histogram[255] / (rgb.width * rgb.height)
    left, top, right, bottom = bbox
    occupancy = max((right - left) / rgb.width, (bottom - top) / rgb.height)
    minimum_margin = min(left / rgb.width, top / rgb.height, (rgb.width - right) / rgb.width,
                         (rgb.height - bottom) / rgb.height)
    grayscale = rgb.convert("L")
    stats = ImageStat.Stat(grayscale, mask=mask)
    background_stats = ImageStat.Stat(grayscale, mask=ImageChops.invert(mask))
    foreground_mean = stats.mean[0] if stats.count[0] else 255.0
    background_mean = background_stats.mean[0] if background_stats.count[0] else 255.0
    return {
        "foreground_fraction": round(foreground_fraction, 6),
        "occupancy": round(occupancy, 6),
        "minimum_edge_margin_fraction": round(minimum_margin, 6),
        "contrast_span": round(abs(background_mean - foreground_mean), 3),
        "foreground_bbox": list(bbox),
    }


def validate_png(
    path: str | Path,
    expected_size: tuple[int, int],
    background_mode: str = DEFAULT_BACKGROUND_MODE,
) -> list[dict[str, Any]]:
    asset = Path(path)
    checks: list[dict[str, Any]] = []
    if not asset.is_file() or asset.stat().st_size == 0:
        return [result("FILE-PNG-001", "FAIL", f"PNG missing or empty: {asset.name}")]
    try:
        with Image.open(asset) as image:
            image.load()
            rgba = image.convert("RGBA")
            checks.append(result(
                "FILE-PNG-002",
                "PASS" if image.format == "PNG" else "FAIL",
                "File opens as PNG",
                measured_value=image.format,
                threshold="PNG",
            ))
            checks.append(result(
                "FILE-PNG-003",
                "PASS" if image.size == expected_size else "FAIL",
                "Actual dimensions match expected dimensions",
                measured_value=list(image.size),
                threshold=list(expected_size),
            ))
            required_mode = "RGB" if background_mode == "white" else "RGBA"
            checks.append(result(
                "FILE-PNG-004",
                "PASS" if image.mode == required_mode else "FAIL",
                f"PNG mode matches the declared {background_mode} background",
                measured_value=image.mode,
                threshold=required_mode,
            ))
            corners = [
                rgba.getpixel((0, 0)),
                rgba.getpixel((rgba.width - 1, 0)),
                rgba.getpixel((0, rgba.height - 1)),
                rgba.getpixel((rgba.width - 1, rgba.height - 1)),
            ]
            background_matches = (
                all(pixel == (255, 255, 255, 255) for pixel in corners)
                if background_mode == "white"
                else all(pixel[3] == 0 for pixel in corners)
            )
            checks.append(result(
                "FILE-PNG-008",
                "PASS" if background_matches else "FAIL",
                f"PNG outer corners match the declared {background_mode} background",
                measured_value=[list(pixel) for pixel in corners],
                threshold="all corners == opaque white" if background_mode == "white" else "all alpha channels == 0",
            ))
            metrics = measurable_metrics(image)
            checks.append(result(
                "FILE-PNG-005",
                "PASS" if metrics["foreground_fraction"] >= 0.002 else "FAIL",
                "PNG is not blank or nearly blank",
                measured_value=metrics["foreground_fraction"],
                threshold=">= 0.002 foreground fraction",
            ))
            parsed = parse_asset_filename(asset.name)
            dimensions_match_name = bool(
                parsed
                and parsed["type"] == "png"
                and (parsed["width"], parsed["height"]) == image.size
            )
            checks.append(result(
                "NAME-PNG-001",
                "PASS" if dimensions_match_name else "FAIL",
                "Filename dimensions match file dimensions",
                measured_value=asset.name,
            ))
    except Exception as exc:
        checks.append(result("FILE-PNG-006", "FAIL", f"PNG cannot be decoded: {exc}"))
    return checks


def _ico_sizes(image: Image.Image) -> set[tuple[int, int]]:
    ico = getattr(image, "ico", None)
    if ico is not None and hasattr(ico, "sizes"):
        return set(ico.sizes())
    sizes: set[tuple[int, int]] = set()
    for frame in range(getattr(image, "n_frames", 1)):
        image.seek(frame)
        sizes.add(image.size)
    return sizes


def validate_ico(
    path: str | Path,
    background_mode: str = DEFAULT_BACKGROUND_MODE,
) -> list[dict[str, Any]]:
    asset = Path(path)
    if not asset.is_file() or asset.stat().st_size == 0:
        return [result("FILE-ICO-001", "FAIL", f"ICO missing or empty: {asset.name}")]
    checks: list[dict[str, Any]] = []
    signature = asset.read_bytes()[:8]
    checks.append(result(
        "FILE-ICO-002",
        "PASS" if signature[:4] == b"\x00\x00\x01\x00" and signature != b"\x89PNG\r\n\x1a\n" else "FAIL",
        "File has an ICO header and is not a renamed PNG",
        measured_value=signature.hex(),
        threshold="00000100 ICO header",
    ))
    try:
        with Image.open(asset) as image:
            image.load()
            checks.append(result(
                "FILE-ICO-003",
                "PASS" if image.format == "ICO" else "FAIL",
                "File opens as ICO",
                measured_value=image.format,
                threshold="ICO",
            ))
            available = _ico_sizes(image)
            required = set(ICO_SIZES)
            checks.append(result(
                "FILE-ICO-004",
                "PASS" if required.issubset(available) else "FAIL",
                "ICO contains all required frames",
                measured_value=[list(size) for size in sorted(available)],
                threshold=[list(size) for size in ICO_SIZES],
            ))
            ico = getattr(image, "ico", None)
            corrupt: list[list[int]] = []
            wrong_background: list[list[int]] = []
            if ico is not None and hasattr(ico, "getimage"):
                for size in sorted(required & available):
                    try:
                        frame = ico.getimage(size)
                        frame.load()
                        if frame.size != size:
                            corrupt.append(list(size))
                            continue
                        rgba = frame.convert("RGBA")
                        corners = [
                            rgba.getpixel((0, 0)),
                            rgba.getpixel((rgba.width - 1, 0)),
                            rgba.getpixel((0, rgba.height - 1)),
                            rgba.getpixel((rgba.width - 1, rgba.height - 1)),
                        ]
                        matches = (
                            all(pixel == (255, 255, 255, 255) for pixel in corners)
                            if background_mode == "white"
                            else all(pixel[3] == 0 for pixel in corners)
                        )
                        if not matches:
                            wrong_background.append(list(size))
                    except Exception:
                        corrupt.append(list(size))
            checks.append(result(
                "FILE-ICO-005",
                "PASS" if not corrupt else "FAIL",
                "Required ICO frames decode at their declared sizes",
                measured_value=corrupt,
                threshold="no corrupt frames",
            ))
            checks.append(result(
                "FILE-ICO-006",
                "PASS" if (256, 256) in available else "FAIL",
                "ICO has a valid 256x256 entry",
                measured_value=(256, 256) in available,
                threshold=True,
            ))
            checks.append(result(
                "FILE-ICO-008",
                "PASS" if not wrong_background else "FAIL",
                f"Required ICO frames match the declared {background_mode} background",
                measured_value=wrong_background,
                threshold=f"no frames with a non-{background_mode} outer background",
            ))
    except Exception as exc:
        checks.append(result("FILE-ICO-007", "FAIL", f"ICO cannot be decoded: {exc}"))
    parsed = parse_asset_filename(asset.name)
    checks.append(result(
        "NAME-ICO-001",
        "PASS" if parsed and parsed["type"] == "ico" else "FAIL",
        "ICO filename matches the naming convention",
        measured_value=asset.name,
    ))
    return checks


def validate_proportional_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    source_width, source_height = geometry["source_artwork_size"]
    rendered_width, rendered_height = geometry["rendered_artwork_size"]
    width_scale = rendered_width / source_width
    height_scale = rendered_height / source_height
    tolerance = max(1 / source_width, 1 / source_height) + 0.02
    proportional = math.isclose(width_scale, height_scale, abs_tol=tolerance)
    canvas_width, canvas_height = geometry["canvas_size"]
    offset_x, offset_y = geometry["offset"]
    uncropped = (
        offset_x >= 0
        and offset_y >= 0
        and offset_x + rendered_width <= canvas_width
        and offset_y + rendered_height <= canvas_height
    )
    centered = abs((canvas_width - rendered_width) / 2 - offset_x) <= 1 and abs(
        (canvas_height - rendered_height) / 2 - offset_y
    ) <= 1
    return result(
        "PROCESS-GEOMETRY-001",
        "PASS" if proportional and uncropped and centered else "FAIL",
        "Artwork scaling is proportional, centered, and uncropped",
        measured_value={
            "width_scale": width_scale,
            "height_scale": height_scale,
            "offset": [offset_x, offset_y],
            "uncropped": uncropped,
            "centered": centered,
        },
        threshold={"scale_difference_max": tolerance, "uncropped": True, "centered": True},
    )


def validate_option_assets(metadata: dict[str, Any], base_dir: str | Path = ".") -> list[dict[str, Any]]:
    base = Path(base_dir)
    checks: list[dict[str, Any]] = []
    source_file = str(metadata["source_file"])
    derived = list(metadata["derived_png_files"])
    ico_file = str(metadata["ico_file"])
    filenames = [source_file, *(str(item["file"]) for item in derived), ico_file]
    declared_background = metadata.get("background_mode")
    if declared_background is None:
        legacy_ico_background = str(metadata.get("ico_background", ""))
        declared_background = "transparent" if legacy_ico_background.startswith("transparent") else DEFAULT_BACKGROUND_MODE
    background_mode = str(declared_background).lower()
    valid_background = background_mode in BACKGROUND_MODES
    checks.append(result(
        "FILE-BACKGROUND-001",
        "PASS" if valid_background else "FAIL",
        "Option declares a supported background mode",
        measured_value=declared_background,
        threshold=list(BACKGROUND_MODES),
    ))
    if not valid_background:
        background_mode = DEFAULT_BACKGROUND_MODE
    name_errors = validate_option_filenames(filenames)
    checks.append(result(
        "NAME-OPTION-001",
        "PASS" if not name_errors else "FAIL",
        "All option filenames share valid summary, option, and salt values",
        measured_value=name_errors,
        threshold="no errors",
    ))
    parsed_names = [parse_asset_filename(filename) for filename in filenames]
    metadata_matches = all(
        parsed
        and parsed["option_number"] == int(metadata["option_number"])
        and parsed["salt"] == str(metadata["salt"])
        for parsed in parsed_names
    )
    checks.append(result(
        "NAME-OPTION-002",
        "PASS" if metadata_matches else "FAIL",
        "Filename option numbers and salts match option metadata",
        measured_value={"option_number": metadata.get("option_number"), "salt": metadata.get("salt")},
        threshold="all filenames agree",
    ))
    checks.append(result(
        "FILE-PNG-009",
        "PASS" if tuple(metadata.get("source_dimensions", ())) == MASTER_SIZE else "FAIL",
        "Declared source dimensions match the normalized master size",
        measured_value=metadata.get("source_dimensions"),
        threshold=list(MASTER_SIZE),
    ))
    checks.extend(validate_png(base / source_file, MASTER_SIZE, background_mode))
    required_derivatives = set(PNG_SIZES)
    actual_derivatives = {tuple(item["dimensions"]) for item in derived}
    checks.append(result(
        "FILE-PNG-007",
        "PASS" if actual_derivatives == required_derivatives else "FAIL",
        "Option declares every exact derivative canvas",
        measured_value=[list(size) for size in sorted(actual_derivatives)],
        threshold=[list(size) for size in PNG_SIZES],
    ))
    for item in derived:
        checks.extend(validate_png(base / str(item["file"]), tuple(item["dimensions"]), background_mode))
        if "geometry" in item:
            checks.append(validate_proportional_geometry(item["geometry"]))
    checks.extend(validate_ico(base / ico_file, background_mode))
    return checks


def validate_package(options: Iterable[dict[str, Any]], base_dir: str | Path = ".") -> list[dict[str, Any]]:
    option_list = list(options)
    checks: list[dict[str, Any]] = []
    salts = [str(option["salt"]) for option in option_list]
    option_numbers = [int(option["option_number"]) for option in option_list]
    checks.append(result(
        "NAME-SALT-001",
        "PASS" if len(salts) == len(set(salts)) else "FAIL",
        "Accepted options use unique permanent salts",
        measured_value=salts,
        threshold="all unique",
    ))
    checks.append(result(
        "NAME-OPTION-003",
        "PASS" if len(option_numbers) == len(set(option_numbers)) else "FAIL",
        "Accepted options use unique option numbers",
        measured_value=option_numbers,
        threshold="all unique",
    ))
    for option in option_list:
        checks.extend(validate_option_assets(option, base_dir))
    return checks


def has_failures(checks: Iterable[dict[str, Any]]) -> bool:
    return any(check["result"] == "FAIL" for check in checks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", type=Path)
    source.add_argument("--metadata", type=Path, action="append")
    parser.add_argument("--base-dir", type=Path)
    args = parser.parse_args()

    if args.manifest:
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
        options = document["options"]
        base = args.base_dir or args.manifest.parent
    else:
        options = [json.loads(path.read_text(encoding="utf-8")) for path in args.metadata]
        base = args.base_dir or Path.cwd()
    checks = validate_package(options, base)
    print(json.dumps({"qa_status": "FAIL" if has_failures(checks) else "PASS", "checks": checks}, indent=2))
    return 1 if has_failures(checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
