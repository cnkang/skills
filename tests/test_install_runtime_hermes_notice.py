"""Installer advisory: detect Hermes and its qdrant-memory plugin."""
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
    monkeypatch.setenv("PATH", "")
    return home


def test_configured_hermes_home_detected(installer, tmp_path, monkeypatch):
    profile = tmp_path / "profile"
    (profile / "plugins" / "qdrant-memory").mkdir(parents=True)
    isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(profile))
    assert "not necessary for Hermes" in installer.hermes_advisory()


def test_default_user_home_detected(installer, tmp_path, monkeypatch):
    home = isolate(monkeypatch, tmp_path)
    (home / ".hermes" / "plugins" / "qdrant-memory").mkdir(parents=True)
    assert "not necessary for Hermes" in installer.hermes_advisory()


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
