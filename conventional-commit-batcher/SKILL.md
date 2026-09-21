---
name: conventional-commit-batcher
description: Split mixed Git changes into logical Conventional Commits when independent changes need separate commits or the user requests batching.
metadata:
  version: "3.0.0"
---

# Conventional Commit Batcher

Produce reviewable commits grouped by purpose. A single cohesive change needs
only one commit; staging-only and push-only tasks do not need a batching workflow.

## Scope and authorization

- Follow the requested action. A plan does not authorize staging or committing;
  staging does not authorize committing; committing does not authorize pushing.
- When commits are requested, execute the agreed scope without an extra plan
  approval. If the user requests a plan or review first, stop at that boundary.
- Preserve unrelated staged and unstaged work. Do not reset the index or sweep
  all changes into a commit.
- Reuse explicit authorization for the same branch, files, and action. Ask about
  new risks or material ambiguity, not merely because another batch has started.
- Keep credentials out of commits and reports. Do not bypass configured hooks.

## Workflow

1. Inspect branch, staged and unstaged diffs, and applicable project instructions.
2. Group changes by purpose and rollback unit. Keep behavior, its tests, and
   directly coupled documentation together. Separate independent changes.
3. For each authorized commit, stage only its files/hunks and review the index.
   Run the safety gate from the target repository:
   `python3 <skill-dir>/scripts/precommit_safety_gate.py`.
   Read [safety gates](references/safety-gates.md) when a finding needs review or
   Python is unavailable. Never treat a nonzero gate result as a pass.
4. Validate the message with
   `python3 <skill-dir>/scripts/validate_conventional_commit.py "<message>"`
   and commit normally. Use project message conventions; the bundled validator
   checks Conventional Commits with a 72-character subject and 100-character
   header by default.
5. If a hook fails, diagnose it. Fix failures caused by this task within the
   authorized scope, rerun affected checks, and retry. Stop for an actual blocker,
   new authorization, or repeated failure without progress.
6. Verify resulting commits and remaining work. Push only when requested, to the
   intended remote and branch without force.

Report commit IDs and purposes, validation results, and remaining changes.
A requested plan should list batch intent, files/hunks, and proposed messages.

## Conditional references

- [Core rules](references/core-rules.md): partial staging, message details, or
  commit/push recovery decisions.
- [Batching guide](references/commit-batching-guide.md) and
  [examples](references/plan-examples.md): ambiguous batch boundaries.
- [Hook example](references/commit-msg-hook-example.md): only when installing hooks.
- Agent installation instructions live in `references/*-setup.md`; read only
  the guide for the requested host.
