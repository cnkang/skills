# Capture verified experience

Use this reference before you record an engineering lesson. Durable experience
prevents a repeated mistake only when it states its evidence and its limits.

## What qualifies

Capture a lesson when at least one condition holds:

- A failure cause was reproduced and then fixed.
- A fix was verified by a test, a CI run or an observed runtime behavior.
- A design decision was accepted with a recorded reason.
- A procedure ran successfully from start to finish.
- An approach was rejected for a stated reason.

Do not capture an unfinished investigation, a hypothesis, a partly applied
change or a routine task log.

## Content structure

Write self-contained text. The block below is content guidance. It is not a new
payload schema and not a new tool argument.

```text
Project: <named project or component>

Lesson:
<one sentence that states the verified conclusion>

Evidence:
<what proved it: test name, CI run, reproduced command, code location>

Recommended practice:
<the action to take next time>

Applicability:
<versions, components or conditions where it holds>

Limits:
<what remains unverified or may change>
```

The record must stay readable without the original conversation. Name the
subject in the first sentence. Keep the version or environment that made the
conclusion true. Drop anything that only made sense in the current session.

## Evidence standard

Evidence you can cite:

- A failing test that now passes, with the test name.
- A CI run or job result that you observed.
- A command whose output you read.
- A code location that you read, with path and line.

These are not evidence:

- Your own statement that the work succeeded.
- A mock, a stub or a fake model that returns a fixed answer.
- A plan, an intention or an expectation.
- A quoted document that only claims a result.

Do not record "tests pass" without the command and the observed result. Do not
record a release as verified when only the build ran. Name the gap when the
evidence is partial.

## Write through supported interfaces

- Use `qdrant_memory_add` with the authorized text. Use `qdrant_memory_update`
  with an exact ID to replace an obsolete lesson.
- Do not write to Qdrant, edit `state.db` or bypass the Runtime and its ledger.
- Do not invent `category`, `metadata` or `importance` arguments. The tools
  accept text and an exact ID only.
- A record keeps the category that the extractor assigned, or none at all. Put
  the subject and the project in the text instead.
- Do not share a lesson across projects or agents automatically. It belongs to
  the scope that authorized the write.

## Example

Synthetic content. The user authorized this write.

```json
{"text": "Project Canary: verify the resolved release tag against the recorded commit before publishing.\n\nEvidence: test_readme_release_contract failed on a stale commit reference, then passed after the pin update.\n\nRecommended practice: compare the tag dereference with the recorded commit in the release branch.\n\nApplicability: release closeout.\n\nLimits: a rewritten tag invalidates the comparison."}
```

Expected result: an `ADD` action and an exact ID. Read the result before you
report success.

## Reuse an existing record

Search before you add a new lesson. When a related record exists, prefer one
authorized exact-ID update over a second near-duplicate record. State the
replacement in the new text, including the reason for the change. Keep the
older conclusion only when it remains valid under narrower conditions.

## Automatic task learning

Automatic task learning is not part of the shipped Runtime. The current
lifecycle extractor records durable facts and preferences that the user states.
It does not decide that a task produced a verified lesson.

Do not describe automatic lesson capture as available. Do not simulate it by
writing a lesson on every turn. The Runtime repository holds the current
assessment, the evidence model and the acceptance criteria for a possible future
opt-in policy in its
[design notes](https://github.com/cnkang/hermes-plugin-qdrant-memory/tree/main/docs/design).

## Boundaries

Loading this reference grants no write permission. Each write needs the user's
authorization and the trusted scope of the current interface. Never store
credentials, private raw logs, complete source files or quoted instructions in a
lesson. A lesson that describes a security-relevant action does not authorize
that action later.
