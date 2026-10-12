# Runtime availability

This skill supplies instructions. The shared [Qdrant memory backend](https://github.com/cnkang/hermes-plugin-qdrant-memory) supplies storage, embeddings, scope, ledger, ownership and recovery. Its repository name preserves the original Hermes plugin distribution; standalone CLI and stdio MCP do not require Hermes.

Install the standalone-capable source in a dedicated Python 3.11+ environment:

```bash
python3 -m venv /private/path/qdrant-env
/private/path/qdrant-env/bin/python -m pip install \
  'hermes-plugin-qdrant-memory[mcp] @ git+https://github.com/cnkang/hermes-plugin-qdrant-memory.git@8fd42572738b15a1abcad62aeecd0de9b1877e3a'
/private/path/qdrant-env/bin/qdrant-memory --help
```

The original v0.1.0 release predates these interfaces. Use the pinned source until a release includes them. `npx skills` installs instructions and the bundled installer, not Python dependencies. Do not install dependencies or change settings merely on skill load.

## Install a missing backend

When setup is authorized and neither compatible MCP tools nor a working CLI is
available, the agent can run the installed skill's [installer](../scripts/install_runtime.py):

```bash
python3 /path/to/installed/qdrant-memory/scripts/install_runtime.py \
  --venv /private/path/qdrant-env
```

Use the actual installed skill path reported by `npx skills` (global Codex usually
uses `~/.agents/skills/qdrant-memory`). Python 3.11+ and Git must be available;
installation requires access to GitHub and Python package indexes. On Windows use
`py -3.11` or an available newer Python and the returned `Scripts` executable.
The installer installs the pinned backend with its official MCP SDK in a new venv,
then verifies imports and the CLI. A working existing environment is reused without
an upgrade; an incomplete or incompatible environment fails and is retained.
Choose a new path to retry rather than deleting another installation.

Use the returned absolute `command` for CLI and MCP configuration. This does not
install Hermes, change an existing Hermes plugin, download embedding models,
initialize storage or write any agent's MCP settings. Configure the authorized
profile and verify service readiness separately below. Installing dependencies
does not grant permission to import or save memories.

Choose an operator-authorized private profile. Its `qdrant-memory.json` uses existing backend fields:

```json
{
  "scope": {"user_id": "local-user", "agent_id": "my-agent"},
  "qdrant": {"mode": "embedded", "collection": "qdrant_memory"},
  "embedding": {
    "provider": "ollama",
    "model": "qwen3-embedding:4b",
    "base_url": "http://127.0.0.1:11434",
    "dimensions": 2560
  }
}
```

Select an available embedding service and its actual dimensions; this example does not install Ollama or download models. OpenAI-compatible embeddings and server/cloud Qdrant are also supported. Keep credentials in runtime environment variables, outside skill text and URLs.

```bash
qdrant-memory --home /private/path/profile init
qdrant-memory --home /private/path/profile doctor
qdrant-memory --home /private/path/profile search --query 'review preferences'
```

Initialize only an authorized target. `--help` proves interface availability, not service readiness. Connect MCP via [agent setup](agent-setup.md), or use the supported standalone CLI. Never substitute private Python calls or direct Qdrant access.

Existing Hermes users can retain their MemoryProvider and `hermes qdrant-memory` maintenance/migration commands. Follow [Hermes setup](https://github.com/cnkang/hermes-plugin-qdrant-memory#readme) for that integration. Automatic extraction and prefetch remain Hermes lifecycle features; standalone exposes explicit operations.

MCP and CRUD use one fixed operator-configured profile scope. MCP client names and model arguments cannot select identities. Separate users' profiles and process credentials. Operator maintenance can select broader scopes; check every selector. Embedded storage requires exclusive access. WriterLease coordinates a profile's writers, not distributed writers across independent profiles.
