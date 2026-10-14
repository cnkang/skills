"""Release selection verifies existing installations without silently upgrading."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def installer(monkeypatch):
    spec = importlib.util.spec_from_file_location("release_installer", ROOT / "qdrant-memory/scripts/install_runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Unit probes mock target processes; exercise supported-interpreter paths
    # even in the skill package's Python 3.10 static validation job.
    monkeypatch.setattr(module.sys, "version_info", (3, 11))
    return module


@pytest.mark.parametrize("installed,expected", [("0.2.2", 0), ("0.2.0", 1), ("0.3.0", 1)])
def test_existing_version_checked_without_pip(installer, tmp_path, monkeypatch, capsys, installed, expected):
    target = tmp_path / "existing"
    target.mkdir()
    sentinel = target / "keep"
    sentinel.write_text("preserve")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"version": installed, "source": None}))

    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
    assert installer.main() == expected
    assert not any("install" in call for call in calls)
    assert sentinel.read_text() == "preserve"
    output = capsys.readouterr()
    if expected:
        assert "new --venv" in output.err
    else:
        assert json.loads(output.out)["installed_version"] == "0.2.2"


def test_new_install_defaults_to_pinned_pypi(installer, tmp_path, monkeypatch, capsys):
    target = tmp_path / "fresh"
    calls = []
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: path.mkdir())
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"version": "0.2.2", "source": None}))

    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
    assert installer.main() == 0
    assert calls[0][-1] == "hermes-plugin-qdrant-memory[mcp]==0.2.2"
    assert json.loads(capsys.readouterr().out)["installed_version"] == "0.2.2"


def test_posix_venv_links_managed_interpreter(installer, tmp_path, monkeypatch):
    """Copied macOS managed executables cannot resolve their relative libpython."""
    import os

    options = []

    class Builder:
        def __init__(self, **kwargs):
            options.append(kwargs)

        def create(self, path):
            raise OSError("stop after observing interpreter configuration")

    monkeypatch.setattr(installer.venv, "EnvBuilder", Builder)
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(tmp_path / "fresh")])
    assert installer.main() == 1
    assert options == [{"with_pip": True, "symlinks": os.name != "nt"}]


def test_python_below_runtime_minimum_refused(installer, tmp_path, monkeypatch):
    target = tmp_path / "absent"
    monkeypatch.setattr(installer.sys, "version_info", (3, 10))
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
    with pytest.raises(SystemExit) as exc:
        installer.main()
    assert exc.value.code == 2
    assert not target.exists()


@pytest.mark.parametrize("source", [None, {"vcs_info": {"commit_id": "b" * 40}}])
def test_existing_source_mismatch_refused_without_upgrade(installer, tmp_path, monkeypatch, source):
    target = tmp_path / "existing"
    target.mkdir()
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"version": "0.2.2", "source": source}))

    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target), "--revision", "a" * 40])
    assert installer.main() == 1
    assert not any("install" in call for call in calls)


@pytest.mark.parametrize("option,value", [("--version", "main"), ("--revision", "main"), ("--revision", "abcdef")])
def test_unpinned_selection_refused(installer, tmp_path, monkeypatch, option, value):
    target = tmp_path / "absent"
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target), option, value])
    with pytest.raises(SystemExit) as exc:
        installer.main()
    assert exc.value.code == 2
    assert not target.exists()
