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
    # Native ACL behavior has separate real-platform tests. These unit tests
    # replace subprocesses to inspect only the installation/probe contract.
    monkeypatch.setattr(module, "_require_private_parent", lambda _path: None)
    monkeypatch.setattr(module, "_require_darwin_allow_acl", lambda _path: None)
    monkeypatch.setattr(module, "_require_private_windows_file", lambda _path: None, raising=False)
    return module


@pytest.fixture
def native_installer():
    """Load the installer without stubbing platform ACL checks."""
    spec = importlib.util.spec_from_file_location(
        "native_release_installer", ROOT / "qdrant-memory/scripts/install_runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_windows_lock_ancestor_probe_uses_replacement_rights(installer):
    script = installer._windows_acl_script(directory=True, replacement_only=True)
    assert "$mask = 0x100D0040" in script
    assert "$skipInheritOnly = $true" in script
    assert "AceFlags -band 0x08" in script


def test_windows_lock_and_parent_probe_remains_strict(installer):
    script = installer._windows_acl_script(directory=False, replacement_only=False)
    assert "$mask = 0x500D0156" in script
    assert "$skipInheritOnly = $false" in script


def test_windows_lock_checks_parent_strictly_and_higher_ancestors_for_replacement(
    native_installer, tmp_path, monkeypatch
):
    from types import SimpleNamespace

    lock = tmp_path / "ancestor" / "private" / "requirements.txt"
    lock.parent.mkdir(parents=True)
    lock.write_text("# lock\n", encoding="utf-8")
    lock.chmod(0o600)
    calls = []
    monkeypatch.setattr(native_installer, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(native_installer, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(
        native_installer,
        "_require_windows_acl",
        lambda path, **options: calls.append((path, options)),
    )

    parser = native_installer.argparse.ArgumentParser()
    args = native_installer.argparse.Namespace(requirements_lock=lock, revision=None)
    assert native_installer._resolve_lock(parser, args) == lock.resolve()

    assert calls[0] == (
        lock.parent,
        {"directory": True, "label": "user-controlled parent"},
    )
    assert calls[1] == (lock, {"directory": False, "label": "lock file"})
    assert calls[2:] == [
        (
            ancestor,
            {"directory": True, "label": "lock ancestor", "replacement_only": True},
        )
        for ancestor in lock.resolve().parents[1:]
    ]


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows DACL behavior")
def test_windows_lock_ancestor_allows_sibling_creation_right(
    native_installer, tmp_path
):
    ancestor = tmp_path / "shared-parent"
    parent = ancestor / "private"
    parent.mkdir(parents=True)
    lock = parent / "requirements.txt"
    lock.write_text("# lock\n", encoding="utf-8")
    subprocess.run(
        ["icacls", str(ancestor), "/grant", "*S-1-5-11:(AD)"],
        check=True,
        capture_output=True,
        text=True,
    )

    native_installer._require_private_windows_file(lock)


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


@pytest.mark.parametrize(
    "installed,expected",
    [("0.5.5", 1), ("0.6.0", 1), ("0.6.1", 1), ("0.6.2", 0), ("0.6.3", 0), ("0.5.3", 1), ("0.2.2", 1)],
)
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
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"version": "0.6.2", "source": None}))

    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
    assert installer.main() == 0
    assert calls[0][-2] == "-r"
    requirements = target / "runtime-requirements.txt"
    assert calls[0][-1] == str(requirements)
    assert requirements.read_text() == "hermes-plugin-qdrant-memory[mcp]==0.6.2\n"
    assert json.loads(capsys.readouterr().out)["installed_version"] == "0.6.2"


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
    lock.chmod(0o600)
    calls = []
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: path.mkdir(exist_ok=True))
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"version": "0.6.2", "source": None}))
    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target), "--requirements-lock", str(lock)])
    assert installer.main() == 0
    command, options = calls[0]
    assert "--require-hashes" in command
    assert "--only-binary=:all:" in command
    assert command[command.index("-r") + 1] == str(lock.resolve())
    assert command[5:] == ["--require-hashes", "--only-binary=:all:", "-r", str(lock.resolve())]
    assert options["cwd"] == lock.resolve().parent
    assert "-I" in command
    assert options["shell"] is False
    assert options["env"]["PIP_CONFIG_FILE"] == os.devnull
    if os.name != "nt":
        assert target.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("installed", ["0.5.2", "0.5.3", "0.6.0", "0.6.1"])
