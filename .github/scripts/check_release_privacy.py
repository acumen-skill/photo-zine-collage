#!/usr/bin/env python3
"""Reject common credentials and machine-specific identifiers in release text files."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


SKIP_DIRECTORIES = {".git", "__pycache__", "test-output", ".venv", "venv"}
TEXT_SUFFIXES = {".cfg", ".ini", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
TEXT_FILENAMES = {".gitattributes", ".gitignore", "LICENSE"}
IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
IDENTIFYING_IMAGE_INFO = {
    "artist",
    "author",
    "comment",
    "copyright",
    "creator",
    "description",
    "exif",
    "parameters",
    "prompt",
    "software",
    "source",
    "workflow",
    "xml",
    "xmp",
}


@dataclass(frozen=True)
class FindingPattern:
    label: str
    expression: re.Pattern[str]


PATTERNS = (
    FindingPattern("macOS user directory", re.compile("/" + r"Users/[A-Za-z0-9._-]+")),
    FindingPattern("Linux user directory", re.compile("/" + r"home/[A-Za-z0-9._-]+")),
    FindingPattern("Windows user directory", re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE)),
    FindingPattern("local file URI", re.compile("file" + r":/{2,3}", re.IGNORECASE)),
    FindingPattern(
        "email address",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    FindingPattern("OpenAI-style secret", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    FindingPattern("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    FindingPattern("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    FindingPattern(
        "private key header",
        re.compile("BEGIN " + r"(?:RSA |OPENSSH |EC )?PRIVATE KEY"),
    ),
)


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_FILENAMES:
            yield path


def scan(root: Path) -> list[str]:
    findings = []
    for path in iter_text_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in PATTERNS:
                if pattern.expression.search(line):
                    findings.append(f"{path.relative_to(root)}:{line_number}: {pattern.label}")
    for path in root.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower() not in IMAGE_SUFFIXES
            or any(part in SKIP_DIRECTORIES for part in path.parts)
        ):
            continue
        with Image.open(path) as image:
            if image.getexif():
                findings.append(f"{path.relative_to(root)}: embedded EXIF metadata")
            for key in image.info:
                if key.lower() in IDENTIFYING_IMAGE_INFO:
                    findings.append(f"{path.relative_to(root)}: embedded {key} metadata")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    findings = scan(args.repository.resolve())
    if findings:
        parser.error("release privacy scan failed:\n" + "\n".join(findings))
    print("Release privacy scan passed.")


if __name__ == "__main__":
    main()
