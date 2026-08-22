# Quality gates and targeted corrections

Review the generated zine at normal size and as a thumbnail. Do not automatically submit a second remote generation. Correct photo fidelity, typography, and ordinary seam issues locally; request another generation only when the user approves it for an irreparable geometry or style failure.

## Photo fidelity

Pass when the important photo fragment still has natural texture, recognizable identity, correct geometry, and source-like color.

- **Repainted subject or color grade:** restore the ungraded original with `scripts/compose_anchor.py`; do not regenerate for photo drift.
- **Changed geometry inside the anchor:** restore the original with the correct `--box`, `--rotation`, and `--crop-center`.
- **Generated continuation does not meet the restored anchor:** keep the first result, report the mismatch, and request approval before any new generation.

## Palette fidelity

Pass when dominant source colors remain dominant in the painted field and minor source accents stay minor.

- **Extension too pale, dark, or muddy:** report the generated-field mismatch; do not silently regenerate.
- **Invented accent:** report the source and result colors before proposing another generation.
- **Skin or product color drift:** restore the original anchor locally.

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
- The remote generation must contain no new text; add the exact line with `scripts/render_micro_text.py` after anchor restoration.
- If the remote result invents pseudo-text, cover it only when that can be done cleanly during local finishing; otherwise report it before proposing another generation.
- Preserve legitimate signatures, provenance marks, and watermarks already present in an input.
- Reject glossy mockup frames, curled-paper depth, strong drop shadows, and unrelated embellishment.
