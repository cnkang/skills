# dev-jev scripts

Run with Python 3; there are no third-party dependencies.

- `python3 telemetry.py mode` — print `off`, `shadow`, or `advisory` (unset defaults to `shadow`; invalid values fail safe to `off`).
- `python3 telemetry.py record --workflow ... --decision-type ... --question-id ... --primitive ... --result ... --final-hermes-action ...` — append one sanitized JSONL event.
- `python3 telemetry.py benchmark [--workflow ...] [--noul-threshold 0.75]` — summarize verified, labeled outcomes by workflow and decision type.
- `python3 test_dev_jev.py` — offline unit tests; never calls TypeSafe.

See `../README.md` for path resolution and field semantics. The logger is an opt-in, explicit helper; this skill does not install hooks or auto-capture tool calls.
