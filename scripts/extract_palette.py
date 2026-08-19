#!/usr/bin/env python3
"""Extract a compact, weighted color palette from a reference image."""

from __future__ import annotations

import argparse
import colorsys
import json
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover - friendly CLI failure
    raise SystemExit("Pillow is required. Install dependencies from requirements.txt.") from exc


BASIC_COLORS = {
    "black": (20, 20, 20),
    "charcoal": (65, 65, 65),
    "gray": (128, 128, 128),
    "cream": (238, 226, 198),
    "white": (242, 242, 242),
    "brown": (120, 78, 48),
    "red": (190, 45, 45),
    "orange": (220, 120, 35),
    "yellow": (220, 195, 45),
    "lime": (205, 230, 105),
    "spring-green": (125, 185, 55),
    "olive": (125, 130, 45),
    "green": (45, 135, 70),
    "forest-green": (30, 85, 45),
    "teal": (35, 135, 135),
    "turquoise": (45, 150, 155),
    "blue": (50, 100, 185),
    "sky-blue": (70, 140, 210),
    "navy": (35, 55, 105),
    "purple": (120, 70, 155),
    "pink": (215, 120, 155),
}


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % rgb


def _nearest_name(rgb: tuple[int, int, int]) -> str:
    return min(BASIC_COLORS, key=lambda name: _distance(rgb, BASIC_COLORS[name]))


def _properties(rgb: tuple[int, int, int]) -> tuple[str, str]:
    h, lightness, saturation = colorsys.rgb_to_hls(*(channel / 255 for channel in rgb))
    if saturation < 0.12:
        temperature = "neutral"
    elif h < 0.17 or h >= 0.90:
        temperature = "warm"
    elif 0.17 <= h < 0.48:
        temperature = "warm-neutral"
    else:
        temperature = "cool"

    if lightness < 0.28:
        value = "dark"
    elif lightness > 0.72:
        value = "light"
    else:
        value = "mid-value"
    return temperature, value


def load_rgb(path: Path, max_side: int = 512) -> Image.Image:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return image


def _merge_nearby(
    entries: Iterable[tuple[tuple[int, int, int], int]], threshold: float = 20.0
) -> list[tuple[tuple[int, int, int], int]]:
    merged: list[list[object]] = []
    for rgb, count in entries:
        for item in merged:
            current = item[0]
            assert isinstance(current, tuple)
            if _distance(rgb, current) <= threshold:
                old_count = int(item[1])
                total = old_count + count
                item[0] = tuple(
                    round((current[i] * old_count + rgb[i] * count) / total)
                    for i in range(3)
                )
                item[1] = total
                break
        else:
            merged.append([rgb, count])
    return sorted(((item[0], int(item[1])) for item in merged), key=lambda x: x[1], reverse=True)


def extract_palette(path: Path, colors: int = 6, max_side: int = 512) -> dict[str, object]:
    if not 3 <= colors <= 12:
        raise ValueError("colors must be between 3 and 12")

    image = load_rgb(path, max_side=max_side)
    quantized = image.quantize(colors=min(48, colors * 6), method=Image.Quantize.MEDIANCUT)
    raw = quantized.getcolors(maxcolors=256) or []
    palette = quantized.getpalette() or []
    entries: list[tuple[tuple[int, int, int], int]] = []
    for count, index in sorted(raw, reverse=True):
        offset = index * 3
        rgb = tuple(palette[offset : offset + 3])
        if len(rgb) == 3:
            entries.append((rgb, count))

    selected = _merge_nearby(entries)[:colors]
    total = sum(count for _, count in selected) or 1
    result = []
    for rgb, count in selected:
        temperature, value = _properties(rgb)
        result.append(
            {
                "hex": _hex(rgb),
                "rgb": list(rgb),
                "name": _nearest_name(rgb),
                "weight": round(count / total, 4),
                "percent": round(100 * count / total, 1),
                "temperature": temperature,
                "value": value,
            }
        )

    # Prefer a color other than the dominant entry so the prompt never asks the
    # same color to be both dominant and subordinate. Uniform images have no
    # distinct accent, so retain the dominant entry as a harmless fallback.
    accent_pool = result[1:] or result
    accent = max(
        accent_pool,
        key=lambda item: colorsys.rgb_to_hls(*(channel / 255 for channel in item["rgb"]))[2]
        * (float(item["weight"]) ** 0.5),
    )
    contract = ", ".join(f'{item["hex"]} {item["percent"]}%' for item in result)
    return {
        "source": path.name,
        "size_analyzed": list(image.size),
        "palette": result,
        "dominant": result[0],
        "source_accent_candidate": accent,
        "prompt_contract": contract,
    }


def format_text(report: dict[str, object]) -> str:
    lines = [f'Source: {report["source"]}', "Weighted palette:"]
    for item in report["palette"]:
        lines.append(
            f'  {item["hex"]}  {item["percent"]:>5}%  '
            f'{item["name"]}, {item["temperature"]}, {item["value"]}'
        )
    accent = report["source_accent_candidate"]
    lines.append(f'Source accent candidate: {accent["hex"]} ({accent["name"]})')
    lines.append(f'Prompt contract: {report["prompt_contract"]}')
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--colors", type=int, default=6)
    parser.add_argument("--max-side", type=int, default=512)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not args.image.is_file():
        parser.error(f"image not found: {args.image}")
    try:
        report = extract_palette(args.image, args.colors, args.max_side)
    except ValueError as exc:
        parser.error(str(exc))

    rendered = json.dumps(report, indent=2, ensure_ascii=False) if args.format == "json" else format_text(report)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Saved {args.output}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
