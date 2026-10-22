"""Exercise native ACL boundaries before an installer can execute venv code."""

import ctypes
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def native_installer(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "qdrant-memory/scripts/install_runtime.py"
    spec = importlib.util.spec_from_file_location("native_acl_installer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "hermes_advisory", lambda: "")
    return module


@pytest.mark.parametrize("code,message", [
    (0, None), (3, "other-account write ACL"),
    (1, "Cannot verify"), (7, "Cannot verify"),
])
def test_windows_acl_process_failure_is_not_a_permission_diagnosis(native_installer, tmp_path, monkeypatch, code, message):
    def windows_directory(buffer, _size):
        buffer.value = "C:\\Windows"
        return len(buffer.value)

    kernel = SimpleNamespace(GetWindowsDirectoryW=windows_directory)
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **kw: kernel, raising=False)
    # Replace only the installer's bindings, never pathlib's global OS module.
    monkeypatch.setattr(native_installer, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(native_installer, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(native_installer.subprocess, "run", lambda argv, **kw: subprocess.CompletedProcess(argv, code))
    if message:
        with pytest.raises(ValueError, match=message):
            native_installer._require_private_parent(tmp_path)
    else:
        native_installer._require_private_parent(tmp_path)


@pytest.mark.skipif(sys.platform != "darwin" or sys.version_info < (3, 11), reason="Native macOS installer test")
def test_macos_inherited_allow_acl_is_rejected_before_creation(native_installer, tmp_path, monkeypatch, capsys):
    parent = tmp_path / "acl-parent"
    parent.mkdir(mode=0o700)
    target = parent / "venv"
    rule = "everyone allow list,search,add_file,add_subdirectory,readattr,writeattr,file_inherit,directory_inherit"
    subprocess.run(["/bin/chmod", "+a", rule, str(parent)], check=True)
    try:
        # The mode alone looks private, but Darwin keeps these granting ACLs.
        assert parent.stat().st_mode & 0o777 == 0o700
        monkeypatch.setattr(native_installer.venv.EnvBuilder, "create", lambda *_: pytest.fail("Untrusted ACL reached venv creation"))
        monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
        assert native_installer.main() == 1
        assert "ACL" in capsys.readouterr().err
        assert not target.exists()
    finally:
        subprocess.run(["/bin/chmod", "-RN", str(parent)], check=True)


@pytest.mark.skipif(os.name != "nt" or sys.version_info < (3, 11, 10), reason="Native supported Windows installer test")
def test_windows_writable_parent_acl_is_rejected_before_creation(native_installer, tmp_path, monkeypatch, capsys):
    parent = tmp_path / "acl-parent"
    parent.mkdir()
    target = parent / "venv"
    # SID syntax avoids localized account names. Only this empty fixture changes.
    subprocess.run(["icacls", str(parent), "/grant", "*S-1-1-0:(OI)(CI)(M)"], check=True, capture_output=True)
    try:
        monkeypatch.setattr(native_installer.venv.EnvBuilder, "create", lambda *_: pytest.fail("Untrusted ACL reached venv creation"))
        monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
        assert native_installer.main() == 1
        assert "ACL" in capsys.readouterr().err
        assert not target.exists()
    finally:
        subprocess.run(["icacls", str(parent), "/remove:g", "*S-1-1-0"], check=True, capture_output=True)


@pytest.mark.skipif(sys.platform not in {"darwin", "win32"} or sys.version_info < (3, 11, 10), reason="Native ACL inspection test")
def test_native_private_parent_is_accepted(native_installer, tmp_path):
    parent = tmp_path / "private-parent"
    parent.mkdir(mode=0o700)
    native_installer._require_private_parent(parent)


@pytest.mark.skipif(sys.platform != "linux" or sys.version_info < (3, 11), reason="Native Linux installer test")
def test_linux_default_acl_is_masked_before_venv_creation(native_installer, tmp_path, monkeypatch, capsys):
    if not shutil.which("setfacl") or not shutil.which("getfacl"):
        pytest.skip("Native ACL utilities are unavailable")
    parent = tmp_path / "acl-parent"
    parent.mkdir(mode=0o700)
    target = parent / "venv"
    subprocess.run(["setfacl", "-m", "d:u:65534:rwx", str(parent)], check=True)

    def inspect_creation(_builder, path):
        assert path.stat().st_mode & 0o777 == 0o700
        acl = subprocess.check_output(["getfacl", "-cpn", str(path)], text=True)
        assert "mask::---" in acl
        raise OSError("Native ACL inspected; no interpreter was executed")

    try:
        monkeypatch.setattr(native_installer.venv.EnvBuilder, "create", inspect_creation)
        monkeypatch.setattr(sys, "argv", ["installer", "--venv", str(target)])
        assert native_installer.main() == 1
        assert "Native ACL inspected" in capsys.readouterr().err
    finally:
        subprocess.run(["setfacl", "-k", str(parent)], check=True)
