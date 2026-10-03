# skills

**English** | [简体中文](README_zh-CN.md)

Four development skills that you can install independently and use as needed. Choose one or any combination; each package includes its own entrypoint, scripts, references, and license, without requiring another skill.

| Skill | Version | Purpose and dependencies |
|---|---|---|
| [conventional-commit-batcher](conventional-commit-batcher/SKILL.md) | 4.0.0 | Split independent changes into Conventional Commits. Requires Git; helper scripts require Python 3.10+. Manual checks are available as a fallback. |
| [repository-quality-gate-fixer](repository-quality-gate-fixer/SKILL.md) | 0.8.0 | Audit or fix repository/PR quality gates. The optional probe requires Python 3.10+; validation uses the project's own toolchain. |
| [sonarcloud-link-inspector](sonarcloud-link-inspector/SKILL.md) | 1.1.0 | Inspect EU/US SonarCloud links using read-only requests. Requires Python 3.10+, requests, and network access; private data requires an authorized token supplied through an environment variable. |
| [dev-jev](dev-jev/SKILL.md) | 0.2.0 | Use available Jev tools for bounded semantic judgment. The provider is optional; continue the main task when it is unavailable. Telemetry requires Python 3.10+ and uses only the standard library. |

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

Distribution tests use isolated HOME, configuration, and project directories. They verify all 15 nonempty skill combinations, project/global and symlink/copy installations for nine hosts, temporary use, and selective updates. Update sources use local Git fixtures without accessing real private repositories or tokens. A script failure does not establish that a real host is unavailable; distinguish packaging defects from upstream CLI changes.

CI checks both the pinned baseline and the latest CLI. See [behavior scenarios](docs/behavior-scenarios.md) for acceptance of real agent authorization and invocation behavior; structural checks cannot establish model behavior. [Release and rollback guidance](docs/releasing.md) covers the default-branch update channel, versions, tags, and migration.

## License

[MIT](LICENSE). Every independent skill package includes a license copy.
