# dev-jev

Hermes skill for using the installed TypeSafe Jev plugin as a fast, bounded semantic judgment layer during software work. Hermes remains responsible for reasoning, coding, debugging, code review, testing, and final decisions. Jev is advisory and cannot authorize an operation.

## Contents

- `SKILL.md` — triggers, tool use, six workflows, confidence/risk policy, privacy, fallback.
- `scripts/telemetry.py` — standard-library-only mode/confidence/JSONL/benchmark helper; no Jev client and no network access.
- `scripts/test_dev_jev.py` — offline unit tests.
- `references/examples.md` — example task, relevance, CI, debugging, review, and release question shapes.
- `references/scenario-tests.md` — requested manual call/no-call acceptance matrix.

## Prerequisites

- Hermes Agent with the TypeSafe Jev plugin enabled. In this profile, the plugin is named `jev` and exposes `jev_evaluate`, `jev_check`, `jev_route`, `jev_score`.
- `TYPESAFE_API_KEY` managed through the plugin/Hermes secret configuration. Do not put it in the skill, repository, command arguments, or logs.
- The current installed plugin defaults to `jev-latest`. Pin a concrete model in `plugins.entries.jev.settings.model` in Hermes `config.yaml` and record the returned model ID when comparing results over time; recalibrate after a model change.
- Python 3 (stdlib only) for local mode, telemetry, and tests. The Jev plugin itself handles the API connection.

Check the installed plugin with `hermes plugins list --plain --no-bundled`. If Jev is absent, use the official community plugin installer (`hermes plugins install ajensenwaud/hermes-jev-plugin`) and enable `jev`; follow its credential prompt or Hermes secret-management workflow. Do not implement a second HTTP client.

## Installation

This skill is already installed at `${HERMES_HOME:-$HOME/.hermes}/skills/dev-jev` in the active profile. For another Hermes profile, copy the complete `dev-jev` directory into that profile's `skills/` directory. A package distributed as a ZIP should retain this tree:

```text
dev-jev/
  SKILL.md
  README.md
  references/
  scripts/
```

Confirm with `hermes skills list`; start a new Hermes session or run `/reload-skills` after adding/updating files.

## Mode

- Unset `DEV_JEV_MODE` → `shadow`.
- `DEV_JEV_MODE=off` → never call Jev.
- `DEV_JEV_MODE=shadow` → call only at bounded checkpoints, log, and ignore its influence on the current workflow.
- `DEV_JEV_MODE=advisory` → Hermes may use clear outputs to reprioritize reversible work, after verification.
- Any invalid value resolves to `off`.

Inspect the current result:

```bash
python3 "${HERMES_HOME:-$HOME/.hermes}/skills/dev-jev/scripts/telemetry.py" mode
```

Set the mode in the environment of the Hermes process, e.g. `DEV_JEV_MODE=shadow hermes`. This package does not change the active environment or silently enable advisory mode.

## Local tests and benchmark

```bash
python3 "${HERMES_HOME:-$HOME/.hermes}/skills/dev-jev/scripts/test_dev_jev.py"
python3 "${HERMES_HOME:-$HOME/.hermes}/skills/dev-jev/scripts/telemetry.py" benchmark
```

Default JSONL destination: `$HERMES_HOME/logs/dev-jev.jsonl`, falling back to `~/.hermes/logs/dev-jev.jsonl`. Override with `DEV_JEV_LOG` or `--log`. The logger stores short labels and metrics only; it does not accept prompts, source, logs, or conversation fields. Add a verified `--ground-truth` only after the result is independently checked. Accuracy and false-negative rate are calculated only when labeled outcomes exist; reports stay separated by workflow and decision type. The benchmark helper defaults the Noul measurement threshold to 0.75, matching the installed plugin's convenience `jev_check` YES boundary; override it for the labeled evaluation protocol, and do not treat it as an action threshold. The plugin response does not currently include latency, so leave that field null unless a real elapsed duration is available. No benchmark result or performance improvement is claimed by this initial skill.

Provider cost and avoided-main-model-token fields are optional estimates, not supplied by Jev automatically. Record per request (not once per each question) to avoid double counting. `--request-id` lets the benchmark deduplicate request-level latency, cost, token, and fallback measures when each answer is logged as a separate event.

## Data egress

When called, the existing Jev plugin sends the supplied state and typed questions over HTTPS to `https://api.typesafe.ai/v1/systemone`. The local telemetry and test scripts never make network requests. Minimize and redact state before invoking Jev; do not submit credentials, secrets, full logs, whole source files, or conversation history. Records remain local in the profile's `logs/` directory unless the user moves them.
