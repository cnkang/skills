# Runtime availability

The interface baseline is `cnkang/hermes-plugin-qdrant-memory` v0.1.0.
Hermes must have that plugin installed, configured for the active profile and
selected as the MemoryProvider. Follow the
[official catalog](https://hermes-agent.nousresearch.com/docs/plugins/qdrant-memory)
and [plugin setup](https://github.com/cnkang/hermes-plugin-qdrant-memory#readme)
when the user requests setup. Do not install dependencies or change configuration
merely because a skill was loaded.

Codex, Claude Code and other agents can install the package but do not thereby
gain Hermes tools. If no compatible, authenticated tool connection exists,
explain this limitation and stop the memory operation. An operator can use
`hermes qdrant-memory --help` to discover maintenance commands; the CLI does not
provide search/add/update/delete equivalents for these explicit agent tools.
There is no standalone `qdrant-memory` console command in the plugin.

Never construct private Python calls or a direct Qdrant client as a substitute.
Credentials remain in the plugin/host secret mechanism, outside skill text.
