"""Installer advisory: detect the Hermes plugin state for the active home."""
import importlib.util
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "qdrant-memory/scripts/install_runtime.py"


@pytest.fixture()
def installer():
    spec = importlib.util.spec_from_file_location("install_runtime_under_test", INSTALLER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def isolate(monkeypatch, tmp_path):
    """Give each case a private user home and no discoverable hermes binary."""
    home = tmp_path / "user-home"
    home.mkdir()
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    return home


def test_configured_hermes_home_detected(installer, tmp_path, monkeypatch):
    profile = tmp_path / "profile"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_text("memory:\n  provider: 'qdrant-memory'\n", encoding="utf-8")
    isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(profile))
    assert "not necessary for Hermes" in installer.hermes_advisory()


def test_default_user_home_detected(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    profile = home / ".hermes"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_text("memory:\n  provider: qdrant-memory\n", encoding="utf-8")
    assert "not necessary for Hermes" in installer.hermes_advisory()


def test_disabled_plugin_asks_to_enable_or_use_mcp(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    profile = home / ".hermes"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_text(
        "plugins:\n  disabled:\n    - qdrant-memory\n  enabled: []\n", encoding="utf-8"
    )
    advisory = installer.hermes_advisory()
    assert "disabled" in advisory
    assert "hermes plugins enable" in advisory
    assert "MCP server" in advisory


def test_inline_disabled_list_detected(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    profile = home / ".hermes"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_text(
        "plugins:\n  disabled: [qdrant-memory]\n", encoding="utf-8"
    )
    assert "not necessary" not in installer.hermes_advisory()


def test_configured_profile_wins_over_default_home(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    (home / ".hermes" / "plugins" / "qdrant-memory").mkdir(parents=True)
    profile = tmp_path / "other-profile"
    profile.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(profile))
    assert "prefer the plugin" in installer.hermes_advisory()


def test_missing_plugin_recommends_catalog_install(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    (home / ".hermes").mkdir()
    assert "hermes plugins install qdrant-memory" in installer.hermes_advisory()


def test_absent_hermes_returns_empty(installer, tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path)
    assert installer.hermes_advisory() == ""


@pytest.mark.skipif(os.name == "nt", reason="POSIX user expansion semantics")
def test_unresolvable_hermes_home_does_not_break(installer, tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("HERMES_HOME", "~hpv-no-such-user-xyz/home")
    assert installer.hermes_advisory() == ""


def test_fallback_scan_tolerates_layout_variations(installer):
    scan = installer._scan_disabled_ids
    assert scan("plugins:\n\n  disabled:\n    - qdrant-memory\n") == {"qdrant-memory"}
    assert scan("plugins:\n  disabled: [qdrant-memory] # note\n") == {"qdrant-memory"}
    assert scan("plugins:\n  disabled:\n    - qdrant-memory # note\n") == {"qdrant-memory"}
    assert scan("plugins:\r\n  disabled:\r\n    - qdrant-memory\r\n") == {"qdrant-memory"}
    assert scan("plugins:\n    disabled:\n        - qdrant-memory\n") == {"qdrant-memory"}
    assert scan("plugins:\n  # comment\n  disabled:\n    # reason\n    - qdrant-memory\n") == {"qdrant-memory"}
    assert scan("plugins:\n  disabled: []\n  enabled:\n    - other\n") == set()
    assert scan("plugins:\n  enabled:\n    - qdrant-memory\n") == set()


def test_blank_line_and_crlf_configs_disable(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    profile = home / ".hermes"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_text(
        "plugins:\n\n  disabled:\n    - qdrant-memory\n", encoding="utf-8"
    )
    assert "disabled" in installer.hermes_advisory()
    (profile / "config.yaml").write_bytes(b"plugins:\r\n  disabled: [qdrant-memory] # note\r\n")
    assert "disabled" in installer.hermes_advisory()


def test_non_mapping_plugins_value_keeps_advisory(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    profile = home / ".hermes"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_text(
        "plugins: not-a-mapping\nmemory:\n  provider: qdrant-memory\n", encoding="utf-8"
    )
    assert "not necessary for Hermes" in installer.hermes_advisory()


def test_inline_ids_keeps_quoted_commas(installer):
    assert installer._inline_ids("['qdrant-memory', 'some, name']") == {"qdrant-memory", "some, name"}


def test_flow_mapping_scan(installer):
    scan = installer._scan_disabled_ids
    assert scan("plugins: {disabled: [qdrant-memory]}\n") == {"qdrant-memory"}
    assert scan("plugins: {disabled: [qdrant-memory], enabled: [other]}\n") == {"qdrant-memory"}
    assert scan("plugins: {enabled: [other]}\n") == set()


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable bit")
def test_hermes_on_path_detected_without_home(installer, tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path)
    bins = tmp_path / "bin"
    bins.mkdir()
    stub = bins / "hermes"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", str(bins))
    assert "prefer the plugin" in installer.hermes_advisory()


def test_relative_hermes_home_ignored(installer, tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("HERMES_HOME", "relative-profile")
    assert installer.hermes_advisory() == ""


def test_non_utf8_config_keeps_advisory(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    profile = home / ".hermes"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_bytes(b"plugins:\n  disabled: [\xff]\n")
    assert "not selected as its memory provider" in installer.hermes_advisory()


def test_fallback_branch_used_without_pyyaml(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    profile = home / ".hermes"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_text(
        "plugins:\n\n  disabled:\n    - qdrant-memory\n", encoding="utf-8"
    )
    monkeypatch.setitem(sys.modules, "yaml", None)  # forces ImportError in the function
    assert "disabled" in installer.hermes_advisory()


def test_fallback_scan_comment_and_indent_edges(installer):
    scan = installer._scan_disabled_ids
    assert scan("plugins: # note\n  disabled:\n    - qdrant-memory\n") == {"qdrant-memory"}
    assert scan("plugins: {disabled: [qdrant-memory]} # note\n") == {"qdrant-memory"}
    assert scan("plugins:\n  disabled:\n  - qdrant-memory\n") == {"qdrant-memory"}
    assert scan("plugins:\n  disabled:\n    qdrant-memory: true\n") == set()


@pytest.mark.skipif(os.name != "nt", reason="Windows PATHEXT resolution")
def test_hermes_on_path_detected_windows(installer, tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path)
    bins = tmp_path / "bin"
    bins.mkdir()
    (bins / "hermes.bat").write_text("@echo off\r\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(bins))
    assert "prefer the plugin" in installer.hermes_advisory()


def test_inactive_plugin_asks_to_select_provider(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    profile = home / ".hermes"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_text("memory:\n  provider: other-provider\n", encoding="utf-8")
    advisory = installer.hermes_advisory()
    assert "not selected as its memory provider" in advisory
    assert "hermes memory setup" in advisory
    assert "MCP server" in advisory


def test_memory_provider_scan_variations(installer):
    scan = installer._scan_memory_provider
    assert scan("memory:\n  provider: qdrant-memory\n") == "qdrant-memory"
    assert scan("memory:\n  provider: 'qdrant-memory' # note\n") == "qdrant-memory"
    assert scan("memory: {provider: qdrant-memory}\n") == "qdrant-memory"
    assert scan("memory:\n\n  provider: qdrant-memory\n") == "qdrant-memory"
    assert scan("memory: {'provider': qdrant-memory}\n") == "qdrant-memory"
    assert scan('memory: {"provider": "qdrant-memory"}\n') == "qdrant-memory"
    assert scan("memory: {previous_provider: qdrant-memory}\n") is None
    assert scan("memory:\n  write_approval: false\n") is None
    assert scan("plugins:\n  disabled: []\n") is None


def test_provider_selection_forces_fallback_branch(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    profile = home / ".hermes"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    (profile / "config.yaml").write_text("memory:\n  provider: qdrant-memory\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "yaml", None)  # forces ImportError in the function
    assert "not necessary for Hermes" in installer.hermes_advisory()


def test_scan_requires_exact_keys(installer):
    d = installer._scan_disabled_ids
    assert d("plugins: {'disabled': [qdrant-memory]}\n") == {"qdrant-memory"}
    assert d("plugins: {previous_disabled: [qdrant-memory]}\n") == set()
    assert d("plugins:\n  'disabled':\n    - qdrant-memory\n") == {"qdrant-memory"}
