"""Fail-closed evaluation of the Required checks aggregate.

The gate reads the job results that GitHub reports and the identity of the
triggering event. The `required-checks` job runs this file from the checkout of
the event under evaluation, so a pull request that edits this file or that job
can change the verdict. Review changes to both; the accepted risk is recorded in
docs/ci-security-audit.md (F-09).
"""

from __future__ import annotations

import json
import os

# Jobs that must run and succeed for every event.
ALWAYS_REQUIRED = (
    "packages",
    "distribution",
    "qdrant-contract",
    "qdrant-e2e",
    "qdrant-current-runtime-e2e",
    "pi-host",
    "qdrant-standalone",
    "workflow-security",
    "secret-scan",
)


def _result(needs: dict, job: str) -> str:
    """Return the reported result for one job, or ``missing``."""
    entry = needs.get(job)
    if not isinstance(entry, dict):
        return "missing"
    result = entry.get("result")
    return result if isinstance(result, str) and result else "missing"


def evaluate(needs: dict, *, event_name: str, fork_pr: bool, dependabot: bool) -> list[str]:
    """Return every policy violation for one completed workflow run."""
    problems: list[str] = []

    for job in ALWAYS_REQUIRED:
        result = _result(needs, job)
        if result != "success":
            problems.append(f"{job}={result} must succeed")

    # SonarCloud needs a maintainer token. Fork and Dependabot pull requests
    # never receive repository secrets, so the job must be skipped there and a
    # successful analysis in those contexts would mean the token was exposed.
    sonar = _result(needs, "sonarcloud")
    if fork_pr or dependabot:
        if sonar != "skipped":
            problems.append(f"sonarcloud={sonar} must be skipped for untrusted pull requests")
    elif sonar != "success":
        problems.append(f"sonarcloud={sonar} must succeed on trusted trees")

    # Dependency review is credential-free but only a pull request has a base
    # commit to compare against.
    review = _result(needs, "dependency-review")
    expected_review = "success" if event_name == "pull_request" else "skipped"
    if review != expected_review:
        problems.append(f"dependency-review={review} must be {expected_review}")

    return problems


def main() -> int:
    """Evaluate the environment that the workflow exports and exit."""
    needs = json.loads(os.environ["NEEDS"])
    problems = evaluate(
        needs,
        event_name=os.environ.get("EVENT_NAME", ""),
        fork_pr=os.environ.get("FORK_PR") == "true",
        dependabot=os.environ.get("DEPENDABOT") == "true",
    )
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        print(
            "Required checks failed. A cancelled, skipped or timed-out required job "
            "cannot be treated as success."
        )
        return 1
    print("All required jobs succeeded under the configured trust policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
