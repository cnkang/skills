# Optional host adapters and v4 migration

The native `SKILL.md` is the sole entrypoint. Version 4 removes the active hidden
`.claude/`, `.kiro/`, `.agents/` wrappers and package `AGENTS.md`/`CLAUDE.md`.
Existing external copies are not removed automatically. Back up customizations,
then deliberately retire old wrappers or replace them with the templates below.
Normal skill installation never installs or enables a hook or specialist agent.

For an explicitly requested adapter, use only a template supported by that host
version. Replace `{{SKILL_DIR}}` with the absolute installed package directory;
quote paths with spaces as the host requires. Inspect the completed configuration
before copying it to its destination. Keep templates inside the installed skill
as examples; updating the skill does not update external deployed copies.

| Package template under `assets/adapters/` | Optional project destination |
|---|---|
| `claude-code/agent.md.template` | `.claude/agents/conventional-commit-batcher.md` |
| `claude-code/command.md.template` | `.claude/commands/commit-batch.md` |
| `claude-code/CLAUDE.md.template` | Merge only the requested guidance into `CLAUDE.md` |
| `shared/agent.md.template` | A host-supported specialist agent configuration |
| `shared/AGENTS.md.template` | Merge only the requested guidance into `AGENTS.md` |
| `kiro-cli/agent.json.template` | `.kiro/agents/conventional-commit-batcher.json` |
| `kiro-cli/prompt.md.template` | `.kiro/prompts/conventional-commit-batcher.md` |
| `kiro-cli/steering.md.template` | `.kiro/steering/commit-batching.md` |
| `kiro-cli/hook.json.template` | `.kiro/hooks/guard-git-commit.json`, only when a hook is requested |

The Kiro hook is advisory agent guidance, not a deterministic security boundary.
Do not overwrite unrelated host configuration. Verify host discovery and the
requested action boundary after deployment; template syntax alone is not proof
of compatibility with every host release.
