#!/usr/bin/env python3
"""Install the reviewed standalone backend into an explicitly selected private venv.

Print a Hermes advisory and continue. The advisory recommends the native
plugin when it is missing. It notes an installed plugin that is disabled or
not selected as the memory provider, and states that the skill is not
necessary for Hermes when the plugin is enabled and selected. Detection reads
the active Hermes profile (HERMES_HOME, or ~/.hermes) and its config.yaml.
The installer does not run a Hermes command. Other agents can still use the
runtime.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
from pathlib import Path
import subprocess
import sys
import venv

VERSION = "0.2.2"
PLUGIN_ID = "qdrant-memory"


def _require_private_mkdir() -> None:
    """Reject Windows builds that ignore mkdir's private-directory mode."""
    version = sys.version_info[:3]
    # CPython backported Windows mkdir(0o700) ACL handling to these releases.
    # Older builds must not create an inherited, potentially shared venv first.
    if sys.platform == "win32" and (
        version < (3, 11, 10) or (3, 12) <= version < (3, 12, 4)
    ):
        raise ValueError("Windows setup requires Python 3.11.10+, 3.12.4+, or 3.13+")


def _release_key(version: str) -> tuple[int, int, int]:
    """Order exact three-part release versions for the compatibility check."""
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def _hermes_home() -> Path | None:
    """Return the active Hermes home: HERMES_HOME when set, else ~/.hermes.

    A relative or unresolvable value returns None. In this case, the default
    home is not used.
    """
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
    """Best-effort scan for a top-level ``plugins:`` -> ``disabled:`` items.

    Handles the block layout plus single-line flow mappings such as
    ``plugins: {disabled: [qdrant-memory]}``, tolerating trailing comments,
    blank lines, CRLF endings and indentation variations (sequence items may
    sit at or below the key's indentation). PyYAML stays preferred when
    importable. Only list values are recognized, matching Hermes' own
    parsing. Unparsed shapes (for example flow mappings split across lines)
    yield an empty set. In this case, the plugin keeps its default state:
    enabled.
    """
    found: set[str] = set()
    sub_indent = None  # indentation of the plugins sub-keys once seen
    in_disabled = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if sub_indent is None:
            if re.fullmatch(r"plugins:[ \t]*(?:#.*)?", line):
                sub_indent = -1  # marker: awaiting the first indented line
            else:
                flow = re.fullmatch(r"plugins:[ \t]*\{(.*)\}[ \t]*(?:#.*)?", line)
                inner = (
                    re.search(r"""(?:^|[,\s])['"]?disabled['"]?[ \t]*:[ \t]*\[(.*?)\]""", flow.group(1))
                    if flow else None
                )
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
        if stripped.startswith("-"):
            if in_disabled:
                item = stripped[1:].split("#", 1)[0].strip().strip("'\"")
                if item:
                    found.add(item)
            continue
        if indent > sub_indent:
            continue
        key, _, value = stripped.partition(":")
        value = value.split("#", 1)[0].strip()
        in_disabled = key.strip().strip("'\"") == "disabled"
        if in_disabled and value.startswith("["):
            found.update(_inline_ids(value))
    return found


def _plugin_disabled_in_config(home: Path) -> bool:
    """True when the profile config explicitly disables the plugin.

    A memory backend is active without a ``plugins.enabled`` entry, so only a
    ``plugins.disabled`` entry turns it off. Detection is best effort: prefer
    YAML when available, and scan the block layout otherwise with tolerance
    for comments, blank lines and indentation variations. Unreadable or
    undecodable configs report False (installed and active).
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


def _scan_memory_provider(text: str) -> str | None:
    """Best-effort scan for a top-level ``memory:`` -> ``provider:`` value.

    Handles the block layout plus single-line flow mappings such as
    ``memory: {provider: qdrant-memory}``, with the same tolerance as
    ``_scan_disabled_ids``.
    """
    sub_indent = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if sub_indent is None:
            if re.fullmatch(r"memory:[ \t]*(?:#.*)?", line):
                sub_indent = -1
            else:
                flow = re.fullmatch(r"memory:[ \t]*\{(.*)\}[ \t]*(?:#.*)?", line)
                inner = (
                    re.search(r"""(?:^|[,\s])['"]?provider['"]?[ \t]*:[ \t]*([^,}\s]+)""", flow.group(1))
                    if flow else None
                )
                if inner:
                    return inner.group(1).strip("'\"") or None
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            break
        indent = len(line) - len(line.lstrip())
        if sub_indent == -1:
            sub_indent = indent
        if indent < sub_indent:
            break
        if indent > sub_indent:
            continue
        key, _, value = stripped.partition(":")
        if key.strip().strip("'\"") == "provider":
            value = value.split("#", 1)[0].strip().strip("'\"")
            return value or None
    return None


