# Qdrant memory compatibility

The independent Qdrant package routes to three documentation workflows using
scoped MCP/Hermes tools, a standalone JSON CLI and the compatible Hermes CLI.
The shared backend is the sole core code source. It owns scope, schema,
embedding, ledger, WriterLease and recovery. Standalone interfaces require no
Hermes and use operator-configured profile identities.
No dependency is installed or configuration changed by loading a skill.

The additive standalone acceptance includes eight installed CLI/official MCP
contracts. It also covers public API/protocol tests for file boundaries and
startup cleanup, real Pi CLI tool discovery and cross-client
shared-scope/private-agent isolation. Installed local Codex/OpenCode/Pi acceptance is opt-in. See
`agent-host-acceptance.md` for exact versions, interface coverage and limits.

## Validation layers

| Layer | Command / coverage | Boundary |
|---|---|---|
| Static/package | `python3 scripts/validate_skills.py`, repository pytest | YAML, controlled catalog, independent resources/license, reference and syntax integrity. No runtime claim. |
| Real skills CLI | `python3 scripts/test_distribution.py --cli-version 1.7.0` and `latest` | Disposable homes/projects, 21 selections, nine host paths, copy/link, selective/ref/source updates and documented GitHub identifier syntax via local Git transport. No agent runtime. |
| Offline plugin contract | `QDRANT_MEMORY_PLUGIN_ROOT=/path/plugin python3 -m pytest -q tests/test_qdrant_plugin_contract.py` | Actual schemas/parser/dispatcher, fixture profile/config, blocked service constructors. No Hermes lifecycle or live embedding. Requires plugin dependencies, Python 3.11+. |
| Hermes Hub fixture | `HERMES_SKILL_HOST_ROOT=/path/hermes-agent python3 -m pytest -q tests/test_hermes_skill_paths.py` in the host environment | Real Hub fetch/quarantine/local scan/install and root Tap parsing with local transport. The optional remote advisory is omitted. No live GitHub publication. |
| Pi skill host | `npm test --prefix tests/agent-hosts/pi` after `npm ci` | Actual discovery/explicit prompt expansion and read-tool loop. The model SSE is scripted localhost. Instructions load on Pi. A separately configured backend supplies memory operations. See `agent-host-acceptance.md`. |
| Disposable runtime E2E | `QDRANT_RUNTIME_E2E=1` with both source roots and `tests/test_qdrant_runtime_e2e.py` | Real Hermes discovery/provider and discovered CLI handler, actual embedded Qdrant/ledger, HTTP embedding transport and subprocess restarts. Deterministic localhost vectors. No semantic model judgment. |
| Real host/model | Scenarios in `behavior-scenarios.md` | Explicit operator acceptance is needed. Static or install tests do not establish it. |

CI retains Ubuntu/macOS/Windows and Python 3.10/3.14 package jobs and pinned/latest
skills CLI jobs. A separate Ubuntu job checks plugin release commit
`c85d2bce788b117dddd854bb124971f7de8e564c` (Runtime 0.2.2). Offline contracts skip
explicitly when no plugin checkout is supplied. A supplied but invalid checkout
fails. A mandatory Ubuntu/macOS/Windows job runs Hub fixtures and disposable
runtime E2E with Hermes pinned to `4787e4d56fc8d9265d4c7d3c0fe5accee86b4078`
and the same plugin release. Ordinary package jobs leave these environment-driven
tests disabled. Dedicated acceptance jobs reject any skip, failure, error or
insufficient test count and retain JUnit reports for 14 days. `Required checks`
fails if any package, distribution, contract, Hermes E2E or Pi host job fails or is skipped.
A separate required three-platform standalone matrix installs the pinned
backend independently with MCP SDK 1.x and 2.x and exercises real JSON CLI
subprocesses and an official MCP client without Hermes source or fake host modules. It retains
zero-skip JUnit reports. No test contacts personal Qdrant or embeddings.

