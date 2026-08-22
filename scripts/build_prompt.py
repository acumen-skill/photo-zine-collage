#!/usr/bin/env python3
"""Compile a palette-aware, layout-aware image-edit prompt for a photo zine."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Optional

from compose_anchor import parse_box, parse_center
from extract_palette import extract_palette


STYLE_BLOCKS = {
    "impressionist-blocks": (
        "Build the painted extension in three scales. First establish eight to fourteen interlocking "
        "medium-to-large oil-color planes; no single plane should consume more than roughly one quarter "
        "of the painted field. Then preserve four to six recognizable mid-scale scene cues such as a "
        "roof edge, path bend, trunk group, shoreline, window rhythm, or figure gesture. Finally add a "
        "sparse layer of smaller bristle accents and broken contours across about 5–10% of the painted "
        "field. Use directional brush movement and dry-brush gaps. The result must still read as bold "
        "color-block painting at thumbnail size, but retain enough structure and incident detail to reward "
        "normal-size viewing. Let one or two source-derived strokes cross the paper edge."
    ),
    "realist-fine-lines": (
        "Extend the scene with accurate perspective and naturalistic proportions using thin tapered "
        "strokes, restrained hatching, short contour fragments, and small controlled brush marks. "
        "Group foliage, grass, fabric, and hair into selected clusters rather than drawing every unit. "
        "Keep detail airy and slightly firmer near the join, lighter toward open paper."
    ),
}


LAYOUT_SPECS = {
    "center-island": (
        "Use one irregular photographic island near the visual center, surrounded by painted paper. "
        "Keep it slightly off-axis rather than perfectly symmetrical."
    ),
    "upper-band": (
        "Place the main photographic field across the upper portion of the poster with an uneven torn "
        "lower boundary. Let the illustrated scene continue downward into generous paper space."
    ),
    "lower-band": (
        "Place the main photographic field across the lower portion of the poster with an uneven torn "
        "upper boundary. Let the illustration grow upward and leave breathing room near the top."
    ),
    "offset-left": (
        "Offset one dominant photo fragment toward the left third. Let the painted continuation occupy "
        "the right and wrap selectively around the upper or lower edge."
    ),
    "offset-right": (
        "Offset one dominant photo fragment toward the right third. Let the painted continuation occupy "
        "the left and wrap selectively around the upper or lower edge."
    ),
    "diagonal-rise": (
        "Use an oblique photographic field and torn handoff that travels from lower-left toward upper-right. "
        "Align the rising seam with a real path, slope, gaze, branch, roofline, or movement in the source."
    ),
    "diagonal-fall": (
        "Use an oblique photographic field and torn handoff that travels from upper-left toward lower-right. "
        "Align the falling seam with a real path, slope, gaze, branch, roofline, or movement in the source."
    ),
    "split-fragments": (
        "Use one main photographic fragment plus one much smaller secondary crop from a different quiet "
        "part of the same source. Stagger them vertically or diagonally, never repeat the core subject, "
        "and connect both fragments through one continuous painted gesture."
    ),
}


LEGACY_POSITIONS = {
    "left": "offset-left",
    "center": "center-island",
    "right": "offset-right",
    "upper": "upper-band",
    "lower": "lower-band",
}


QUIET_TEXT_POSITIONS = {
    "center-island": "lower-right",
    "upper-band": "lower-right",
    "lower-band": "upper-right",
    "offset-left": "upper-right",
    "offset-right": "upper-left",
    "diagonal-rise": "upper-left",
    "diagonal-fall": "upper-right",
    "split-fragments": "lower-right",
}


# Stable restoration footprints make the generated fragment and the exact local
# source-pixel replacement agree without a second visual-planning pass.
ANCHOR_PRESETS = {
    "center-island": {"box": (0.18, 0.25, 0.64, 0.46), "rotation": 0.0},
    "upper-band": {"box": (0.0, 0.0, 1.0, 0.32), "rotation": 0.0},
    "lower-band": {"box": (0.0, 0.68, 1.0, 0.32), "rotation": 0.0},
    "offset-left": {"box": (0.05, 0.24, 0.62, 0.48), "rotation": 0.0},
    "offset-right": {"box": (0.33, 0.24, 0.62, 0.48), "rotation": 0.0},
    "diagonal-rise": {"box": (0.14, 0.25, 0.72, 0.46), "rotation": -8.0},
    "diagonal-fall": {"box": (0.14, 0.25, 0.72, 0.46), "rotation": 8.0},
    "split-fragments": {"box": (0.08, 0.22, 0.62, 0.46), "rotation": 0.0},
}


def _stable_index(scene: str, seed: int, count: int) -> int:
    digest = hashlib.sha256(scene.lower().encode("utf-8")).digest()
    return (digest[0] + seed) % count


def choose_layout(scene: str, seed: int = 0) -> str:
    """Choose a repeatable layout from visible scene cues rather than centering by default."""
    lower = scene.lower()
    if any(cue in lower for cue in ("reflection", "shoreline", "horizon", "lake", "ocean", "sea")):
        candidates = ("upper-band", "lower-band", "center-island", "offset-right")
        return candidates[_stable_index(scene, seed, len(candidates))]
    if any(cue in lower for cue in ("path", "stair", "slope", "diagonal", "road", "ridge")):
        candidates = ("diagonal-rise", "diagonal-fall", "offset-left", "offset-right")
        return candidates[_stable_index(scene, seed, len(candidates))]
    if any(cue in lower for cue in ("garden", "café", "cafe", "forest", "grove", "market")):
        candidates = ("split-fragments", "offset-left", "offset-right", "upper-band")
        return candidates[_stable_index(scene, seed, len(candidates))]
    if any(cue in lower for cue in ("portrait", "person", "figure", "gaze", "walking")):
        candidates = ("offset-left", "offset-right", "diagonal-rise", "diagonal-fall")
        return candidates[_stable_index(scene, seed, len(candidates))]
    candidates = tuple(LAYOUT_SPECS)
    return candidates[_stable_index(scene, seed, len(candidates))]


def resolve_layout(
    layout: str,
    scene: str,
    seed: int = 0,
    anchor_position: Optional[str] = None,
) -> str:
    if anchor_position:
        if layout != "auto":
            raise ValueError("use either --layout or legacy --anchor-position, not both")
        return LEGACY_POSITIONS[anchor_position]
    return choose_layout(scene, seed) if layout == "auto" else layout


def suggest_micro_text(scene: str) -> str:
    """Return a restrained scene-aware English line when the agent did not supply one."""
    lower = scene.lower()
    if any(cue in lower for cue in ("reflection", "reflected", "mirror", "mirrored")):
        return "Sky Held Below"
    if any(cue in lower for cue in ("garden", "café", "cafe", "lawn")):
        return "Afternoon Under Leaves"
    if any(cue in lower for cue in ("lake", "water", "shore")) and any(
        cue in lower for cue in ("mountain", "ridge", "peak")
    ):
        return "Water Keeps the Peaks"
    if any(cue in lower for cue in ("mountain", "ridge", "peak", "snow")):
        return "Above the Quiet Line"
    if any(cue in lower for cue in ("forest", "tree", "grove", "wood")):
        return "Where Light Settles"
    if any(cue in lower for cue in ("sea", "ocean", "tide", "coast")):
        return "Tide Holds Light"
    if any(cue in lower for cue in ("city", "street", "building", "architecture")):
        return "Between Passing Streets"
    if any(cue in lower for cue in ("family", "friends", "together")):
        return "A Pause Together"
    if any(cue in lower for cue in ("rain", "storm", "window")):
        return "After the Weather"
    return "A Quiet Interval"


def validate_micro_text(text: str) -> str:
    """Validate the concise single-line wording promised by the skill."""
    cleaned = text.strip()
    if any(character in cleaned for character in "\r\n\t"):
        raise ValueError("micro-text must be a single line")
    if len(cleaned) > 24:
        raise ValueError("micro-text must be 24 characters or fewer")
    word_count = len(cleaned.split())
    if not 1 <= word_count <= 4:
        raise ValueError("micro-text must contain one to four words")
    return cleaned


def build_finishing_plan(
    scene: str,
    layout: str = "auto",
    layout_seed: int = 0,
    micro_text: str = "",
    no_text: bool = False,
    text_position: str = "auto",
    anchor_position: Optional[str] = None,
    anchor_box: tuple[float, float, float, float] | None = None,
    crop_center: tuple[float, float] = (0.5, 0.5),
) -> dict[str, object]:
    if anchor_box is not None:
        x, y, width, height = anchor_box
        if min(anchor_box) < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise ValueError("anchor box must fit inside normalized 0..1 bounds")
    if len(crop_center) != 2 or any(not 0 <= part <= 1 for part in crop_center):
        raise ValueError("crop center must contain two numbers from 0 to 1")
    selected_layout = resolve_layout(layout, scene, layout_seed, anchor_position)
    selected_text = "" if no_text else validate_micro_text(micro_text or suggest_micro_text(scene))
    selected_text_position = (
        QUIET_TEXT_POSITIONS[selected_layout] if text_position == "auto" else text_position
    )
    preset = ANCHOR_PRESETS[selected_layout]
    selected_box = anchor_box or preset["box"]
    return {
        "layout": selected_layout,
        "micro_text": selected_text,
        "text_position": selected_text_position,
        "text_free": no_text,
        "anchor_box": list(selected_box),
        "anchor_rotation": preset["rotation"],
        "crop_center": list(crop_center),
    }


def build_prompt(
    image: Path,
    style: str,
    scene: str,
    must_keep: str,
    layout: str = "auto",
    layout_seed: int = 0,
    anchor_share: int = 52,
    micro_text: str = "",
    no_text: bool = False,
    text_position: str = "auto",
    colors: int = 6,
    color_note: str = "",
    anchor_position: Optional[str] = None,
    anchor_box: tuple[float, float, float, float] | None = None,
    crop_center: tuple[float, float] = (0.5, 0.5),
    palette_report: dict[str, object] | None = None,
) -> str:
    if style not in STYLE_BLOCKS:
        raise ValueError(f"unknown style: {style}")
    if layout != "auto" and layout not in LAYOUT_SPECS:
        raise ValueError(f"unknown layout: {layout}")
    if anchor_position and anchor_position not in LEGACY_POSITIONS:
        raise ValueError(f"unknown anchor position: {anchor_position}")
    if not 30 <= anchor_share <= 70:
        raise ValueError("anchor-share must be between 30 and 70")
    if no_text and micro_text:
        raise ValueError("use either --micro-text or --no-text, not both")

    plan = build_finishing_plan(
        scene,
        layout,
        layout_seed,
        micro_text,
        no_text,
        text_position,
        anchor_position,
        anchor_box,
        crop_center,
    )
    selected_layout = str(plan["layout"])
    selected_text_position = str(plan["text_position"])
    box = plan["anchor_box"]
    assert isinstance(box, list)
    box_instruction = (
        f"Keep the main locally restorable photo fragment at approximately {box[0] * 100:.0f}% from "
        f"the left and {box[1] * 100:.0f}% from the top, spanning {box[2] * 100:.0f}% of canvas width "
        f"and {box[3] * 100:.0f}% of canvas height."
    )

    report = palette_report or extract_palette(image, colors=colors)
    palette = report["palette"]
    contract = report["prompt_contract"]
    dominant = palette[0]
    accent = report["source_accent_candidate"]
    accent_instruction = (
        f' If a small accent is useful, use {accent["hex"]} ({accent["name"]}) from the source '
        "and keep it subordinate."
        if accent["hex"] != dominant["hex"]
        else ""
    )
    local_color_instruction = (
        f" Semantically critical local colors that must also remain accurate: {color_note}."
        if color_note
        else ""
    )
    text_instruction = (
        f"Leave a calm, low-detail paper pocket in the {selected_text_position} for typography that "
        "will be added locally after generation. Do not render any new letters, numbers, labels, "
        "signatures, or pseudo-text. Preserve text or provenance already inside the photo."
        if not no_text
        else "Preserve text or provenance already inside the photo, but render no new letters, numbers, labels, signatures, or pseudo-text."
    )

    return f"""Task and layout
