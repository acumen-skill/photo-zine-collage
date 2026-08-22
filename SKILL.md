---
name: photo-zine-collage
description: "Create portrait zine collages from user-supplied photographs while preserving exact source pixels, source colors, signatures, and provenance. Supports impressionist oil-paint color blocks or realistic fine-line brushwork, one remote image edit, deterministic local typography, and fast batched local finishing. Use for photo-to-zine, torn-paper collage posters, 印象派大色块, or 写实细线条."
---

# Photo Zine Collage

Create a finished 3:5 portrait zine from a supplied photo. The photo remains the factual anchor; generated painting and paper extend its scene.

## Choose the mode

Use the user's stated mode. If absent, ask once:

- `impressionist-blocks`: broad oil-color planes, broken contours, visible bristle movement.
- `realist-fine-lines`: natural proportions, restrained fine strokes, airy detail.

Create one scene-matched English micro-text line of one to four words unless the user supplies exact wording or explicitly requests no text. The remote model never renders this line; local finishing does.

## Fast path

The normal run has two local commands around exactly one remote image edit. Do not expand it into separate palette, prompt, compose, typography, and audit calls.

### 1. Prepare everything locally in one command

From the skill directory, run:

```bash
python3 scripts/collage_pipeline.py prepare \
  --source <source-image> \
  --output-dir <project-output-dir> \
  --stem <short-job-name> \
  --style <impressionist-blocks|realist-fine-lines> \
  --scene "<one factual sentence>" \
  --must-keep "<identity, geometry, colors, signature, and provenance invariants>" \
  --layout <auto|chosen-layout> \
  --crop-center <x,y> \
  --micro-text "<exact local wording>" \
  --color-note "<small critical colors if any>"
```

Use `--no-text` instead of `--micro-text` only when explicitly requested. Use `--max-side 2560` only for a genuinely small face, product, or landmark; otherwise keep 2048.

The command returns JSON containing the full remote prompt and all paths. Use that output directly. Do not reopen the prompt, palette, or plan files merely to read them.

Choose the layout and crop center once from the visible source:

- horizontal horizon/open sky: `upper-band` or `lower-band`;
- gaze, motion, portrait, uneven weight: `offset-left` or `offset-right`;
- path, stairs, slope, ridge: `diagonal-rise` or `diagonal-fall`;
- central symmetry/iconic subject: `center-island`;
- two useful non-repeating source regions: `split-fragments`.

`--crop-center` is normalized source `x,y`. Keep `0.5,0.5` normally. Move it toward a protected face, product, signature, watermark, or provenance mark near an edge. This decision is saved in the finishing plan so local restoration does not require a later trial crop. Override the layout's stable restoration footprint with `--anchor-box x,y,width,height` only when the user explicitly needs a custom composition.

The preparation step keeps the original untouched. A small ordinary JPEG is copied byte-for-byte into the project instead of being inflated to PNG; large or unusual inputs are normalized into a bounded PNG.

If the source was already visible in the user's message, do not add another image-view call. Otherwise view the returned working image once before generation. Do not send the full-resolution original remotely.

### 2. Generate exactly once

Use the available image editing/generation tool once with:

- the returned `prompt`;
- the returned `working_image` as the edit target.

Prefer portrait 3:5 when supported. Do not claim unsupported fidelity or quality controls. The prompt fixes a stable main-fragment footprint so deterministic local restoration aligns with the generated layout.

Do not submit an automatic second generation. The generation result is already visible in the image tool response, so do not make a separate view call before ordinary local finishing. If the style or geometry is unusable and cannot be repaired locally, retain the first result and ask before retrying.

### 3. Finish everything locally in one command

Use the image tool's saved generated-file path directly:

```bash
python3 scripts/collage_pipeline.py finish \
  --generated <image-tool-saved-file> \
  --source <full-resolution-original> \
  --plan <returned-finishing-plan> \
  --output <final.png> \
  --generated-copy <optional-project-copy.png>
```

This single command restores ungraded original pixels with a torn edge, applies the saved crop center and layout footprint, renders exact local micro-text, and reports palette difference. It does not overwrite the source or generated input. Use `--anchored-output` only when an intermediate artifact is actually needed.

View the final image once. Do not perform separate normal-size and thumbnail tool calls; assess both from the same displayed result. A palette result below 6 is close; 6–12 merits visual attention; above 12 indicates likely local restoration mismatch. Report an issue instead of entering an automatic correction loop.

## Quality invariants

- Preserve subject identity, relative positions, perspective, horizon, light direction, local contrast, white balance, and source colors inside the restored photo.
- Preserve existing signatures, provenance marks, and watermarks. Never remove or fabricate them.
- Continue at least two real source edges into the painted field.
- Keep a narrow irregular fiber boundary; avoid uniform outlines, large shadows, curled paper, glossy mockups, or unrelated decoration.
- Use only source-derived accents. Do not globally grade, wash out, or stylize the restored photo.
- Add no logos, calls to action, fabricated credits, or named-living-artist imitation.

## Output

Return the final image, selected style, saved path, palette verdict, and a compact sentence describing the photo-to-paint connection. Mention the number of remote generations and measured generation/local times when available. Include the prompt only when requested.

## Failure-only references

Normal runs do not need supporting-reference reads; the compiler already contains the mode and layout language.

- Read [references/style-modes.md](references/style-modes.md) only when diagnosing a style failure.
- Read [references/layouts-and-text.md](references/layouts-and-text.md) only for a nonstandard composition or text-placement failure.
- Read [references/quality-gates.md](references/quality-gates.md) only after a reported quality-gate failure.

Do not run `--help` or inspect helper implementations during a normal generation unless a command fails.
