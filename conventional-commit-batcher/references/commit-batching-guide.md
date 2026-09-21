# Choosing Batch Boundaries

Split changes when their purposes or rollback decisions are independent.
File type, audience, or different test commands alone are not enough.

Keep a behavior change with its regression tests and directly coupled docs.
Keep dependency declarations with their lockfile. Separate unrelated formatting
and refactors that have independent value.

Examples:

- Fix and regression test: one commit.
- New behavior and its API documentation: normally one commit.
- Two unrelated skill workflows: separate commits.
- Dependency update and unrelated lint cleanup: separate commits.
- Mechanical refactor needed by a fix: separate only if each intermediate state
  remains valid and the refactor has independent review value.

For mixed hunks in one file, stage by intent and inspect the index. Preserve
unrelated work. See [plan-examples.md](plan-examples.md) for examples and
[safety-gates.md](safety-gates.md) only for gate findings or manual fallback.
