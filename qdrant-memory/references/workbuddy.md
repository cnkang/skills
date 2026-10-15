# WorkBuddy

Use the [Qdrant Memory connector guide](https://github.com/cnkang/qdrant-memory-mcp/tree/main/integrations/workbuddy).
The connector packages this canonical Skill at an exact commit. Keep its body
and references together. WorkBuddy-specific metadata belongs to the connector.

Discover the four scoped `qdrant_memory_*` MCP tools, including any prefix shown
by WorkBuddy. Follow [usage](usage.md) for authorized saves and exact-ID edits.
The MCP connection provides explicit operations, not automatic turn capture.

The published Python/uvx connector requires a separately prepared backend. A
managed launcher source candidate is a separate installation option. Consult
its documented validation status before you describe it as marketplace-ready.
Model/runtime preparation may take several minutes. A successful handshake
does not mean the backend is ready. An unready tool error never means a save
succeeded. Retry after preparation. Never queue a write. Do not repeat an
uncertain write unless a repeat is safe for that operation.

Keep WorkBuddy's profile separate from DSH and Hermes. This separation is
recommended. Authorized agents can also share one profile when they connect
one at a time, under the [shared memory](shared-memory.md) rules. Loading this
Skill does not authorize software installation, profile replacement, erasure
or migration.
Credentials belong in the host's credential form/environment, not Skill files,
arguments or diagnostics. Use [maintenance](maintenance.md) for authorized CLI
operations. No Hermes installation is required.