def _plugin_provider_selected(home: Path) -> bool:
    """True when the profile selects the plugin as its memory provider.

    Detection is best effort and mirrors ``_plugin_disabled_in_config``. An
    unreadable config or a missing ``memory.provider`` value reports False:
    the plugin is then installed but not active.
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
            memory = (yaml.safe_load(text) or {}).get("memory")
            if isinstance(memory, dict):
                return str(memory.get("provider") or "") == PLUGIN_ID
        except Exception:
            pass
    return _scan_memory_provider(text) == PLUGIN_ID


def hermes_plugin_state() -> str:
    """Return 'absent', 'disabled', 'inactive' or 'enabled' for the active profile."""
    home = _hermes_home()
    if home is None:
        return "absent"
    try:
        if not (home / "plugins" / PLUGIN_ID).is_dir():
            return "absent"
    except OSError:
        return "absent"
    if _plugin_disabled_in_config(home):
        return "disabled"
    if not _plugin_provider_selected(home):
        return "inactive"
    return "enabled"


def hermes_advisory() -> str:
    """Return the Hermes install advisory, or an empty string when none applies."""
    if not hermes_detected():
        return ""
    state = hermes_plugin_state()
    if state == "enabled":
        return (
            "Note: Hermes on this machine already has the qdrant-memory plugin enabled\n"
            "and selected as its memory provider. This skill is not necessary for Hermes:\n"
            "use the native qdrant-memory tools and the \"hermes qdrant-memory\" commands.\n"
            "Other agents can still use the skill, for example Codex, Claude Code,\n"
            "OpenCode or Pi."
        )
    if state == "inactive":
        return (
            "Note: Hermes on this machine has the qdrant-memory plugin installed but\n"
            "not selected as its memory provider. Run \"hermes memory setup\" and\n"
            "select qdrant-memory, or register this skill's MCP server for the profile\n"
            "instead. Other agents can still use the runtime."
        )
    if state == "disabled":
        return (
            "Note: Hermes on this machine has the qdrant-memory plugin installed but\n"
            "disabled. Enable it for the native memory tools (\"hermes plugins enable\n"
            "qdrant-memory\"). Then run \"hermes memory setup\" and select\n"
            "qdrant-memory, or register this skill's MCP server for the profile\n"
            "instead. Other agents can use the runtime either way."
        )
    return (
        "Note: Hermes is present on this machine, but its qdrant-memory plugin is not\n"
        "installed. For Hermes, prefer the plugin: install it from the Plugin Catalog\n"
        "with \"hermes plugins install qdrant-memory\". Other agents can still use this\n"
        "runtime and skill, for example Codex, Claude Code, OpenCode or Pi."
    )


def main() -> int:
    """Install or verify the runtime selected by the required ``--venv`` CLI path.

    Expand ``~`` and resolve the absolute path. If absent, create a venv and
    install a pinned PyPI release with MCP support, or an explicitly selected
    full Git SHA. Existing environments are verified without upgrading; a
    newer compatible release is accepted.
    On success, print JSON containing ``ok``, absolute ``python`` and ``command``
    paths, requested and installed versions and the optional revision, then return 0.

    Return 1 with a stderr diagnostic for OSError or CalledProcessError during
    creation, installation, or verification, retaining any partial installation.
    Argument parsing, Python 3.11+ and unsafe POSIX path checks raise SystemExit.
    Path expansion/resolution errors and ValueError from venv creation propagate.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", required=True, type=Path, help="new private environment, or an already working installation")
    parser.add_argument("--version", default=VERSION, help="exact Runtime release version (default: %(default)s)")
    parser.add_argument("--requirements-lock", type=Path, help="optional trusted hash-locked requirements for binary-only release installation")
    parser.add_argument("--revision", help="optional full immutable Git SHA for candidate/development installation")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version):
        parser.error("--version must be an exact three-part release version")
    if args.revision and not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("--revision must be a full lowercase 40-character Git SHA")
    requirement = f"hermes-plugin-qdrant-memory[mcp]=={args.version}"
    if args.revision:
        requirement = "hermes-plugin-qdrant-memory[mcp] @ git+https://github.com/cnkang/hermes-plugin-qdrant-memory.git@" + args.revision
    if sys.version_info < (3, 11):
        parser.error("Python 3.11+ is required")
    selected = args.venv.expanduser()
    if selected.is_symlink():
        parser.error("--venv must not be a symlink")
    target = selected.resolve()
    existing = target
    while not existing.exists():
        existing = existing.parent
    info = existing.stat()
    if os.name != "nt" and (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022):
        parser.error("Choose a venv in a private, user-owned directory")
    if args.requirements_lock and args.revision:
        parser.error("--requirements-lock is for release installations, not source revisions")
    lock = args.requirements_lock.expanduser().resolve() if args.requirements_lock else None
    if lock and not lock.is_file():
        parser.error("--requirements-lock must name a trusted requirements file")
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
    env["PIP_CONFIG_FILE"] = os.devnull
    try:
        if not target.exists():
            _require_private_mkdir()
            # Managed POSIX Python builds can resolve libpython relative to the
            # original executable. Match `python -m venv` rather than copying it.
            # Create the root private: a later chmod would leave a window in which
            # another account could write into the directory pip later imports from.
            previous_umask = os.umask(0o077) if os.name != "nt" else None
            try:
                # Pre-create the root with an explicit private mode so inherited
                # entries are masked before anything runs inside it.
                target.mkdir(mode=0o700, parents=True, exist_ok=False)
                venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(target)
            finally:
                if previous_umask is not None:
                    os.umask(previous_umask)
            if os.name != "nt":
                target.chmod(0o700)
            if lock:
                # Read the operator's lock in place: relative includes and local
                # artifact paths must resolve against its own directory.
                lock_path = Path(lock).resolve()
                selection = ["--require-hashes", "--only-binary=:all:", "-r", str(lock_path)]
                pip_cwd = lock_path.parent
            else:
                # Keep the requested version out of the argv; pip reads it from a
                # file this installer writes inside the private venv root.
                requirement_file = target / "runtime-requirements.txt"
                requirement_file.write_text(f"{requirement}\n", encoding="utf-8")
                selection = ["-r", str(requirement_file)]
                pip_cwd = target.parent
            subprocess.run(
                [str(python), "-I", "-m", "pip", "install", *selection],
                env=env,
                cwd=pip_cwd,
                check=True,
                stdout=sys.stderr,
            )
        # Existing environments are verified, never overwritten or upgraded.
        # A newer compatible release satisfies the check; an older one does not.
        probe = subprocess.run([str(python), "-I", "-c", "import importlib.metadata as m, json; import qdrant_memory.standalone; from qdrant_memory.mcp_server import create_server; create_server(None); d=m.distribution('hermes-plugin-qdrant-memory'); print(json.dumps({'version': d.version, 'source': json.loads(d.read_text('direct_url.json') or 'null')}))"], env=env, cwd=target, check=True, stdout=subprocess.PIPE, stderr=sys.stderr, text=True)
        installed = json.loads(probe.stdout)
        if lock and installed["version"] != args.version:
            raise ValueError(f"Installed Runtime {installed['version']} does not match requested {args.version}")
        if _release_key(installed["version"]) < _release_key(args.version):
            raise ValueError(f"Installed Runtime {installed['version']} is older than requested {args.version}")
        if args.revision and (installed.get("source") or {}).get("vcs_info", {}).get("commit_id") != args.revision:
            raise ValueError("Installed Runtime source does not match the requested immutable revision")
        subprocess.run([str(console), "--help"], env=env, cwd=target, check=True, stdout=sys.stderr)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as exc:
        print(f"Runtime installation/verification failed: {exc}. Existing files were retained; choose a new --venv path to retry a partial installation.", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "python": str(python), "command": str(console), "requested_version": args.version, "installed_version": installed["version"], "requested_revision": args.revision}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