@pytest.mark.parametrize("existing", [False, True])
def test_hash_lock_requires_requested_runtime_version(installer, tmp_path, monkeypatch, capsys, installed, existing):
    target = tmp_path / "runtime"
    if existing:
        target.mkdir()
    lock = tmp_path / "requirements.txt"
    lock.write_text("# trusted operator-supplied lock")
    lock.chmod(0o600)
    calls = []
    monkeypatch.setattr(installer.venv.EnvBuilder, "create", lambda self, path: path.mkdir(exist_ok=True))
    monkeypatch.setattr(installer, "hermes_advisory", lambda: "")

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"version": installed, "source": None}))

    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target), "--requirements-lock", str(lock)])
    assert installer.main() == 1
    assert f"does not match requested {installer.VERSION}" in capsys.readouterr().err
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


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX ownership and mode checks")
def test_group_or_world_writable_lock_rejected_before_execution(installer, tmp_path, monkeypatch, capsys):
    target = tmp_path / "fresh"
    lock = tmp_path / "requirements.txt"
    lock.write_text("# attacker-writable lock")
    lock.chmod(0o666)
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: pytest.fail("must not execute"))
    monkeypatch.setattr(
        sys, "argv", ["installer", "--venv", str(target), "--requirements-lock", str(lock)]
    )
    with pytest.raises(SystemExit) as exc:
        installer.main()
    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert "group/world-writable" in error
    assert str(lock) in error
    assert "chmod go-w" in error
    assert not target.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file-type check")
def test_directory_as_lock_rejected_before_execution(installer, tmp_path, monkeypatch, capsys):
    lock = tmp_path / "lockdir"
    lock.mkdir()
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: pytest.fail("must not execute"))
    monkeypatch.setattr(
        sys, "argv", ["installer", "--venv", str(tmp_path / "fresh"), "--requirements-lock", str(lock)]
    )
    with pytest.raises(SystemExit) as exc:
        installer.main()
    assert exc.value.code == 2
    assert "regular file" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX ownership and mode checks")
def test_lock_in_writable_directory_rejected_before_execution(
    installer, tmp_path, monkeypatch, capsys
):
    parent = tmp_path / "shared"
    parent.mkdir()
    parent.chmod(0o777)
    lock = parent / "requirements.txt"
    lock.write_text("# lock in a shared directory")
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: pytest.fail("must not execute"))
    monkeypatch.setattr(
        sys, "argv", ["installer", "--venv", str(tmp_path / "fresh"), "--requirements-lock", str(lock)]
    )
    with pytest.raises(SystemExit) as exc:
        installer.main()
    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert "private, user-owned directory" in error
    assert str(parent) in error
    assert "chmod go-w" in error


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX ownership and mode checks")
def test_lock_under_writable_ancestor_rejected(installer, tmp_path, monkeypatch, capsys):
    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(0o777)
    private = shared / "private"
    private.mkdir()
    private.chmod(0o700)
    lock = private / "requirements.txt"
    lock.write_text("# lock reachable through a writable ancestor")
    lock.chmod(0o600)
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: pytest.fail("must not execute"))
    monkeypatch.setattr(
        sys, "argv", ["installer", "--venv", str(tmp_path / "fresh"), "--requirements-lock", str(lock)]
    )
    with pytest.raises(SystemExit) as exc:
        installer.main()
    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert "replaceable by another account" in error
    assert str(shared) in error
    assert "chmod go-w" in error


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX ancestor walk")
def test_lock_ancestor_acl_probe_visits_lock_and_ancestors(installer, tmp_path, monkeypatch):
    """Every component that can replace the lock is passed to the ACL probe."""
    checked = []
    monkeypatch.setattr(installer, "_require_private_parent", lambda _path: None)
    monkeypatch.setattr(
        installer, "_require_darwin_allow_acl", lambda path: checked.append(path)
    )
    lock = tmp_path / "requirements.txt"
    lock.write_text("# lock")
    lock.chmod(0o600)
    parser = installer.argparse.ArgumentParser()
    args = installer.argparse.Namespace(requirements_lock=lock, revision=None)
    assert installer._resolve_lock(parser, args) == lock.resolve()
    assert set(checked) == {lock.resolve(), *lock.resolve().parents}


