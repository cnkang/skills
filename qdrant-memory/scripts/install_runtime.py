#!/usr/bin/env python3
"""Install the reviewed standalone backend into an explicitly selected private venv.

Print a Hermes advisory and continue: recommend the native plugin when it is
missing, and state that the skill is not necessary for Hermes when the plugin
is installed. Other agents can still use the runtime.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import venv

REVISION = "1f0bfc0fbaf6f3b7ec2bc791728d89ceb31b0ad4"
REQUIREMENT = (
    "hermes-plugin-qdrant-memory[mcp] @ "
    "git+https://github.com/cnkang/hermes-plugin-qdrant-memory.git@" + REVISION
)


def _hermes_homes() -> list[Path]:
    """Return candidate Hermes profile homes without failing setup."""
    homes = []
    configured = os.environ.get("HERMES_HOME")
    if configured:
        homes.append(Path(configured).expanduser())
    homes.append(Path.home() / ".hermes")
    return homes


def hermes_detected() -> bool:
    """Report Hermes on this machine without failing setup."""
    if shutil.which("hermes"):
        return True
    for home in _hermes_homes():
        try:
            if home.is_dir():
                return True
        except OSError:
            continue
    return False


def hermes_plugin_installed() -> bool:
    """Report an installed Hermes qdrant-memory plugin without failing setup."""
    for home in _hermes_homes():
        try:
            if (home / "plugins" / "qdrant-memory").is_dir():
                return True
        except OSError:
            continue
    executable = shutil.which("hermes")
    if not executable:
        return False
    try:
        result = subprocess.run(
            [executable, "plugins", "list"], capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "qdrant-memory" in (result.stdout or "")


def hermes_advisory() -> str:
    """Return the Hermes install advisory, or an empty string when none applies."""
    if not hermes_detected():
        return ""
    if hermes_plugin_installed():
        return (
            "Note: Hermes on this machine already has the qdrant-memory plugin installed.\n"
            "This skill is not necessary for Hermes: use the native qdrant-memory tools\n"
            "and the \"hermes qdrant-memory\" commands. The skill remains usable for other\n"
            "agents, for example Codex, Claude Code, OpenCode or Pi."
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
    advisory = hermes_advisory()
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
