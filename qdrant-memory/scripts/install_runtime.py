#!/usr/bin/env python3
"""Install the reviewed standalone backend into an explicitly selected private venv.

Print a Hermes advisory and continue: recommend the native plugin when it is
missing, note when an installed plugin is disabled, and state that the skill
is not necessary for Hermes when the plugin is enabled. Detection reads the
active Hermes profile (HERMES_HOME, or ~/.hermes) and its config.yaml; no
Hermes command runs. Other agents can still use the runtime.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
import subprocess
import sys
import venv

REVISION = "1f0bfc0fbaf6f3b7ec2bc791728d89ceb31b0ad4"
PLUGIN_ID = "qdrant-memory"
REQUIREMENT = (
    "hermes-plugin-qdrant-memory[mcp] @ "
    "git+https://github.com/cnkang/hermes-plugin-qdrant-memory.git@" + REVISION
)


def _hermes_home() -> Path | None:
    """Return the active Hermes home: HERMES_HOME when set, else ~/.hermes."""
    configured = os.environ.get("HERMES_HOME")
    if configured:
        try:
            home = Path(configured).expanduser()
        except (OSError, RuntimeError, ValueError):
            return None
        return home if home.is_absolute() else None
    try:
        return Path.home() / ".hermes"
    except (OSError, RuntimeError, ValueError):
        return None


def hermes_detected() -> bool:
    """Report Hermes on this machine without failing setup."""
    if shutil.which("hermes"):
        return True
    home = _hermes_home()
    if home is None:
        return False
    try:
        return home.is_dir()
    except OSError:
        return False


def _inline_ids(value: str) -> set[str]:
    """IDs from an inline list value such as ``[qdrant-memory, other]``."""
    inner = value.strip().lstrip("[").rstrip("]")
    items: list[str] = []
    buf = ""
    quote = ""
    for char in inner:
        if quote:
            if char == quote:
                quote = ""
            else:
                buf += char
        elif char in "'\"":
            quote = char
        elif char == ",":
            items.append(buf)
            buf = ""
        else:
            buf += char
    items.append(buf)
    return {item.strip() for item in items if item.strip()}


def _scan_disabled_ids(text: str) -> set[str]:
    """Best-effort scan for ``plugins:`` -> ``disabled:`` items.

    Handles the block layout plus single-line flow mappings such as
    ``plugins: {disabled: [qdrant-memory]}``, tolerating comments, blank
    lines, CRLF endings and indentation variations; PyYAML stays preferred
    when importable. Unparsed shapes (for example flow mappings split across
    lines) yield an empty set — the plugin is then treated as enabled, its
    default backend state.
    """
    found: set[str] = set()
    sub_indent = None  # indentation of the plugins sub-keys once seen
    in_disabled = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if sub_indent is None:
            if re.fullmatch(r"plugins:[ \t]*", line):
                sub_indent = -1  # marker: awaiting the first indented line
            else:
                flow = re.fullmatch(r"plugins:[ \t]*\{(.*)\}[ \t]*", line)
                inner = re.search(r"disabled:[ \t]*\[(.*?)\]", flow.group(1)) if flow else None
                if inner:
                    found.update(_inline_ids("[" + inner.group(1) + "]"))
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            break  # left the plugins mapping
        indent = len(line) - len(line.lstrip())
        if sub_indent == -1:
            sub_indent = indent
        if indent < sub_indent:
            break
        if indent > sub_indent:
            if in_disabled and stripped.startswith("-"):
                item = stripped[1:].split("#", 1)[0].strip().strip("'\"")
                if item:
                    found.add(item)
            continue
        key, _, value = stripped.partition(":")
        value = value.split("#", 1)[0].strip()
        in_disabled = key == "disabled"
        if in_disabled and value.startswith("["):
            found.update(_inline_ids(value))
    return found


def _plugin_disabled_in_config(home: Path) -> bool:
    """True when the profile config explicitly disables the plugin.

    A memory backend is active without a ``plugins.enabled`` entry, so only a
    ``plugins.disabled`` entry turns it off. Best effort: YAML when available,
    a tolerant scan of the block layout otherwise (comments, blank lines and
    indentation variations are accepted); unreadable or undecodable configs
    report False (installed and active).
    """
    try:
        text = (home / "config.yaml").read_text(encoding="utf-8")
    except (OSError, ValueError):
        return False
    try:
        import yaml  # optional; the venv under construction may not have it
    except ImportError:
        yaml = None
    if yaml is not None:
        try:
            plugins = (yaml.safe_load(text) or {}).get("plugins")
            if isinstance(plugins, dict) and isinstance(plugins.get("disabled"), list):
                return PLUGIN_ID in {str(item) for item in plugins["disabled"]}
        except Exception:
            pass
    return PLUGIN_ID in _scan_disabled_ids(text)


def hermes_plugin_state() -> str:
    """Return 'absent', 'enabled' or 'disabled' for the active Hermes home."""
    home = _hermes_home()
    if home is None:
        return "absent"
    try:
        if not (home / "plugins" / PLUGIN_ID).is_dir():
            return "absent"
    except OSError:
        return "absent"
    return "disabled" if _plugin_disabled_in_config(home) else "enabled"


def hermes_advisory() -> str:
    """Return the Hermes install advisory, or an empty string when none applies."""
    if not hermes_detected():
        return ""
    state = hermes_plugin_state()
    if state == "enabled":
        return (
            "Note: Hermes on this machine already has the qdrant-memory plugin enabled.\n"
            "This skill is not necessary for Hermes: use the native qdrant-memory tools\n"
            "and the \"hermes qdrant-memory\" commands. The skill remains usable for other\n"
            "agents, for example Codex, Claude Code, OpenCode or Pi."
        )
    if state == "disabled":
        return (
            "Note: Hermes on this machine has the qdrant-memory plugin installed but\n"
            "disabled. Enable it for the native memory tools (\"hermes plugins enable\n"
            "qdrant-memory\"), or register this skill's MCP server for the profile\n"
            "instead. Other agents, for example Codex, Claude Code, OpenCode or Pi,\n"
            "can use the runtime either way."
        )
    return (
        "Note: Hermes is present on this machine, but its qdrant-memory plugin is not\n"
        "installed. For Hermes, prefer the plugin: install it from the Plugin Catalog\n"
        "with \"hermes plugins install qdrant-memory\". This runtime and skill remain\n"
        "usable for other agents, for example Codex, Claude Code, OpenCode or Pi."
    )


def main() -> int:
    """Install or verify the runtime selected by the required ``--venv`` CLI path.

    Expand ``~`` and resolve the absolute path. If absent, create a venv and
    install the pinned backend with MCP support; otherwise, only verify imports
    and CLI availability, without upgrading or checking the installed revision.
    On success, print JSON containing ``ok``, absolute ``python`` and ``command``
    paths, and ``requested_revision``, then return 0.

    Return 1 with a stderr diagnostic for OSError or CalledProcessError during
    creation, installation, or verification, retaining any partial installation.
    Argument parsing, Python 3.11+ and unsafe POSIX path checks raise SystemExit.
    Path expansion/resolution errors and ValueError from venv creation propagate.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", required=True, type=Path, help="new private environment, or an already working installation")
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error("Python 3.11+ is required")
    target = args.venv.expanduser().resolve()
    # pip can generate POSIX console scripts with a shell-wrapper shebang.
    # Keep the interpreter path safe even when subprocess itself uses argv.
    if os.name != "nt" and any(
        char in "\"'`$\\;&|<>(){}[]*?" or ord(char) < 32 or ord(char) == 127
        for char in str(target)
    ):
        parser.error("shell-sensitive characters in --venv path; choose a private path with ordinary names (spaces are supported)")
    try:
        advisory = hermes_advisory()
    except Exception:
        advisory = ""  # The advisory must never fail the install.
    if advisory:
        print(advisory, file=sys.stderr)
    scripts = target / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    console = scripts / ("qdrant-memory.exe" if os.name == "nt" else "qdrant-memory")
    # Public-source installation needs OS essentials, not agent credentials.
    allowed = ("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR",
               "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "TEMP",
               "TMP", "TMPDIR", "LANG", "TZ", "SSL_CERT_FILE", "SSL_CERT_DIR")
    env = {key: value for key in allowed if (value := os.getenv(key)) is not None}
    try:
        if not target.exists():
            venv.EnvBuilder(with_pip=True).create(target)
            subprocess.run([str(python), "-m", "pip", "install", REQUIREMENT], env=env, cwd=target, check=True, stdout=sys.stderr)
        # Existing environments are verified, never overwritten or upgraded.
        subprocess.run([str(python), "-I", "-c", "import qdrant_memory.standalone; import mcp.server.fastmcp"], env=env, cwd=target, check=True, stdout=sys.stderr)
        subprocess.run([str(console), "--help"], env=env, cwd=target, check=True, stdout=sys.stderr)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Runtime installation/verification failed: {exc}. Existing files were retained; choose a new --venv path to retry a partial installation.", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "python": str(python), "command": str(console), "requested_revision": REVISION}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
