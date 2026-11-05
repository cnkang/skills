# CI security audit

Audit date: 2026-11-05. Scope: every workflow, the Dependabot configuration, the
`protect-main` ruleset, and the third-party scanners that see this repository.

## Method

- Read every file under `.github/` and the scripts that `validate.yml` calls.
- Queried the GitHub API for branch protection, rulesets, environments, Actions
  permissions, secret names (never values), fork approval policy, artifact
  retention and 30 days of workflow runs.
- Inspected the individual jobs of `actions/runs/41905293761` to classify the
  abandoned macOS job.
- Ran actionlint 1.7.12, zizmor 1.32.0 and gitleaks 8.30.1 against this tree.
- Replayed `scripts/check_required_checks.py` against simulated job results.
- Checked the published free-tier terms; citations are in
  [CI free-tier policy](ci-free-tier-policy.md).

## Workflow inventory

| Workflow | Trigger | Credential | Trust level |
| --- | --- | --- | --- |
| `validate.yml` | push `main`/`codex/**`, PR, dispatch | `SONAR_TOKEN` in one job only | Tier 1 plus Tier 2 |
| `workbuddy-preview.yml` | push, PR, dispatch | none | Tier 2 |
| `workbuddy-release.yml` | tag, dispatch | `contents: write` in the attach job | Tier 4 |
| `scorecard.yml` | push `main`, weekly, dispatch | OIDC, read-only token | Tier 3 |

CodeQL runs as a GitHub-managed CodeQL workflow (dynamic), not a repository file.

## Trust boundary analysis

**Fork pull requests.** No repository secret, a read-only `GITHUB_TOKEN`, no
OIDC identity. The SonarCloud job skips a pull request whose head repository
differs from this one. No workflow uses `pull_request_target` or `workflow_run`.

**Tag workflows.** `workbuddy-release.yml` runs on tags with `contents: write`
in the attach job. It is not reachable from a pull request.

**Artifacts.** Each acceptance job uploads its JUnit XML. No privileged job
consumes an artifact, and no `workflow_run` reads one.

**Caches.** `setup-node` caching is enabled only for the Pi test lockfile
(`cache-dependency-path: tests/agent-hosts/pi/package-lock.json`). No release
workflow reads a cache.

**OIDC.** Only `scorecard.yml` requests `id-token: write`, and it never gates a
merge.

## Findings

| ID | Severity | Finding | Status |
| --- | --- | --- | --- |
| F-01 | High | The `protect-main` ruleset existed but was **disabled**. `main` had no deletion protection, no force-push protection and no required status check; `GET branches/main/protection` returned 404. | Fixed. The ruleset is enabled with deletion, non-fast-forward, pull-request and required-status-check rules. |
| F-02 | High | No required check enforced the test matrix. `Required checks` was computed but nothing consumed it. | Fixed. `protect-main` requires the `Required checks` context. |
| F-03 | Medium | `actions/runs/41905293761` failed because `Hermes Hub and disposable Qdrant E2E (macos-latest)` was **cancelled before it started**: `runner_name` was empty, `steps` was empty, and it waited 28.5 minutes. The gate correctly failed closed. | Diagnosed. Not a test failure and not a timeout. The gate now records job conclusion, runner and executed-step count on failure, so this class is labelled on sight. |
| F-04 | Medium | The Dependabot path would fail: Dependabot pull requests never receive `SONAR_TOKEN`, and the SonarCloud job had no Dependabot exclusion. | Fixed. The job skips `dependabot[bot]` by immutable pull-request author. |
| F-05 | Medium | No workflow-level security lint, no secret scan, and Dependency Review only saw manifests that this repository does not have. The real dependency inputs are the hash locks under `.github/`. | Fixed. `workflow-security` runs actionlint and zizmor; `secret-scan` runs gitleaks on the event's commits; `dependency-review` additionally runs OSV-Scanner over every `.github/requirements-*.txt` lock. |
| F-06 | Low | No CODEOWNERS. | Fixed. Workflows, lock files, scripts and the Runtime installer request the maintainer. |
| F-07 | Low | Dependabot adopted new releases immediately. | Fixed. Seven-day cooldown. |
| F-08 | Accepted | `main` requires zero approving reviews. A solo maintainer cannot approve their own pull request. | Accepted. CODEOWNERS is the review prompt; revisit with a second maintainer. |
| F-09 | Accepted | `required-checks` runs `scripts/check_required_checks.py` from the pull request tree. | The job holds no secret and a read-only token, and a removed job is treated as `missing`, which fails. Workflow changes still need review. |
| F-10 | Open | 38% of `Validate skills` runs in 30 days ended `cancelled`. | Mostly superseded runs from `cancel-in-progress`. A cancelled run for the current head SHA blocks merge until it is rerun, which is the intended fail-closed behaviour. See the run baseline. |

