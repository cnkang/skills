# Bounded judgment workflows

### Task triage

For a non-obvious task, call `jev_evaluate` once with the compact task request and optional repository summary. Ask one Choice for task type (`trivial`, `implementation`, `bugfix`, `debugging`, `refactor`, `testing`, `documentation`, `code_review`, `security_review`, `performance`, `release`, `research`, `unknown`), one Choice for complexity (`trivial`, `low`, `medium`, `high`, `very_high`), one Choice for risk (`low`, `medium`, `high`, `critical`), and five separate Nouls: repository inspection, tests, external docs, security attention, and parallel investigation needed. These labels change the current agent' investigation plan only; they do not grant permission. Skip this call when the task category and next step are obvious.

### Search/context relevance

After lexical, path, changed-file, and other deterministic filters, rank only the shortlist. Send candidate IDs, paths, concise descriptions/snippets, and the query—not all raw grep output. Use one Choice per candidate with `irrelevant`, `peripheral`, `useful`, `important`, `essential`. Batch up to the plugin's 20-question limit.

- `essential`/`important`: read first.
- `useful`: read if the context budget allows.
- `peripheral`: defer but keep the candidate reference.
- `irrelevant`: omit only from this context pass when confidence is HIGH; never delete or discard the underlying evidence.
- LOW confidence, missing confidence, or unavailable Jev: retain the candidate for the current agent to assess.

Every omission is reversible: keep IDs, source paths, and a way to retrieve the candidate. Low Jev relevance is never a deletion instruction.

### CI/test failure triage

Parse the exit code, test name, retry count, and a short normalized log excerpt first. Ask one Choice for `compile_error`, `test_regression`, `flaky_test`, `timeout`, `dependency`, `environment`, `config`, `network`, `permission`, `memory`, `performance`, or `unknown`; ask independent Nouls for likely transient, likely caused by the current diff, needs more evidence, and worth one safe retry. Do not send raw megabyte logs.

Jev can nominate one retry only when the failure is plausibly transient and the retry is safe, bounded, and useful. Never retry repeatedly on a Jev suggestion. If likely caused by the current diff, inspect the diff and failing path. If unknown, low-confidence, or service-unavailable, return to the current agent debugging.

### Agent loop controller

Include only `goal`, `current_hypothesis`, `last_action`, `last_result`, `failure_signature`, `attempt_count`, `files_changed`, and `tests_run`, using short summaries. Ask for one Choice among `CONTINUE`, `RETRY`, `RETRY_DIFFERENT_APPROACH`, `INSPECT_MORE_CODE`, `GATHER_MORE_EVIDENCE`, `RUN_MORE_TESTS`, `REVERT_LAST_CHANGE`, `USE_SUBAGENT`, `ESCALATE_REASONING`, `ASK_USER`, `DONE`.

- After two equivalent failures, phrase the question around changing strategy, not repeating the same retry.
- After three equivalent failures, stop asking Jev for a next step and re-plan with the current agent.
- `DONE` is a suggestion, never proof the goal or gates are satisfied.
- Never let a Jev choice loop into unbounded retries. the current agent owns stopping, reverting, delegation, and user escalation.

### Code-review risk triage

the current agent performs the review. Jev may help prioritize changed files/hunks by separate bounded questions: behavior change, security relevance, memory-safety relevance, concurrency relevance, performance relevance, compatibility relevance, test-gap risk, and documentation-contract risk. Send concise diff summaries or relevant small hunks; do not ask Jev whether a PR is correct or mergeable.

HIGH/critical candidate risk means read the code, trace callers, inspect tests, and delegate if useful. MEDIUM gets normal review. LOW only permits a faster first pass; it never justifies skipping review or treating a finding as false.

### Release/merge evidence check

Ask only atomic questions about evidence completeness, likely regression risk, test-coverage concern, documentation concern, likely need for manual testing, or whether additional review may help. Never ask for or emit `MERGE`, `RELEASE`, or `APPROVE`. Final readiness comes from code facts, tests, CI, release gates, the current agent reasoning, and any required human decision.

