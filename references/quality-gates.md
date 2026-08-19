# Quality gates and targeted corrections

Review the generated zine at normal size and as a thumbnail. Regenerate only for an observed failure and change one instruction at a time.

## Photo fidelity

Pass when the important photo fragment still has natural texture, recognizable identity, correct geometry, and source-like color.

- **Repainted subject:** state that the supplied photo region is locked and must remain photographic; identify the exact face, garment, object, or landmark to preserve.
- **Changed geometry:** restate the horizon, pose, gaze, path, or overlap as an invariant.
- **Color grade over the photo:** prohibit global tinting and restore the ungraded source with `scripts/compose_anchor.py` when regeneration still drifts.

## Palette fidelity

Pass when dominant source colors remain dominant in the painted field and minor source accents stay minor.

- **Extension too pale:** repeat the source hex colors and ask for comparable saturation and value; prohibit a paper-colored veil.
- **Extension too dark or muddy:** preserve distinct palette families and reduce overmixing.
- **Invented accent:** replace it with a reported source accent and state its maximum visual share.
- **Skin or product color drift:** lock that local color separately from the surrounding palette.

Use `scripts/check_palette.py` on the anchor when visual inspection is uncertain. A low numeric difference can still hide a local problem, so always inspect important semantic colors.

## Collage integration

Pass when the photo and generated field share geometry, color, and material cues.

- **Sticker effect:** remove the uniform outline and shadow; vary the torn edge and let selected paint marks cross it.
- **Invisible collage:** reveal a narrow paper/fiber interruption along part of the edge.
- **Disconnected decoration:** replace arbitrary marks with continuations of visible source shapes.
- **Hard seam:** match local brightness on both sides and continue two real edges across the boundary.
- **Repeated centered layout:** choose a source-driven upper/lower, offset, diagonal, or split-fragment layout; do not merely nudge a centered island.
- **Arbitrary diagonal:** align its angle with a real path, slope, gaze, ridge, roofline, or movement.
- **Split-fragment repetition:** use a secondary crop from a different quiet region and never duplicate the core subject.

## Style fidelity

### Impressionist blocks

Pass when the extension reads first as clear color masses with visible brush direction while retaining a second tier of recognizable structure.

- **Blocks too large:** divide the painted field into eight to fourteen interlocking planes, restore four to six mid-scale scene cues, and add a sparse 5–10% detail layer.
- **Too detailed:** merge small marks back into medium-to-large planes while retaining only a few descriptive accents.
- **Too flat:** add broken bristle edges and controlled optical mixing without adding new colors.
- **Too abstract:** restore the source horizon plus several scene-specific mid-scale cues.

### Realist fine lines

Pass when the extension remains spatially convincing, delicate, and airy.

- **Lines too heavy:** reduce width and contrast; keep the darkest strokes near the join only.
- **Too busy:** retain selected clusters and open more untouched paper.
- **Too generic:** reintroduce two source-specific contours or rhythms.

## Text and finish

Pass when the single English micro-text line is scene-related, exact, small, legible, and placed in quiet paper.

- By default author one original English line of one to four words from visible content or atmosphere. Avoid quotations, attribution, dates, locations, and metadata.
- Remove any additional invented words, pseudo-labels, dates, signatures, or credits.
- If exact text renders incorrectly, regenerate once with the wording isolated and quoted. If it remains wrong, omit it unless the user asks for deterministic typography.
- Preserve legitimate signatures, provenance marks, and watermarks already present in an input.
- Reject glossy mockup frames, curled-paper depth, strong drop shadows, and unrelated embellishment.
