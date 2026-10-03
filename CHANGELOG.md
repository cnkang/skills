# Changelog

## Unreleased

- **conventional-commit-batcher 4.0.0 (breaking):** one native skill entrypoint;
  legacy hidden adapters and AGENTS/CLAUDE files move to opt-in templates. Existing
  external adapters require deliberate migration. Safety checks read index blob
  sizes, handle special paths and unresolved index entries, and withhold secret
  snippets from reports.
- **repository-quality-gate-fixer 0.8.0:** local installed-skill scanning is off by
  default. Opt in with `--skill-scan`; `--no-skill-scan` remains supported.
- **sonarcloud-link-inspector 1.1.0:** EU/US routing, precise URL/endpoint validation,
  bounded transient-only retries, retained batch failures, fetch statuses and
  process exit codes. Existing data fields remain; callers should now handle
  nonzero exits for partial/failed results or invalid input/configuration.
- **dev-jev 0.2.0:** host-neutral instructions and optional Hermes provider setup;
  neutral telemetry arguments/platform paths with legacy argument, field and
  log-reading compatibility. Missing providers never block the main task.
- **Distribution:** individual/selected installation and updates, self-contained
  licenses, native UI metadata, package validation and isolated CLI regressions.

Unit, packaging and CLI results are separate from live-host/model behavior.
Snapshot tags and release publication occur after authorized review/merge.
