# Changelog

## qdrant-memory 0.3.1

- Add a shared-security reference: protected enrollment, Owner-only write
  credentials, diagnostic limits, coherent backups and unsupported remote
  transport. Link setup and maintenance guidance to it.
- Separate unpublished Runtime hardening work from the released 0.3.0 baseline.
- Fix the exact-ID authorization contract test so each tool receives valid
  arguments. The scope denial assertion is unchanged.

## qdrant-memory 0.3.0

- Add the cross-agent shared-memory reference: single-owner service, loopback
  bridge, explicit spaces, grants, revisions and retry rules. The service is
  opt-in and operator-configured.
- Separate private and shared workflows. Private records stay isolated. A
  read-only grant cannot mutate. Native Provider automatic shared extraction
  remains out of scope.
- Document the Runtime 0.4.0 install path and the WorkBuddy and DSH client
  configuration.

## qdrant-memory 0.2.6

- Route DeepSeek Harness and WorkBuddy users to dedicated setup references:
  tool-catalogue discovery, credential and scope boundaries, and acceptance
  steps for the four scoped MCP tools.
- Document the shared Runtime installation options and the connector Skill pin.
- Clarify retry and profile-sharing guidance for explicit memory operations.

## qdrant-memory 0.2.5

- Pin Runtime 0.2.2 and MCP distribution 0.1.2 with MCP Python SDK 1.x/2.x
  support. Keep the four scoped tools and stdio configuration unchanged.
- Verify installation through the Runtime server adapter instead of the
  SDK 1.x-only FastMCP import. Exercise both SDK majors in standalone acceptance.
- Synchronize English and Chinese installation guidance and version references.

## Unreleased

- **WorkBuddy distribution:** separate reproducible preview ZIPs and checksums
  for every controlled catalog skill, including future skills registered in the catalog. It also adds
  annotated snapshot-tag automation that prepares verified Draft Release
  assets before manual publication. Bilingual metadata exists only in the
  generated package. Canonical skills and runtime versions remain unchanged.

- **WorkBuddy preview:** a manual workflow run can build one selected catalog
  skill through the `skill` input. An empty input builds every catalog skill.

- CI: enable grouped weekly Dependabot version updates for the GitHub Actions pins.

## qdrant-memory 0.2.4 — 2026-10-13

- Default authorized backend installation to exact PyPI Runtime 0.2.1, with
  optional immutable source installation and version/provenance verification.
  Reuse matching environments and refuse implicit upgrades of other versions.
- Recommend MCP distribution 0.1.1 for MCP-focused agents. Both installation
  choices use the same Runtime and require no Hermes installation.
- Document deterministic explicit-add deduplication: distinct texts remain
  separate even when highly similar, without an LLM. Preserve scope, writer
  ownership, Hermes lifecycle, and authorized maintenance boundaries.
- Synchronize English and Chinese README version guidance and validate the
  installer and standalone CLI/MCP contracts across supported platforms.

## Earlier updates

- Apply Simplified Technical English across all skill documentation: shorter
  sentences, no semicolons, active voice. No interface changes.

- **qdrant-memory 0.2.3:** recommend one memory interface for each Hermes
  profile in the skill guidance and MCP/Hermes setup notes. Direct users to
  enable the native plugin when needed, then select it with `hermes memory
  setup`. The bundled installer detects Hermes and prints an advisory. The
  advisory recommends the native plugin when it is missing. It reports an
  installed plugin that is disabled or not selected as the memory provider. It
  states that the skill is not necessary for Hermes only when the plugin
  is enabled and selected. It infers the plugin state from the active
  profile's config.yaml and never runs a Hermes command. Other agents can
  still use the runtime. No interface changes.

- Clarify public Qdrant compatibility and authorized runtime setup guidance.
  Exclude local environment secrets while retaining publishable example files.

- **qdrant-memory 0.2.2:** pin new backend installation and required runtime CI
  to the merged backend PR #35 with the transcript-author isolation fix. Preserve
  CLI/MCP interfaces. Document that receiving the security update requires a fresh
  private environment because the installer never upgrades an existing runtime.

- **qdrant-memory 0.2.1:** make the four MCP tools, skill/runtime separation,
  local stdio setup and verified host boundaries explicit. Keep Hermes lifecycle
  compatibility and sequential shared scopes. Pin installation and CI to the
  tested merged backend snapshot, refreshed after backend PR #34. Bundle an
  authorized missing-backend installer. Reject shell-sensitive POSIX environment
  paths before pip creates CLI wrappers, with literal-path and space-path
  regression checks in installation acceptance. Require real npx distribution,
  fresh VCS installation and CLI/MCP acceptance in CI. No backend runtime
  interface changes.

- **qdrant-memory 0.2.0:** agent-neutral standalone JSON CLI and stdio MCP
  instructions, fixed-profile scope, Codex/Claude Code/OpenCode/Pi setup, and
  no-Hermes runtime acceptance. Preserve the original Hermes tools and CLI.
  Automatic extraction remains its lifecycle feature. Pin the additive backend
  source until a release includes standalone support.

- **Second agent host:** add MIT Pi Coding Agent 1.1.0 SDK acceptance with a
  pinned integrity-checked npm lockfile. Eleven tests exercise all five packages'
  discovery and explicit expansion plus real Qdrant reference reads. Three OS
  jobs, zero-skip JUnit gates and required-check aggregation need no paid API,
  account, model download or GPU. Model responses are deterministic fixtures.

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
  aggregate complete the CI gates. No production services. Existing skill
  versions and paths remain.

- **conventional-commit-batcher 4.0.0 (breaking):** one native skill entrypoint.
  Legacy hidden adapters and AGENTS/CLAUDE files move to opt-in templates. Existing
  external adapters require deliberate migration. Safety checks read index blob
  sizes, handle special paths and unresolved index entries, and withhold secret
  snippets from reports.
- **repository-quality-gate-fixer 0.8.0:** local installed-skill scanning is off by
  default. Opt in with `--skill-scan`. The `--no-skill-scan` flag remains supported.
  Home-path display handles Windows separators, case and UNC paths. Git fixtures
  use an explicit identity so tests do not depend on user configuration.
- **sonarcloud-link-inspector 1.1.0:** EU/US routing, precise URL/endpoint validation,
  bounded transient-only retries, retained batch failures, fetch statuses and
  process exit codes. Existing data fields remain. Callers should now handle
  nonzero exits for partial/failed results or invalid input/configuration.
- **dev-jev 0.2.0:** host-neutral instructions and optional Hermes provider setup.
  Neutral telemetry arguments and platform paths keep legacy argument, field and
  log-reading compatibility. Missing providers never block the main task.
- **Distribution:** individual/selected installation and updates, self-contained
  licenses, native UI metadata, package validation and isolated CLI regressions.

Unit, packaging and CLI results are separate from live-host/model behavior.
Snapshot tags and release publication occur after authorized review/merge.
