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


def test_repository_contains_only_four_entrypoints():
    assert validate_repository(ROOT) == []
