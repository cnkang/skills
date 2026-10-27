# dev-jev scenario verification matrix

Use these cases to verify three points. First, when the skill calls the plugin. Second,
when it deliberately does not. Third, how the current agent workflow behaves in shadow,
advisory and off modes. The matrix is a manual acceptance suite. It does not
claim the model classified these examples correctly. Run offline helper tests
from the repository development checkout with
`python3 -m pytest -q tests/test_dev_jev.py`.

| Case | Jev call? | Bounded judgment | Required behavior |
|---|---|---|---|
| A one-line README typo or simple heading edit | No | The request is obvious. No semantic routing is needed | Edit and run the relevant deterministic docs check. Do not call Jev just because a task started |
| Ordinary Python bugfix with uncertain ownership or task shape | One intake batch, if ambiguity matters | Task type, complexity, risk, investigation needs | In shadow, preserve the current agent plan. In advisory, use it only to pick a reversible first inspection. |
| Complex C/Rust FFI bug | At most one intake batch, then focused calls only at decision boundaries | Complexity/risk and whether to inspect tests/security/safety paths | The current agent reads code, traces ownership and ABI paths, debugs, and tests. Jev cannot establish memory safety. |
| CI timeout | After parser summarizes timeout, if retry evidence is semantic | Failure kind, transient likelihood, worth one bounded retry | At most one safe retry. Inspect deterministic runner state. No repeated Jev retries. |
| Flaky test | After two comparable outcomes or when retry policy is unclear | Whether observed variance looks flaky and whether one retry is informative | Keep original logs. One retry is evidence collection, not proof of correctness. |
| Clear regression caused by current diff | Optional single call if cause is still uncertain | Whether failure is plausibly caused by diff | Review the diff/test path first. Jev cannot overrule reproducible failure evidence. |
| Large grep/search result set | Yes, after deterministic narrowing to a bounded candidate batch | Candidate relevance | Preserve IDs and sources. Low or missing confidence keeps the candidate. Any omission is reversible. |
| Security-sensitive diff | Yes only to prioritize review attention | Separate security/memory/concurrency/compatibility concerns | Deep agent review and tests remain mandatory. A low Jev score does not skip them and grants no permission or merge authorization. |
| Release review | Yes for atomic evidence-gap questions only | Coverage concern, manual-test likelihood, documentation concern | Check CI/release gates and human approval. Never ask Jev to approve, merge, or release. |
| Repeated debugging loop | After first failure when next-step options are genuinely ambiguous. After two equivalent failures, ask about a strategy change | A closed set of next-step types | At three equivalent failures, stop Jev calls and re-plan with the current agent. No infinite retry loop. |
| Jev plugin missing, key absent, network/API failure | No successful judgment. Log a fallback if useful | None | Continue all deterministic work. Tests and completion must not depend on Jev. |

## Mode checks

- `off`: every case follows the no-call path.
- `shadow` (default): Jev may be called only at the stated checkpoints. Its result must not alter the workflow. Record the final agent action for later comparison.
- `advisory`: only a sufficiently clear answer may reprioritize reversible work. The safeguards in the final column remain mandatory.

## Automated verification boundary

The offline tests cover mode resolution, confidence bands, sanitized JSONL logging, unavailable-provider fallback records, workflow-separated benchmark metrics, and request-level metric deduplication. They do not make network calls and do not validate Jev's semantic accuracy. For a live plugin smoke test, use synthetic, non-sensitive state and inspect the typed response. Do not use real source or secrets as a test fixture.
