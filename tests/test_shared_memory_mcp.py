"""Cross-client persistence and isolation through the real standalone MCP process."""
import asyncio
import json
import os

import pytest

from test_local_agent_mcp import backend_profile

pytestmark = pytest.mark.skipif(os.environ.get("QDRANT_STANDALONE_E2E") != "1", reason="standalone runtime acceptance is opt-in")


def test_two_client_names_share_only_the_fixed_operator_scope(backend_profile):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Implementation

    home, env, executable = backend_profile
    path = home / "qdrant-memory.json"
    cfg = json.loads(path.read_text())
    cfg["scope"]["agent_id"] = None
    path.write_text(json.dumps(cfg), encoding="utf-8")

    async def call(client_name, tool, arguments):
        parameters = StdioServerParameters(command=executable, args=["--home", str(home), "mcp"], env=env)
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write, client_info=Implementation(name=client_name, version="fixture")) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
                return result.model_dump(by_alias=True)["isError"], json.loads(result.content[0].text)

    async def check():
        error, saved = await call("agent-a", "qdrant_memory_add", {"text": "Shared review summaries use Chinese"})
        assert not error
        error, recalled = await call("agent-b", "qdrant_memory_search", {"query": "Shared review summaries use Chinese"})
        assert not error and recalled["memories"][0]["id"] == saved["id"]
        error, updated = await call("agent-b", "qdrant_memory_update", {"id": saved["id"], "text": "Shared review summaries use English"})
        assert not error and updated["action"] == "UPDATE"
        error, recalled = await call("agent-a", "qdrant_memory_search", {"query": "Shared review summaries use English"})
        assert not error and recalled["memories"][0]["id"] == saved["id"]
        cfg["scope"]["agent_id"] = "private-agent"
        path.write_text(json.dumps(cfg), encoding="utf-8")
        error, recalled = await call("agent-a", "qdrant_memory_search", {"query": "Shared review summaries"})
        assert not error and not recalled["memories"]
        error, _ = await call("agent-a", "qdrant_memory_delete", {"id": saved["id"]})
        assert error

    asyncio.run(check())
