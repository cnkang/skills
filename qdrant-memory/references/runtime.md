# Runtime availability

This skill supplies instructions. The shared [Qdrant memory backend](https://github.com/cnkang/hermes-plugin-qdrant-memory) supplies storage, embeddings, scope, ledger, ownership and recovery. Its repository name preserves the original Hermes plugin distribution. The standalone CLI and stdio MCP do not require Hermes.

The commands below pin Runtime 0.2.2 and MCP distribution 0.1.3, the verified
baseline for this skill. Newer releases are published (Runtime 0.3.0, MCP
distribution 0.1.4), and the installer accepts an installed Runtime that is at
least the requested version. For MCP-focused agents, prefer the metadata-only
[MCP distribution](https://github.com/cnkang/qdrant-memory-mcp):

```bash
uvx --from qdrant-memory-mcp==0.1.3 qdrant-memory-mcp --home /private/path/profile mcp
```

Configure and initialize the profile first. Both distribution choices share the
same Runtime. Existing Runtime installations need not switch distributions.
For direct CLI use, install Runtime in a dedicated Python 3.11+ environment:

```bash
python3 -m venv /private/path/qdrant-env
/private/path/qdrant-env/bin/python -m pip install \
  'hermes-plugin-qdrant-memory[mcp]==0.2.2'
/private/path/qdrant-env/bin/qdrant-memory --help
```

The original v0.1.0 release predates standalone interfaces. PyPI Runtime 0.2.0
includes them. Version 0.2.1 fixes highly similar explicit adds without an LLM.
Runtime 0.2.2 supports MCP Python SDK 1.x and 2.x (`mcp>=1.30,<3`).
No prerelease selector is required. The four tools and stdio launch arguments
are the same for both SDK majors.

If your private environment specifically requires SDK 2.x, install both
constraints together:

```bash
/private/path/qdrant-env/bin/python -m pip install \
  'hermes-plugin-qdrant-memory[mcp]==0.2.2' 'mcp>=2,<3'
```

For SDK 1.x use `mcp>=1.30,<2` instead. This selects the server process's Python
SDK. A client running in another process can use its own compatible SDK.
`npx skills` distributes instructions and the bundled installer, not Python
dependencies. Do not install dependencies or change settings merely on skill load.

## Install a missing backend

When setup is authorized and neither compatible MCP tools nor a working CLI is
available, the agent can run the installed skill's [installer](../scripts/install_runtime.py):

```bash
python3 /path/to/installed/qdrant-memory/scripts/install_runtime.py \
  --venv /private/path/qdrant-env --version 0.2.2
```

Use the actual installed skill path reported by `npx skills` (global Codex usually
uses `~/.agents/skills/qdrant-memory`). Python 3.11+ must be available.
Default installation requires PyPI access. Optional source installation also needs Git/GitHub. On Windows use
`py -3.11` or an available newer Python and the returned `Scripts` executable.
The installer installs an exact PyPI version with its official MCP SDK in a new
venv, then verifies package version, imports and CLI. A matching existing environment
is reused without an upgrade. An incomplete or different-version environment fails
and is retained, with a suggestion to choose a new private environment.
Choose a new path to retry rather than deleting another installation.
Use a new private environment for an authorized upgrade. Back up the profile and
destination and retain the same collection, scope and embedding pipeline.
For an explicitly authorized candidate/development/fallback source, use
`--version 0.2.2 --revision FULL_40_CHARACTER_SHA`. The installer verifies both
version and VCS commit. A moving `main` or short SHA is rejected. Source installs
are optional and never the production default. Never silently fall back from PyPI.
The standalone acceptance checks pin revision
`c85d2bce788b117dddd854bb124971f7de8e564c`. The published release tag is the
source of truth.
For Hermes users, the pin preserves transcript-author isolation across restarts.
Unknown historical attribution disables whole-transcript supplementary extraction
until an explicit fresh transcript reset. Attributed per-turn writes continue.

On POSIX, choose an ordinary private path. Spaces are supported. Interpreter
links preserve managed Python's shared-library lookup. Windows uses copies
without requiring symlink privileges. Shell
metacharacters and control characters are rejected before installation. pip's
generated CLI entrypoint may use a shell wrapper, so unsafe interpreter paths
must be rejected even though the installer passes subprocess arguments as lists.

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

Select an available embedding service and its actual dimensions. This example does not install Ollama or download models. OpenAI-compatible embeddings and server/cloud Qdrant are also supported. Keep credentials in runtime environment variables, outside skill text and URLs.

```bash
qdrant-memory --home /private/path/profile init
qdrant-memory --home /private/path/profile doctor
qdrant-memory --home /private/path/profile search --query 'review preferences'
```

Initialize only an authorized target. `--help` proves interface availability, not service readiness. Connect MCP via [agent setup](agent-setup.md), or use the supported standalone CLI. Never substitute private Python calls or direct Qdrant access.

Existing Hermes users can retain their MemoryProvider and `hermes qdrant-memory` maintenance/migration commands. Follow [Hermes setup](https://github.com/cnkang/hermes-plugin-qdrant-memory#readme) for that integration. Automatic extraction and prefetch remain Hermes lifecycle features. Standalone exposes explicit operations.

MCP and CRUD use one fixed operator-configured profile scope. MCP client names and model arguments cannot select identities. Separate users' profiles and process credentials. Operator maintenance can select broader scopes. Check every selector. Embedded storage requires exclusive access. WriterLease coordinates a profile's writers, not distributed writers across independent profiles.
