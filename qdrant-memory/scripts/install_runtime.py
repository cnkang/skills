#!/usr/bin/env python3
"""Install the reviewed standalone backend into an explicitly selected private venv."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

REVISION = "8fd42572738b15a1abcad62aeecd0de9b1877e3a"
REQUIREMENT = (
    "hermes-plugin-qdrant-memory[mcp] @ "
    "git+https://github.com/cnkang/hermes-plugin-qdrant-memory.git@" + REVISION
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", required=True, type=Path, help="new private environment, or an already working installation")
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error("Python 3.11+ is required")
    target = args.venv.expanduser().absolute()
    scripts = target / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    console = scripts / ("qdrant-memory.exe" if os.name == "nt" else "qdrant-memory")
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
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
