"""Real Git regression tests for index inspection; no mutation of the user's repo."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
import precommit_safety_gate as gate


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.delenv("GIT_WORK_TREE", raising=False)
    monkeypatch.delenv("GIT_INDEX_FILE", raising=False)
    subprocess.run(["git", "init", "-b", "feature/test", str(tmp_path)], check=True, capture_output=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, capture_output=True, text=True)


def execute_gate(repo, *args):
    return subprocess.run([sys.executable, str(Path(gate.__file__).resolve()), *args], cwd=repo, capture_output=True, text=True)


def test_large_index_blob_not_small_worktree(repo):
    p = repo / "data.txt"
    p.write_text("a" * 600_000)
    git("add", "data.txt")
    p.write_text("small unstaged edit")
    assert gate.staged_file_sizes(repo, ["data.txt"]) == {"data.txt": 600_000}
    result = execute_gate(repo)
    assert result.returncode == 2
    assert "600000 bytes" in result.stdout


def test_small_index_blob_not_large_worktree(repo):
    p = repo / "data.txt"
    p.write_text("small")
    git("add", "data.txt")
    p.write_text("a" * 600_000)
    assert execute_gate(repo).returncode == 0
    p.unlink()
    assert gate.staged_file_sizes(repo, ["data.txt"]) == {"data.txt": 5}


@pytest.mark.parametrize("name", ["space ü.txt", "-leading.txt", "literal[1].txt", "tab\tname.txt", 'quote"name.txt', "line\nname.txt"])
def test_special_paths_are_preserved(repo, name):
    if os.name == "nt" and any(c in name for c in '\t\n"'):
        pytest.skip("Windows filesystem forbids this filename")
    (repo / name).write_text("a" * 600_000)
    git("add", "--", name)
    paths, _, _, rows = gate.inspect_index(repo)
    assert paths == [name]
    assert rows[0][2] == name
    assert gate.staged_file_sizes(repo, paths)[name] == 600_000
    assert execute_gate(repo).returncode == 2


def commit_base():
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")


def test_staged_rename_and_deletion(repo):
    (repo / "old.txt").write_text("initial")
    git("add", "old.txt")
    commit_base()
    git("mv", "old.txt", "new name.txt")
    assert gate.inspect_index(repo)[0] == ["new name.txt"]
    assert gate.staged_file_sizes(repo, ["new name.txt"])["new name.txt"] == 7
    assert execute_gate(repo).returncode == 0
    commit_base()
    git("rm", "new name.txt")
    assert gate.inspect_index(repo)[0] == []
    assert execute_gate(repo).returncode == 0


def test_unmerged_index_blocks_even_with_other_staged_content(repo):
    (repo / "conflict.txt").write_text("base\n")
    git("add", "conflict.txt")
    commit_base()
    git("checkout", "-b", "other")
    (repo / "conflict.txt").write_text("other\n")
    git("add", "conflict.txt")
    commit_base()
    git("checkout", "feature/test")
    (repo / "conflict.txt").write_text("ours\n")
    git("add", "conflict.txt")
    commit_base()
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "merge", "other", check=False)
    (repo / "clean.txt").write_text("ok")
    git("add", "clean.txt")
    result = execute_gate(repo, "--allow-sensitive", "--allow-large-or-binary")
    assert result.returncode == 3
    assert "Unresolved index entries" in result.stdout


def test_secret_value_never_appears_in_report(repo):
    secret = "fixture-private-value"
    (repo / "app.py").write_text(f"password = '{secret}'\n")
    git("add", "app.py")
    result = execute_gate(repo)
    assert result.returncode == 2
    assert secret not in result.stdout + result.stderr
    assert "app.py" in result.stdout


def test_git_failure_is_not_a_pass(repo, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["gate"])
    monkeypatch.setattr(gate, "run_git", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("git")))
    assert gate.main() == 1
