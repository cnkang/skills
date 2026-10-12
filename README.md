# skills

**English** | [简体中文](README_zh-CN.md)

Five skills for development and Qdrant memory workflows that you can install independently and use as needed. Each package includes its own entrypoint, required resources and license, without requiring another skill.

| Skill | Version | Purpose and dependencies |
|---|---|---|
| [conventional-commit-batcher](conventional-commit-batcher/SKILL.md) | 4.0.0 | Split independent changes into Conventional Commits. Requires Git; helper scripts require Python 3.10+. Manual checks are available as a fallback. |
| [repository-quality-gate-fixer](repository-quality-gate-fixer/SKILL.md) | 0.8.0 | Audit or fix repository/PR quality gates. The optional probe requires Python 3.10+; validation uses the project's own toolchain. |
| [sonarcloud-link-inspector](sonarcloud-link-inspector/SKILL.md) | 1.1.0 | Inspect EU/US SonarCloud links using read-only requests. Requires Python 3.10+, requests, and network access; private data requires an authorized token supplied through an environment variable. |
| [dev-jev](dev-jev/SKILL.md) | 0.2.0 | Use available Jev tools for bounded semantic judgment. The provider is optional; continue the main task when it is unavailable. Telemetry requires Python 3.10+ and uses only the standard library. |
| [qdrant-memory](qdrant-memory/SKILL.md) | 0.1.0 | Memory search/edit, maintenance and Mem0 migration workflows. Requires the Hermes Qdrant Memory plugin runtime; references load on demand. |

Skill entrypoints and bundled instructions use English by default. Installing or loading a skill does not authorize edits, commits, pushes, or remote changes. Skills can cooperate when the task calls for it; there is no mandatory invocation chain.

## Install one or several skills

Requires Node.js/npm. The verified baseline is `skills 1.7.0`, which requires Node.js **22.20.0+**. Run `npx skills@latest --version` to check the actual CLI version.

```bash
# List available skills without installing
npx skills@latest add cnkang/skills --list

# Choose skills, agents, and installation mode interactively; project scope is the default
npx skills@latest add cnkang/skills

# Install just one skill for the current project
npx skills@latest add cnkang/skills --skill conventional-commit-batcher -a codex

# Install only the two selected skills for the current project
npx skills@latest add cnkang/skills --skill repository-quality-gate-fixer sonarcloud-link-inspector -a codex

# Install one skill globally
npx skills@latest add cnkang/skills --skill dev-jev -a codex -g
```

`-a` selects the agent without requiring a separate adapter package. Available IDs include `codex`, `claude-code`, `opencode`, `cursor`, `gemini-cli`, `kiro-cli`, `kimi-code-cli`, `qwen-code`, and `hermes-agent`. Supply multiple IDs to install for multiple hosts.

The default installation uses shared copies and symlinks. Add `--copy` for independent copies or filesystems that do not support links. The current CLI shares project or user-level directories for universal hosts using `.agents/skills`; check its output for the actual location. Other hosts use their corresponding installation directories. A successful installation verifies file availability; host discovery and behavior still require live verification.

