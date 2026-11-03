# Codex portability

Discover the actual installed `qdrant-memory codex --help` before use. This is
an optional capability beyond Runtime 0.5.5's released interface; do not assume
it exists because this reference is present. The Codex plugin pins the Runtime
source containing the adapter. Keep the Runtime as the sole storage engine.

Use an explicitly authorized canonical `--codex-home` (or CODEX_HOME). Inspect
both v1 and v2 without reading chats, raw memories, credentials or unrelated
agent data. Configuration inspection cannot prove effective client settings.
Read the source preview locally and run `codex migrate --dry-run` before the
operator approves `--confirm --verify`. Resume with `--resume --retry-failed`.
Do not bypass WriterLease or protected Shared Owner enrollment. A second ledger
must never concurrently write the same collection.

Use `codex export --output ./new-handoff --confirm` for a scoped JSON/Markdown
bundle, then `codex verify --output ./new-handoff`. Keep the original store.
Report HANDOFF_PENDING until adoption is confirmed in the actual native client.
Ask the user to review facts, enable native memory and explicitly ask Codex to
remember approved items. Verify in a fresh chat. Do not edit generated memory
files or internal databases; AGENTS.md is not native memory. Never copy private
content into a cloud processing path without authorization.

There is no verified stable plugin bulk-write API for Codex native memory.
Internal note backends do not establish such a public contract. Preserve this
limitation when describing reversibility. Users retain readable, checksummed
data even when a harness cannot automatically ingest it.
