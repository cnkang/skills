# Pre-commit Safety Gates

Run the existing deterministic gate against the staged content from the target
repository, using the script's absolute path when the skill lives elsewhere.

```bash
python3 <skill-dir>/scripts/precommit_safety_gate.py
```

Exit codes: `0` passes; `2` requires review and explicit authorization for the
flagged category; `3` blocks the commit until fixed. The script's allow flags are
acknowledgments, not proof of safety. Do not change thresholds to hide findings.

## Review findings

Inspect exact staged files and content, not only filenames. Report the gate,
paths, and a redacted explanation; never print a secret-bearing snippet.
Distinguish real credentials from placeholders or test fixtures.

| Finding | Required resolution |
|---|---|
| Sensitive file/content | Remove real credentials from the batch. For intentional non-secret fixtures/examples, establish that inclusion is authorized and document why it is safe. Ask if that intent is unclear. |
| Local/generated artifact | Exclude accidental artifacts while preserving user files. Include intentional generated deliverables only within authorized scope. Do not untrack existing files or change ignore policy merely to silence a gate. |
| Protected/release branch | Verify the intended branch. Reuse explicit authorization for that target; ask if the destination is unexpected or unspecified. Do not switch branches silently. |
| Large/binary artifact | Review its purpose and size. Include only intentional, authorized deliverables. |
| Conflict markers or empty stage | Resolve the conflict or correct the batch; do not bypass a blocking result. |

For reviewed and authorized findings, rerun with only the matching option:
`--allow-sensitive`, `--allow-local-artifacts`,
`--allow-protected-branch`, or `--allow-large-or-binary`.
Record the rationale. A flag applies to the current staged batch; recheck after
its content changes. Existing authorization remains valid only for the same
scope and risk, not an unrelated newly detected file.

## Manual fallback

When a compatible Python interpreter is unavailable, inspect the same surfaces:

- `git diff --cached --name-only` and `git diff --cached`: sensitive paths
  such as .env, private keys, credential stores, and hardcoded credentials.
- `git status --short --untracked-files=all` and ignore rules: local-only files,
  caches, environment configuration, and unintended generated artifacts.
- `git branch --show-current`: expected branch; main/master and release/hotfix
  branches require intentional targeting.
- Staged file contents and unmerged index entries: unresolved conflict markers.
  Inspect added lines/content, not a diff regex that misses the leading `+`.
- `git diff --cached --numstat` and staged blob sizes: binary files or files
  larger than the script's default 512 KiB threshold.
- `git diff --cached --quiet`: exit 0 means there is nothing to commit;
  distinguish Git errors from a nonempty diff.

Apply the same review/authorization and blocking decisions. Report that fallback
checks were used; do not claim the script ran.
