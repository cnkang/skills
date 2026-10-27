"""Make independently distributed skill helpers importable from repository tests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPT_DIRS = (
    "conventional-commit-batcher/scripts",
    "dev-jev/scripts",
    "repository-quality-gate-fixer/scripts",
    "sonarcloud-link-inspector/scripts",
)

for relative in SKILL_SCRIPT_DIRS:
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)
