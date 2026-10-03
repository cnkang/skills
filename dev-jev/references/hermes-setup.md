# Optional Hermes Jev provider

The core skill does not require Hermes. When using Hermes, the community Jev
plugin can provide `jev_evaluate`, `jev_check`, `jev_route`, and `jev_score`.
Inspect the installed plugin's schema and configuration before relying on its
limits or model defaults. Plugin names and fields may vary by version.

Inspect with `hermes plugins list --plain --no-bundled`. Install or enable a
provider only when requested, using its documented installer; the historical
community package is `ajensenwaud/hermes-jev-plugin`. Configure `TYPESAFE_API_KEY`
in the host secret/environment configuration, never in prompts, source or logs.
The provider sends supplied state to TypeSafe over HTTPS; confirm its endpoint
and data policy. No second HTTP client is needed in this skill.

For reproducible evaluation, pin the provider model using the installed plugin's
supported settings and record the returned model ID. Moving aliases are not
stable benchmark identities. Recalibrate only from labeled evidence.

Use the actual installed package path for telemetry. If `HERMES_HOME` is explicitly
set, the logger keeps `HERMES_HOME/logs/dev-jev.jsonl`. Otherwise it uses the host
platform directory; read older `~/.hermes/logs/dev-jev.jsonl` with `--log`.
After installation, verify Hermes skill discovery and reload using the commands
supported by the installed host version. Skill installation does not install or
enable this plugin, set credentials, or change `DEV_JEV_MODE`.
