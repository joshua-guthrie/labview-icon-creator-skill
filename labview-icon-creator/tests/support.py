"""Synthetic test fixtures; no live image generation is required."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))


def create_source(path: Path, size: tuple[int, int] = (256, 256), variant: int = 0) -> Path:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    inset = 38 + variant
    draw.rounded_rectangle(
        (inset, 52, size[0] - inset, size[1] - 52),
        radius=18,
        fill=(20, 90 + variant * 5, 180),
        outline=(10, 30, 70),
        width=8,
    )
    # Enclosed white foreground verifies that border-connected removal is safe.
    draw.ellipse((104, 96, 152, 144), fill="white", outline=(10, 30, 70), width=6)
    draw.rectangle((120, 79, 136, 161), fill=(220, 35, 45))
    draw.rectangle((95, 112, 161, 128), fill=(220, 35, 45))
    image.save(path, format="PNG")
    return path
