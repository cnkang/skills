# skills

A collection of agent skills for AI-assisted development workflows.

## Included Skills

### [conventional-commit-batcher](conventional-commit-batcher/)

Split mixed changes into logical Conventional Commits when independent changes need separate commits. Planning, staging, committing, and pushing retain their own authorization boundaries.

Key features:
- Keep each behavior change with its tests and directly coupled docs
- Built-in safety gates (sensitive data, conflict markers, protected branches, large files, etc.)
- Execute requested commits; stop at a plan when only a plan is requested
- Cross-platform support: Codex, Claude Code, Kiro, Kimi, Qwen, Gemini, OpenAI

### [sonarcloud-link-inspector](sonarcloud-link-inspector/)

Inspect SonarCloud project, issue, and security hotspot links with normalized read-only output. Modify local code only when remediation is requested.

Key features:
- Supports project, issue, and security hotspot links
- Batch processing for multiple links
- Agent-friendly JSON and markdown output
- Read-only — never modifies SonarCloud state

### [repository-quality-gate-fixer](repository-quality-gate-fixer/)

Audit or repair repository quality gates with scoped fixes and current evidence. Load local, remote, environment, or NGINX guidance only when relevant.

Key features:
- Optional read-only probe collects repository context; installed-skill scanning is opt-in in the recommended workflow
- Quality Gate Manifest with evidence-based completion gate
- Scope control: focus on current branch/PR, avoid legacy debt cleanup
- Infer audit/fix/commit/push scope from the request and reuse existing authorization
- Context-aware workflow parser: ignores `env.run`/`with.run`, handles block scalar comments
- Secret redaction (URL credentials, tokens, Bearer/Basic auth, private keys) and credential safety
- `--base-ref` for accurate diff scope aligned with PR base (supports branch, tag, SHA)
- Nested `AGENTS.md` discovery for per-module agent instructions
- JSON output includes `schema_version`, `probe_version`, `generated_at`
- Markdown paths normalize `$HOME` to `~`
- Extended config detection: Python, JVM, C/C++, containers, task runners
- C / NGINX-adjacent repository checks
- Requires Python 3.10+

## Usage

```bash
npx skills add cnkang/skills --skill <skill-name>
```

For a global Codex installation of these three skills:

```bash
npx skills add cnkang/skills -g -a codex -y --skill conventional-commit-batcher repository-quality-gate-fixer sonarcloud-link-inspector
```

### Versions and updates

| Skill | Version |
|---|---|
| conventional-commit-batcher | 3.0.0 |
| repository-quality-gate-fixer | 0.7.0 |
| sonarcloud-link-inspector | 1.0.0 |

Versions are recorded in `SKILL.md` under `metadata.version`. The `skills` CLI
detects updates using the installed source and skill-folder hash, not a semantic
version comparison. See the [upstream update implementation](https://github.com/vercel-labs/skills/blob/main/src/cli.ts).

Update only these global skills with a CLI version that supports named updates
(verified with skills 1.7.0):

```bash
npx skills update conventional-commit-batcher repository-quality-gate-fixer sonarcloud-link-inspector -g -y
```

If `conventional-commit-batcher` was installed from the older standalone
`cnkang/conventional-commit-batcher` repository, first run the global installation
command above to switch its tracked source to `cnkang/skills`. Merely copying
files or changing a version field does not migrate the CLI's source record.

## License

[MIT](LICENSE)
