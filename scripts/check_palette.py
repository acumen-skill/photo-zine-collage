#!/usr/bin/env python3
"""Compare the source palette with a generated result or its photo-anchor crop."""

from __future__ import annotations

import argparse
import math
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required. Install dependencies from requirements.txt.") from exc

from compose_anchor import parse_box
from extract_palette import extract_palette


def _srgb_channel(value: int) -> float:
    value /= 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb: list[int]) -> tuple[float, float, float]:
    red, green, blue = (_srgb_channel(value) for value in rgb)
    x = (0.4124564 * red + 0.3575761 * green + 0.1804375 * blue) / 0.95047
    y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
    z = (0.0193339 * red + 0.1191920 * green + 0.9503041 * blue) / 1.08883

    def f(value: float) -> float:
        delta = 6 / 29
        return value ** (1 / 3) if value > delta**3 else value / (3 * delta**2) + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(left: list[int], right: list[int]) -> float:
    return math.dist(rgb_to_lab(left), rgb_to_lab(right))


def crop_to_temp(image_path: Path, box: tuple[float, float, float, float], destination: Path) -> None:
    with Image.open(image_path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        x, y, width, height = box
        pixel_box = (
            round(x * image.width),
            round(y * image.height),
            round((x + width) * image.width),
            round((y + height) * image.height),
        )
        image.crop(pixel_box).save(destination, format="PNG")


def compare(source_report: dict[str, object], result_report: dict[str, object]) -> float:
    target_palette = result_report["palette"]
    weighted = 0.0
    for source_color in source_report["palette"]:
        nearest = min(delta_e(source_color["rgb"], target["rgb"]) for target in target_palette)
        weighted += float(source_color["weight"]) * nearest
    return weighted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--result-box", type=parse_box)
    parser.add_argument("--colors", type=int, default=6)
    args = parser.parse_args()

    for path in (args.source, args.result):
        if not path.is_file():
            parser.error(f"image not found: {path}")

    target_path = args.result
    with tempfile.TemporaryDirectory(prefix="photo-zine-palette-") as temp_dir:
        if args.result_box:
            target_path = Path(temp_dir) / "anchor.png"
            crop_to_temp(args.result, args.result_box, target_path)
        source_report = extract_palette(args.source, colors=args.colors)
        result_report = extract_palette(target_path, colors=args.colors)
        difference = compare(source_report, result_report)

    if difference < 6:
        verdict = "close"
    elif difference <= 12:
        verdict = "inspect important local colors"
    else:
        verdict = "likely color drift"
    print(f"Weighted palette difference (Delta E 76): {difference:.2f}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
