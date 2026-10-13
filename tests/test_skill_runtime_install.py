"""Real skill distribution, pinned release/candidate installation and MCP acceptance."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("QDRANT_SKILL_INSTALL_E2E") != "1", reason="network installation acceptance is opt-in")
ROOT = Path(__file__).resolve().parents[1]


def test_npx_skill_installs_missing_runtime_and_calls_mcp(tmp_path):
    backend = Path(os.environ["QDRANT_STANDALONE_ROOT"])
    spec = importlib.util.spec_from_file_location("install_backend_fixture", backend / "tests/standalone/test_standalone.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixture = module.profile.__wrapped__(tmp_path)
    home, env = next(fixture)
    try:
        isolated = tmp_path / "user"
        isolated.mkdir()
        env.update({"HOME": str(isolated), "CODEX_HOME": str(isolated / ".codex"), "XDG_CONFIG_HOME": str(isolated / ".config"), "XDG_DATA_HOME": str(isolated / ".local/share"), "XDG_CACHE_HOME": str(isolated / ".cache"), "NPM_CONFIG_CACHE": str(tmp_path / "npm-cache"), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        env.update({"USERPROFILE": str(isolated), "APPDATA": str(isolated / "AppData/Roaming"), "LOCALAPPDATA": str(isolated / "AppData/Local")})

        def run(command, timeout=600):
            result = subprocess.run(command, cwd=isolated, env=env, text=True, capture_output=True, timeout=timeout)
            assert result.returncode == 0, (result.stdout[-3000:], result.stderr[-5000:])
            return result.stdout

        source = os.environ.get("QDRANT_SKILLS_SOURCE", str(ROOT))
        run(["npx", "--yes", "skills@1.7.0", "add", source, "--skill", "qdrant-memory", "-a", "codex", "-g", "-y"])
        installed = isolated / ".agents/skills/qdrant-memory"
        installer = installed / "scripts/install_runtime.py"
        selection = ["--version", "0.2.1"]
        candidate = os.environ.get("QDRANT_SKILL_INSTALL_REVISION")
        if candidate:
            selection += ["--revision", candidate]
        assert installer.is_file()
        assert (installed / "references/mcp.md").is_file()
        assert "install_runtime.py" in (installed / "SKILL.md").read_text()
        if os.name != "nt":
            for payload in ("$(touch QDRANT_INSTALL_SHELL_MARKER)", "`touch QDRANT_INSTALL_SHELL_MARKER`", "';touch QDRANT_INSTALL_SHELL_MARKER;#"):
                unsafe = tmp_path / ("unsafe runtime " + payload)
                refused = subprocess.run([sys.executable, str(installer), "--venv", str(unsafe)], cwd=isolated, env=env, capture_output=True, text=True, timeout=30)
                assert refused.returncode != 0 and "shell-sensitive" in refused.stderr
                assert not unsafe.exists()
            assert not list(tmp_path.rglob("QDRANT_INSTALL_SHELL_MARKER"))
        venv = tmp_path / "fresh runtime with spaces"
        assert not venv.exists()
        result = json.loads(run([sys.executable, str(installer), "--venv", str(venv), *selection]))
        assert result["ok"]
        assert not list(tmp_path.rglob("QDRANT_INSTALL_SHELL_MARKER"))
        # Candidate provenance is explicit; default release installation uses PyPI.
        origin = json.loads(run([result["python"], "-I", "-c", "import importlib.metadata as m, json, qdrant_memory; d=m.distribution('hermes-plugin-qdrant-memory'); print(json.dumps({'origin': qdrant_memory.__file__, 'version': d.version, 'source': json.loads(d.read_text('direct_url.json') or 'null')}))"]))
        assert Path(origin["origin"]).is_relative_to(venv)
        assert origin["version"] == result["installed_version"] == "0.2.1"
        if candidate:
            revision = origin["source"]["vcs_info"]["commit_id"]
            assert revision == result["requested_revision"] == candidate
            assert revision in (installed / "references/runtime.md").read_text()
        else:
            assert origin["source"] is None
        executable = result["command"]
        assert json.loads(run([executable, "--home", str(home), "init"]))["ok"]
        assert json.loads(run([executable, "--home", str(home), "doctor"]))["ok"]
        saved = json.loads(run([executable, "--home", str(home), "add", "--text", "Installation acceptance remembers this fact"]))
        similar = []
        for text in ("similarity-fixture: cats preferred", "similarity-fixture: cats avoided"):
            added = json.loads(run([executable, "--home", str(home), "add", "--text", text]))
            assert added["action"] == "ADD"
            similar.append(added["id"])
        assert len(set(similar)) == 2

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def check():
            parameters = StdioServerParameters(command=executable, args=["--home", str(home), "mcp"], env=env)
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert {tool.name for tool in tools.tools} == {"qdrant_memory_" + name for name in ("search", "add", "update", "delete")}
                    response = await session.call_tool("qdrant_memory_add", {"text": "similarity-fixture: cats preferred"})
                    assert not response.isError
                    assert json.loads(response.content[0].text) == {"action": "SKIP", "id": similar[0]}
                    response = await session.call_tool("qdrant_memory_search", {"query": "Installation acceptance remembers this fact"})
                    assert not response.isError
                    assert json.loads(response.content[0].text)["memories"][0]["id"] == saved["id"]
                    response = await session.call_tool("qdrant_memory_update", {"id": saved["id"], "text": "Installation updated fact"})
                    assert not response.isError
                    response = await session.call_tool("qdrant_memory_delete", {"id": saved["id"]})
                    assert not response.isError

        asyncio.run(check())
        found = json.loads(run([executable, "--home", str(home), "search", "--query", "similarity-fixture: cats"]))
        assert set(similar) <= {memory["id"] for memory in found["memories"]}
        # Reuse a verified installation without another pip invocation.
        assert json.loads(run([sys.executable, str(installer), "--venv", str(venv), *selection]))["command"] == executable
        # A registered Hermes plugin produces the advisory on the verify path.
        (isolated / ".hermes/plugins/qdrant-memory").mkdir(parents=True)
        (isolated / ".hermes/config.yaml").write_text("memory:\n  provider: qdrant-memory\n", encoding="utf-8")
        empty_bin = tmp_path / "empty-bin"
        empty_bin.mkdir()
        advisory = subprocess.run([sys.executable, str(installer), "--venv", str(venv), *selection], cwd=isolated, env={**env, "PATH": str(empty_bin)}, capture_output=True, text=True, timeout=60)
        assert advisory.returncode == 0
        assert "not necessary for Hermes" in advisory.stderr
        assert json.loads(advisory.stdout)["ok"]
        unrelated = tmp_path / "unrelated-environment"
        unrelated.mkdir()
        sentinel = unrelated / "keep.txt"
        sentinel.write_text("existing user files")
        refused = subprocess.run([sys.executable, str(installer), "--venv", str(unrelated)], cwd=isolated, env=env, capture_output=True, text=True, timeout=30)
        assert refused.returncode != 0
        assert sentinel.read_text() == "existing user files"
        assert list(unrelated.iterdir()) == [sentinel]
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
