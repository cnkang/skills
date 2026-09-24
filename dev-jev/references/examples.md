# dev-jev examples

These are direct payload shapes for the installed Hermes `jev_evaluate` plugin tool. Keep `state` short; do not copy sensitive source, secrets, or a whole conversation. The JSON below is illustrative input, not an assertion about what Jev will answer.

## 1. Task intake: one batched request

```json
{
  "state": "Task: fix a Python bug where CSV export drops rows with embedded newlines. The request says exports must preserve all records. Repository summary: Python service with unit tests; no other context supplied.",
  "questions": {
    "task_type": {
      "type": "choice",
      "instructions": "Which single category best describes the requested work?",
      "criteria": {
        "trivial": "A small, obvious edit with no behavior investigation",
        "implementation": "Add a new behavior or capability",
        "bugfix": "Correct existing behavior that does not meet its contract",
        "debugging": "Find the cause of a failure before a fix is known",
        "refactor": "Change internal structure without intending behavior changes",
        "testing": "Add or improve tests without changing product behavior",
        "documentation": "Change docs only",
        "code_review": "Inspect a proposed code change for defects",
        "security_review": "Inspect security properties or a security finding",
        "performance": "Investigate or improve runtime or resource use",
        "release": "Prepare or validate a release",
        "research": "Gather evidence or compare approaches",
        "unknown": "Evidence does not support another category"
      }
    },
    "complexity": {
      "type": "choice",
      "instructions": "How complex is the work based on the stated scope and evidence?",
      "criteria": {
        "trivial": "One obvious localized change; little or no investigation",
        "low": "Small change in one component with a clear verification path",
        "medium": "Several interacting details or nontrivial investigation",
        "high": "Cross-component behavior, substantial uncertainty, or compatibility concerns",
        "very_high": "Broad architectural or safety-critical work with multiple unknowns"
      }
    },
    "risk": {
      "type": "choice",
      "instructions": "What is the potential impact if the change is wrong?",
      "criteria": {
        "low": "Local, readily reversible impact",
        "medium": "Noticeable regression with a practical recovery path",
        "high": "Significant security, compatibility, reliability, or data-integrity impact",
        "critical": "Potential for severe or broad harm, data loss, or unsafe operation"
      }
    },
    "needs_repository_inspection": {"type": "noul", "instructions": "Does completing this request require inspecting repository code or configuration?", "criteria": {"true": "Repository facts are needed", "false": "The request is self-contained and can be completed without repository inspection"}},
    "needs_tests": {"type": "noul", "instructions": "Should behavior-specific tests be run or added for this work?", "criteria": {"true": "A test or existing test suite is relevant", "false": "No behavior or testable contract is involved"}},
    "needs_external_docs": {"type": "noul", "instructions": "Is current external documentation needed to answer the task correctly?", "criteria": {"true": "Versioned or external facts are required", "false": "Repository and supplied facts suffice"}},
    "needs_security_attention": {"type": "noul", "instructions": "Does the described task create a concrete reason for extra security attention?", "criteria": {"true": "The stated scope touches a security-sensitive property", "false": "No such property is apparent from the supplied state"}},
    "needs_parallel_investigation": {"type": "noul", "instructions": "Would independent parallel investigations materially help this task?", "criteria": {"true": "There are separable unknowns worth investigating in parallel", "false": "A single focused investigation is sufficient"}}
  }
}
```

In advisory mode, use this only to pick the first reversible investigation. In shadow mode, keep Hermes' own plan unchanged and log the comparison.

## 2. Search-result relevance

First filter by changed paths, file types, exact symbols, and other deterministic criteria. For a batch of up to 20 remaining candidates, put stable candidate IDs and concise metadata in `state`, then add a Choice question per candidate:

