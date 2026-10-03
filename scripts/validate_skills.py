#!/usr/bin/env python3
"""Validate discoverability and self-contained Agent Skills packages (requires PyYAML)."""
from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from urllib.parse import unquote

import yaml

SKILLS = ("conventional-commit-batcher", "dev-jev", "repository-quality-gate-fixer", "sonarcloud-link-inspector")
FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
LINK = re.compile(r"\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)")
RESOURCE = re.compile(r"(?<![\w/])(?:scripts|references|examples|assets|agents)/[\w./-]+")
IGNORED = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}


def files_under(root: Path):
    return (p for p in root.rglob("*") if p.is_file() and not any(part in IGNORED for part in p.relative_to(root).parts))


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("missing YAML frontmatter")
    value = yaml.safe_load(text.split("\n---\n", 1)[0][4:])
    if not isinstance(value, dict):
        raise ValueError("frontmatter must be a mapping")
    return value


def check_target(root: Path, source: Path, target: str, errors: list[str]) -> None:
    if ":" in target or target.startswith("#"):
        return
    path = unquote(target.split("#", 1)[0])
    if not path:
        return
    destination = (source.parent / path).resolve()
    if not destination.is_relative_to(root.resolve()):
        errors.append(f"{source}: package-external reference {target}")
    elif not destination.exists():
        errors.append(f"{source}: missing reference {target}")


def validate_skill(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = frontmatter(root / "SKILL.md")
    except (ValueError, OSError, yaml.YAMLError) as exc:
        return [f"{root}: invalid entrypoint ({exc})"]
    name = data.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64 or name != root.name:
        errors.append(f"{root}: name must match folder and naming constraints")
    if set(data) - FIELDS:
        errors.append(f"{root}: unsupported fields {sorted(set(data) - FIELDS)}")
    for field, limit in (("description", 1024), ("compatibility", 500)):
        value = data.get(field)
        if (field == "description" or value is not None) and (not isinstance(value, str) or not 0 < len(value) <= limit):
            errors.append(f"{root}: invalid {field}")
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()):
        errors.append(f"{root}: metadata must map strings to strings")
    elif not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][\w.-]+)?", metadata.get("version", "")):
        errors.append(f"{root}: metadata.version must be a quoted semantic version")
    if data.get("license") != "MIT" or not (root / "LICENSE").is_file():
        errors.append(f"{root}: independently distributed MIT license is missing")
    for path in files_under(root):
        if not path.resolve().is_relative_to(root.resolve()):
            errors.append(f"{path}: package-external symlink")
        if path.name == "SKILL.md" and path != root / "SKILL.md":
            errors.append(f"{path}: duplicate nested entrypoint")
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeError) as exc:
                errors.append(f"{path}: Python syntax error ({exc})")
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            check_target(root, path, target, errors)
        # Resource mentions are relative to the package unless explicitly linked.
        if path.name == "SKILL.md":
            for target in RESOURCE.findall(text):
                check_target(root, path, target.rstrip("."), errors)
            if re.search(r"\bTODO\b|\bTBD\b|\[INSERT", text):
                errors.append(f"{path}: unfinished entrypoint placeholder")
    ui = root / "agents" / "openai.yaml"
    if ui.exists():
        try:
            config = yaml.safe_load(ui.read_text(encoding="utf-8"))
            interface = config["interface"]
            short = interface["short_description"]
            if not 25 <= len(short) <= 64 or f"${name}" not in interface["default_prompt"]:
                errors.append(f"{ui}: invalid UI description or invocation prompt")
        except (KeyError, TypeError, yaml.YAMLError):
            errors.append(f"{ui}: invalid UI metadata")
    return errors


def validate_repository(root: Path) -> list[str]:
    errors = []
    entries = [p for p in files_under(root) if p.name == "SKILL.md"]
    expected = {root / name / "SKILL.md" for name in SKILLS}
    if set(entries) != expected:
        errors.append("repository must expose exactly the four unique top-level skill entrypoints")
    for name in SKILLS:
        errors.extend(validate_skill(root / name))
    for folder in (root / "scripts", root / "tests"):
        if folder.exists():
            for path in folder.rglob("*.py"):
                try:
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                except SyntaxError as exc:
                    errors.append(f"{path}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate_skill(args.path) if (args.path / "SKILL.md").exists() else validate_repository(args.path)
    for error in errors:
        print(error)
    if not errors:
        print("Skill package validation passed")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