The Ubuntu standalone job additionally uses real `npx skills@1.7.0`. It installs
the candidate package from GitHub at the exact branch/PR head commit into an
isolated global Codex directory. It executes that
installed package's backend installer in a fresh venv. The installer fetches
an exact PyPI release by default, or the explicitly configured immutable Runtime
candidate while that release is unpublished. It verifies version and source provenance,
CLI init/doctor/add, official stdio MCP discovery/search/delete and safe reuse.
The installation report has a required zero-skip gate. Embeddings use localhost
fixtures, with no Hermes installation or paid model calls.

For local acceptance, install `requirements-runtime-tests.txt` and the pinned
plugin into an isolated environment, then run:

```bash
HERMES_SKILL_HOST_ROOT=/path/hermes-agent \
QDRANT_MEMORY_PLUGIN_ROOT=/path/runtime-at-0.2.2 \
QDRANT_RUNTIME_E2E=1 python -m pytest -q \
  tests/test_hermes_skill_paths.py tests/test_qdrant_runtime_e2e.py \
  --junitxml=reports/runtime-e2e.xml
python scripts/check_test_report.py reports/runtime-e2e.xml --minimum-tests 5
```

Runtime coverage includes scoped explicit CRUD, duplicate reconciliation,
foreign-ID denial, competing writer refusal and persistence after process
restart. It also covers dry-run isolation, migration/resume/verification,
failed embedding and recovery, scoped export and overwrite refusal, and
confirmed scoped deletion. It does not
exercise an LLM, automatic extraction, remote Qdrant or abrupt process termination.

## Installation and runtime limits

Install the skill independently, then install/configure the shared backend using
[runtime setup](../qdrant-memory/references/runtime.md). The additive standalone
installation defaults to exact PyPI Runtime 0.2.2; MCP-focused
agents may use metadata-only distribution 0.1.2 instead. Both support MCP Python
SDK 1.x and 2.x. Development/candidate
installs require an explicitly chosen full SHA and expected version. Both retain
the durable transcript-author isolation fix. Original release v0.1.0 remains
the Hermes compatibility baseline. Skill installation alone does not create memory tools.
Connect an authorized MCP process or use the standalone JSON CRUD CLI. Hermes
native tools remain supported. Do not use private APIs. MCP client names and
model arguments do not choose scope. Automatic extraction/prefetch remain Hermes
lifecycle features. Common agent connection examples describe supported
interfaces, not evidence that every model or host has been exercised.

Hermes GitHub direct identifiers preserve root paths:
`hermes skills install cnkang/skills/qdrant-memory`. The local Hub fixture
validates this package path using local transport. Remote fetching is a separate
installation step. Security scanning/confirmation remains part of the
real host installation workflow.

Default Tap `path: "skills/"` misses this root layout. Hermes supports a stored
Tap `path: ""` for repository-root discovery. The CI fixture verifies the
manager and discovery behavior. Prefer direct install. If the user chooses a
Tap, deliberately set that entry in the active profile's `skills/.hub/taps.json`:

```json
{"taps": [{"repo": "cnkang/skills", "path": ""}]}
```

This shows the entry format, not permission to overwrite other Tap entries.
Never copy packages into a second `skills/` publishing tree. Older Hermes
versions may differ. Check their actual Hub support.

Known plugin limits: vector reuse is refused. Migration has no scope remapping.
List/export without scope may disclose all collection users. CLI selections are
operator-authorized, unlike trusted native-tool scope. Embedded readers need
exclusive storage access. Diagnostics open Ledger and may create/migrate local
state. Retry and deletion modify durable state. Interrupted deletion/reset must
finish through recorded plugin recovery. No direct state-file repair.

## Sources checked

- [Agent Skills specification](https://agentskills.io/specification): standard
  frontmatter and optional scripts/references. Retain repository string metadata.
- [Hermes authoring](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills):
  progressive disclosure and native skill resources.
- [Hermes Skills/Hub](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills):
  direct GitHub identifiers and non-default Tap paths.
- [skills CLI](https://github.com/vercel-labs/skills): selection and host paths.
  Local tests verify actual released CLI behavior.
- [Runtime source](https://github.com/cnkang/hermes-plugin-qdrant-memory/tree/c85d2bce788b117dddd854bb124971f7de8e564c):
  tools, CLI parser/dispatch and ownership contract, not planned README features.