```json
{
  "state": "Query: identify the implementation and tests for CSV newline escaping. Candidates: [{\"id\":\"c1\",\"path\":\"src/export.py\",\"summary\":\"CSV writer and row serialization\"},{\"id\":\"c2\",\"path\":\"tests/test_export.py\",\"summary\":\"Export behavior tests\"},{\"id\":\"c3\",\"path\":\"docs/api.md\",\"summary\":\"Public export API contract\"}]",
  "questions": {
    "candidate_c1": {"type": "choice", "instructions": "How relevant is candidate c1 to the query?", "criteria": {"irrelevant": "Does not help answer the query", "peripheral": "Indirect background only", "useful": "May contain supporting context", "important": "Directly supports the investigation", "essential": "Likely required to answer correctly"}},
    "candidate_c2": {"type": "choice", "instructions": "How relevant is candidate c2 to the query?", "criteria": {"irrelevant": "Does not help answer the query", "peripheral": "Indirect background only", "useful": "May contain supporting context", "important": "Directly supports the investigation", "essential": "Likely required to answer correctly"}},
    "candidate_c3": {"type": "choice", "instructions": "How relevant is candidate c3 to the query?", "criteria": {"irrelevant": "Does not help answer the query", "peripheral": "Indirect background only", "useful": "May contain supporting context", "important": "Directly supports the investigation", "essential": "Likely required to answer correctly"}}
  }
}
```

Keep the ID-to-path lookup locally. If confidence is LOW/missing, retain that candidate for Hermes rather than filtering it out. Never delete any result.

## 3. Compact CI failure triage

```json
{
  "state": "CI job unit-tests exited 1. Deterministic parser: test test_export_embedded_newline failed with expected 3 rows, got 2. The current diff changes CSV row serialization in src/export.py. Previous runs: one failure; no retry yet. Redacted excerpt: assertion mismatch at tests/test_export.py:88.",
  "questions": {
    "failure_kind": {"type": "choice", "instructions": "Which category best matches the parsed failure?", "criteria": {"compile_error": "Compiler or type-check failure", "test_regression": "A test exposes changed or incorrect behavior", "flaky_test": "A test is nondeterministic across equivalent runs", "timeout": "A time limit was exceeded", "dependency": "Missing or incompatible package", "environment": "Runner or host state caused the failure", "config": "Configuration is invalid", "network": "External connectivity or service failure", "permission": "Access or authorization was denied", "memory": "Memory exhaustion or invalid memory behavior", "performance": "The job is too slow or resource-heavy", "unknown": "Available evidence does not distinguish these"}},
    "likely_transient": {"type": "noul", "instructions": "Is this failure likely transient, such that one safe retry could produce a different result?"},
    "likely_caused_by_diff": {"type": "noul", "instructions": "Is the current diff a plausible cause of the specific failing assertion?"},
    "needs_more_evidence": {"type": "noul", "instructions": "Is the supplied state insufficient to identify the next useful debugging step?"},
    "worth_one_safe_retry": {"type": "noul", "instructions": "Would one bounded retry be useful before changing code, given this failure and retry history?"}
  }
}
```

The example state is already summarized. Never substitute a full CI log. A likely regression sends Hermes to inspect the diff and test; an uncertain answer sends Hermes to gather evidence.

## 4. Debug loop

Send only the controller fields: `goal`, `current_hypothesis`, `last_action`, `last_result`, `failure_signature`, `attempt_count`, `files_changed`, `tests_run`. Ask one Choice from the defined action set in `SKILL.md`. At attempt 2 with the same normalized signature, explicitly ask whether to change strategy. At attempt 3, do not call Jev again; let Hermes re-plan.

## 5. Review and release

For a short changed-file/hunk summary, batch separate Nouls for behavior change, security relevance, memory safety, concurrency, performance, compatibility, test gap, and docs contract. HIGH/critical prioritizes code reading and call-path review; LOW never skips review.

Near release, ask separate questions such as “Is there evidence of an untested behavior change?” and “Does the current evidence indicate manual testing is still needed?” Do not ask whether to merge, release, or approve. Verify every gate independently.
