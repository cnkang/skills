# CI free-tier policy

Every service used by this repository must have a written free-use basis, a
known trigger, and a defined failure mode. A service without all three is not a
merge gate.

Policy checked on 2026-11-05. Re-check the linked pages before adding a service
or changing a trigger.

## Services and free-use basis

| Service | Free basis | Metered? | Can a fork PR trigger it? |
| --- | --- | --- | --- |
| GitHub Actions (standard runners) | Free for public repositories | No billing for standard runners | Yes, but only credential-free jobs |
| GitHub CodeQL | Code scanning is free for public repositories | No | Yes |
| GitHub Dependency Review | Free for public repositories; needs the dependency graph | No | Yes |
| GitHub secret scanning and push protection | Free for public repositories | No | Push protection applies to every push |
| zizmor | Open source, runs offline, no account | No | Yes |
| actionlint | Open source, no account | No | Yes |
| gitleaks (CLI) | Open source, MIT, no account | No | Yes |
| OSV-Scanner | Open source, queries the free OSV database, no account | No | Yes |
| OpenSSF Scorecard | Open source action; publishing uses the workflow's OIDC identity | No | No |
| SonarCloud | <https://www.sonarsource.com/plans-and-pricing/> lists SonarQube for OSS as free forever for public, OSI-licensed repositories with the paid Pro feature set | No | No (token held by the maintainer) |
| CodeRabbit | Open-source plan for public repositories | Partly: see below | It may comment, but it is not a gate |
| Sourcery | Free forever for public repositories | No for public repos | It may review, but it is not a gate |
| Socket | Free for open source | No for public repos | It may comment, but it is not a gate |

This repository does not use Snyk. It has no Snyk secret and no Snyk step.

## SonarCloud

Public OSI-licensed repositories get SonarQube for OSS at no cost with the paid
Pro feature set. This repository keeps one analysis per trusted event.

Trigger policy:

| Job | Trigger | Calls per trigger |
| --- | --- | --- |
| `SonarCloud quality gate` | push to `main`/`codex/**`, same-repository PR, dispatch | one analysis |

Fork and Dependabot pull requests skip the job, and `Required checks` accepts
that skip only for those two identities. A successful analysis in a fork or
Dependabot context would fail the gate, because it would mean the token reached
the pull request.

Failure handling: a scanner error, an expired token or a failed quality gate
fails the job. `sonar.qualitygate.wait=true` waits for the verdict. No path
reports a missing analysis as a pass.

## OSV-Scanner

Dependency Review reads GitHub's dependency graph. This repository keeps its real
Python dependency inputs as hash locks under `.github/requirements-*.txt`, which
that graph does not index. The pull-request job therefore runs OSV-Scanner 2.7.0
over those locks as a second, targeted check. It queries the free OSV database,
needs no account, and fails on every advisory the database reports.

Dependency Review reports only vulnerabilities that a pull request introduces.
Indexing those locks would not make it check unchanged dependencies, so the OSV
step stays.

## CodeRabbit

<https://docs.coderabbit.ai/management/plans> states that open-source projects
receive Team features with no paid subscription and that OSS review limits are
1–10 reviews per developer per hour, scoped per repository. Public repositories
with fewer than 10 stars require a manual trigger.

On-demand products are billed separately and require a payment method:
CodeRabbit Security Scan, CodeRabbit Agent, usage-based reviews and Deep Scan.
This repository enables none of them. Adding one would create an unmetered cost
path, so it is out of policy.

## Sourcery and Socket

<https://www.sourcery.ai/pricing> lists the Open Source plan as free forever for
public repositories, including security checks on every pull request.
<https://socket.dev/pricing> states that Socket is and will always be free for
open source. Neither is a required check; both are advisory reviewers.

## What only the maintainer can verify

1. SonarCloud: confirm the project is bound to
   `https://github.com/cnkang/skills`, that Automatic Analysis is off (it
   conflicts with CI analysis), and that the quality gate still requires new
   coverage.
2. CodeRabbit organisation: confirm usage-based reviews, Security Scan, Agent
   and Deep Scan are all disabled.
3. GitHub organisation billing: confirm no paid runner or metered product is
   attached to this repository.
4. Dependabot: confirm the seven-day cooldown appears in the dependency update
   configuration page.

## Review cadence

Re-check this document and the linked free-tier pages at each release and after
any change to a workflow trigger. A new trigger that adds a metered call needs a
row in the trigger table before it merges.
