# Contributing

Contributions should keep `photo-zine-collage` focused on producing a single portrait photo-zine collage while preserving source identity, geometry, and color.

## Set up

Use Python 3.10 or newer and install the runtime dependency:

```bash
python3 -m pip install -r requirements.txt
```

## Before opening a pull request

Run the same checks used by CI:

```bash
python3 .github/scripts/check_release_privacy.py .
python3 .github/scripts/validate_skill.py .
python3 -m compileall -q scripts tests .github/scripts
python3 -m unittest discover -s tests -v
```

When changing prompt behavior, add a test for the observable rule or invariant rather than matching the entire generated prompt. Keep `SKILL.md` concise and route substantial mode-specific guidance through the existing references.

## Images and privacy

Do not commit user photographs, generated outputs derived from private photographs, EXIF/XMP metadata, or local test prompts. Keep experiments in `test-output/`, which is ignored by Git.

Only add a public preview when all people and source assets are cleared for publication and identifying metadata has been removed. Prefer a synthetic or purpose-created fixture for automated tests.

## Scope

Changes for multi-page publishing, print production, unrelated image styles, or external service integrations should begin with a proposal explaining why they belong in this focused skill.
