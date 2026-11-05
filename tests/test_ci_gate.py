"""Execute the Required checks gate and assert the workflow trust policy."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_required_checks import ALWAYS_REQUIRED, evaluate  # noqa: E402

WORKFLOWS = ROOT / ".github/workflows"


def _workflow(name):
    """Load one workflow document with the trigger parsed as a string."""
    document = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    if "on" not in document and True in document:
        document["on"] = document.pop(True)
    return document


def _needs(**overrides):
    """Build a complete needs payload with the policy default for each job."""
    payload = {job: {"result": "success", "outputs": {}} for job in ALWAYS_REQUIRED}
    payload.update(
        {
            "sonarcloud": {"result": "success", "outputs": {}},
            "dependency-review": {"result": "success", "outputs": {}},
        }
    )
    payload.update(overrides)
    return payload


def _gate(needs, *, event="pull_request", fork=False, dependabot=False):
    """Evaluate one scenario."""
    return evaluate(needs, event_name=event, fork_pr=fork, dependabot=dependabot)


def test_fork_pull_request_passes_with_skipped_scanner():
    """A fork pull request passes while the credentialed scan stays skipped."""
    assert _gate(_needs(sonarcloud={"result": "skipped"}), fork=True) == []


def test_fork_pull_request_cannot_claim_the_scanner():
    """A successful credentialed scan on a fork means the token was exposed."""
    problems = _gate(_needs(), fork=True)
    assert any("sonarcloud=success" in problem for problem in problems)


def test_dependabot_pull_request_skips_the_scanner():
    """Dependabot pull requests never receive repository secrets."""
    assert _gate(_needs(sonarcloud={"result": "skipped"}), dependabot=True) == []


def test_internal_pull_request_requires_the_quality_gate():
    """An internal pull request must produce a real SonarCloud result."""
    problems = _gate(_needs(sonarcloud={"result": "skipped"}))
    assert any("sonarcloud=skipped" in problem for problem in problems)


def test_main_push_requires_the_quality_gate():
    """A main push must produce a real SonarCloud result."""
    needs = _needs(**{"dependency-review": {"result": "skipped"}})
    assert _gate(needs, event="push") == []


@pytest.mark.parametrize("job", ALWAYS_REQUIRED)
@pytest.mark.parametrize("result", ["failure", "skipped", "cancelled", "timed_out"])
def test_required_jobs_never_pass_without_success(job, result):
    """A cancelled, skipped or timed-out job is not a pass."""
    problems = _gate(_needs(**{job: {"result": result}}))
    assert any(problem.startswith(f"{job}={result}") for problem in problems)


def test_missing_job_is_a_failure():
    """A removed job must not shrink the required set."""
    needs = _needs()
    del needs["qdrant-e2e"]
    assert any("qdrant-e2e=missing" in problem for problem in _gate(needs))


def test_dependency_review_is_required_for_pull_requests_only():
    """Every pull request must evaluate dependency changes."""
    problems = _gate(_needs(**{"dependency-review": {"result": "skipped"}}))
    assert any("dependency-review=skipped" in problem for problem in problems)
    assert _gate(_needs(**{"dependency-review": {"result": "skipped"}}), event="push") == []


def test_gate_step_executes_the_committed_script():
    """The workflow must delegate to the reviewed script, not inline logic."""
    gate = _workflow("validate.yml")["jobs"]["required-checks"]
    assert gate["if"] == "always()"
    run = next(step for step in gate["steps"] if step.get("run") == "python3 scripts/check_required_checks.py")
    assert "NEEDS" in run["env"]

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_required_checks.py")],
        env={
            **os.environ,
            "NEEDS": json.dumps(_needs()),
            "EVENT_NAME": "pull_request",
            "FORK_PR": "false",
            "DEPENDABOT": "false",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_required_checks.py")],
        env={
            **os.environ,
            "NEEDS": json.dumps(_needs(sonarcloud={"result": "cancelled"})),
            "EVENT_NAME": "pull_request",
            "FORK_PR": "false",
            "DEPENDABOT": "false",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "::error::sonarcloud=cancelled" in result.stdout


def test_gate_needs_cover_every_reported_result():
    """Every job the gate evaluates must be declared in needs."""
    gate = _workflow("validate.yml")["jobs"]["required-checks"]
    assert set(gate["needs"]) == set(_needs())


def test_gate_can_read_job_metadata_for_diagnosis():
    """A cancelled job needs evidence that it never started."""
    gate = _workflow("validate.yml")["jobs"]["required-checks"]
    assert gate["permissions"]["actions"] == "read"
    diagnostic = next(
        step for step in gate["steps"] if step.get("name") == "Record why each job ended the way it did"
    )
    assert diagnostic["if"] == "failure()"
    assert "runner_name" in diagnostic["run"]


def test_sonarcloud_skips_forks_and_dependabot_only():
    """SonarCloud runs on trusted trees and skips fork and bot pull requests."""
    condition = _workflow("validate.yml")["jobs"]["sonarcloud"]["if"]
    assert "github.event.pull_request.head.repo.full_name == github.repository" in condition
    assert "github.event.pull_request.user.login == 'dependabot[bot]'" in condition
    assert "github.actor" not in condition


TIER_ONE = (
    "packages",
    "distribution",
    "qdrant-contract",
    "qdrant-e2e",
    "qdrant-current-runtime-e2e",
    "pi-host",
    "qdrant-standalone",
    "workflow-security",
    "secret-scan",
    "dependency-review",
)


@pytest.mark.parametrize("job", TIER_ONE)
def test_credential_free_jobs_hold_no_secret(job):
    """Checks that run on untrusted pull requests must not read secrets."""
    document = json.dumps(_workflow("validate.yml")["jobs"][job])
    assert "secrets." not in document
    assert "SONAR_TOKEN" not in document


@pytest.mark.parametrize("job", ["workflow-security", "secret-scan", "dependency-review"])
def test_new_jobs_bound_their_runtime(job):
    """Every new job needs an explicit timeout."""
    assert _workflow("validate.yml")["jobs"][job]["timeout-minutes"] <= 15


def test_security_tools_are_pinned():
    """Security tooling must never float."""
    jobs = _workflow("validate.yml")["jobs"]
    zizmor = next(
        step
        for step in jobs["workflow-security"]["steps"]
        if step.get("uses", "").startswith("zizmorcore/zizmor-action@")
    )
    assert len(zizmor["uses"].split("@")[1]) == 40
    assert zizmor["with"]["version"] == "1.32.0"
    assert zizmor["with"]["online-audits"] is False

    review = json.dumps(jobs["dependency-review"])
    assert "actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294" in review
    assert "160c6253e2922e9e0a6a9771c5c4c40a4b3c6090b34a3cdd5e80c96cc2e4218b" in review
    assert "osv-scanner_linux_amd64" in review
    assert ".github/requirements-*.txt" in review

    secret = json.dumps(jobs["secret-scan"])
    assert "gitleaks_8.30.1_linux_x64.tar.gz" in secret
    assert "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb" in secret
    assert "--redact" in secret


def test_scorecard_runs_only_on_trusted_events():
    """Scorecard publishes with OIDC and never gates a pull request."""
    workflow = _workflow("scorecard.yml")
    assert set(workflow["on"]) == {"push", "schedule", "workflow_dispatch"}
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert workflow["jobs"]["analysis"]["permissions"]["id-token"] == "write"


def test_codeowners_covers_the_privileged_paths():
    """Workflow, installer and lock changes must request the maintainer."""
    entries = (ROOT / ".github/CODEOWNERS").read_text(encoding="utf-8")
    for path in (".github/workflows/", "scripts/", "qdrant-memory/scripts/", ".github/requirements-"):
        assert path in entries, path
    assert "@cnkang" in entries


def test_dependabot_waits_before_adopting_releases():
    """A fresh release must not enter the build immediately."""
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text(encoding="utf-8"))
    for update in config["updates"]:
        assert update["cooldown"]["default-days"] == 7
