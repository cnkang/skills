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

## Usage

```bash
npx skills add cnkang/skills/<skill-name>
```

## License

[MIT](LICENSE)
