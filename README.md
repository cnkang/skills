# skills

A collection of agent skills for AI-assisted development workflows.

## Included Skills

### [conventional-commit-batcher](conventional-commit-batcher/)

Auto-split mixed changes into logical commit batches with validated Conventional Commit messages. Automatically intercepts all `git add`, `git commit`, and `git push` operations to enforce a plan-first workflow with built-in safety gates.

Key features:
- Plan-first workflow prevents accidental mixed commits
- Built-in safety gates (sensitive data, conflict markers, protected branches, large files, etc.)
- Auto-execute by default, plan-first on request
- Cross-platform support: Codex, Claude Code, Kiro, Kimi, Qwen, Gemini, OpenAI

### [sonarcloud-link-inspector](sonarcloud-link-inspector/)

Parse SonarCloud project, issue, and security hotspot links, then fetch normalized read-only details for agent analysis and code-fix workflows.

Key features:
- Supports project, issue, and security hotspot links
- Batch processing for multiple links
- Agent-friendly JSON and markdown output
- Read-only — never modifies SonarCloud state

### [repository-quality-gate-fixer](repository-quality-gate-fixer/)

Orchestrate a complete local repository quality-gate closure loop: audit, fix, and verify against AGENTS.md, local CI, Skills, reviews, specs, and quality gates, then produce an evidence-backed report.

Key features:
- Read-only probe collects git state, CI workflows, configs, stack, tools, and local Skills
- Quality Gate Manifest with evidence-based completion gate
- Scope control: focus on current branch/PR, avoid legacy debt cleanup
- Mode escalation requires explicit authorization
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
npx skills add cnkang/skills/<skill-name>
```

## License

[MIT](LICENSE)
