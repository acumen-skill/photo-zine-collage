#!/usr/bin/env python3
"""Place an ungraded source photo into a generated zine with an irregular paper edge."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required. Install dependencies from requirements.txt.") from exc


def parse_box(value: str) -> tuple[float, float, float, float]:
    try:
        box = tuple(float(part) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("box must be x,y,width,height") from exc
    if len(box) != 4:
        raise argparse.ArgumentTypeError("box must contain four numbers")
    x, y, width, height = box
    if min(box) < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise argparse.ArgumentTypeError("box values must fit inside normalized 0..1 bounds")
    return x, y, width, height


def parse_center(value: str) -> tuple[float, float]:
    try:
        center = tuple(float(part) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("crop center must be x,y") from exc
    if len(center) != 2 or any(not 0 <= part <= 1 for part in center):
        raise argparse.ArgumentTypeError("crop center must contain two numbers from 0 to 1")
    return center


def cover(
    image: Image.Image,
    size: tuple[int, int],
    centering: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=centering)


def torn_mask(size: tuple[int, int], seed: int, jitter_ratio: float) -> Image.Image:
    width, height = size
    rng = random.Random(seed)
    jitter = max(2, round(min(width, height) * jitter_ratio))
    step = max(8, round(min(width, height) * 0.045))
    points: list[tuple[int, int]] = []

    for x in range(0, width + step, step):
        points.append((min(x, width), rng.randint(0, jitter)))
    for y in range(step, height + step, step):
        points.append((width - rng.randint(0, jitter), min(y, height)))
    for x in range(width - step, -step, -step):
        points.append((max(x, 0), height - rng.randint(0, jitter)))
    for y in range(height - step, 0, -step):
        points.append((rng.randint(0, jitter), max(y, 0)))

    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)

    # Fine pinholes and short edge nicks create a reproducible fibrous contour.
    draw = ImageDraw.Draw(mask)
    for _ in range(max(24, (width + height) // 24)):
        side = rng.randrange(4)
        if side == 0:
            x, y = rng.randrange(width), rng.randrange(max(1, jitter * 2))
        elif side == 1:
            x, y = width - 1 - rng.randrange(max(1, jitter * 2)), rng.randrange(height)
        elif side == 2:
            x, y = rng.randrange(width), height - 1 - rng.randrange(max(1, jitter * 2))
        else:
            x, y = rng.randrange(max(1, jitter * 2)), rng.randrange(height)
        length = rng.randint(1, max(2, jitter))
        draw.line((x, y, x + rng.randint(-length, length), y + rng.randint(-length, length)), fill=0, width=1)

    return mask.filter(ImageFilter.GaussianBlur(radius=0.35))


def local_paper_color(background: Image.Image, pixel_box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    x0, y0, x1, y1 = pixel_box
    pad = max(4, round(min(x1 - x0, y1 - y0) * 0.025))
    sample_box = (
        max(0, x0 - pad),
        max(0, y0 - pad),
        min(background.width, x1 + pad),
        min(background.height, y1 + pad),
    )
    mean = ImageStat.Stat(background.crop(sample_box)).mean[:3]
    return tuple(min(255, round(channel + 5)) for channel in mean)


def compose(
    background: Image.Image,
    photo: Image.Image,
    box: tuple[float, float, float, float],
    seed: int,
    jitter_ratio: float,
    rotation: float = 0.0,
    crop_center: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    canvas = background.convert("RGB")
    x, y, width, height = box
    x0, y0 = round(x * canvas.width), round(y * canvas.height)
    target_size = (round(width * canvas.width), round(height * canvas.height))

    fragment = cover(
        ImageOps.exif_transpose(photo).convert("RGB"),
        target_size,
        centering=crop_center,
    )
    mask = torn_mask(target_size, seed=seed, jitter_ratio=jitter_ratio)
    photo_layer = fragment.convert("RGBA")
    photo_layer.putalpha(mask)

    if rotation:
        photo_layer = photo_layer.rotate(
            rotation,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=(0, 0, 0, 0),
        )
    mask = photo_layer.getchannel("A")

    paste_x = x0 - (photo_layer.width - target_size[0]) // 2
    paste_y = y0 - (photo_layer.height - target_size[1]) // 2
    paste_box = (
        max(0, paste_x),
        max(0, paste_y),
        min(canvas.width, paste_x + photo_layer.width),
        min(canvas.height, paste_y + photo_layer.height),
    )

    expanded = mask.filter(ImageFilter.MaxFilter(5))
    ring = expanded.point(lambda value: value if value else 0)
    ring_color = local_paper_color(canvas, paste_box)
    paper_layer = Image.new("RGB", photo_layer.size, ring_color)
    fragment = paper_layer.copy()
    fragment.paste(photo_layer, (0, 0), mask)
    canvas.paste(paper_layer, (paste_x, paste_y), ring)
    canvas.paste(fragment, (paste_x, paste_y), mask)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--background", required=True, type=Path)
    parser.add_argument("--photo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--box", required=True, type=parse_box)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--edge-jitter", type=float, default=0.018)
    parser.add_argument(
        "--rotation",
        type=float,
        default=0.0,
        help="rotate the restored photo fragment in degrees for diagonal layouts",
    )
    parser.add_argument(
        "--crop-center",
        type=parse_center,
        default=(0.5, 0.5),
        help="normalized x,y focus point retained when fitting the original photo",
    )
    args = parser.parse_args()

    if not 0.003 <= args.edge_jitter <= 0.08:
        parser.error("edge-jitter must be between 0.003 and 0.08")
    if not -30 <= args.rotation <= 30:
        parser.error("rotation must be between -30 and 30 degrees")
    for path in (args.background, args.photo):
        if not path.is_file():
            parser.error(f"image not found: {path}")
    if args.output.resolve() in {args.background.resolve(), args.photo.resolve()}:
        parser.error("output must differ from both inputs")

    with Image.open(args.background) as background, Image.open(args.photo) as photo:
        result = compose(
            background,
            photo,
            args.box,
            args.seed,
            args.edge_jitter,
            args.rotation,
            args.crop_center,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output, format="PNG")
    print(f"Saved {args.output} ({result.width}x{result.height})")


if __name__ == "__main__":
    main()
