# Commit Batching Details

Use the scope and authorization contract in [SKILL.md](../SKILL.md).
These are workflow details, not permission to expand a task.

## Inspect and group changes

Inspect the branch, `git status --short`, and both `git diff` and
`git diff --cached`. Check in-progress Git operations before staging.
Existing staged work may belong to the user; do not unstage or commit it merely
to make a batch convenient. Ask if ownership cannot be resolved from the request.

Group by shared intent and rollback needs, not file type. Keep regression tests,
lockfiles, and documentation with the change they directly validate or describe.
Separate unrelated formatting or an independently useful refactor. Different
validation commands alone do not require separate commits.

If a file contains multiple purposes, stage explicit hunks and inspect the staged
diff. Never use `git add .` to absorb unrelated work. The index, not the working
tree alone, is the content about to be committed.

## Execute authorized batches

From the target repository, using the actual skill directory:

```bash
git diff --cached --stat
git diff --cached
python3 <skill-dir>/scripts/precommit_safety_gate.py
python3 <skill-dir>/scripts/validate_conventional_commit.py "<type(scope): subject>"
git commit -m "<type(scope): subject>"
```

Handle gate findings using [safety-gates.md](safety-gates.md). Resolve findings
before running the commit command; this example is not an unconditional script.

Use prior validation if it still applies to the staged content and environment.
Rerun checks affected by later edits or hook changes and execute required project
gates. Do not rerun an unchanged full suite just because the next batch starts.
A test of a combined working tree does not prove that an earlier partial commit
works independently; check that commit separately when the split creates a risk.

After each commit, inspect its content and remaining status. If a hook modifies
files, review and stage only intended modifications before retrying. Never retry
a failing hook blindly or bypass it with `--no-verify`. Continue authorized
in-scope repairs; report the failing command, exit code, redacted evidence, and
remaining Git state if blocked.

## Message conventions

Follow the project's convention. For Conventional Commits:

- Format: `<type>(<optional-scope>)!: <subject>`; scope and breaking marker are optional.
- Types supported by the validator: feat, fix, docs, style, refactor, perf, test,
  build, ci, chore, revert.
- Scope underscores are accepted unless `--strict-scope` is used.
- Subject length defaults to 72 characters, full header to 100; no trailing period.
- English is the default message language unless the user requests another.
  Keep standard type and `BREAKING CHANGE:` tokens.
- Separate an optional body/footer with a blank line. Explain why when useful.
- Mark a breaking change with `!` or a `BREAKING CHANGE:` footer.
- Lowercase and imperative wording are style warnings by default.

For a multiline message, write exact text to a file and use validator `--file`
and `git commit --file`; do not interpolate untrusted text into shell commands.

## Push and completion

Push only with authorization, verify the destination, and do not force push.
If the remote advanced, inspect the divergence and preserve both histories.
Resolve in-scope integration conflicts only when authorized; do not discard
remote work or rewrite shared history.

A commit ID proves a local commit. Verify the remote ref after a push before
claiming publication. When the task includes CI closure, inspect checks for the
final pushed SHA until terminal results or a bounded wait limit. Running,
unavailable, and absent checks are not passing checks.

For plan-only tasks, deliver the plan without changing the index. For execution,
report the actual commits, validation, remote status when applicable, and any
uncommitted work or blockers.
