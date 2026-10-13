# Changelog

## Unreleased

- **qdrant-memory 0.2.3:** recommend one memory interface for each Hermes
  profile in the skill guidance and MCP/Hermes setup notes. The bundled
  installer detects Hermes and prints an advisory. The advisory recommends the
  native plugin when it is missing. It reports an installed plugin that is
  disabled, and states that the skill is not necessary for Hermes when the
  plugin is enabled. It infers the plugin state from the active profile's config.yaml
  and never runs a Hermes command. Other agents can still use the runtime.
  No interface changes.

- Clarify public Qdrant compatibility and authorized runtime setup guidance.
  Exclude local environment secrets while retaining publishable example files.

- **qdrant-memory 0.2.2:** pin new backend installation and required runtime CI
  to the merged backend PR #35 with the transcript-author isolation fix. Preserve CLI/MCP interfaces;
  document that receiving the security update requires a fresh private environment
  because the installer never upgrades an existing runtime.

- **qdrant-memory 0.2.1:** make the four MCP tools, skill/runtime separation,
  local stdio setup and verified host boundaries explicit. Keep Hermes lifecycle
  compatibility and sequential shared scopes. Pin installation and CI to the
  tested merged backend snapshot, refreshed after backend PR #34. Bundle an
  authorized missing-backend installer;
  reject shell-sensitive POSIX environment paths before pip creates CLI wrappers,
  with literal-path and space-path regression checks in installation acceptance;
  require real npx distribution, fresh VCS installation and CLI/MCP acceptance
  in CI. No backend runtime interface changes.

- **qdrant-memory 0.2.0:** agent-neutral standalone JSON CLI and stdio MCP
  instructions, fixed-profile scope, Codex/Claude Code/OpenCode/Pi setup, and
  no-Hermes runtime acceptance. Preserve the original Hermes tools and CLI;
  automatic extraction remains its lifecycle feature. Pin the additive backend
  source until a release includes standalone support.

- **Second agent host:** add MIT Pi Coding Agent 1.1.0 SDK acceptance with a
  pinned integrity-checked npm lockfile. Eleven tests exercise all five packages'
  discovery and explicit expansion plus real Qdrant reference reads. Three OS
  jobs, zero-skip JUnit gates and required-check aggregation need no paid API,
  account, model download or GPU; model responses are deterministic fixtures.

- **qdrant-memory 0.1.0:** one independent document-only package with
  usage, maintenance and migration workflows loaded on demand, using the Hermes
  Qdrant plugin v0.1.0 public tools/CLI.
  Scope, exact-ID checks, writer ownership, destructive recovery and unsupported
  vector reuse are explicit. No plugin core, direct write path or auto-setup.
- **Validation/distribution:** controlled five-skill catalog, document-only
  package support, 21 bounded selections retaining all 15 legacy subsets,
  Qdrant Codex/Hermes paths and document-only selective/pinned/source updates.
  A separate offline CI job checks the immutable plugin release parser/tool
  contract. Three-platform Hermes Hub and disposable runtime E2E use pinned host
  and plugin sources, real embedded storage and local HTTP embedding fixtures.
  JUnit artifacts, rejection of skipped/empty acceptance and a required-checks
  aggregate complete the CI gates; no production services. Existing skill
  versions and paths remain.

- **conventional-commit-batcher 4.0.0 (breaking):** one native skill entrypoint;
  legacy hidden adapters and AGENTS/CLAUDE files move to opt-in templates. Existing
  external adapters require deliberate migration. Safety checks read index blob
  sizes, handle special paths and unresolved index entries, and withhold secret
  snippets from reports.
- **repository-quality-gate-fixer 0.8.0:** local installed-skill scanning is off by
  default. Opt in with `--skill-scan`; `--no-skill-scan` remains supported.
  Home-path display handles Windows separators, case and UNC paths; Git fixtures
  use an explicit identity so tests do not depend on user configuration.
- **sonarcloud-link-inspector 1.1.0:** EU/US routing, precise URL/endpoint validation,
  bounded transient-only retries, retained batch failures, fetch statuses and
  process exit codes. Existing data fields remain; callers should now handle
  nonzero exits for partial/failed results or invalid input/configuration.
- **dev-jev 0.2.0:** host-neutral instructions and optional Hermes provider setup;
  neutral telemetry arguments/platform paths with legacy argument, field and
  log-reading compatibility. Missing providers never block the main task.
- **Distribution:** individual/selected installation and updates, self-contained
  licenses, native UI metadata, package validation and isolated CLI regressions.

Unit, packaging and CLI results are separate from live-host/model behavior.
Snapshot tags and release publication occur after authorized review/merge.
