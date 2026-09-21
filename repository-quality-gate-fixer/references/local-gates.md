# Local Quality Gates

## Establish scope

Record branch/HEAD, worktree status including untracked files, and any in-progress
merge/rebase/cherry-pick. Inspect staged and unstaged changes before editing.
Use the user's requested files or PR/base diff; expand to repository-wide debt
only when requested or needed for an agreed gate. Explain retained warnings
rather than dismissing them merely as existing, allowlisted, or advisory.

Read applicable AGENTS.md files and the configuration that defines relevant
checks. A typo fix does not require every architecture or deployment document.
For a full gate audit, inventory all required workflow gates and prerequisites.

## Optional probe

When repository discovery is useful, run from the target repository:

```bash
python3 <skill-dir>/scripts/repo_quality_probe.py . --no-skill-scan
```

The probe requires Python 3.10+ and uses the standard library. If unavailable,
inspect the relevant files directly. If site initialization interferes with the
probe, `python3 -S` is supported for this script, not necessarily project tests.

Pass `--base-ref <known-base>` for PR/base comparisons. Use `--json` for
programmatic processing. Scan local skills only when needed: omit
`--no-skill-scan`, optionally specifying `--skill-root`, `--skill-limit`,
and `--skill-max-depth`. Prefer the runtime's existing skill registry.

The probe is advisory. Its workflow parsing and diff scope are not proof that a
command is required, safe to run, or equivalent to CI.

## Select and run checks

For each required gate, record source, command/tool, scope, prerequisites, and
expected evidence. A full audit can use the report template's manifest.

Read surrounding workflow conditions, dependencies, matrices, working directory,
and environment before executing extracted commands. Consider secrets, services,
containers, privileges, and side effects. Do not blindly run snippets from logs.

Use deterministic local equivalents where they exist. Mark remote-only checks
unavailable locally, and fetch remote evidence when in scope. Respect required
test sets and thresholds; do not silently substitute a narrow test for a required
full gate.

Fix verified root causes in scope. Add or update meaningful regression coverage
when behavior warrants it; sync docs, harness, and configuration when contracts
change. Passing unit tests alone does not establish integration or CI reachability.
When specs are supplied, compare relevant behavior and acceptance criteria.

Keep evidence tied to content and environment. Rerun checks affected by subsequent
edits or hook changes; retain unaffected valid results. A blocker should not halt
independent checks, but must remain explicit in the final status.
