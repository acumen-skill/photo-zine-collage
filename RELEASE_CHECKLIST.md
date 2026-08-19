# Release Checklist

## Repository content

- [x] `SKILL.md` and `agents/openai.yaml` pass repository validation.
- [x] Runtime scripts compile and automated tests pass locally.
- [x] Release text passes the privacy and machine-path scan.
- [x] User photographs and local generated outputs are excluded by `.gitignore`.
- [x] README, license, changelog, contribution guidance, and security policy are present.
- [x] CI covers Python 3.10–3.14 with read-only repository permissions.

## Before the first public push

- [ ] Initialize this directory as the standalone repository root and review the exact staged file list.
- [ ] Confirm that no parent-workspace files are included.
- [x] Select publication-cleared preview images and export metadata-checked derivatives.
- [ ] Create the remote repository and set its description and topics.
- [ ] Push to a non-release branch and confirm that all GitHub Actions jobs pass.
- [ ] Enable GitHub private vulnerability reporting.

## Version release

- [ ] Move the relevant `Unreleased` changelog entries under the intended version and release date.
- [ ] Re-run privacy, metadata, skill, dependency, compile, and unit-test checks from a clean checkout.
- [ ] Create the signed or annotated version tag.
- [ ] Publish release notes and verify installation from the public repository URL.
