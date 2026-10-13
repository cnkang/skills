# skills

**English** | [简体中文](README_zh-CN.md)

Five skills for development and Qdrant memory workflows that you can install independently and use as needed. Each package includes its own entrypoint, required resources and license, without requiring another skill.

| Skill | Version | Purpose and dependencies |
|---|---|---|
| [conventional-commit-batcher](conventional-commit-batcher/SKILL.md) | 4.0.0 | Split independent changes into Conventional Commits. Requires Git. Helper scripts require Python 3.10+. Manual checks are available as a fallback. |
| [repository-quality-gate-fixer](repository-quality-gate-fixer/SKILL.md) | 0.8.0 | Audit or fix repository/PR quality gates. The optional probe requires Python 3.10+. Validation uses the project's own toolchain. |
| [sonarcloud-link-inspector](sonarcloud-link-inspector/SKILL.md) | 1.1.0 | Inspect EU/US SonarCloud links using read-only requests. Requires Python 3.10+, requests, and network access. Private data requires an authorized token supplied through an environment variable. |
| [dev-jev](dev-jev/SKILL.md) | 0.2.0 | Use available Jev tools for bounded semantic judgment. The provider is optional. Continue the main task when it is unavailable. Telemetry requires Python 3.10+ and uses only the standard library. |
| [qdrant-memory](qdrant-memory/SKILL.md) | 0.2.4 | Agent-neutral memory tools/CLI, maintenance and Mem0 migration. Standalone runtime and MCP work without Hermes. Existing Hermes integration remains supported. On Hermes, use one memory interface per profile. |

Skill entrypoints and bundled instructions use English by default. Installing or loading a skill does not authorize edits, commits, pushes, or remote changes. Skills can cooperate when the task calls for it. There is no mandatory invocation chain.

## Install one or several skills

Requires Node.js/npm. The verified baseline is `skills 1.7.0`, which requires Node.js **22.20.0+**. Run `npx skills@latest --version` to check the actual CLI version.

```bash
# List available skills without installing
npx skills@latest add cnkang/skills --list

# Choose skills, agents, and installation mode interactively. Project scope is the default
npx skills@latest add cnkang/skills

# Install just one skill for the current project
npx skills@latest add cnkang/skills --skill conventional-commit-batcher -a codex

# Install only the two selected skills for the current project
npx skills@latest add cnkang/skills --skill repository-quality-gate-fixer sonarcloud-link-inspector -a codex

# Install one skill globally
npx skills@latest add cnkang/skills --skill dev-jev -a codex -g
```

`-a` selects the agent without requiring a separate adapter package. Available IDs include `codex`, `claude-code`, `opencode`, `cursor`, `gemini-cli`, `kiro-cli`, `kimi-code-cli`, `qwen-code`, and `hermes-agent`. Supply multiple IDs to install for multiple hosts.

The default installation uses shared copies and symlinks. Add `--copy` for independent copies or filesystems that do not support links. The current CLI shares project or user-level directories for universal hosts using `.agents/skills`. Check its output for the actual location. Other hosts use their corresponding installation directories. A successful installation verifies file availability. Host discovery and behavior still require live verification.