OpenCode supports global installation. PromptScript is a separate agent that supports only project installation; its restriction does not apply to OpenCode. See [CLI supported agents](https://github.com/vercel-labs/skills#supported-agents) for other host restrictions.

The CLI does not install Python dependencies, a Jev provider, or legacy commands/hooks. Install SonarCloud dependencies in the virtual environment used for your task:

```bash
python3 -m pip install -r <installed-sonarcloud-skill-dir>/requirements.txt
```

## Use a skill independently

Reference an installed skill in a supported host, for example:

```text
Use $conventional-commit-batcher to split these changes into logical commits and commit them. Do not push.
Use $repository-quality-gate-fixer to audit this PR. Do not edit, commit, or push.
Use $sonarcloud-link-inspector to explain this URL without editing code or changing remote state.
Use $dev-jev for one bounded judgment if compatible tools are available, then continue the task normally.
Use $qdrant-memory to recall my review preferences without saving or changing memories.
```

Each request works independently without installing the other skills. Ask for “plan only” to review a commit plan first, and explicitly request fixes, commits, or pushes when needed. Jev's default `shadow` mode must not affect real actions, and a missing provider does not block the task.

CLI versions that support `skills use` can also load a single skill temporarily:

```bash
# Print a prompt containing temporary resource paths; do not persist an installation or launch an agent
npx skills@latest use cnkang/skills --skill sonarcloud-link-inspector

# Pass the generated prompt to a supported agent and launch that host
npx skills@latest use cnkang/skills --skill conventional-commit-batcher --agent codex
```

Launching a host requires that agent to be installed and follows its own permission settings. `use` does not automatically add other skills. See [CLI use documentation](https://github.com/vercel-labs/skills#use-a-skill-without-installing).

## Update only selected skills

```bash
# Run from the target project: update just one skill
npx skills@latest update conventional-commit-batcher -p

# Update only the two selected global skills
npx skills@latest update repository-quality-gate-fixer sonarcloud-link-inspector -g
```

Add `-y` for automation. Use explicit names and `-p`/`-g` to avoid updating unrelated skills or guessing the installation scope. An `update` without names updates all skills in the selected scope.

`skills@latest` selects the latest published CLI. Skill content updates follow the recorded source, path, and ref. `metadata.version` documents a release; it is not the CLI's version comparison mechanism. Changes to scripts or references can also trigger updates. Installations pinned to a tag/ref continue to follow that ref and do not automatically switch to the default branch. See the [upstream update implementation](https://github.com/vercel-labs/skills/blob/main/src/update.ts).

Updates may replace the entire installed package; back up intentional local changes first. The CLI may restore the shared symlink installation mode, so environments using `--copy` should check the resulting layout and reinstall with the original command plus `--copy` if needed. Updating optional adapter templates inside a package does not update commands or hooks deployed elsewhere.

## Migration and advanced installation

- To migrate from the old `cnkang/conventional-commit-batcher` source, rerun `add cnkang/skills --skill conventional-commit-batcher` with the required agent and scope. A regular `update` does not change the source.
- For manually copied packages, old locks missing a path/source, or installations that updates cannot identify, back up customizations and reinstall the selected skill with `add` to record its source. Do not edit version fields to simulate an update.
- Commit batcher **v4** removes legacy entrypoints in hidden directories and automatically discovered package AGENTS/CLAUDE files. Optional commands, dedicated agents, steering, and hooks are now templates. See [adapter setup](conventional-commit-batcher/references/adapter-setup.md) for migration. Do not automatically delete external custom configuration.
- Jev still accepts legacy telemetry arguments and reads historical logs. See [dev-jev](dev-jev/SKILL.md) for neutral paths and optional Hermes configuration.

Install every skill only when you need them all:

```bash
npx skills@latest add cnkang/skills --skill '*' -a codex
```

Keep the complete skill directory. Copying only `SKILL.md` omits scripts and references. Manual installation does not provide CLI source tracking.

## Development, validation, and releases

```bash
python3 -m venv .venv
# After activating the project virtual environment:
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_skills.py
python3 -m pytest -q conventional-commit-batcher/scripts repository-quality-gate-fixer/tests sonarcloud-link-inspector/tests dev-jev/scripts/test_dev_jev.py tests
python3 scripts/test_distribution.py --cli-version 1.7.0
```

Distribution tests use isolated HOME, configuration, and project directories. They retain all 15 original-skill subsets and add the Qdrant singleton, full catalog and a mix with each original skill (21 total). They verify repeat installation, project/global and symlink/copy paths for nine hosts, the Qdrant package on Codex/Hermes, temporary use and selective updates including document-only packages. Update sources use local Git fixtures without accessing real private repositories or tokens. A script failure does not establish that a real host is unavailable; distinguish packaging defects from upstream CLI changes.

CI checks both the pinned baseline and the latest CLI. See [behavior scenarios](docs/behavior-scenarios.md) for acceptance of real agent authorization and invocation behavior; structural checks cannot establish model behavior. [Release and rollback guidance](docs/releasing.md) covers the default-branch update channel, versions, tags, and migration.

Required three-platform [agent host acceptance](docs/agent-host-acceptance.md)
uses Hermes and the MIT-licensed Pi Coding Agent. Pi verifies real skill discovery,
explicit loading and reference reads with a local deterministic model fixture,
requiring no paid API or downloaded model. Host loading is distinct from real-model
judgment and each skill's runtime dependencies.

## Qdrant memory skill

[qdrant-memory](qdrant-memory/SKILL.md) is this repository's independently
installable skill for memory search and explicit edits, maintenance, and Mem0
migration. It loads the relevant workflow reference on demand.

### Install

```bash
# Install for the current Hermes project
npx skills@latest add cnkang/skills --skill qdrant-memory -a hermes-agent

# Or install globally for Hermes
npx skills@latest add cnkang/skills --skill qdrant-memory -a hermes-agent -g

# Install the instructions for Codex (runtime dependencies still apply)
npx skills@latest add cnkang/skills --skill qdrant-memory -a codex -g

# Alternatively, use Hermes's native installer
hermes skills install cnkang/skills/qdrant-memory
```

Choose the project or global scope you need; these are alternative installation
methods. Add `--copy` to an `npx skills` command for independent copies. Keep the
entire skill directory, including `references/`.

### Use

After installation, explicitly select the skill in a host that supports skill
invocation. For example, use `$qdrant-memory` in Codex; in Hermes, ask the agent to
use the `qdrant-memory` skill. In Pi, `/skill:qdrant-memory` loads its instructions.

| Workflow | Examples | Required interface |
|---|---|---|
| [Usage](qdrant-memory/references/usage.md) | Recall preferences, save an authorized fact, update/delete an exact memory ID | Available `qdrant_memory_search`, `qdrant_memory_add`, `qdrant_memory_update`, `qdrant_memory_delete` tools |
| [Maintenance](qdrant-memory/references/maintenance.md) | Local status, diagnostics, scoped inventory/export and authorized recovery | `hermes qdrant-memory` CLI |
| [Migration](qdrant-memory/references/migration.md) | Plan a Mem0 JSON/collection import, then resume/retry and verify an authorized import | `hermes qdrant-memory migrate mem0` CLI |

Example requests:

```text
Use $qdrant-memory to find my review language preference; do not change memories.
Use $qdrant-memory to save this preference: write my code review summaries in Chinese.
Use $qdrant-memory to find the outdated preference and show its exact ID before editing it.
Use $qdrant-memory to report local status; do not retry or delete anything.
Use $qdrant-memory to plan a dry-run from my authorized JSON export; do not import yet.
```

For operators with a configured runtime, start with these CLI commands:

```bash
hermes qdrant-memory --help
hermes qdrant-memory status
hermes qdrant-memory migrate mem0 --source-json /private/path/export.json \
  --target-collection TARGET --dry-run
```

Replace the source path and target collection with the authorized values. The
migration command only plans the import; execute it after reviewing source
identities, target and writer ownership using the
[migration guide](qdrant-memory/references/migration-commands.md).

Update only this skill in the scope where it was installed:

```bash
npx skills@latest update qdrant-memory -p
# Use -g instead of -p for a global installation
```

### Runtime dependencies and boundaries

The skill supplies workflow instructions. The separate
[Hermes Qdrant Memory plugin](https://github.com/cnkang/hermes-plugin-qdrant-memory)
supplies automatic memory, embedding, storage, scope enforcement and persistence.
To execute memory operations, install/configure that runtime for the active
Hermes profile as described in the
[plugin setup](https://github.com/cnkang/hermes-plugin-qdrant-memory#readme) and
[official catalog](https://hermes-agent.nousresearch.com/docs/plugins/qdrant-memory).
Loading the skill does not perform setup or change configuration.

Installing the skill on Codex or Pi does not provide Hermes's native tools. If
the relevant tools or CLI are unavailable, the agent explains the dependency and
stops that memory operation. There is no standalone `qdrant-memory` executable
or private Python/direct Qdrant fallback in the skill.

Native tools enforce caller scope and exact-ID checks. CLI inventory without
`--user` can expose the entire collection; CLI scope selection is an operator
permission boundary, not automatic current-user filtering. Retry mutates durable
state. Export writes sensitive local data. Deletion requires explicit scope,
dry-run review and authorization; confirmation and all-agent expansion are never
automatic. Embedded Qdrant readers can conflict with an active provider's file
lock. Preserve ledger and writer ownership during recovery. Migration re-embeds;
`--reuse-vectors` is refused and scope remapping is absent.

The root layout remains. `hermes skills tap add cnkang/skills` defaults to scanning
`skills/` and will not discover these packages. The
[Hermes non-default-path documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills#non-default-paths)
describes editing the active profile's `skills/.hub/taps.json`; use an empty
`path` for the repository root only as a deliberate configuration change.
Prefer direct-path install. See [compatibility and test boundaries](docs/qdrant-memory-compatibility.md)
for fixture validation versus live GitHub/host acceptance. The tested runtime
baseline is plugin v0.1.0; required CI covers Hermes and Pi on three platforms.

## License

[MIT](LICENSE). Every independent skill package includes a license copy.
