# Changelog

Notable project changes are recorded here. Version tags follow semantic versioning.

## Unreleased

### Added

- Source-aware layout selection across eight composition types.
- Impressionist-block and realist-fine-line visual modes.
- Palette extraction, prompt compilation, image normalization, anchor restoration, and palette comparison helpers.
- Automatic scene-matched English micro-text with explicit text-free support.
- Two publication-approved, metadata-checked preview images.
- Unit tests, skill metadata validation, release privacy scanning, and a Python 3.10–3.14 CI matrix.
- Bounded working-copy preparation and deterministic local micro-text rendering.
- A batched `collage_pipeline.py` fast path for one-call preparation and one-call local finishing.

### Changed

- Public documentation now states installation, privacy boundaries, supported dependencies, and known limitations.
- Source accent selection now prefers a non-dominant palette color.
- Remote generation now uses the working copy once; original photo restoration and typography are mandatory local finishing steps.
- Automatic second-generation corrections were removed.
- Normal runs now use stable per-layout restoration footprints and avoid intermediate prompt, plan, generated-image, anchor, thumbnail, and help-query calls.
- Small standard JPEG inputs are copied byte-for-byte as working images instead of being expanded to PNG.

### Fixed

- Prevented prompts from describing the same color as both dominant and subordinate.
- Enforced the documented one-line, one-to-four-word, 24-character micro-text limit.
