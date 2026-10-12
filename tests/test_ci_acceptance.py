"""Acceptance gates must fail closed on missing/skipped runtime tests."""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_test_report import validate_report


@pytest.mark.parametrize("xml", [
    '<testsuites/>',
    '<testsuite><testcase name="fixture"><skipped/></testcase></testsuite>',
    '<testsuite><testcase name="fixture"><failure/></testcase></testsuite>',
    '<testsuite><testcase name="fixture"><error/></testcase></testsuite>',
])
def test_unverified_acceptance_is_rejected(tmp_path, xml):
    path = tmp_path / "results.xml"
    path.write_text(xml, encoding="utf-8")
    with pytest.raises(ValueError):
        validate_report(path, 1)


def test_successful_acceptance(tmp_path):
    path = tmp_path / "results.xml"
    path.write_text('<testsuites><testsuite><testcase name="fixture"/></testsuite></testsuites>', encoding="utf-8")
    validate_report(path, 1)
    with pytest.raises(ValueError):
        validate_report(path, 2)


def test_runtime_ci_is_required_pinned_and_opted_in():
    jobs = yaml.safe_load((ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8"))["jobs"]
    runtime = jobs["qdrant-e2e"]
    assert set(runtime["strategy"]["matrix"]["os"]) == {"ubuntu-latest", "macos-latest", "windows-latest"}
    refs = {step["with"]["repository"]: step["with"]["ref"] for step in runtime["steps"]
            if "repository" in step.get("with", {})}
    assert refs == {"cnkang/hermes-agent": "4787e4d56fc8d9265d4c7d3c0fe5accee86b4078",
                    "cnkang/hermes-plugin-qdrant-memory": "5babd3e4b4c022aad38a2b6db82cbd5b601f1ef8"}
    execution = next(step for step in runtime["steps"] if "--junitxml" in step.get("run", ""))
    assert execution["env"]["QDRANT_RUNTIME_E2E"] == "1"
    assert execution["env"]["HERMES_SKILL_HOST_ROOT"] and execution["env"]["QDRANT_MEMORY_PLUGIN_ROOT"]
    assert any("check_test_report.py" in step.get("run", "") and "--minimum-tests 5" in step["run"]
               for step in runtime["steps"])
    assert any("check_test_report.py" in step.get("run", "") and "--minimum-tests 25" in step["run"]
               for step in jobs["qdrant-contract"]["steps"])
    assert set(jobs["required-checks"]["needs"]) == {"packages", "distribution", "qdrant-contract", "qdrant-e2e", "pi-host", "qdrant-standalone"}
    assert jobs["required-checks"]["if"] == "always()"


def test_pi_host_is_locked_required_and_rejects_skips():
    import json
    jobs = yaml.safe_load((ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8"))["jobs"]
    pi = jobs["pi-host"]
    assert set(pi["strategy"]["matrix"]["os"]) == {"ubuntu-latest", "macos-latest", "windows-latest"}
    assert any("npm ci" in step.get("run", "") and "--ignore-scripts" in step["run"] for step in pi["steps"])
    assert any("check_test_report.py" in step.get("run", "") and "--minimum-tests 11" in step["run"]
               for step in pi["steps"])
    directory = ROOT / "tests/agent-hosts/pi"
    package = json.loads((directory / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((directory / "package-lock.json").read_text(encoding="utf-8"))
    name = "@earendil-works/pi-coding-agent"
    assert package["devDependencies"][name] == "1.1.0"
    assert lock["packages"][f"node_modules/{name}"]["version"] == "1.1.0"
    assert lock["packages"][f"node_modules/{name}"]["integrity"].startswith("sha512-")


def test_standalone_acceptance_has_no_hermes_checkout_and_rejects_skips():
    jobs = yaml.safe_load((ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8"))["jobs"]
    job = jobs["qdrant-standalone"]
    assert set(job["strategy"]["matrix"]["os"]) == {"ubuntu-latest", "macos-latest", "windows-latest"}
    checkouts = [step["with"] for step in job["steps"] if "repository" in step.get("with", {})]
    assert len(checkouts) == 1
    assert checkouts[0]["repository"] == "cnkang/hermes-plugin-qdrant-memory"
    import re
    assert re.fullmatch(r"[0-9a-f]{40}", checkouts[0]["ref"])
    for document in ("README.md", "README_zh-CN.md", "qdrant-memory/references/runtime.md"):
        assert "git@" + checkouts[0]["ref"] in (ROOT / document).read_text(encoding="utf-8")
    assert any('[mcp]' in step.get("run", "") for step in job["steps"])
    assert any("tests/standalone" in step.get("run", "") for step in job["steps"])
    assert any("check_test_report.py" in step.get("run", "") and "--minimum-tests 27" in step["run"] for step in job["steps"])
    assert any("test_installed_pi_discovers_scoped_mcp" in step.get("run", "") for step in job["steps"])
    assert any("pi-mcp.xml --minimum-tests 1" in step.get("run", "") for step in job["steps"])
    assert any("test_shared_memory_mcp.py" in step.get("run", "") for step in job["steps"])
    assert any("shared-memory.xml --minimum-tests 1" in step.get("run", "") for step in job["steps"])
