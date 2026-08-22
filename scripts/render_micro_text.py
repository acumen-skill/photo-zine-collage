#!/usr/bin/env python3
"""Render exact, lightly worn micro-text onto a finished zine locally."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required. Install dependencies from requirements.txt.") from exc

from build_prompt import validate_micro_text


POSITIONS = ("upper-left", "upper-right", "lower-left", "lower-right")
FONT_CANDIDATES = (
    "DejaVuSansMono.ttf",
    "LiberationMono-Regular.ttf",
    "Courier New.ttf",
    "Menlo.ttc",
)


def parse_color(value: str) -> tuple[int, int, int]:
    cleaned = value.removeprefix("#")
    if len(cleaned) != 6:
        raise argparse.ArgumentTypeError("color must be a six-digit hex value")
    try:
        return tuple(int(cleaned[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("color must be a six-digit hex value") from exc


def load_font(size: int, font_path: Path | None = None) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (str(font_path),) if font_path else FONT_CANDIDATES
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    if font_path:
        raise ValueError(f"font not found or unsupported: {font_path}")
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow 9 compatibility for downstream users.
        return ImageFont.load_default()


def _position_xy(
    canvas_size: tuple[int, int],
    text_size: tuple[int, int],
    position: str,
    margin_ratio: float,
) -> tuple[int, int]:
    width, height = canvas_size
    text_width, text_height = text_size
    margin_x = round(width * margin_ratio)
    margin_y = round(height * margin_ratio)
    x = margin_x if position.endswith("left") else width - margin_x - text_width
    y = margin_y if position.startswith("upper") else height - margin_y - text_height
    return max(0, x), max(0, y)


def _adaptive_color(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    sample = image.crop(box).convert("L")
    luminance = ImageStat.Stat(sample).mean[0] if sample.width and sample.height else 255
    return (66, 60, 54) if luminance >= 125 else (232, 224, 207)


def render_text(
    image: Image.Image,
    text: str,
    position: str,
    size_ratio: float = 0.018,
    margin_ratio: float = 0.055,
    color: tuple[int, int, int] | None = None,
    seed: int = 7,
    font_path: Path | None = None,
) -> Image.Image:
    cleaned = validate_micro_text(text)
    if position not in POSITIONS:
        raise ValueError(f"unknown position: {position}")
    if not 0.010 <= size_ratio <= 0.040:
        raise ValueError("size-ratio must be between 0.010 and 0.040")
    if not 0.02 <= margin_ratio <= 0.15:
        raise ValueError("margin-ratio must be between 0.02 and 0.15")

    canvas = image.convert("RGB")
    font_size = max(10, round(canvas.height * size_ratio))
    font = load_font(font_size, font_path)
    scratch = ImageDraw.Draw(Image.new("L", canvas.size, 0))
    bbox = scratch.textbbox((0, 0), cleaned, font=font)
    text_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])

    max_width = round(canvas.width * (1 - 2 * margin_ratio))
    while text_size[0] > max_width and font_size > 10:
        font_size -= 1
        font = load_font(font_size, font_path)
        bbox = scratch.textbbox((0, 0), cleaned, font=font)
        text_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])

    x, y = _position_xy(canvas.size, text_size, position, margin_ratio)
    draw_xy = (x - bbox[0], y - bbox[1])
    text_box = (x, y, min(canvas.width, x + text_size[0]), min(canvas.height, y + text_size[1]))
    ink = color or _adaptive_color(canvas, text_box)

    alpha = Image.new("L", canvas.size, 0)
    alpha_draw = ImageDraw.Draw(alpha)
    alpha_draw.text(draw_xy, cleaned, font=font, fill=218)

    # Reproducible pinholes and hairline wear keep the type quiet and letterpress-like.
    rng = random.Random(seed)
    wear = ImageDraw.Draw(alpha)
    wear_count = max(4, round(text_size[0] * text_size[1] / 650))
    for _ in range(wear_count):
        px = rng.randrange(x, max(x + 1, x + text_size[0]))
        py = rng.randrange(y, max(y + 1, y + text_size[1]))
        radius = rng.choice((1, 1, 2))
        wear.ellipse((px - radius, py - radius, px + radius, py + radius), fill=0)

    ink_layer = Image.new("RGB", canvas.size, ink)
    canvas.paste(ink_layer, (0, 0), alpha)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--plan", type=Path, help="finishing-plan JSON from build_prompt.py")
    parser.add_argument("--text")
    parser.add_argument("--position", choices=POSITIONS)
    parser.add_argument("--size-ratio", type=float, default=0.018)
    parser.add_argument("--margin-ratio", type=float, default=0.055)
    parser.add_argument("--color", type=parse_color)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()

    if not args.image.is_file():
        parser.error(f"image not found: {args.image}")
    if args.output.resolve() == args.image.resolve():
        parser.error("output must differ from the input image")
    if args.output.suffix.lower() != ".png":
        parser.error("output must use a .png extension")
    if args.font and not args.font.is_file():
        parser.error(f"font not found: {args.font}")

    plan: dict[str, object] = {}
    if args.plan:
        if not args.plan.is_file():
            parser.error(f"plan not found: {args.plan}")
        try:
            plan = json.loads(args.plan.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            parser.error(f"could not read finishing plan: {exc}")
        if plan.get("text_free") and not args.text:
            parser.error("finishing plan is text-free")

    text = args.text or plan.get("micro_text")
    position = args.position or plan.get("text_position")
    if not isinstance(text, str) or not text:
        parser.error("provide --text or a finishing plan with micro_text")
    if not isinstance(position, str) or position not in POSITIONS:
        parser.error("provide --position or a finishing plan with a valid text_position")

    try:
        with Image.open(args.image) as opened:
            result = render_text(
                opened,
                text,
                position,
                args.size_ratio,
                args.margin_ratio,
                args.color,
                args.seed,
                args.font,
            )
    except ValueError as exc:
        parser.error(str(exc))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output, format="PNG")
    print(f'Saved {args.output} with exact local text "{validate_micro_text(text)}"')


if __name__ == "__main__":
    main()