OpenCode supports global installation. PromptScript is a separate agent that supports only project installation. Its restriction does not apply to OpenCode. See [CLI supported agents](https://github.com/vercel-labs/skills#supported-agents) for other host restrictions.

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

`skills@latest` selects the latest published CLI. Skill content updates follow the recorded source, path, and ref. `metadata.version` documents a release. It is not the CLI's version comparison mechanism. Changes to scripts or references can also trigger updates. Installations pinned to a tag/ref continue to follow that ref and do not automatically switch to the default branch. See the [upstream update implementation](https://github.com/vercel-labs/skills/blob/main/src/update.ts).

Updates may replace the entire installed package. Back up intentional local changes first. The CLI may restore the shared symlink installation mode. Environments using `--copy` should check the resulting layout and reinstall with the original command plus `--copy` if needed. Updating optional adapter templates inside a package does not update commands or hooks deployed elsewhere.

## Migration and advanced installation

- To migrate from the old `cnkang/conventional-commit-batcher` source, rerun `add cnkang/skills --skill conventional-commit-batcher` with the required agent and scope. A regular `update` does not change the source.
- For manually copied packages, old locks missing a path/source, or installations that updates cannot identify, back up customizations. Reinstall the selected skill with `add` to record its source. Do not edit version fields to simulate an update.
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

Distribution tests use isolated HOME, configuration, and project directories. They retain all 15 original-skill subsets and add the Qdrant singleton, full catalog and a mix with each original skill (21 total). They verify repeat installation, project/global and symlink/copy paths for nine hosts. They also cover the Qdrant package on Codex/Hermes, temporary use and selective reference/helper updates. Update sources use local Git fixtures without accessing real private repositories or tokens. A script failure does not establish that a real host is unavailable. Distinguish packaging defects from upstream CLI changes.

CI checks both the pinned baseline and the latest CLI. See [behavior scenarios](docs/behavior-scenarios.md) for acceptance of real agent authorization and invocation behavior. Structural checks cannot establish model behavior. [Release and rollback guidance](docs/releasing.md) covers the default-branch update channel, versions, tags, and migration.

Required three-platform [agent host acceptance](docs/agent-host-acceptance.md)
uses Hermes and the MIT-licensed Pi Coding Agent. Pi verifies real skill discovery,
explicit loading and reference reads with a local deterministic model fixture,
requiring no paid API or downloaded model. Host loading is distinct from real-model
judgment and each skill's runtime dependencies.

## Qdrant memory skill

[qdrant-memory](qdrant-memory/SKILL.md) supplies agent-neutral memory search,
explicit edits, maintenance and Mem0 migration instructions. It supports Codex,
OpenCode, Pi, Hermes and other agents that can call its CLI or MCP tools. Agents can share
an authorized memory scope or keep private scopes. Install the skill and its
runtime separately. Skill 0.2.4 uses Runtime 0.2.1 or MCP distribution 0.1.1.
The commands pin exact PyPI versions:

```bash
npx skills@latest add cnkang/skills --skill qdrant-memory -a codex -g
# Choose another supported agent ID, or multiple IDs, as needed.
python3 -m venv /private/path/qdrant-env
/private/path/qdrant-env/bin/python -m pip install \
  'hermes-plugin-qdrant-memory[mcp]==0.2.1'
```

The backend retains its original repository/distribution name. Its standalone
CLI and stdio MCP server require no Hermes installation. The original v0.1.0
release does not contain these interfaces. The command pins a PyPI release.
For MCP-focused agents, prefer `uvx --from qdrant-memory-mcp==0.1.1
qdrant-memory-mcp --home /private/path/profile mcp`. Configure
and initialize the profile first. Both install choices share the Runtime.

If the backend is missing, an agent authorized to set it up can instead run the
bundled installer from the installed skill directory:

```bash
python3 ~/.agents/skills/qdrant-memory/scripts/install_runtime.py --venv /private/path/qdrant-env
```

Use the actual skill directory printed by the CLI. By default the installer needs only Python 3.11+ and PyPI. Source installs also
need Git and GitHub access. It returns the absolute runtime command and verifies CLI/MCP imports.
It leaves existing installations and Hermes settings intact. `npx skills` itself
does not execute it. CI exercises real npx distribution, fresh pinned-source
backend installation, CLI CRUD and MCP discovery/calls using isolated profiles.

Configure the private profile and embedding service following
[runtime setup](qdrant-memory/references/runtime.md), then initialize an authorized
collection:

```bash
qdrant-memory --home /private/path/profile init
qdrant-memory --home /private/path/profile doctor
qdrant-memory --home /private/path/profile search --query 'review preferences'
```

Use the executable from the virtual environment (activate it or use its absolute
path). Connect [Codex, Claude Code, OpenCode or Pi through MCP](qdrant-memory/references/agent-setup.md),
or use the standalone JSON CLI from an agent with command execution. Discover
the four scoped tools before operations. MCP client names do not grant identity:
scope comes from the operator's fixed profile configuration.

### MCP capabilities

The skill supplies operating instructions. The separately installed runtime
supplies a local stdio MCP server. A client can use that server without loading
the skill. Agents that support skill instructions can use them together with
MCP tools or the JSON CLI.

| MCP tool | Operation |
|---|---|
| `qdrant_memory_search` | Recall scoped memories with IDs and provenance. |
| `qdrant_memory_add` | Persist an explicitly authorized fact or preference. |
| `qdrant_memory_update` | Replace an authorized memory by exact ID. |
| `qdrant_memory_delete` | Delete an authorized memory by exact ID. |

Verify a connected server and discovery of all four tools before requesting an
authorized search. MCP exposes explicit memory operations. Maintenance/migration
uses the CLI. Automatic conversation extraction remains a Hermes feature.
See [MCP capabilities and verification](qdrant-memory/references/mcp.md) for
transport, permissions, sharing and host-specific validation boundaries.

### Shared memory and workflows

For [cross-agent sharing](qdrant-memory/references/shared-memory.md), configure
the same user/profile and `agent_id: null`. This is one shared partition.
Explicit agent IDs remain private. Current embedded/MCP writers access it
sequentially under the profile lease.

| Workflow | Examples | Interface |
|---|---|---|
| [Usage](qdrant-memory/references/usage.md) | Search, authorized save, exact-ID update/delete | Scoped MCP/Hermes tools or standalone CRUD CLI |
| [Maintenance](qdrant-memory/references/maintenance.md) | Status, diagnostics, inventory/export, recovery | Standalone CLI or compatible Hermes CLI |
| [Migration](qdrant-memory/references/migration.md) | Mem0 dry-run/import/resume/verify | Standalone or Hermes `migrate mem0` |

```text
Use $qdrant-memory to find my review language preference; do not change memories.
Use $qdrant-memory to save this preference: write review summaries in Chinese.
Use $qdrant-memory to show the exact outdated memory ID before editing it.
Use $qdrant-memory to dry-run my authorized JSON migration; do not import yet.
```

Hermes users can retain their existing MemoryProvider, native tools and
`hermes qdrant-memory` commands. Install instructions with
`npx skills@latest add cnkang/skills --skill qdrant-memory -a hermes-agent`
or `hermes skills install cnkang/skills/qdrant-memory`. Automatic extraction and
prefetch remain Hermes lifecycle features. Loading a skill does not install
services, authorize writes or change configuration.

Update only this skill using `npx skills@latest update qdrant-memory -p` (use
`-g` for global scope). Keep its complete reference directory.

Maintenance list/export can select all collection users when no user selector
is provided. Check operator authorization and selectors. Preserve ledger and
ownership during recovery. Embedded storage requires exclusive access.
WriterLease is not a distributed lock across independent profiles. Migration
re-embeds. Vector reuse and scope remapping remain unsupported.
See [compatibility and validation boundaries](docs/qdrant-memory-compatibility.md).

## License

[MIT](LICENSE). Every independent skill package includes a license copy.
