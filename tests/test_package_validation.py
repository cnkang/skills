"""Package invariants validated against isolated copies, not wording snapshots."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_skills import SKILLS, validate_skill, validate_repository

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def skill(tmp_path):
    dest = tmp_path / SKILLS[0]
    shutil.copytree(ROOT / SKILLS[0], dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def test_independent_package_passes_without_siblings(skill):
    assert list(skill.parent.iterdir()) == [skill]
    assert validate_skill(skill) == []


def test_hidden_duplicate_is_rejected(skill):
    nested = skill / ".agents/skills" / skill.name
    nested.mkdir(parents=True)
    shutil.copyfile(skill / "SKILL.md", nested / "SKILL.md")
    assert any("duplicate" in error for error in validate_skill(skill))


def test_package_external_reference_is_rejected(skill):
    external = skill.parent / "sibling.md"
    external.write_text("outside package")
    with (skill / "SKILL.md").open("a") as stream:
        stream.write("\n[external](../sibling.md)\n")
    assert any("package-external" in error for error in validate_skill(skill))


def test_broken_resource_is_rejected(skill):
    (skill / "references/safety-gates.md").unlink()
    assert any("missing reference" in error for error in validate_skill(skill))


def test_invalid_frontmatter_is_rejected(skill):
    p = skill / "SKILL.md"
    p.write_text(p.read_text().replace('  version: "4.0.0"', '  version: 4'))
    assert any("metadata" in error for error in validate_skill(skill))


def test_python_syntax_failure_is_rejected(skill):
    (skill / "scripts/broken.py").write_text("def broken(\n")
    assert any("syntax error" in error for error in validate_skill(skill))


def test_repository_contains_controlled_entrypoints():
    assert validate_repository(ROOT) == []
    assert {p.parent.name for p in ROOT.glob("*/SKILL.md")} == set(SKILLS)


@pytest.mark.parametrize("name", SKILLS)
def test_each_package_is_independent(tmp_path, name):
    dest = tmp_path / name
    shutil.copytree(ROOT / name, dest, ignore=shutil.ignore_patterns("__pycache__"))
    assert validate_skill(dest) == []


def test_document_only_package_and_missing_resource(tmp_path):
    name = "qdrant-memory"
    dest = tmp_path / name
    shutil.copytree(ROOT / name, dest)
    assert not (dest / "scripts").exists()
    assert validate_skill(dest) == []
    next((dest / "references").glob("*.md")).unlink()
    assert any("missing reference" in error for error in validate_skill(dest))


def test_duplicate_name_is_rejected(skill):
    dest = skill.parent / "impostor"
    shutil.copytree(skill, dest)
    assert any("name must match" in error for error in validate_skill(dest))
    assert any("controlled" in error for error in validate_repository(skill.parent))


def test_unlisted_and_nested_repository_entries_are_rejected(tmp_path):
    for name in SKILLS:
        shutil.copytree(ROOT / name, tmp_path / name)
    assert validate_repository(tmp_path) == []
    nested = tmp_path / ".hidden" / "fixture"
    nested.mkdir(parents=True)
    shutil.copyfile(tmp_path / SKILLS[0] / "SKILL.md", nested / "SKILL.md")
    assert any("controlled" in error for error in validate_repository(tmp_path))
