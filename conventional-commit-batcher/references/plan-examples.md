# Commit Plan Examples

A plan is a proposal, not authorization to stage or commit. When the user already
requested execution, use the same reasoning and proceed within that scope.

## Behavior with tests and docs

```text
Batch 1: feat(auth): add refresh token rotation
Intent: deliver rotation with its contract and regression coverage
Files: src/auth/service.ts, src/auth/service.test.ts, docs/auth.md
Batch 2: style(ui): normalize unrelated button formatting
Intent: independent formatting cleanup requested by the user
Files: src/ui/button.ts
```

Do not split the first batch merely because it includes code, tests, and docs.

## Refactor and independent fix

If the mechanical refactor is independently useful and both intermediate states
are valid, commit it first. Keep the fix and its regression test together.
If separating them produces an invalid intermediate state, keep them together.
Use partial staging for shared files and verify staged content.

## Dependency and unrelated cleanup

```text
Batch 1: build(deps): add zod for schema validation
Files: package.json, pnpm-lock.yaml
Batch 2: style(app): normalize unrelated lint formatting
Files: src/app.ts
```

Leave unrelated changes outside the user's requested scope uncommitted.
