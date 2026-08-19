#!/usr/bin/env python3
"""Validate the repository's skill metadata without non-runtime dependencies."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---(?:\n|$)", re.DOTALL)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "metadata", "license", "allowed-tools"}


def parse_quoted_scalar(value: str, label: str) -> str:
    value = value.strip()
    if len(value) < 2 or value[0] != '"' or value[-1] != '"':
        raise ValueError(f"{label} must be a double-quoted string")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not a valid quoted string: {exc}") from exc
    if not isinstance(parsed, str):
        raise ValueError(f"{label} must be a string")
    return parsed


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise ValueError("SKILL.md must begin with YAML frontmatter")

    values: dict[str, str] = {}
    keys: set[str] = set()
    for line in match.group(1).splitlines():
        if not line or line.startswith((" ", "\t")):
            continue
        key_match = re.match(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$", line)
        if not key_match:
            raise ValueError(f"unsupported frontmatter line: {line}")
        key, raw_value = key_match.group(1), key_match.group(2) or ""
        if key in keys:
            raise ValueError(f"duplicate frontmatter key: {key}")
        keys.add(key)
        if key not in ALLOWED_FRONTMATTER_KEYS:
            raise ValueError(f"unexpected frontmatter key: {key}")
        if key in {"name", "description"}:
            values[key] = (
                parse_quoted_scalar(raw_value, key)
                if raw_value.startswith('"')
                else raw_value.strip()
            )
    return values


def validate_skill(root: Path) -> None:
    skill_path = root / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)

    name = frontmatter.get("name", "").strip()
    description = frontmatter.get("description", "").strip()
    if not name or not NAME_PATTERN.fullmatch(name) or len(name) > 64:
        raise ValueError("skill name must be hyphen-case and at most 64 characters")
    if root.name != name:
        raise ValueError(f"skill folder must be named {name}")
    if not description or len(description) > 1024 or any(char in description for char in "<>"):
        raise ValueError("description must be non-empty, at most 1024 characters, and contain no angle brackets")
    if "TODO" in text or "[TODO" in text:
        raise ValueError("SKILL.md contains an unfinished placeholder")

    for target in MARKDOWN_LINK_PATTERN.findall(text):
        if "://" in target or target.startswith("#"):
            continue
        if not (root / target).resolve().is_file():
            raise ValueError(f"missing SKILL.md link target: {target}")

    metadata_path = root / "agents" / "openai.yaml"
    metadata = metadata_path.read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    for key in ("display_name", "short_description", "default_prompt"):
        match = re.search(rf"^  {key}:\s*(.+)$", metadata, re.MULTILINE)
        if not match:
            raise ValueError(f"agents/openai.yaml is missing interface.{key}")
        fields[key] = parse_quoted_scalar(match.group(1), f"interface.{key}")

    if not 25 <= len(fields["short_description"]) <= 64:
        raise ValueError("interface.short_description must contain 25 to 64 characters")
    if f"${name}" not in fields["default_prompt"]:
        raise ValueError(f"interface.default_prompt must mention ${name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_directory", type=Path)
    args = parser.parse_args()
    try:
        validate_skill(args.skill_directory.resolve())
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print("Skill metadata is valid.")


if __name__ == "__main__":
    main()