## Repository settings

Verified through the API on 2026-11-05:

| Setting | Skills |
| --- | --- |
| Default workflow permissions | read |
| Workflow can approve pull requests | no |
| Secret scanning | enabled |
| Push protection | enabled |
| Dependabot security updates | enabled |
| Artifact and log retention | 90 days |
| Branch protection on `main` | none; the ruleset provides it |
| Ruleset `protect-main` | was disabled, now active |
| Required check | `Required checks` (after this change) |
| Force push / deletion | blocked by the ruleset |
| Fork workflow approval | `all_external_contributors` |

## Run baseline (30 days)

| Workflow | Runs | Success | Cancelled | Failure | Median | p95 |
| --- | --- | --- | --- | --- | --- | --- |
| Validate skills | 100+ | 44% | 38% | 18% | 12 min | 51 min |
| WorkBuddy preview | 100+ | 99% | 1% | 0% | 1 min | 8 min |
| CodeQL | 100+ | 99% | 1% | 0% | 2 min | 18 min |
| WorkBuddy draft release assets | 15 | 67% | 0% | 33% | 1 min | 5 min |
| Dependabot Updates | 6 | 83% | 0% | 17% | 1 min | 2 min |

The p95 for `Validate skills` is dominated by queue time on macOS runners, not
by test execution. Three jobs in that workflow run on `macos-latest`.

## The abandoned macOS job

`actions/runs/41905293761` (push to `main`, commit `cc592289`) failed at
2026-11-04 20:46 UTC. The job record shows:

- `started_at` 20:18:09, `completed_at` 20:46:48: 28 minutes 39 seconds.
- `runner_name` empty and `steps: []`: no runner ever picked it up.
- `timeout-minutes: 10` never applied, because the job never started.
- Every other job in the run succeeded, including `Required checks` prerequisites.

That signature is queue starvation on a hosted macOS runner. It is not a test
assertion failure, not a concurrency cancellation (the run was the newest attempt
for its SHA) and not a job timeout. The correct response is
`gh run rerun <run-id> -R cnkang/skills --failed`, which re-queues only the
cancelled job.

The gate keeps failing closed for this case: a cancelled required job is not a
pass. What changed is the diagnosis. The gate now appends a table of job name,
conclusion, runner name and executed-step count to the run summary whenever it
fails, so an empty runner with zero steps is visible without reading the API.

## Verification

- `pytest tests/test_ci_gate.py tests/test_ci_acceptance.py`: 73 passed. Covers
  every required job against failure, skipped, cancelled and `timed_out`, plus a
  missing job, fork and Dependabot pull requests, a main push, the gate script
  execution, the diagnostic step, the tool pins and CODEOWNERS coverage.
- actionlint 1.7.12: clean.
- zizmor 1.32.0 offline: no findings, no exceptions.
- gitleaks 8.30.1 full history: zero findings.

## Manual actions

1. Confirm the ruleset in the UI shows `Required checks` as required and that
   `main` cannot be deleted or force-pushed.
2. Optional: require a code-owner review once a second maintainer exists.
   Fork workflow approval is already `all_external_contributors`; rollback is
   `-f approval_policy=first_time_contributors`.

## Residual risks

- A hosted-runner queue stall can still delay a merge, because the required check
  stays red until the job is rerun. That is deliberate: a cancelled required job
  must never be read as success.
- The `workbuddy-release.yml` attach job holds `contents: write` behind a tag.
  It never runs for a pull request.
- OSV-Scanner and Dependency Review overlap on purpose only for the hash locks.
  Indexing those locks would not make Dependency Review check unchanged
  dependencies, so the OSV step stays.
