"""Release selection verifies existing installations without silently upgrading.

A newer compatible release satisfies the check; an older one does not.
"""
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
    monkeypatch.setattr(module.sys, "version_info", (3, 11, 10))
    return module


@pytest.mark.parametrize("version,supported", [
    ((3, 11, 9), False), ((3, 11, 10), True),
    ((3, 12, 3), False), ((3, 12, 4), True), ((3, 13, 0), True),
])
def test_windows_private_directory_requires_security_backport(installer, monkeypatch, version, supported):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "version_info", version)
    if supported:
        installer._require_private_mkdir()
    else:
        with pytest.raises(ValueError, match="3.11.10"):
            installer._require_private_mkdir()


@pytest.mark.parametrize("version", [(3, 11, 9), (3, 12, 3)])
def test_unsupported_windows_build_creates_no_venv(installer, tmp_path, monkeypatch, capsys, version):
    target = tmp_path / "must-not-exist"
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "version_info", version)
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda *_: pytest.fail("venv creation must not run"))
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
    assert installer.main() == 1
    assert not target.exists()
    assert "3.11.10" in capsys.readouterr().err


@pytest.mark.parametrize("installed,expected", [("0.2.2", 0), ("0.2.5", 0), ("0.3.0", 0), ("0.2.0", 1)])
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
        assert json.loads(output.out)["installed_version"] == installed


def test_new_install_defaults_to_pinned_pypi(installer, tmp_path, monkeypatch, capsys):
    target = tmp_path / "fresh"
    calls = []
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: path.mkdir(exist_ok=True))
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"version": "0.2.2", "source": None}))

    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
    assert installer.main() == 0
    assert calls[0][-2] == "-r"
    requirements = target / "runtime-requirements.txt"
    assert calls[0][-1] == str(requirements)
    assert requirements.read_text() == "hermes-plugin-qdrant-memory[mcp]==0.2.2\n"
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


def test_hash_lock_uses_binary_only_and_ignores_pip_config(installer, tmp_path, monkeypatch):
    import os
    target = tmp_path / "fresh"
    lock = tmp_path / "requirements.txt"
    lock.write_text("# trusted operator-supplied lock")
    calls = []
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: path.mkdir(exist_ok=True))
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"version": "0.2.2", "source": None}))
    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target), "--requirements-lock", str(lock)])
    assert installer.main() == 0
    command, options = calls[0]
    assert "--require-hashes" in command and "--only-binary=:all:" in command
    assert command[command.index("-r") + 1] == str(lock.resolve())
    assert command[5:] == ["--require-hashes", "--only-binary=:all:", "-r", str(lock.resolve())]
    assert options["cwd"] == lock.resolve().parent
    assert "-I" in command
    assert options["env"]["PIP_CONFIG_FILE"] == os.devnull
    if os.name != "nt":
        assert target.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("installed", ["0.2.0", "0.2.5"])
@pytest.mark.parametrize("existing", [False, True])
def test_hash_lock_requires_requested_runtime_version(installer, tmp_path, monkeypatch, capsys, installed, existing):
    target = tmp_path / "runtime"
    if existing:
        target.mkdir()
    lock = tmp_path / "requirements.txt"
    lock.write_text("# trusted operator-supplied lock")
    calls = []
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: path.mkdir(exist_ok=True))
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"version": installed, "source": None}))

    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target), "--requirements-lock", str(lock)])
    assert installer.main() == 1
    assert "does not match requested 0.2.2" in capsys.readouterr().err
    assert not any("--help" in call for call in calls)
    assert any("install" in call for call in calls) is not existing


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX ownership and mode checks")
def test_writable_existing_venv_rejected_before_execution(installer, tmp_path, monkeypatch):
    target = tmp_path / "existing"
    target.mkdir()
    target.chmod(0o777)
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: pytest.fail("must not execute"))
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
    with pytest.raises(SystemExit):
        installer.main()
    assert target.stat().st_mode & 0o777 == 0o777


def test_source_revision_cannot_use_release_hash_lock(installer, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(tmp_path / "new"), "--requirements-lock", str(tmp_path / "lock"), "--revision", "a" * 40])
    with pytest.raises(SystemExit):
        installer.main()
    assert not (tmp_path / "new").exists()
