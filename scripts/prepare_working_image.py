#!/usr/bin/env python3
"""Create a bounded RGB working copy for inspection and remote image editing."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required. Install dependencies from requirements.txt.") from exc


def prepare(source: Path, output: Path, max_side: int = 2048) -> tuple[tuple[int, int], tuple[int, int]]:
    if not 1024 <= max_side <= 4096:
        raise ValueError("max-side must be between 1024 and 4096")

    with Image.open(source) as opened:
        opened.seek(0)
        source_format = opened.format
        orientation = opened.getexif().get(274, 1)
        original_size = opened.size
        if (
            source_format == "JPEG"
            and output.suffix.lower() in {".jpg", ".jpeg"}
            and max(original_size) <= max_side
            and orientation in (None, 1)
            and opened.mode == "RGB"
        ):
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, output)
            return original_size, original_size
        image = ImageOps.exif_transpose(opened).convert("RGB")
    original_size = image.size
    image.thumbnail(
        (max_side, max_side),
        Image.Resampling.LANCZOS,
        reducing_gap=3.0,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() in {".jpg", ".jpeg"}:
        image.save(output, format="JPEG", quality=95, subsampling=0, optimize=True)
    else:
        image.save(output, format="PNG")
    return original_size, image.size


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-side", type=int, default=2048)
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"image not found: {args.source}")
    if args.source.resolve() == args.output.resolve():
        parser.error("output must differ from the source")
    if args.output.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        parser.error("output must use a .png, .jpg, or .jpeg extension")

    try:
        original_size, working_size = prepare(args.source, args.output, args.max_side)
    except ValueError as exc:
        parser.error(str(exc))
    print(
        f"Saved {args.output} "
        f"({original_size[0]}x{original_size[1]} -> {working_size[0]}x{working_size[1]}, "
        f"{args.output.suffix.lower().lstrip('.').upper()})"
    )


if __name__ == "__main__":
    main()
