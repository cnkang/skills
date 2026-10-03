#!/usr/bin/env python3
"""Real skills CLI installation/update tests in disposable home/project directories."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_skills import SKILLS, validate_skill

ROOT = Path(__file__).resolve().parents[1]
AGENTS = {
    "codex": (".agents/skills", ".codex/skills"),
    "claude-code": (".claude/skills", ".claude/skills"),
    "opencode": (".agents/skills", ".config/opencode/skills"),
    "cursor": (".agents/skills", ".cursor/skills"),
    "gemini-cli": (".agents/skills", ".gemini/skills"),
    "kiro-cli": (".kiro/skills", ".kiro/skills"),
    "kimi-code-cli": (".agents/skills", ".agents/skills"),
    "qwen-code": (".qwen/skills", ".qwen/skills"),
    "hermes-agent": (".hermes/skills", ".hermes/skills"),
}
HELPERS = {
    "conventional-commit-batcher": "validate_conventional_commit.py",
    "dev-jev": "telemetry.py",
    "repository-quality-gate-fixer": "repo_quality_probe.py",
    "sonarcloud-link-inspector": "inspect_sonarcloud_link.py",
}


def isolated_env(home: Path) -> dict[str, str]:
    # Do not forward tokens, Git credentials, runtime agent identity or user config.
    keys = ("PATH", "SystemRoot", "SYSTEMROOT", "COMSPEC", "PATHEXT", "TEMP", "TMP", "LANG", "LC_ALL")
    env = {key: os.environ[key] for key in keys if key in os.environ}
    home.mkdir(parents=True, exist_ok=True)
    env.update({"HOME": str(home), "USERPROFILE": str(home), "XDG_CONFIG_HOME": str(home / ".config"), "XDG_STATE_HOME": str(home / ".local/state"), "APPDATA": str(home / "AppData/Roaming"), "LOCALAPPDATA": str(home / "AppData/Local"), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "DO_NOT_TRACK": "1", "DISABLE_TELEMETRY": "1", "CI": "1", "NO_COLOR": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    return env


def run(argv: list[str], cwd: Path, env: dict[str, str], *, timeout: int = 120) -> str:
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed: {argv[:4]}\n{result.stdout[-3000:]}\n{result.stderr[-1000:]}")
    return result.stdout


def resolve_cli(version: str, temp: Path) -> Path:
    if not re.fullmatch(r"latest|\d+\.\d+\.\d+", version):
        raise ValueError("Use a released CLI version or latest")
    env = isolated_env(temp / "bootstrap-home")
    env["npm_config_cache"] = str(temp / "npm-cache")
    command = ["npm", "exec", "--yes", f"--package=skills@{version}", "--", sys.executable, "-c", "import os,shutil; print(os.path.realpath(shutil.which('skills')))"]
    if os.name == "nt":
        command = ["cmd", "/d", "/c", *command]
    path = Path(run(command, temp, env, timeout=240).strip().splitlines()[-1])
    cli = path if path.suffix == ".mjs" else path.parent.parent / "skills/bin/cli.mjs"
    if not cli.exists():
        raise RuntimeError("Could not resolve installed skills CLI")
    return cli


def hash_folder(folder: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(path.relative_to(folder).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def verify_package(folder: Path, env: dict[str, str], cwd: Path) -> None:
    errors = validate_skill(folder)
    if errors:
        raise AssertionError("\n".join(errors))
    run([sys.executable, str(folder / "scripts" / HELPERS[folder.name]), "--help"], cwd, env)
    if folder.name == "dev-jev":
        assert run([sys.executable, str(folder / "scripts/telemetry.py"), "mode"], cwd, env).strip() == "shadow"
    if folder.name == "repository-quality-gate-fixer":
        report = json.loads(run([sys.executable, str(folder / "scripts/repo_quality_probe.py"), str(cwd), "--json"], cwd, env))
        assert report["local_skills"] == []


def smoke(cli: Path, temp: Path) -> int:
    commands = 0
    node = shutil.which("node")
    assert node
    # All 15 subsets, each in a fresh project and home.
    for count in range(1, 5):
        for number, selected in enumerate(itertools.combinations(SKILLS, count)):
            base = temp / f"subset-{count}-{number}"
            cwd = base / "project"
            cwd.mkdir(parents=True)
            env = isolated_env(base / "home")
            run([node, str(cli), "add", str(ROOT), "--skill", *selected, "-a", "codex", "-y"], cwd, env)
            commands += 1
            folder = cwd / ".agents/skills"
            assert {p.name for p in folder.iterdir() if (p / "SKILL.md").exists()} == set(selected)
            for name in selected:
                verify_package(folder / name, env, cwd)
            before = {name: hash_folder(folder / name) for name in selected}
            run([node, str(cli), "add", str(ROOT), "--skill", *selected, "-a", "codex", "-y"], cwd, env)
            assert before == {name: hash_folder(folder / name) for name in selected}
            commands += 1
    print("PASS: 15 independent selection combinations and repeat installation", flush=True)
    # Every named host, both scopes, both install methods; only one skill present.
    for agent, paths in AGENTS.items():
        for global_scope in (False, True):
            for copy in (False, True):
                base = temp / f"host-{agent}-{global_scope}-{copy}"
                cwd = base / "project"
                cwd.mkdir(parents=True)
                env = isolated_env(base / "home")
                flags = (["-g"] if global_scope else []) + (["--copy"] if copy else [])
                run([node, str(cli), "add", str(ROOT), "--skill", SKILLS[0], "-a", agent, "-y", *flags], cwd, env)
                commands += 1
                folder = Path(env["HOME"]) / (".agents/skills" if paths[0] == ".agents/skills" else paths[1]) if global_scope else cwd / paths[0]
                verify_package(folder / SKILLS[0], env, cwd)
                assert {p.name for p in folder.iterdir() if (p / "SKILL.md").exists()} == {SKILLS[0]}
        print(f"PASS: {agent} project/global symlink/copy package installation", flush=True)
    # Prompt output only: no host executable is started or persistent skill installed.
    base = temp / "use"
    cwd = base / "project"
    cwd.mkdir(parents=True)
    env = isolated_env(base / "home")
    prompt = run([node, str(cli), "use", str(ROOT), "--skill", "dev-jev"], cwd, env)
    assert "dev-jev" in prompt
    assert not (cwd / ".agents/skills").exists()
    assert not (Path(env["HOME"]) / ".agents/skills").exists()
    commands += 1
    print("PASS: single-skill temporary use emits a prompt without persistent installation", flush=True)
    return commands


def commit_fixture(source: Path, env: dict[str, str]) -> None:
    run(["git", "add", "--all"], source, env)
    run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture update"], source, env)


def update_tests(cli: Path, temp: Path) -> int:
    node = shutil.which("node")
    assert node
    count = 0
    for scope in ("project", "global"):
        for copy in (False, True):
            base = temp / f"update-{scope}-{copy}"
            cwd = base / "project"
            cwd.mkdir(parents=True)
            env = isolated_env(base / "home")
            preload = base / "offline-fetch.mjs"
            preload.write_text('globalThis.fetch = async () => new Response("fixture-only", {status: 404});\n')
            env["NODE_OPTIONS"] = "--import=" + preload.as_uri()
            source = base / "source.git"
            source.mkdir()
            for name in SKILLS:
                shutil.copytree(ROOT / name, source / name, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
            run(["git", "init", "-b", "main"], source, env)
            (source / SKILLS[0] / "references/obsolete-fixture.md").write_text("old reference\n")
            commit_fixture(source, env)
            run(["git", "tag", "fixture-v1"], source, env)
            # A Git URL and branch/ref semantics with no external service or credentials.
            url = "https://skills-fixture.invalid/fixtures/source.git"
            env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"url.{source.as_uri()}.insteadOf", "GIT_CONFIG_VALUE_0": url})
            scope_flags = ["-g"] if scope == "global" else []
            method = ["--copy"] if copy else []
            def add(names, origin=url, extra=()):
                nonlocal count
                run([node, str(cli), "add", origin, "--skill", *names, "-a", "codex", "-y", *scope_flags, *method, *extra], cwd, env)
                count += 1
            def update(names):
                nonlocal count
                output = run([node, str(cli), "update", *names, "-g" if scope == "global" else "-p", "-y"], cwd, env)
                if "Failed" in output or "Cannot" in output or "could not" in output:
                    raise RuntimeError(output)
                count += 1
                return output
            add(SKILLS)
            installed = Path(env["HOME"]) / ".agents/skills" if scope == "global" else cwd / ".agents/skills"
            before = {n: hash_folder(installed / n) for n in SKILLS}
            # Change only references/scripts, never metadata.version: hash-based updates.
            for name in SKILLS:
                (source / name / "references/update-fixture.md").write_text("new reference\n")
                (source / name / "scripts/update_fixture.py").write_text('print("new helper")\n')
            (source / SKILLS[0] / "references/obsolete-fixture.md").unlink()
            commit_fixture(source, env)
            update_output = update([SKILLS[0]])
            assert hash_folder(installed / SKILLS[0]) != before[SKILLS[0]], update_output
            assert not (installed / SKILLS[0] / "references/obsolete-fixture.md").exists()
            for name in SKILLS[1:]:
                assert hash_folder(installed / name) == before[name]
            first_updated = hash_folder(installed / SKILLS[0])
            update([SKILLS[1], SKILLS[2]])
            assert hash_folder(installed / SKILLS[0]) == first_updated
            assert hash_folder(installed / SKILLS[3]) == before[SKILLS[3]]
            for name in SKILLS[1:3]:
                assert (installed / name / "scripts/update_fixture.py").exists()
            # Pinned ref keeps old content; changing version cannot migrate source/ref.
            add([SKILLS[3]], url + "#fixture-v1")
            pinned = hash_folder(installed / SKILLS[3])
            update([SKILLS[3]])
            assert hash_folder(installed / SKILLS[3]) == pinned
            # A deliberate re-add migrates the source and leaves other skills intact.
            migrated = base / "migrated.git"
            shutil.copytree(source, migrated, ignore=shutil.ignore_patterns(".git"))
            run(["git", "init", "-b", "main"], migrated, env)
            (migrated / SKILLS[3] / "references/migration-fixture.md").write_text("new source\n")
            commit_fixture(migrated, env)
            second_url = "https://skills-fixture.invalid/fixtures/migrated.git"
            env.update({"GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_1": f"url.{migrated.as_uri()}.insteadOf", "GIT_CONFIG_VALUE_1": second_url})
            add([SKILLS[3]], second_url)
            lock_path = Path(env["XDG_STATE_HOME"]) / "skills/.skill-lock.json" if scope == "global" else cwd / "skills-lock.json"
            lock = json.loads(lock_path.read_text())
            assert lock["skills"][SKILLS[3]]["sourceUrl"] == second_url
            assert (installed / SKILLS[3] / "references/migration-fixture.md").exists()
            assert hash_folder(installed / SKILLS[0]) == first_updated
            for name in SKILLS:
                verify_package(installed / name, env, cwd)
            print(f"PASS: {scope} {'copy' if copy else 'symlink'} selective updates, hash changes, deletion, pinned ref and source migration", flush=True)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, help="existing skills/bin/cli.mjs; skips npm bootstrap")
    parser.add_argument("--cli-version", default="1.7.0")
    parser.add_argument("--only", choices=["all", "install", "update"], default="all")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="skills-distribution-") as work:
        temp = Path(work)
        cli = args.cli.resolve() if args.cli else resolve_cli(args.cli_version, temp)
        env = isolated_env(temp / "version-home")
        version = run([shutil.which("node"), str(cli), "--version"], temp, env).strip()
        print(f"Python {sys.version.split()[0]}; Node {run(['node', '--version'], temp, env).strip()}; skills {version}", flush=True)
        commands = (smoke(cli, temp) if args.only != "update" else 0) + (update_tests(cli, temp) if args.only != "install" else 0)
        print(f"PASS: {commands} real CLI install/use/update commands in isolated fixtures", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
