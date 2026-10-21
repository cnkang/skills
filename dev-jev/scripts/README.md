# dev-jev scripts

Run with Python 3.10+. There are no third-party dependencies.

- `python3 telemetry.py mode`: print `off`, `shadow`, or `advisory` (unset defaults to `shadow` and invalid values fail safe to `off`).
- `python3 telemetry.py record --workflow ... --decision-type ... --question-id ... --primitive ... --result ... --final-agent-action ...`: append one sanitized JSONL event.
- `python3 telemetry.py benchmark [--workflow ...] [--noul-threshold 0.75]`: summarize verified, labeled outcomes by workflow and decision type.
- `python3 test_dev_jev.py`: offline unit tests. Never calls TypeSafe.

See `../README.md` for path resolution and field semantics. The logger is an opt-in, explicit helper. This skill does not install hooks or auto-capture tool calls.


Telemetry creates a new JSONL log with private mode 0600 on POSIX before writing.
It rejects symlinks, reparse points, nonregular files and files with additional
hard links. Existing POSIX files must be owned by the current user. Their mode is tightened
through the opened descriptor before append. The parent must be owned by the current user and
not writable by other users. Keep custom log parents and ancestors trusted.
Windows relies on a private inherited ACL. No directory ACL is configured by
this helper, and the path checks are not a concurrent-filesystem sandbox.
