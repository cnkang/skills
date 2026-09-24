# skills

Agent skills for scoped development workflows. Choose the skill that matches
the task; installing a skill does not authorize edits, commits, or remote actions.

## Choose a skill

| Skill | Version | Use it for |
|---|---|---|
| [conventional-commit-batcher](conventional-commit-batcher/SKILL.md) | 3.0.0 | Split independent changes into reviewable Conventional Commits |
| [dev-jev](dev-jev/SKILL.md) | 0.1.0 | Use Jev as a bounded, advisory semantic judgment layer during software work |
| [repository-quality-gate-fixer](repository-quality-gate-fixer/SKILL.md) | 0.7.0 | Audit quality gates or repair verified repository/PR failures |
| [sonarcloud-link-inspector](sonarcloud-link-inspector/SKILL.md) | 1.0.0 | Inspect SonarCloud URLs and support explicitly requested remediation |

The entrypoints contain the scope and essential workflow. Supporting references
are loaded only when needed.

## Install

Use Node.js/npm with `npx`. Preview the available skills:

```bash
npx skills add cnkang/skills --list
```

Install one skill for a project (run from that project):

```bash
npx skills add cnkang/skills --skill repository-quality-gate-fixer -a codex
```

Install all three for your global Codex environment:

```bash
npx skills add cnkang/skills -g -a codex -y --skill conventional-commit-batcher repository-quality-gate-fixer sonarcloud-link-inspector
```

For another supported host, select it using the CLI's `--agent` option.
The commit package also includes adapters and setup notes for
[Codex](conventional-commit-batcher/references/codex-setup.md),
[Claude Code](conventional-commit-batcher/references/claude-setup.md),
[Kiro](conventional-commit-batcher/references/kiro-setup.md),
[Kimi](conventional-commit-batcher/references/kimi-setup.md),
[Qwen](conventional-commit-batcher/references/qwen-setup.md), and
[Gemini](conventional-commit-batcher/references/gemini-setup.md).
Keep the whole package together when installing manually; copying one loader or
reference file is insufficient.

## Example requests

### Commit independent changes

```text
Use $conventional-commit-batcher to split my requested changes into logical
commits, validate each batch, and commit them. Do not push.
```

For a proposal only, ask for a commit plan and say not to stage or commit.
A staging-only or push-only request does not start the batching workflow.
Behavior, its regression tests, and directly coupled docs normally stay together.
Safety checks and configured Git hooks remain in effect.

### Audit or repair quality gates

```text
Use $repository-quality-gate-fixer to audit this PR's quality gates.
Do not edit source files, commit, or push. Report verified findings and blockers.
```

To request repairs, say what to fix and whether to commit or push.
The skill distinguishes audit-only, fix, commit, and push scopes. It preserves
unrelated work, verifies findings against current code, and reports local results
separately from checks on the final pushed SHA.

The optional probe requires Python 3.10+. It discovers repository context, not
proof of passing CI. Use `--base-ref` when a known PR/base comparison is needed;
the recommended workflow disables installed-skill scanning unless it is useful.
See [local checks](repository-quality-gate-fixer/references/local-gates.md).

### Explain a SonarCloud finding

```text
Use $sonarcloud-link-inspector to explain this hotspot URL and its branch/PR
context. Do not modify code or change the hotspot's remote state.
```

Ask explicitly for remediation when you want local code changes. The inspector
never transitions issues, reviews hotspots, or posts comments remotely.
Its helper needs Python 3 and the dependencies in
[requirements.txt](sonarcloud-link-inspector/requirements.txt).
Supply authentication through the environment when needed; see
[API details](sonarcloud-link-inspector/references/api-details.md).

### Get a bounded semantic judgment

```text
Use $dev-jev to triage this ambiguous task with a single bounded Jev call,
then continue reasoning and executing yourself. Do not let Jev authorize
any action.
```

Jev is advisory only: it supplies typed judgments for routing attention, never
generates code, and cannot approve merges, releases, or destructive operations.
The skill reuses the installed TypeSafe Jev plugin and honors `DEV_JEV_MODE`
(`off`, `shadow`, `advisory`); its telemetry and test scripts are stdlib-only and
make no network requests. Minimize and redact state before invoking Jev.

## Upgrade and migration

Versions live in `SKILL.md` under `metadata.version`. They identify releases for
readers. The `skills` CLI detects updates from the tracked source and skill-folder
hash, not semantic-version comparison. See the
[upstream implementation](https://github.com/vercel-labs/skills/blob/main/src/cli.ts).

With a CLI supporting named updates (verified with skills 1.7.0), update these
global skills:

```bash
npx skills update conventional-commit-batcher dev-jev repository-quality-gate-fixer sonarcloud-link-inspector -g -y
```

For project installations, run from the project and replace `-g` with `-p`.
Use `npx skills --version` and `npx skills --help` to check your CLI.
Back up intentional local customizations before reinstalling.

If the commit skill was installed from `cnkang/conventional-commit-batcher`,
run the global installation command above once to migrate to `cnkang/skills`.
An ordinary update follows the recorded source; changing a local version field
or copying files does not migrate it.

### Changes in this release

- **Commit batcher 3.0.0:** removes blanket Git interception and limits execution
  to the requested action. This intentionally changes the old automatic workflow.
  Existing safety checks remain; authorized in-scope hook repairs can continue.
- **Quality gate fixer 0.7.0:** replaces the default-fix assumption with scope
  inferred from the request, routes optional guidance, and avoids redundant checks.
- **SonarCloud inspector 1.0.0:** first explicit version; inspection remains
  read-only unless local remediation is requested.
- **dev-jev 0.1.0:** new skill that uses the installed TypeSafe Jev plugin as a
  bounded, advisory judgment layer. It never generates code or authorizes actions,
  and defaults to `shadow` mode.

The workflows were checked against current
[OpenAI skills guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).
Cross-host adapters have structural checks; not every host/model
combination has been exercised.

## Development checks

From the repository root, with pytest available in your Python environment:

```bash
python3 -m pytest -q conventional-commit-batcher/scripts
python3 -m unittest discover -s repository-quality-gate-fixer/tests -p 'test_*.py'
git diff --check
```

Use a project-local virtual environment for missing Python dependencies.
These script checks do not prove skill routing or model behavior; also exercise
realistic requests with isolated fixtures when changing workflow boundaries.

## License

[MIT](LICENSE)
