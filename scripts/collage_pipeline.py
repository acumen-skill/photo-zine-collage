#!/usr/bin/env python3
"""Run photo-zine deterministic preparation or finishing in one local command."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from PIL import Image, ImageOps

from build_prompt import (
    LAYOUT_SPECS,
    STYLE_BLOCKS,
    build_finishing_plan,
    build_prompt,
)
from check_palette import compare
from compose_anchor import compose, parse_box, parse_center
from extract_palette import extract_palette, format_text
from prepare_working_image import prepare
from render_micro_text import render_text


def _working_suffix(source: Path, max_side: int) -> str:
    """Reuse a small ordinary JPEG byte-for-byte; use PNG when resizing or normalizing."""
    try:
        with Image.open(source) as opened:
            orientation = opened.getexif().get(274, 1)
            passthrough = (
                opened.format == "JPEG"
                and opened.mode == "RGB"
                and orientation in (None, 1)
                and max(opened.size) <= max_side
            )
    except OSError:
        passthrough = False
    return ".jpg" if passthrough else ".png"


def prepare_job(args: argparse.Namespace) -> dict[str, object]:
    started = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    suffix = _working_suffix(args.source, args.max_side)
    working = args.output_dir / f"{args.stem}-working{suffix}"
    palette_path = args.output_dir / f"{args.stem}-palette.txt"
    prompt_path = args.output_dir / f"{args.stem}-prompt.txt"
    plan_path = args.output_dir / f"{args.stem}-finishing-plan.json"
    if working.resolve() == args.source.resolve():
        raise ValueError("working image must differ from the source")

    original_size, working_size = prepare(args.source, working, args.max_side)
    palette_report = extract_palette(working, args.colors)
    prompt = build_prompt(
        image=working,
        style=args.style,
        scene=args.scene.strip(),
        must_keep=args.must_keep.strip(),
        layout=args.layout,
        layout_seed=args.layout_seed,
        anchor_share=args.anchor_share,
        micro_text=args.micro_text,
        no_text=args.no_text,
        text_position=args.text_position,
        colors=args.colors,
        color_note=args.color_note.strip(),
        anchor_box=args.anchor_box,
        crop_center=args.crop_center,
        palette_report=palette_report,
    )
    plan = build_finishing_plan(
        args.scene.strip(),
        args.layout,
        args.layout_seed,
        args.micro_text,
        args.no_text,
        args.text_position,
        None,
        args.anchor_box,
        args.crop_center,
    )
    palette_path.write_text(format_text(palette_report) + "\n", encoding="utf-8")
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "phase": "prepare",
        "working_image": str(working.resolve()),
        "prompt_file": str(prompt_path.resolve()),
        "plan_file": str(plan_path.resolve()),
        "palette_file": str(palette_path.resolve()),
        "original_size": list(original_size),
        "working_size": list(working_size),
        "working_bytes": working.stat().st_size,
        "layout": plan["layout"],
        "anchor_box": plan["anchor_box"],
        "crop_center": plan["crop_center"],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "prompt": prompt,
    }


def finish_job(args: argparse.Namespace) -> dict[str, object]:
    started = time.perf_counter()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    box = tuple(float(item) for item in plan["anchor_box"])
    crop_center = tuple(float(item) for item in plan.get("crop_center", (0.5, 0.5)))
    if len(box) != 4:
        raise ValueError("finishing plan anchor_box must contain four numbers")
    x, y, width, height = box
    if min(box) < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise ValueError("finishing plan anchor_box must fit normalized 0..1 bounds")
    if len(crop_center) != 2 or any(not 0 <= item <= 1 for item in crop_center):
        raise ValueError("finishing plan crop_center must contain two numbers from 0 to 1")
    rotation = float(plan.get("anchor_rotation", 0.0))

    with Image.open(args.generated) as generated, Image.open(args.source) as source:
        anchored = compose(
            generated,
            source,
            box,
            seed=args.seed,
            jitter_ratio=args.edge_jitter,
            rotation=rotation,
            crop_center=crop_center,
        )
    if args.anchored_output:
        args.anchored_output.parent.mkdir(parents=True, exist_ok=True)
        anchored.save(args.anchored_output, format="PNG")

    text_free = bool(plan.get("text_free"))
    if text_free:
        final = anchored
    else:
        final = render_text(
            anchored,
            str(plan["micro_text"]),
            str(plan["text_position"]),
            seed=args.seed,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    final.save(args.output, format="PNG")

    if args.generated_copy:
        args.generated_copy.parent.mkdir(parents=True, exist_ok=True)
        if args.generated.resolve() != args.generated_copy.resolve():
            shutil.copyfile(args.generated, args.generated_copy)

    anchor = final.crop(
        (
            round(x * final.width),
            round(y * final.height),
            round((x + width) * final.width),
            round((y + height) * final.height),
        )
    )
    source_report = extract_palette(args.source, colors=args.colors)
    with ImageOps.exif_transpose(anchor).convert("RGB") as normalized_anchor:
        # extract_palette intentionally accepts a path; one short-lived PNG keeps
        # this audit deterministic without another CLI or user-visible phase.
        audit_path = args.output.with_name(f".{args.output.stem}-palette-audit.png")
        normalized_anchor.save(audit_path, format="PNG")
    try:
        difference = compare(source_report, extract_palette(audit_path, colors=args.colors))
    finally:
        audit_path.unlink(missing_ok=True)
    verdict = "close" if difference < 6 else "inspect" if difference <= 12 else "likely color drift"

    return {
        "phase": "finish",
        "output": str(args.output.resolve()),
        "generated_copy": str(args.generated_copy.resolve()) if args.generated_copy else None,
        "anchored_output": str(args.anchored_output.resolve()) if args.anchored_output else None,
        "layout": plan["layout"],
        "anchor_box": list(box),
        "crop_center": list(crop_center),
        "palette_delta_e76": round(difference, 2),
        "palette_verdict": verdict,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def add_prepare_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("prepare", help="prepare working copy, prompt, palette, and plan")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--stem", required=True)
    parser.add_argument("--style", required=True, choices=tuple(STYLE_BLOCKS))
    parser.add_argument("--scene", required=True)
    parser.add_argument("--must-keep", required=True)
    parser.add_argument("--layout", choices=("auto", *LAYOUT_SPECS), default="auto")
    parser.add_argument("--layout-seed", type=int, default=0)
    parser.add_argument("--anchor-share", type=int, default=52)
    parser.add_argument("--anchor-box", type=parse_box)
    parser.add_argument("--crop-center", type=parse_center, default=(0.5, 0.5))
    parser.add_argument("--micro-text", default="")
    parser.add_argument("--no-text", action="store_true")
    parser.add_argument(
        "--text-position",
        choices=("auto", "upper-left", "upper-right", "lower-left", "lower-right"),
        default="auto",
    )
    parser.add_argument("--colors", type=int, default=6)
    parser.add_argument("--color-note", default="")
    parser.add_argument("--max-side", type=int, default=2048)
    parser.set_defaults(handler=prepare_job)


def add_finish_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("finish", help="restore source, add text, and audit palette")
    parser.add_argument("--generated", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-copy", type=Path)
    parser.add_argument("--anchored-output", type=Path)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--edge-jitter", type=float, default=0.018)
    parser.add_argument("--colors", type=int, default=6)
    parser.set_defaults(handler=finish_job)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_prepare_parser(subparsers)
    add_finish_parser(subparsers)
    args = parser.parse_args()

    required_paths = [args.source]
    if args.command == "finish":
        required_paths.extend((args.generated, args.plan))
    for path in required_paths:
        if not path.is_file():
            parser.error(f"file not found: {path}")
    if args.command == "finish" and not 0.003 <= args.edge_jitter <= 0.08:
        parser.error("edge-jitter must be between 0.003 and 0.08")
    if args.command == "finish":
        protected = {args.source.resolve(), args.generated.resolve(), args.plan.resolve()}
        if args.output.resolve() in protected:
            parser.error("output must differ from source, generated image, and plan")
        if args.output.suffix.lower() != ".png":
            parser.error("output must use a .png extension")

    try:
        result = args.handler(args)
    except (KeyError, ValueError, json.JSONDecodeError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
