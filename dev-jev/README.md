# dev-jev

Independently installable bounded Jev triage for any agent with a compatible
provider. A missing provider does not block software work. The skill does not
require another skill and does not install a provider or modify host settings.

```bash
npx skills@latest add cnkang/skills --skill dev-jev -a codex
```

Read [SKILL.md](SKILL.md) for modes, routing, privacy and fallback, or
[Hermes setup](references/hermes-setup.md) for that optional provider.
Use the actual installed path for Python 3.10+ helpers:

```bash
python3 <skill-dir>/scripts/telemetry.py mode
python3 <skill-dir>/scripts/test_dev_jev.py
```

Telemetry is opt-in and stdlib-only. `--log` overrides `DEV_JEV_LOG`, then explicit
`HERMES_HOME`, then the platform user directory documented in the entrypoint.
Historical Hermes arguments and records remain supported. No semantic accuracy,
cost reduction, or performance improvement is claimed without labeled evidence.
