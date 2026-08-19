#!/usr/bin/env python3
"""Normalize the first visible frame of an image to a standard RGB PNG copy."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required. Install dependencies from requirements.txt.") from exc


def normalize(source: Path, output: Path) -> tuple[int, int]:
    with Image.open(source) as opened:
        opened.seek(0)
        image = ImageOps.exif_transpose(opened).convert("RGB")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG")
    return image.size


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"image not found: {args.source}")
    if args.source.resolve() == args.output.resolve():
        parser.error("output must differ from the source")
    if args.output.suffix.lower() != ".png":
        parser.error("output must use a .png extension")

    width, height = normalize(args.source, args.output)
    print(f"Saved {args.output} ({width}x{height}, RGB PNG)")


if __name__ == "__main__":
    main()
