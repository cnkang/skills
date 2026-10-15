# DeepSeek Harness

Use the shared MCP server through DSH's official `@deepseek-ai/dsh-mcp-client`.
Follow the [English installation guide](https://github.com/cnkang/qdrant-memory-mcp/blob/main/docs/dsh-integration.md)
or [中文说明](https://github.com/cnkang/qdrant-memory-mcp/blob/main/docs/dsh-integration.zh-CN.md).
Loading this Skill does not authorize installing software or modifying a profile.

Install this canonical `qdrant-memory` directory under a standard DSH Skill
root, such as `.agents/skills/qdrant-memory/SKILL.md` in the selected project.
Keep its `references` and `scripts` together. DSH's filesystem provider also
supports custom Skill roots; point it at the directory containing
`qdrant-memory`, not at `SKILL.md`. Do not maintain an independently edited copy.

Choose a dedicated DSH memory profile. Prepare the backend before enabling the
MCP overlay; DSH may start and close a temporary probe process before starting
the persistent connection. Never put downloads or initialization in that probe.
Apply the additional overlay with `dsh web --patch /absolute/path/to/overlay`.
Do not overwrite `cordis.patch.yml` or modify the default Profile. Enable only
one Qdrant Memory overlay per profile.

With server name `qdrant-memory`, discover:

| Tool | Operation |
| --- | --- |
| `mcp__qdrant-memory__qdrant_memory_search` | Scoped recall |
| `mcp__qdrant-memory__qdrant_memory_add` | Authorized explicit save |
| `mcp__qdrant-memory__qdrant_memory_update` | Authorized exact-ID replacement |
| `mcp__qdrant-memory__qdrant_memory_delete` | Authorized exact-ID deletion |

DSH scrubs credential-shaped variables from inherited stdio environments.
Explicitly forward required credential variables in the trusted MCP configuration
using `!!js process.env.VARIABLE`; do not put secret values in YAML, arguments,
Skill text, transcripts or diagnostics. Respect DSH tool approval and cancellation.

A connected transport and four discovered tools do not establish backend
readiness. If preparation is pending or fails, report that no operation succeeded.
After interruption, search before repeating an uncertain write. For acceptance,
save a synthetic fact in one session, retrieve and use it in a fresh session
without supplying the old transcript, then verify exact-ID update/delete and
full host restart persistence. Distinguish official client tests from model/GUI
acceptance; neither implies automatic extraction or prefetch.

Use [maintenance](maintenance.md) through the standalone CLI when authorized.
Do not require Hermes CLI or WorkBuddy metadata. Never bypass WriterLease or open
the same embedded storage from two hosts; see [shared memory](shared-memory.md).
