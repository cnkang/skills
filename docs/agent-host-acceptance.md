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
Hermes MemoryProvider/native tools or `hermes qdrant-memory`; no Pi bridge is added.

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
