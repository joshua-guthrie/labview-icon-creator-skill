#!/usr/bin/env python3
"""Create a QA-only contact sheet with native and pixel-magnified previews."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

try:
    from .process_icons import (
        BACKGROUND_MODES,
        DEFAULT_BACKGROUND_MODE,
        apply_background,
        fit_artwork,
        normalize_master,
        open_source,
    )
except ImportError:  # Direct script execution.
    from process_icons import (
        BACKGROUND_MODES,
        DEFAULT_BACKGROUND_MODE,
        apply_background,
        fit_artwork,
        normalize_master,
        open_source,
    )

PREVIEW_SIZES = ((29, 29), (30, 23), (30, 18), (16, 16))


def create_contact_sheet(
    candidates: Iterable[dict[str, str]],
    output: str | Path,
    magnification: int = 12,
    background_mode: str = DEFAULT_BACKGROUND_MODE,
) -> Path:
    candidate_list = list(candidates)
    if not candidate_list:
        raise ValueError("at least one candidate is required")
    if not 10 <= magnification <= 16:
        raise ValueError("magnification must be between 10 and 16")

    font = ImageFont.load_default()
    padding = 14
    label_width = 160
    source_width = 180
    preview_columns = [max(90, width * magnification + 2 * padding) for width, _ in PREVIEW_SIZES]
    sheet_width = label_width + source_width + sum(preview_columns) + padding * 2
    row_height = max(210, max(height * magnification for _, height in PREVIEW_SIZES) + 56)
    header_height = 42
    sheet = Image.new("RGB", (sheet_width, header_height + row_height * len(candidate_list)), "#d8d8d8")
    draw = ImageDraw.Draw(sheet)

    x_positions = [padding, padding + label_width, padding + label_width + source_width]
    for column_width in preview_columns[:-1]:
        x_positions.append(x_positions[-1] + column_width)
    headers = ["Candidate", "Source thumbnail", "29x29", "30x23", "30x18", "16x16"]
    for x, header in zip(x_positions, headers):
        draw.text((x, 14), header, fill="black", font=font)

    for row, candidate in enumerate(candidate_list):
        top = header_height + row * row_height
        draw.rectangle((0, top, sheet_width - 1, top + row_height - 1), fill="white", outline="#999999")
        draw.multiline_text((padding, top + padding), candidate.get("label", f"Candidate {row + 1}"), fill="black", font=font, spacing=4)
        master = normalize_master(open_source(candidate["source"]))
        thumbnail = apply_background(master, background_mode)
        thumbnail.thumbnail((source_width - 2 * padding, row_height - 2 * padding), Image.Resampling.LANCZOS)
        sheet.paste(thumbnail, (padding + label_width + (source_width - thumbnail.width) // 2, top + (row_height - thumbnail.height) // 2))

        x = padding + label_width + source_width
        for size, column_width in zip(PREVIEW_SIZES, preview_columns):
            native, _ = fit_artwork(master, size)
            native = apply_background(native, background_mode)
            native_x = x + padding
            native_y = top + padding + 18
            draw.rectangle((native_x - 1, native_y - 1, native_x + size[0], native_y + size[1]), outline="#777777")
            sheet.paste(native, (native_x, native_y))
            magnified = native.resize((size[0] * magnification, size[1] * magnification), Image.Resampling.NEAREST)
            mag_x = x + (column_width - magnified.width) // 2
            mag_y = top + 52
            sheet.paste(magnified, (mag_x, mag_y))
            draw.rectangle((mag_x - 1, mag_y - 1, mag_x + magnified.width, mag_y + magnified.height), outline="#444444")
            x += column_width

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG", optimize=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, action="append", required=True)
    parser.add_argument("--label", action="append")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--magnification", type=int, default=12)
    parser.add_argument("--background", choices=BACKGROUND_MODES, default=DEFAULT_BACKGROUND_MODE)
    args = parser.parse_args()
    labels = args.label or []
    if labels and len(labels) != len(args.source):
        parser.error("--label count must match --source count")
    candidates = [
        {"source": str(source), "label": labels[index] if labels else f"Candidate {index + 1}"}
        for index, source in enumerate(args.source)
    ]
    print(create_contact_sheet(candidates, args.output, args.magnification, args.background))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
