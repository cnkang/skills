#!/usr/bin/env python3
"""Read-only repository quality-gate probe.

Collects git, CI, config, documentation, and local Skill signals so an agent can
start a quality-gate closure workflow with stable evidence. The script does not
modify the repository or contact external services.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROBE_VERSION = "0.6"
SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------

SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # URL credentials: https://user:token@host or https://token@host
    (
        re.compile(r"(https?://)([^/\s:@]+):([^/\s@]+)@"),
        r"\1<redacted>:<redacted>@",
    ),
    (
        re.compile(r"(https?://)([^/\s:@]+)@"),
        r"\1<redacted>@",
    ),
    # Bearer tokens (before colon-form to avoid partial match)
    (
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
        "Bearer <redacted>",
    ),
    # Basic auth headers
    (
        re.compile(r"(?i)\bBasic\s+[A-Za-z0-9._~+/=-]{16,}"),
        "Basic <redacted>",
    ),
    # Common token assignments with = sign
    (
        re.compile(
            r"(?i)(?:\b|\.)(token|secret|password|passwd|api[_-]?key"
            r"|sonar[_-]?token|sonar[_-]?login|sonar\.login|sonar\.token"
            r"|github[_-]?token)\s*=\s*[^\s]+"
        ),
        r"\1=<redacted>",
    ),
    # Common token assignments with : sign (YAML, JSON, logs)
    (
        re.compile(
            r"(?i)(?:\b|\.)(token|secret|password|passwd|api[_-]?key"
            r"|sonar[_-]?token|sonar[_-]?login|sonar\.login|sonar\.token"
            r"|github[_-]?token|authorization)\s*:\s*[^\s]+"
        ),
        r"\1: <redacted>",
    ),
    # JSON-style quoted token keys
    (
        re.compile(r'(?i)["\'](?:token|secret|password|api[_-]?key)["\']\s*:\s*["\'][^"\']+["\']'),
        '"<redacted-key>": "<redacted>"',
    ),
    # GitHub fine-grained personal access tokens
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "<redacted-github-pat>"),
    # GitHub classic tokens
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "<redacted-github-token>"),
    # npm tokens
    (re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b"), "<redacted-npm-token>"),
    # Private key blocks
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "<redacted-private-key>",
    ),
]


def redact_text(value: str) -> str:
    """Apply lightweight secret redaction to a string."""
    redacted = value
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_result(result: dict[str, Any]) -> dict[str, Any]:
    """Redact secrets from stdout/stderr in a git command result."""
    clean = dict(result)
    for key in ("stdout", "stderr"):
        if isinstance(clean.get(key), str):
            clean[key] = redact_text(clean[key])
    return clean


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_PATTERNS = [
    "package.json",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "Makefile",
    "CMakeLists.txt",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "sonar-project.properties",
    "tsconfig.json",
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    ".prettierrc",
    "ruff.toml",
    "pytest.ini",
    "vitest.config.js",
    "vitest.config.ts",
    "jest.config.js",
    "jest.config.ts",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.cfg",
    "setup.py",
    "tox.ini",
    "noxfile.py",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
    ".editorconfig",
    ".markdownlint.json",
    ".markdownlint.yaml",
    ".yamllint.yml",
    ".yamllint.yaml",
    "justfile",
    "Taskfile.yml",
    "Taskfile.yaml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "compile_commands.json",
    ".clang-format",
    ".clang-tidy",
    "config",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
]

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "node_modules",
    "target",
    "build",
    "dist",
    "__pycache__",
}

COMMON_TOOLS = [
    "git",
    "gh",
    "make",
    "python3",
    "node",
    "npm",
    "npx",
    "pnpm",
    "yarn",
    "cargo",
    "rustc",
    "go",
    "cmake",
    "ninja",
    "docker",
    "coderabbit",
    "sonar-scanner",
    "cc",
    "gcc",
    "clang",
    "clang-format",
    "clang-tidy",
    "valgrind",
    "perl",
    "prove",
    "nginx",
]

DOC_PATTERNS = [
    "AGENTS.md",
    "README.md",
    "README",
    "CONTRIBUTING.md",
    "CONTRIBUTING",
    "docs",
    "specs",
    "spec",
]

SKILL_ROOTS = [
    "~/.codex/skills",
    "~/.codex/plugins/cache",
    "~/.agents/skills",
    "~/.claude/skills",
]


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


DEFAULT_GIT_TIMEOUT = 15


def run_git(
    repo: Path, args: list[str], timeout_seconds: int = DEFAULT_GIT_TIMEOUT
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": "git command not found"}
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"git command timed out after {timeout_seconds}s: git {' '.join(args)}",
        }

    raw = {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    return redact_result(raw)


def git_stdout(repo: Path, args: list[str]) -> str:
    """Run a git command and return stdout if successful, else empty string."""
    result = run_git(repo, args)
    return result.get("stdout", "") if result.get("ok") else ""


def git_dir(repo: Path) -> Path | None:
    result = run_git(repo, ["rev-parse", "--git-dir"])
    if not result["ok"]:
        return None
    path = Path(result["stdout"])
    if path.is_absolute():
        return path
    return (repo / path).resolve()


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def existing_paths(repo: Path, names: list[str]) -> list[str]:
    found: list[str] = []
    for name in names:
        path = repo / name
        if path.exists():
            found.append(name)
    return found


def discover_configs(repo: Path, names: list[str], max_depth: int = 3) -> list[str]:
    names_set = set(names)
    found: list[str] = []
    for root, dirs, files in os.walk(repo):
        root_path = Path(root)
        try:
            rel_root = root_path.relative_to(repo)
        except ValueError:
            continue
        depth = 0 if str(rel_root) == "." else len(rel_root.parts)
        dirs[:] = [
            dirname
            for dirname in dirs
            if dirname not in EXCLUDED_DIRS and depth < max_depth
        ]
        if depth > max_depth:
            continue
        for filename in files:
            if filename in names_set:
                found.append(str((root_path / filename).relative_to(repo)))
    return sorted(found)


# ---------------------------------------------------------------------------
# Workflow parsing
# ---------------------------------------------------------------------------


def workflow_files(repo: Path) -> list[str]:
    root = repo / ".github" / "workflows"
    if not root.exists():
        return []
    return sorted(str(path.relative_to(repo)) for path in root.glob("*.y*ml"))


RUN_STEP_RE = re.compile(r"^(?P<indent>\s*)(?:-\s*)?run:\s*(?P<value>.*)$")

_BLOCK_SCALAR_RE = re.compile(r"^[|>](?:[+-]?\d*|\d*[+-]?)$")

BLOCK_SCALARS = {"|", ">", "|-", ">-", "|+", ">+"}

_NESTED_KEYS = frozenset({
    "env", "with", "secrets", "inputs", "outputs", "defaults",
    "permissions", "strategy", "matrix", "services", "container",
    "volumes", "options", "credentials", "retry", "browser",
    "artifacts", "cache",
})


def _strip_yaml_comment(value: str) -> str:
    in_single = False
    in_double = False
    i = 0
    while i < len(value):
        c = value[i]
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif c == '#' and not in_single and not in_double:
            return value[:i].rstrip()
        elif c == '\\' and in_double and i + 1 < len(value):
            i += 1
        i += 1
    return value


def _is_block_scalar(value: str) -> bool:
    return _BLOCK_SCALAR_RE.fullmatch(value) is not None


def _is_folded_block_scalar(value: str) -> bool:
    return value.startswith(">")


def _append_block(commands: list[str], block: list[str], folded: bool) -> None:
    if not block:
        return
    if folded:
        commands.append(" ".join(part.strip() for part in block if part.strip()))
    else:
        commands.append("\n".join(block))


def extract_workflow_steps(repo: Path, files: list[str]) -> dict[str, list[str]]:
    steps: dict[str, list[str]] = {}
    for rel in files:
        path = repo / rel
        commands: list[str] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            steps[rel] = [f"<unable to read: {exc}>"]
            continue

        capture_block = False
        block_parent_indent = 0
        folded = False
        block: list[str] = []

        in_steps = False
        steps_indent = -1
        step_item_indent = -1
        nested_depth = 0

        for line in lines:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(" "))

            if capture_block:
                if stripped and indent > block_parent_indent:
                    block.append(line[block_parent_indent + 2 :].rstrip() if len(line) > block_parent_indent + 2 else stripped)
                    continue

                _append_block(commands, block, folded)
                capture_block = False
                folded = False
                block = []

            if not stripped or stripped.startswith("#"):
                continue

            if in_steps and indent <= steps_indent:
                in_steps = False
                steps_indent = -1
                step_item_indent = -1
                nested_depth = 0

            if not in_steps:
                if stripped.startswith("steps:") or stripped.startswith("steps: "):
                    in_steps = True
                    steps_indent = indent
                    step_item_indent = -1
                    nested_depth = 0
                    continue

            if not in_steps:
                continue

            if step_item_indent >= 0 and indent <= step_item_indent:
                if stripped.startswith("- "):
                    step_item_indent = indent
                    nested_depth = 0
                else:
                    step_item_indent = -1
                    nested_depth = 0

            if step_item_indent < 0:
                if stripped.startswith("- "):
                    step_item_indent = indent
                    nested_depth = 0

            if nested_depth > 0 and indent <= step_item_indent + 2:
                nested_depth = 0

            if nested_depth == 0 and step_item_indent >= 0:
                key_candidate = stripped.split(":")[0].strip()
                if key_candidate.startswith("- "):
                    key_candidate = key_candidate[2:].strip()
                if key_candidate in _NESTED_KEYS:
                    nested_depth = 1
                    continue

            if nested_depth > 0:
                continue

            match = RUN_STEP_RE.match(line)
            if match:
                value = match.group("value").strip()
                if not value or value.startswith("#"):
                    continue
                value = _strip_yaml_comment(value)
                value = value.strip("\"'")
                if _is_block_scalar(value):
                    capture_block = True
                    block_parent_indent = len(match.group("indent"))
                    folded = _is_folded_block_scalar(value)
                    block = []
                    continue
                if value:
                    commands.append(value)

        if capture_block and block:
            _append_block(commands, block, folded)

        steps[rel] = commands
    return steps


# ---------------------------------------------------------------------------
# Git state
# ---------------------------------------------------------------------------


def detect_git_state(repo: Path) -> dict[str, bool]:
    gdir = git_dir(repo)
    if gdir is None:
        return {
            "is_git_repo": False,
            "merge": False,
            "rebase": False,
            "cherry_pick": False,
            "revert": False,
        }
    return {
        "is_git_repo": True,
        "merge": (gdir / "MERGE_HEAD").exists(),
        "rebase": (gdir / "rebase-apply").exists()
        or (gdir / "rebase-merge").exists(),
        "cherry_pick": (gdir / "CHERRY_PICK_HEAD").exists(),
        "revert": (gdir / "REVERT_HEAD").exists(),
    }


# ---------------------------------------------------------------------------
# Diff scope
# ---------------------------------------------------------------------------


def discover_agent_files(repo: Path, max_depth: int = 5) -> list[str]:
    found: list[str] = []
    for root, dirs, files in os.walk(repo):
        root_path = Path(root)
        try:
            rel_root = root_path.relative_to(repo)
        except ValueError:
            continue
        depth = 0 if str(rel_root) == "." else len(rel_root.parts)
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and depth < max_depth]
        if "AGENTS.md" in files:
            found.append(str((root_path / "AGENTS.md").relative_to(repo)))
    return sorted(found)


def collect_diff_scope(
    repo: Path, base_ref: str | None = None
) -> dict[str, Any]:
    """Collect upstream, merge-base, and changed file information for scope."""
    upstream = git_stdout(
        repo,
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
    )
    head = git_stdout(repo, ["rev-parse", "HEAD"])

    effective_base = ""
    base_ref_source = ""
    base_ref_resolved = ""

    if base_ref:
        verify = run_git(
            repo, ["rev-parse", "--verify", "--quiet", f"{base_ref}^{{commit}}"]
        )
        if verify.get("ok") and verify.get("stdout"):
            effective_base = base_ref
            base_ref_source = "explicit"
            base_ref_resolved = verify["stdout"]
        else:
            base_ref_source = "explicit_unresolved"
    if not effective_base and not base_ref and upstream:
        effective_base = upstream
        base_ref_source = "upstream"
    if not effective_base and not base_ref:
        for candidate in ("origin/main", "origin/master", "main", "master"):
            resolved = git_stdout(repo, ["rev-parse", "--abbrev-ref", candidate])
            if resolved:
                effective_base = resolved
                base_ref_source = "fallback"
                break

    data: dict[str, Any] = {
        "upstream": upstream,
        "head": head,
        "base_ref": effective_base,
        "base_ref_source": base_ref_source,
        "base_ref_resolved": base_ref_resolved,
        "merge_base": "",
        "changed_vs_base": [],
        "staged": [],
        "unstaged": [],
        "untracked": [],
    }

    staged = git_stdout(repo, ["diff", "--cached", "--name-status"])
    data["staged"] = staged.splitlines() if staged else []

    unstaged = git_stdout(repo, ["diff", "--name-status"])
    data["unstaged"] = unstaged.splitlines() if unstaged else []

    untracked = git_stdout(
        repo, ["ls-files", "--others", "--exclude-standard"]
    )
    data["untracked"] = untracked.splitlines() if untracked else []

    if effective_base:
        merge_base = git_stdout(repo, ["merge-base", "HEAD", effective_base])
        data["merge_base"] = merge_base
        if merge_base:
            changed = git_stdout(
                repo, ["diff", "--name-status", f"{merge_base}...HEAD"]
            )
            data["changed_vs_base"] = changed.splitlines() if changed else []

    return data


# ---------------------------------------------------------------------------
# Stack inference
# ---------------------------------------------------------------------------


def infer_stack(configs: list[str]) -> list[str]:
    stack: list[str] = []
    add = stack.append
    basenames = {Path(config).name for config in configs}
    if "package.json" in basenames:
        add("Node.js/JavaScript")
    if "Cargo.toml" in basenames:
        add("Rust/Cargo")
    if "pyproject.toml" in basenames or "pytest.ini" in basenames:
        add("Python")
    if "go.mod" in basenames:
        add("Go")
    if "CMakeLists.txt" in basenames:
        add("C/C++/CMake")
    if "Makefile" in basenames:
        add("Make")
    if "sonar-project.properties" in basenames:
        add("SonarCloud/SonarQube")
    return stack


# ---------------------------------------------------------------------------
# Tool availability
# ---------------------------------------------------------------------------


def collect_tool_availability() -> dict[str, str | None]:
    return {tool: shutil.which(tool) for tool in COMMON_TOOLS}


# ---------------------------------------------------------------------------
# Local Skills
# ---------------------------------------------------------------------------


def read_skill_summary(skill_md: Path) -> dict[str, str]:
    """Extract name and description from a SKILL.md file."""
    name = skill_md.parent.name
    description = ""
    try:
        for line in skill_md.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            stripped = line.strip()
            if stripped.startswith("name:"):
                name = stripped.partition(":")[2].strip().strip("\"'")
            elif stripped.startswith("description:"):
                description = stripped.partition(":")[2].strip().strip("\"'")
            if name and description:
                break
    except OSError:
        pass
    return {"name": name, "path": str(skill_md), "description": description}


def collect_local_skills(
    repo: Path,
    limit: int,
    roots: list[Path] | None = None,
    max_depth: int = 6,
) -> tuple[list[dict[str, str]], list[str]]:
    """Discover local Skills with bounded depth and count.

    Returns a tuple of (skills_found, warnings).
    """
    warnings: list[str] = []

    if limit <= 0:
        return [], ["Local Skill scan disabled by skill limit <= 0."]

    search_roots = roots or [
        Path(os.path.expanduser(root)) for root in SKILL_ROOTS
    ]
    search_roots.extend([repo / ".skills", repo / "skills"])

    skills: list[dict[str, str]] = []
    seen: set[Path] = set()

    for root in search_roots:
        if not root.exists():
            continue
        if not root.is_dir():
            warnings.append(f"Skill root is not a directory: {root}")
            continue
        try:
            resolved_root = root.resolve()
        except OSError as exc:
            warnings.append(f"Unable to resolve skill root {root}: {exc}")
            continue

        for current, dirs, files in os.walk(resolved_root, followlinks=False):
            current_path = Path(current)
            try:
                rel = current_path.relative_to(resolved_root)
            except ValueError:
                continue

            depth = 0 if str(rel) == "." else len(rel.parts)
            if depth >= max_depth:
                dirs[:] = []
                continue

            dirs[:] = [
                d
                for d in dirs
                if d not in EXCLUDED_DIRS
                and d not in {"__pycache__", "__MACOSX"}
                and not d.startswith(".")
            ]

            if "SKILL.md" not in files:
                continue

            skill_md = current_path / "SKILL.md"
            try:
                resolved_skill = skill_md.resolve()
            except OSError:
                continue

            if resolved_skill in seen:
                continue
            seen.add(resolved_skill)

            skills.append(read_skill_summary(skill_md))
            if len(skills) >= limit:
                warnings.append(
                    f"Local Skill scan stopped after reaching limit={limit}."
                )
                return skills, warnings

    return skills, warnings


# ---------------------------------------------------------------------------
# Skill root builder
# ---------------------------------------------------------------------------


def build_skill_roots(
    explicit: list[str], extra: list[str]
) -> list[Path] | None:
    """Build the skill roots list from CLI arguments.

    --skill-root: replaces default roots entirely.
    --extra-skill-root: appends to default roots.
    If neither is provided, returns None to use defaults.
    """
    if explicit:
        return [Path(p).expanduser() for p in explicit]
    if extra:
        roots = [Path(os.path.expanduser(root)) for root in SKILL_ROOTS]
        roots.extend(Path(p).expanduser() for p in extra)
        return roots
    return None


# ---------------------------------------------------------------------------
# Main collector
# ---------------------------------------------------------------------------


def collect(
    repo: Path,
    skill_limit: int,
    skill_scan: bool = True,
    skill_roots: list[Path] | None = None,
    skill_max_depth: int = 6,
    base_ref: str | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    git_state = detect_git_state(repo)
    is_git = git_state.get("is_git_repo", False)

    workflows = workflow_files(repo)
    root_configs = existing_paths(repo, CONFIG_PATTERNS)
    discovered_configs = discover_configs(repo, CONFIG_PATTERNS)
    configs = sorted(set(root_configs) | set(discovered_configs))
    docs = existing_paths(repo, DOC_PATTERNS)
    agent_files = discover_agent_files(repo)

    warnings: list[str] = [
        "Workflow run-step extraction is best-effort; read workflow files directly before claiming CI equivalence.",
        "The probe is read-only and advisory; it does not replace real validation commands.",
    ]

    if skill_scan:
        local_skills, skill_warnings = collect_local_skills(
            repo,
            skill_limit,
            roots=skill_roots,
            max_depth=skill_max_depth,
        )
        warnings.extend(skill_warnings)
    else:
        local_skills = []
        warnings.append("Local Skill scan disabled by --no-skill-scan.")

    if is_git:
        git_data: dict[str, Any] = {
            "state": git_state,
            "branch": run_git(repo, ["branch", "--show-current"]),
            "status_short": run_git(repo, ["status", "--short"]),
            "remote_v": run_git(repo, ["remote", "-v"]),
            "recent_commits": run_git(
                repo, ["log", "--oneline", "-n", "5"]
            ),
            "head": run_git(repo, ["rev-parse", "HEAD"]),
        }
        diff_scope = collect_diff_scope(repo, base_ref=base_ref)
    else:
        git_data = {
            "state": git_state,
            "branch": {"ok": False, "stdout": "", "stderr": "not a git repository"},
            "status_short": {"ok": False, "stdout": "", "stderr": "not a git repository"},
            "remote_v": {"ok": False, "stdout": "", "stderr": "not a git repository"},
            "recent_commits": {"ok": False, "stdout": "", "stderr": "not a git repository"},
            "head": {"ok": False, "stdout": "", "stderr": "not a git repository"},
        }
        diff_scope = {}
        warnings.append(
            "Not a git repository; git-related sections are unavailable."
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "probe_version": PROBE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "git": git_data,
        "diff_scope": diff_scope,
        "docs": docs,
        "configs": configs,
        "root_configs": root_configs,
        "agent_instruction_files": agent_files,
        "stack": infer_stack(configs),
        "tool_availability": collect_tool_availability(),
        "workflows": workflows,
        "workflow_run_steps": extract_workflow_steps(repo, workflows),
        "local_skills": local_skills,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Path display
# ---------------------------------------------------------------------------


def display_path(path: str) -> str:
    home = str(Path.home())
    if path == home:
        return "~"
    if path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------


def print_markdown(data: dict[str, Any]) -> None:
    git = data["git"]
    state = git["state"]
    is_git = state.get("is_git_repo", False)

    print("# Repository Quality Probe")
    print()
    print(f"- Repository: `{display_path(data['repo'])}`")

    if is_git:
        print(f"- Branch: `{git['branch'].get('stdout') or '<unknown>'}`")
        print(f"- HEAD: `{git['head'].get('stdout') or '<unknown>'}`")
    else:
        print("- Branch: `<not a git repository>`")
        print("- HEAD: `<not a git repository>`")

    print(
        "- Git state: "
        + ", ".join(f"{key}={value}" for key, value in state.items())
    )
    print()

    print("## Warnings")
    for warning in data.get("warnings", []) or ["<none>"]:
        print(f"- {warning}")
    print()

    print("## Worktree")
    if not is_git:
        status = "<not a git repository>"
    else:
        status = git["status_short"].get("stdout") or "<clean>"
    print("```text")
    print(status)
    print("```")
    print()

    print("## Recent Commits")
    if not is_git:
        print("```text")
        print("<not a git repository>")
        print("```")
    else:
        print("```text")
        print(git["recent_commits"].get("stdout") or "<unavailable>")
        print("```")
    print()

    # Diff scope
    diff_scope = data.get("diff_scope", {})
    if diff_scope:
        print("## Diff Scope")
        print(
            f"- Upstream: `{diff_scope.get('upstream') or '<unavailable>'}`"
        )
        base_ref_val = diff_scope.get("base_ref", "")
        base_ref_src = diff_scope.get("base_ref_source", "")
        if base_ref_val:
            print(f"- Base ref: `{base_ref_val}` (source: {base_ref_src})")
        print(
            f"- Merge base: `{diff_scope.get('merge_base') or '<unavailable>'}`"
        )
        print()

        changed = diff_scope.get("changed_vs_base", [])
        print("### Changed vs base")
        print("```text")
        print("\n".join(changed) if changed else "<none or base unavailable>")
        print("```")
        print()

        staged = diff_scope.get("staged", [])
        print("### Staged changes")
        print("```text")
        print("\n".join(staged) if staged else "<none>")
        print("```")
        print()

        unstaged = diff_scope.get("unstaged", [])
        print("### Unstaged changes")
        print("```text")
        print("\n".join(unstaged) if unstaged else "<none>")
        print("```")
        print()

        untracked = diff_scope.get("untracked", [])
        print("### Untracked files")
        print("```text")
        print("\n".join(untracked) if untracked else "<none>")
        print("```")
        print()

    print("## Detected Stack")
    for item in data["stack"] or ["<none detected from common configs>"]:
        print(f"- {item}")
    print()

    print("## Rule And Config Inputs")
    for item in data["docs"] + data["configs"]:
        print(f"- `{item}`")
    if not data["docs"] and not data["configs"]:
        print("- <none detected>")
    print()

    agent_files = data.get("agent_instruction_files", [])
    if agent_files:
        print("## Agent Instruction Files")
        for af in agent_files:
            print(f"- `{af}`")
        print()

    print("## Common Tool Availability")
    for tool, path in data["tool_availability"].items():
        value = f"`{display_path(path)}`" if path else "<not found>"
        print(f"- `{tool}`: {value}")
    print()

    print("## GitHub Workflow Run Steps")
    print(
        "These extracted run steps are best-effort and must be verified "
        "against the workflow files directly."
    )
    print()
    if not data["workflows"]:
        print("- <no .github/workflows/*.yml files detected>")
    for rel, steps in data["workflow_run_steps"].items():
        print(f"- `{rel}`")
        for step in steps or ["<no run steps detected>"]:
            print(f"  - `{step}`")
    print()

    print("## Local Skills")
    if not data["local_skills"]:
        print("- <none detected>")
    for skill in data["local_skills"]:
        desc = f" - {skill['description']}" if skill["description"] else ""
        print(f"- `{skill['name']}`: `{skill['path']}`{desc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_path", nargs="?", default=".")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument(
        "--skill-limit",
        type=int,
        default=80,
        help="maximum number of local skills to list",
    )
    parser.add_argument(
        "--no-skill-scan",
        action="store_true",
        help="disable local Skill discovery",
    )
    parser.add_argument(
        "--skill-root",
        action="append",
        default=[],
        help=(
            "explicit user-level Skill root to scan instead of default user-level roots; "
            "repository-local .skills/ and skills/ are still included; "
            "can be provided multiple times"
        ),
    )
    parser.add_argument(
        "--extra-skill-root",
        action="append",
        default=[],
        help=(
            "additional Skill root to scan along with default roots; "
            "can be provided multiple times"
        ),
    )
    parser.add_argument(
        "--skill-max-depth",
        type=int,
        default=6,
        help="maximum directory depth for local Skill discovery",
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help="explicit base ref for diff scope, e.g. origin/main",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo_path)
    if not repo.exists():
        print(f"repo path does not exist: {repo}", file=sys.stderr)
        return 2

    data = collect(
        repo,
        skill_limit=max(args.skill_limit, 0),
        skill_scan=not args.no_skill_scan,
        skill_roots=build_skill_roots(args.skill_root, args.extra_skill_root),
        skill_max_depth=max(args.skill_max_depth, 1),
        base_ref=args.base_ref,
    )

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print_markdown(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
