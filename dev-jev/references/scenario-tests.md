# dev-jev scenario verification matrix

Use these cases to verify when the skill calls the plugin, when it deliberately does not, and how the Hermes workflow behaves in shadow/advisory/off modes. The matrix is a manual acceptance suite; it does not claim the model classified these examples correctly. Run offline helper tests separately with `scripts/test_dev_jev.py`.

| Case | Jev call? | Bounded judgment | Required Hermes behavior |
|---|---|---|---|
| A one-line README typo or simple heading edit | No | The request is obvious; no semantic routing is needed | Edit and run the relevant deterministic docs check; do not call Jev just because a task started |
| Ordinary Python bugfix with uncertain ownership or task shape | One intake batch, if ambiguity matters | Task type, complexity, risk, investigation needs | In shadow, preserve the Hermes plan; in advisory, use only to pick a reversible first inspection |
| Complex C/Rust FFI bug | At most one intake batch, then focused calls only at decision boundaries | Complexity/risk and whether to inspect tests/security/safety paths | Hermes reads code, traces ownership and ABI paths, debugs and tests; Jev cannot establish memory safety |
| CI timeout | After parser summarizes timeout, if retry evidence is semantic | Failure kind, transient likelihood, worth one bounded retry | At most one safe retry; inspect deterministic runner state; no repeated Jev retries |
| Flaky test | After two comparable outcomes or when retry policy is unclear | Whether observed variance looks flaky and whether one retry is informative | Keep original logs; one retry is evidence collection, not proof of correctness |
| Clear regression caused by current diff | Optional single call if cause is still uncertain | Whether failure is plausibly caused by diff | Review diff/test path first; Jev cannot overrule reproducible failure evidence |
| Large grep/search result set | Yes, after deterministic narrowing to a bounded candidate batch | Candidate relevance | Preserve IDs and sources; low/missing confidence keeps candidate; any omission is reversible |
| Security-sensitive diff | Yes only to prioritize review attention | Separate security/memory/concurrency/compatibility concerns | Deep Hermes review and tests remain mandatory; no Jev-low skip and no permission/merge authorization |
| Release review | Yes for atomic evidence-gap questions only | Coverage concern, manual-test likelihood, documentation concern | Check CI/release gates and human approval; never ask Jev to approve, merge, or release |
| Repeated debugging loop | After first failure when next-step options are genuinely ambiguous; after two equivalent failures ask about strategy change | A closed set of next-step types | At three equivalent failures, stop Jev calls and re-plan with Hermes; no infinite retry loop |
| Jev plugin missing, key absent, network/API failure | No successful judgment; log fallback if useful | None | Continue all deterministic/Hermes work; tests and completion must not depend on Jev |

## Mode checks

- `off`: every case follows the no-call path.
- `shadow` (default): Jev may be called only at the stated checkpoints; its result must not alter the workflow. Record the final Hermes action for later comparison.
- `advisory`: only a sufficiently clear answer may reprioritize reversible work; the safeguards in the final column remain mandatory.

## Automated verification boundary

The offline tests cover mode resolution, confidence bands, sanitized JSONL logging, unavailable-provider fallback records, workflow-separated benchmark metrics, and request-level metric deduplication. They do not make network calls and do not validate Jev's semantic accuracy. For a live plugin smoke test, use synthetic, non-sensitive state and inspect the typed response; do not use real source or secrets as a test fixture.
