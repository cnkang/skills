# Agent host acceptance

Two independent open-source hosts have mandatory acceptance jobs: Hermes and Pi.
The existing skills CLI distribution matrix separately checks nine installation
layouts. A layout check alone is not evidence that a host loads instructions.

## Pi baseline and scope

[Pi Coding Agent](https://github.com/earendil-works/pi) is MIT licensed and exposes
a Node.js SDK with native Agent Skills discovery and built-in read tools. Its
[skills documentation](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md)
and [SDK documentation](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/sdk.md)
describe the interfaces used by these tests. The published SDK is pinned to
`@earendil-works/pi-coding-agent@1.1.0`; the npm lockfile pins transitive versions
and integrity hashes. Node 24 runs the suite without a Python host environment,
model download, GPU, paid API, account or real credentials. Install scripts are
disabled with `npm ci --ignore-scripts`.

The real Pi SDK performs discovery, catalog prompt construction, `/skill:name`
expansion, agent iteration and its built-in `read` tool. Only the model server
is a scripted localhost OpenAI-compatible SSE fixture. It returns predetermined
read calls and a completion, allowing CI to verify the instructions and reference
contents actually enter the model requests without probabilistic judgments.
The suite removes inherited provider credentials and uses disposable profiles,
in-memory sessions/settings, disabled external model-catalog refresh and a read-only
tool allowlist. It never executes package scripts or memory operations.

| Acceptance | Assertions |
|---|---|
| Project `.pi/skills` and global `<agentDir>/skills` discovery | Exact five-package catalog, names/descriptions, expected paths and no diagnostics. |
| Independent Qdrant installation | Only Qdrant is present; no sibling dependencies. |
| Explicit invocation of all five skills | Actual `/skill:name` expansion sends the installed body to the fixture model, including CRLF normalization exercised on every OS. |
| Qdrant progressive disclosure | Initial prompt contains catalog metadata, not the full skill body. |
| Usage, maintenance and migration | Real read-tool loop reads the entrypoint and selected reference; full file content appears in subsequent model requests. |

These are 11 required tests. They establish host loading and deterministic tool
transport compatibility. They do not establish autonomous skill selection,
reasoning quality, execution of all workflows or support for every model/version.
Package loading on Pi supplies instructions. Qdrant operations still require the
configured standalone CLI/MCP or Hermes integration. The skill-loading suite
does not test Pi MCP transport; the separate official MCP acceptance verifies
the backend protocol.

## CI and local reproduction

`Pi skill host acceptance` runs on Ubuntu, macOS and Windows, alongside the pinned
Hermes Hub/disposable Qdrant runtime jobs. Both hosts feed `Required checks`.
Pi reports must contain at least 11 cases with zero skips, failures or errors;
JUnit artifacts are kept for 14 days, including failed runs. No account secrets
are required by this job.

```bash
npm ci --prefix tests/agent-hosts/pi --ignore-scripts --no-audit --no-fund
python3 -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True)"
npm test --prefix tests/agent-hosts/pi
python3 scripts/check_test_report.py reports/pi-host.xml --minimum-tests 11
```

When upgrading Pi, deliberately change the exact SDK version and regenerate its
lockfile, then rerun all three OS jobs. Retain the host test count and failure
gates. For real-model behavioral acceptance, use the separate scenarios in
`behavior-scenarios.md` and record host/model versions and results explicitly.

Local baseline on 2026-10-12: all 11 tests and the JUnit gate passed on macOS
with Node 24.18.0 in under one second of test runtime after dependency installation.
Local results do not establish remote three-platform success; inspect the CI
results for the exact pushed commit before merging.

## Standalone memory and installed local CLIs

The required three-platform standalone job installs the immutable additive
backend with its MCP extra and runs eight real CLI/official-client contracts
plus 19 public API/protocol boundary tests without Hermes source. It also runs
the locked Pi 1.1.0 CLI, requiring successful
stdio connection and discovery of four memory tools, and a cross-client test:
two different MCP client names share persisted records in the same fixed scope;
a separate agent scope cannot search/delete them. Every report rejects skips.
The cross-client names are protocol fixtures, not real-model executions.

Opt-in local acceptance uses installed CLIs with disposable homes/configuration,
the same backend's deterministic HTTP embedding fixture and embedded Qdrant:

```bash
QDRANT_LOCAL_AGENTS=1 QDRANT_STANDALONE_ROOT=/path/standalone-backend \
  python -m pytest -q tests/test_local_agent_mcp.py
QDRANT_STANDALONE_E2E=1 QDRANT_STANDALONE_ROOT=/path/standalone-backend \
  python -m pytest -q tests/test_shared_memory_mcp.py
```

Local 2026-10-12 results: Codex CLI 0.160.0, OpenCode 2.0.24 and Pi 1.1.0
passed three tests; shared-scope acceptance passed separately. Codex's actual
app-server discovers four tools and calls add/search. Pi's actual CLI connects
and inventories the tools. OpenCode registers in isolated global configuration
and verifies the saved executable, profile arguments and enabled local entry
before separately adding/connecting the runtime through its API and verifying connected
inventory. Its project CLI listing can reflect a different loaded location;
this test does not certify automatic project-config activation. No paid model,
account authentication, production profile or real embedding service is used.