Edit the supplied photograph into a vertical 3:5 handmade editorial zine collage. The supplied image is the edit target, not a loose mood reference. Selected layout: {selected_layout}. {LAYOUT_SPECS[selected_layout]} {box_instruction} Keep the combined photographic area near {anchor_share}% of the canvas, adjusted by visual weight. Leave at least one calm paper pocket. Use a flat front-facing scan with no frame or tabletop mockup.

Photo lock and scene continuity
The photo shows: {scene}. Keep unchanged: {must_keep}. Inside every photo fragment, preserve the original photographic identity, geometry, texture, local contrast, white balance, and color. Do not repaint, smooth, stylize, relight, crop away the protected subject, or globally grade it. Continue at least two real source edges—such as a horizon, path, roofline, branch direction, body gesture, or shadow—into the generated field. Match source light direction and local contrast across each join.

Palette contract
Use these source-derived colors in approximately this visual order: {contract}. Keep {dominant["hex"]} ({dominant["name"]}) dominant.{accent_instruction}{local_color_instruction} Generated paint next to the photo must match the neighboring source color in lightness and saturation. Do not invent a complementary accent, apply a cream/sepia/gray veil, desaturate vegetation, or shift skin, sky, water, clothing, or product colors. Paper may be a quiet natural neutral only in uncovered areas.

