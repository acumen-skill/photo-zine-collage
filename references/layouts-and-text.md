# Layout and micro-text system

## Layout selection

Choose layout from the source's strongest geometry, not from a fixed template. Use `--layout auto` by default; set `--layout-seed` to a different integer when creating another version from the same scene.

- `center-island`: reserve for strong central symmetry or a single iconic subject.
- `upper-band`: use for horizons, reflections, skies, or scenes that should flow downward.
- `lower-band`: use when upward growth, architecture, trees, or open sky carries the image.
- `offset-left` / `offset-right`: use for portraits, gaze, movement, or unbalanced visual weight; leave space in front of the subject.
- `diagonal-rise` / `diagonal-fall`: align with a path, stair, slope, ridge, roofline, branch, gaze, or body movement.
- `split-fragments`: use one main crop and one much smaller crop from a different quiet region; connect them with one painted gesture and never duplicate the focal subject.

For a series, avoid the same layout twice in succession. Change `--layout-seed`, inspect the new selection, and override it only when the scene geometry disagrees.

The legacy `--anchor-position` option maps to simple layouts for compatibility, but new work should use `--layout`.

## Automatic English micro-text

Create one short English line by default. Prefer an agent-authored line after inspecting the source. If no line is supplied, `build_prompt.py` derives a conservative fallback from `--scene`.

Rules:

- Use one to four words, normally no more than 24 characters.
- Refer to a visible subject, light, weather, movement, or the scene's quiet emotional residue.
- Write an original fragment, not a quotation or attributed phrase.
- Avoid dates, coordinates, place names, captions, marketing copy, and archive metadata.
- Render it once at roughly 1.4–2.2% of poster height.
- Use worn typewriter or letterpress lettering in warm charcoal or a restrained source color.
- Place it in the largest quiet paper pocket, opposite the main visual weight.
- Preserve any text or provenance already inside the photograph.

Use `--micro-text "Exact Words"` to override the automatic line. Use `--no-text` only when the user explicitly asks for a text-free image.
