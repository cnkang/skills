# Runtime availability

This skill supplies instructions. The shared [Qdrant memory backend](https://github.com/cnkang/hermes-plugin-qdrant-memory) supplies storage, embeddings, scope, ledger, ownership and recovery. Its repository name preserves the original Hermes plugin distribution; standalone CLI and stdio MCP do not require Hermes.

Install the standalone-capable source in a dedicated Python 3.11+ environment:

```bash
python3 -m venv /private/path/qdrant-env
/private/path/qdrant-env/bin/python -m pip install \
  'hermes-plugin-qdrant-memory[mcp] @ git+https://github.com/cnkang/hermes-plugin-qdrant-memory.git@6a15fb4935d9e99ac4adc074c76f2c98db9abc82'
/private/path/qdrant-env/bin/qdrant-memory --help
```

The original v0.1.0 release predates these interfaces. Use the pinned source until a release includes them. Skill installation does not install the runtime. Do not install dependencies or change settings merely on skill load.

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
