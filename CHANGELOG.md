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

### Changed

- Public documentation now states installation, privacy boundaries, supported dependencies, and known limitations.
- Source accent selection now prefers a non-dominant palette color.

### Fixed

- Prevented prompts from describing the same color as both dominant and subordinate.
- Enforced the documented one-line, one-to-four-word, 24-character micro-text limit.