Selected style: {style}
{STYLE_BLOCKS[style]} Keep the result painterly and handmade without imitating a named artist. At each material join, show a narrow, irregular torn-paper/fiber interruption along only part of the fragment; vary the edge naturally, keep it flat, and let a few source-derived paint marks pass over or under it. The seam must combine aligned geometry, matched palette, and a readable paper change.

Local finishing space and hard constraints
{text_instruction} No unrelated photographs or scenery, decorative stickers, uniform white outlines, strong drop shadows, curled paper, glossy depth, logos, calls to action, watermark removal, or fabricated credits. The generated image should read as one coherent scene assembled from truthful photography, paper, and painting, with the requested quiet pocket left empty for local finishing."""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--style", required=True, choices=tuple(STYLE_BLOCKS))
    parser.add_argument("--scene", required=True)
    parser.add_argument("--must-keep", required=True)
    parser.add_argument("--layout", choices=("auto", *LAYOUT_SPECS), default="auto")
    parser.add_argument("--layout-seed", type=int, default=0)
    parser.add_argument(
        "--anchor-position",
        choices=tuple(LEGACY_POSITIONS),
        help="legacy alias for simple placement; prefer --layout",
    )
    parser.add_argument("--anchor-share", type=int, default=52)
    parser.add_argument("--micro-text", default="")
    parser.add_argument("--no-text", action="store_true")
    parser.add_argument(
        "--text-position",
        choices=("auto", "upper-left", "upper-right", "lower-left", "lower-right"),
        default="auto",
    )
    parser.add_argument("--colors", type=int, default=6)
    parser.add_argument("--color-note", default="")
    parser.add_argument(
        "--anchor-box",
        type=parse_box,
        help="normalized x,y,width,height restoration footprint; defaults from the selected layout",
    )
    parser.add_argument(
        "--crop-center",
        type=parse_center,
        default=(0.5, 0.5),
        help="normalized source focus retained during the final local restoration",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--plan-output",
        type=Path,
        help="save the local finishing layout and exact micro-text as JSON",
    )
    args = parser.parse_args()

    if not args.image.is_file():
        parser.error(f"image not found: {args.image}")
    try:
        prompt = build_prompt(
            image=args.image,
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
            anchor_position=args.anchor_position,
            anchor_box=args.anchor_box,
            crop_center=args.crop_center,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(prompt + "\n", encoding="utf-8")
        print(f"Saved {args.output}")
    else:
        print(prompt)

    if args.plan_output:
        plan = build_finishing_plan(
            args.scene.strip(),
            args.layout,
            args.layout_seed,
            args.micro_text,
            args.no_text,
            args.text_position,
            args.anchor_position,
            args.anchor_box,
            args.crop_center,
        )
        args.plan_output.parent.mkdir(parents=True, exist_ok=True)
        args.plan_output.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Saved {args.plan_output}")


if __name__ == "__main__":
    main()
