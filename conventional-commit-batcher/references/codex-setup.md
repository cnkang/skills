# Codex setup

Use the native Agent Skills installation through `npx skills@latest add cnkang/skills --skill conventional-commit-batcher -a codex`.
Choose the CLI agent ID for your host; consult `npx skills@latest --help` and the upstream supported-agent list.
Keep the complete package so scripts and references resolve from its actual location.

Native skill installation does not deploy commands, specialist agents, steering,
or hooks. For explicitly requested legacy integration, read
[adapter setup](adapter-setup.md). Loading any adapter grants no Git authorization.
