---
name: photo-zine-collage
description: "Create portrait zine collages from user-supplied photographs while keeping photo fragments natural, matching generated areas to the source palette, choosing varied source-driven center, upper/lower, offset, diagonal, or split layouts, and adding one automatic scene-matched English micro-text line. Offer two modes: detailed impressionist oil-paint color blocks or realistic elegant fine-line brushwork. Use for photo-to-zine, torn-paper photo collage, painterly editorial poster, palette-matched image extension, or requests such as 生成 zine 图片, 照片拼贴海报, 印象派大色块, and 写实细线条."
---

# Photo Zine Collage

Build a finished 3:5 portrait zine from a supplied photo. Preserve the photo as the factual anchor of the collage, extend its scene and colors into a painterly paper field, and make the join look intentionally handmade.

## Required choices

Confirm the style only when the user has not already chosen one:

- `impressionist-blocks`: broad oil-painted color masses, broken edges, visible bristle movement, and simplified shapes.
- `realist-fine-lines`: naturalistic proportions, controlled fine strokes, thin contours, and restrained, elegant detail.

Ask in one short sentence and proceed after the choice. Do not silently blend both modes. Read [references/style-modes.md](references/style-modes.md) after the style is selected.

Create one short, scene-matched English micro-text line by default. Use supplied wording exactly when present. Omit text only when the user explicitly requests a text-free result. Read [references/layouts-and-text.md](references/layouts-and-text.md) before compiling the prompt.

## Workflow

### 1. Inspect the source

If the image is a local file and the active image tool requires visible context, load it with the available image-viewing tool first.

Record a compact visual map:

- main subject and protected identity details;
- horizon, path, pose, gaze, or other geometry that must not move;
- two or three shapes that can continue beyond the photo;
- light direction and contrast level;
- likely placement of the photo fragment and one quiet paper area.

Choose a layout from the source's dominant geometry. Do not repeatedly center the photo:

- use upper/lower bands for horizons, reflections, tall growth, or open sky;
- use an offset layout for gaze, movement, portraits, or uneven visual weight;
- use a diagonal seam for paths, stairs, slopes, ridges, or strong directional lines;
- use split fragments when two different source regions can create a useful visual rhythm;
- reserve a centered island for genuine central symmetry or a single iconic subject.

Do not upload, browse for, or commit the source image unless the user asks.

Some phone and messaging-app exports use MPO data behind a `.jpg` extension. If the image tool reports an unsupported format, normalize a copy without touching the original:

```bash
python3 scripts/normalize_image.py <source-image> <working-copy.png>
```

### 2. Extract a source palette

Run from the skill directory:

```bash
python3 scripts/extract_palette.py <source-image> --colors 6
```

Use the reported colors and percentages as a palette contract. Keep dominant source colors dominant; choose any accent from the source report instead of inventing an unrelated hue. Paper color is a material neutral, not permission to wash out the photo or painted extension.

The report describes the global palette. Visually add any small but semantically critical local colors—such as skin, snow, flowers, a product color, or an existing provenance mark—with `--color-note` when compiling the prompt.

If Pillow is missing, tell the user to install the dependency from `requirements.txt`. Never substitute a personal interpreter path.

### 3. Compile the generation prompt

Describe the scene and protected relationships, then run:

```bash
python3 scripts/build_prompt.py \
  --image <source-image> \
  --style <impressionist-blocks|realist-fine-lines> \
  --scene "<one factual sentence>" \
  --must-keep "<subject and spatial invariants>" \
  --layout auto \
  --layout-seed 0 \
  --color-note "<optional critical local colors>"
```

Before running the command, author one original English line of one to four words from the visible scene and pass it with `--micro-text "<exact wording>"`. If omitted, the compiler generates a conservative scene-based fallback. Use `--no-text` only on explicit request.

Keep `--layout auto` for normal use. It selects from `center-island`, `upper-band`, `lower-band`, `offset-left`, `offset-right`, `diagonal-rise`, `diagonal-fall`, and `split-fragments`. Increment `--layout-seed` for a different repeatable composition from the same scene. Override `--layout` when visual inspection suggests a stronger choice.

Use `--output <file>` when the prompt needs to be saved. The compiler reads the photograph directly, so do not manually replace its palette with generic color names.

### 4. Generate as an image edit

Use the available image generation/editing tool. Treat the supplied photograph as the edit target, not merely a mood reference. Pass the compiled prompt and the source image together.

Prefer a portrait output near 3:5. Use high quality or high input fidelity when those controls exist. Do not claim that unsupported tool parameters were used.

The generated result must satisfy all three joins:

1. **Geometric join:** painted lines, ground planes, architecture, or foliage continue from real source edges.
2. **Color join:** nearby generated regions reuse the source palette at similar value and saturation.
3. **Material join:** a narrow irregular paper/fiber boundary is visible, with a few painted strokes crossing it; avoid a uniform sticker outline or heavy shadow.

### 5. Restore the exact photo when needed

If generation repaints faces, clothing, products, landmarks, or important source colors, do not accept the drift. First try one targeted regeneration that locks the photo fragment.

When the fragment is still altered, restore the ungraded source pixels with the optional compositor:

```bash
python3 scripts/compose_anchor.py \
  --background <generated-zine> \
  --photo <source-image> \
  --output <final.png> \
  --box 0.18,0.22,0.64,0.52 \
  --rotation -8 \
  --seed 7
```

`--box` is normalized `x,y,width,height`. Adjust it to the intended fragment and use `--rotation` for diagonal anchors. This step preserves source color and adds a reproducible irregular paper edge without applying a global grade. Save to a new output path; do not overwrite the source. For a split layout, restore the main fragment first; restore a secondary crop only when its source fidelity matters.

### 6. Check color fidelity and finish

For a quick palette audit, crop the result to the photo anchor with the same normalized box:

```bash
python3 scripts/check_palette.py \
  --source <source-image> \
  --result <final.png> \
  --result-box 0.18,0.22,0.64,0.52
```

Interpret the weighted color difference as guidance, not a substitute for visual review:

- below `6`: close;
- `6–12`: inspect skin, sky, grass, and other important colors;
- above `12`: likely color drift; restore the source fragment or regenerate with a stricter palette lock.

Inspect once at normal size and once as a thumbnail. Apply only one correction at a time. Use [references/quality-gates.md](references/quality-gates.md) for failure-specific fixes.

## Output

Return the final image, selected style, saved path for project-bound work, and one compact sentence describing how the photo and painted field connect. Include the full prompt only when the user asks for it.

Never remove signatures, provenance marks, or watermarks from an existing image. Never add fabricated credits or imitate a named living artist. Avoid logos, calls to action, mockup frames, unrelated decorative motifs, and extra text.

## Resource map

- [references/style-modes.md](references/style-modes.md): load the chosen visual mode and its correction language.
- [references/layouts-and-text.md](references/layouts-and-text.md): load for automatic layout and English micro-text decisions.
- [references/quality-gates.md](references/quality-gates.md): load during review or regeneration.
- `scripts/extract_palette.py`: extract a weighted source palette.
- `scripts/normalize_image.py`: convert MPO or unsupported inputs to a standard RGB PNG copy.
- `scripts/build_prompt.py`: create a complete palette-aware edit prompt.
- `scripts/compose_anchor.py`: optionally restore an ungraded photo fragment with a torn edge.
- `scripts/check_palette.py`: compare source and anchor palettes.
- `requirements.txt`: runtime dependency.