@pytest.mark.parametrize(
    "directive",
    [
        "-r other.txt",
        "\ufeff-r other.txt",
        "--requirement other.txt",
        "--requirement=other.txt",
        "-c constraints.txt",
        "--constraint=constraints.txt",
        "-r \\\n  other.txt",
        "--requirement \\\nother.txt",
        "-c \\\nconstraints.txt",
        "some-package==1.0 -r other.txt",
        "some-package==1.0 --constraint=constraints.txt",
        '"--requirement" "other.txt"',
        "--require-hashes -r other.txt",
        "--requi other.txt",
        "--const other.txt",
        "some-package @ https://example.com/pkg#fragment -r other.txt",
    ],
)
def test_requirements_lock_must_be_self_contained(installer, tmp_path, capsys, directive):
    """Pip must read only the file whose path and ancestors were validated."""
    lock = tmp_path / "requirements.txt"
    lock.write_text(directive + "\n", encoding="utf-8")
    lock.chmod(0o600)
    parser = installer.argparse.ArgumentParser()
    args = installer.argparse.Namespace(requirements_lock=lock, revision=None)
    with pytest.raises(SystemExit):
        installer._resolve_lock(parser, args)
    assert "self-contained" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("directive", "rejected"),
    [
        pytest.param("${X} other.txt", True, id="line-start-include"),
        pytest.param("--index-url ${PIP_INDEX_URL}", True, id="option-value"),
        pytest.param("some-package==1.0 # ${COMMENT_ONLY}", False, id="comment"),
        pytest.param("$\\\n{X} other.txt", True, id="continuation"),
    ],
)
def test_pip_environment_expansion_is_rejected_after_comment_removal(
    installer, tmp_path, capsys, directive, rejected, monkeypatch
):
    lock = tmp_path / "requirements.txt"
    lock.write_text(directive + "\n", encoding="utf-8")
    lock.chmod(0o600)
    parser = installer.argparse.ArgumentParser()
    args = installer.argparse.Namespace(requirements_lock=lock, revision=None)
    monkeypatch.setenv("X", "-r")

    if rejected:
        with pytest.raises(SystemExit):
            installer._resolve_lock(parser, args)
        assert "pip environment-variable expansion" in capsys.readouterr().err
    else:
        assert installer._resolve_lock(parser, args) == lock.resolve()


def test_invalid_utf8_requirements_lock_is_rejected(installer, tmp_path, capsys):
    lock = tmp_path / "requirements.txt"
    lock.write_bytes(b"\xff-r other.txt\n")
    lock.chmod(0o600)
    parser = installer.argparse.ArgumentParser()
    args = installer.argparse.Namespace(requirements_lock=lock, revision=None)

    with pytest.raises(SystemExit):
        installer._resolve_lock(parser, args)
    assert "requirements lock as UTF-8" in capsys.readouterr().err


def test_lock_text_that_mentions_include_options_is_not_rejected(installer, tmp_path):
    """A URL or comment containing '-r' is not a requirements include."""
    lock = tmp_path / "requirements.txt"
    lock.write_text(
        "# -r is mentioned here only\n"
        "some-package @ https://example.com/-r/wheel.whl\n"
        "some-package @ https://example.com/pkg#fragment\n"
        '--find-links "-r"\n'
        '--index-url "https://example.com/-r"\n',
        encoding="utf-8",
    )
    lock.chmod(0o600)
    parser = installer.argparse.ArgumentParser()
    args = installer.argparse.Namespace(requirements_lock=lock, revision=None)
    assert installer._resolve_lock(parser, args) == lock.resolve()


def test_missing_lock_file_is_rejected(installer, tmp_path):
    parser = installer.argparse.ArgumentParser()
    args = installer.argparse.Namespace(requirements_lock=tmp_path / "missing", revision=None)
    with pytest.raises(SystemExit):
        installer._resolve_lock(parser, args)


def test_lock_probe_failure_is_reported(installer, tmp_path, monkeypatch, capsys):
    lock = tmp_path / "requirements.txt"
    lock.write_text("# lock")
    lock.chmod(0o600)

    def fail(_path):
        raise ValueError("probe failed")

    monkeypatch.setattr(installer, "_require_private_parent", fail)
    parser = installer.argparse.ArgumentParser()
    args = installer.argparse.Namespace(requirements_lock=lock, revision=None)
    with pytest.raises(SystemExit):
        installer._resolve_lock(parser, args)
    assert "probe failed" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX ancestor walk")
def test_ancestor_acl_failure_is_reported(installer, tmp_path, monkeypatch, capsys):
    lock = tmp_path / "requirements.txt"
    lock.write_text("# lock")
    lock.chmod(0o600)
    monkeypatch.setattr(installer, "_require_private_parent", lambda _path: None)

    def fail_ancestor(path):
        if path != lock.resolve():
            raise ValueError("ancestor ACL")

    monkeypatch.setattr(installer, "_require_darwin_allow_acl", fail_ancestor)
    parser = installer.argparse.ArgumentParser()
    args = installer.argparse.Namespace(requirements_lock=lock, revision=None)
    with pytest.raises(SystemExit):
        installer._resolve_lock(parser, args)
    assert "ancestor ACL" in capsys.readouterr().err


def test_source_revision_cannot_use_release_hash_lock(installer, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(tmp_path / "new"), "--requirements-lock", str(tmp_path / "lock"), "--revision", "a" * 40])
    with pytest.raises(SystemExit):
        installer.main()
    assert not (tmp_path / "new").exists()
