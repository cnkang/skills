"""Prevent the distributed qdrant-memory skill from drifting across install paths."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_skills import validate_skill  # noqa: E402


def test_qdrant_memory_skill_structure_and_links_validate():
    skill = ROOT / "qdrant-memory"
    assert skill.is_dir()
    assert validate_skill(skill) == []


def test_install_existing_backend_and_daily_use_are_the_first_routes():
    text = (ROOT / "qdrant-memory/SKILL.md").read_text(encoding="utf-8")
    assert text.index("## First choose:") < text.index("## Choose the detailed workflow")
    first = text.split("## Choose the detailed workflow", 1)[0]
    for phrase in ("First install", "Connect an existing backend", "Daily use"):
        assert phrase in first
    assert "hermes-plugin-qdrant-memory/blob/main/INSTALL.md" in first
    assert "qdrant-memory-mcp/blob/main/docs/quickstart.md" in first
    assert "read-only first" in first
    assert "does not authorize provider switching" in first
    assert "leave the current provider and data in place" in first
    assert "do not run Hermes memory" in first
    assert "or request its credentials" in first


def test_hermes_native_is_first_and_catalog_lag_is_explicit():
    text = (ROOT / "qdrant-memory/SKILL.md").read_text(encoding="utf-8")
    hermes = text.split("## Hermes interface choice", 1)[1]
    assert hermes.index("hermes plugins list") < hermes.index("register this skill's")
    assert "Runtime installation guide" in hermes
    assert "hermes-plugin-qdrant-memory/blob/main/INSTALL.md" in hermes
    assert "stop before `hermes memory setup`" in hermes
    assert "Do not request Qdrant credentials just to install" in hermes
    assert "currently pins Runtime 0.6.3" in hermes
    assert "INSTALL.md" in hermes
    assert (ROOT / "qdrant-memory/scripts/install_runtime.py").exists()
    assert (ROOT / "qdrant-memory/references/migration.md").exists()
    assert (ROOT / "qdrant-memory/references/maintenance.md").exists()


def test_dsh_public_prerelease_and_acceptance_are_separate():
    text = (ROOT / "qdrant-memory/references/dsh.md").read_text(encoding="utf-8")
    assert "latest published Bundle,\n`0.2.0-rc.5`" in text
    assert "0.1.0-rc.14" in text
    assert "Runtime 0.7.2" in text
    assert "Bundle `0.2.0-rc.6` and launcher `0.1.0-rc.15`" in text
    assert "remain unpublished candidates" in text
    assert "npm prerelease is installable" in text
    assert "real-model" in text
    assert "protected Cloud" in text
    assert "Desktop GUI acceptance remains unverified" in text
    assert "source candidate is not a published" not in text
    assert "currently published Bundle remains 0.1.6" not in text
    assert "0.2.0-rc.1" not in text
