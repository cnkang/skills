# Remote Reviews, Commits, and CI

## External signals

Fetch only signals relevant to the PR or requested gate. For GitHub, review
comments and checks; for SonarCloud/SonarQube, issues, hotspots, and gate status;
for CodeRabbit or another reviewer, the applicable review result.

Record target branch/PR/SHA and run or analysis identity. Verify findings against
current source. Historical reviews may guide diagnosis but do not prove current
closure. A stale result, rate limit, missing service, or permission error is not
success. Continue independent local work.

Prepare replies for rejected or false-positive comments if useful. Post replies,
resolve threads, request reviews, change labels, or merge only if authorized.

## Commit and push

Inspect the final staged diff and preserve unrelated user changes. Follow the
project's commit convention and configured hooks. Use commit batching only for
independent changes, not merely because multiple file types changed.

Do not bypass hooks with `--no-verify`. Diagnose failures and repair those within
scope. If hooks modify files, inspect the changes and rerun affected checks.
Reuse valid evidence for unchanged content; validation before relevant later
edits cannot certify those edits.

For authorized push tasks, verify branch and remote and push without force.
Inspect a rejected push or diverged history; do not discard remote changes.
Monitor checks for the final pushed SHA, including checks created by a subsequent
repair push. Confirm the remote ref as well as check conclusions.

Use bounded status waits, typically 30–60 seconds, or a service's retry guidance.
Fetch full logs when failure or diagnosis calls for them, not on every poll.
Keep the user informed during long waits and respect the total wait budget.

If checks fail, diagnose and repair in scope, then push and validate again within
the retry budget. If time expires, report exact SHA, run identity, last status,
and remaining work. No runs or check results is not evidence of passing CI.

Report remote actions and outcomes separately from local validation.
