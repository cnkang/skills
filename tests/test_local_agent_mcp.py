"""Opt-in installed agent acceptance; isolated profiles, no model/API calls."""
import importlib.util
import json
import os
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import sys
import sysconfig
import threading

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("QDRANT_LOCAL_AGENTS") != "1", reason="installed CLI acceptance is opt-in")


@pytest.fixture
def backend_profile(tmp_path):
    root = Path(os.environ["QDRANT_STANDALONE_ROOT"])
    spec = importlib.util.spec_from_file_location("standalone_fixture", root / "tests/standalone/test_standalone.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generator = module.profile.__wrapped__(tmp_path)
    try:
        profile = next(generator)
        module.command(profile, "init")
        home, env = profile
        for key in list(env):
            if any(word in key.upper() for word in ("TOKEN", "API_KEY", "AUTH", "PASSWORD")):
                env.pop(key)
        env.update(HOME=str(tmp_path), CODEX_HOME=str(tmp_path / "codex"),
                   XDG_CONFIG_HOME=str(tmp_path / "config"), XDG_DATA_HOME=str(tmp_path / "data"),
                   XDG_CACHE_HOME=str(tmp_path / "cache"))
        Path(env["CODEX_HOME"]).mkdir()
        executable = str(Path(sysconfig.get_path("scripts")) / ("qdrant-memory.exe" if os.name == "nt" else "qdrant-memory"))
        yield home, env, executable
    finally:
        try:
            next(generator)
        except StopIteration:
            pass



def test_installed_codex_discovers_and_calls_scoped_mcp(backend_profile):
    home, env, executable = backend_profile
    assert shutil.which("codex")
    subprocess.run(["codex", "mcp", "add", "qdrant-memory", "--", executable, "--home", str(home), "mcp"], env=env, cwd=home, check=True, capture_output=True, timeout=20)
    process = subprocess.Popen(["codex", "app-server", "--stdio"], env=env, cwd=home,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    messages = queue.Queue()
    def read():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                pass
    threading.Thread(target=read, daemon=True).start()
    def rpc(identifier, method, params):
        process.stdin.write(json.dumps({"id": identifier, "method": method, "params": params}) + "\n")
        process.stdin.flush()
        while True:
            message = messages.get(timeout=45)
            if message.get("id") == identifier:
                assert "error" not in message, message
                return message["result"]
    try:
        rpc(1, "initialize", {"clientInfo": {"name": "qdrant-acceptance", "version": "1"}, "capabilities": {"experimentalApi": True}})
        process.stdin.write('{"method":"initialized"}\n')
        process.stdin.flush()
        thread = rpc(2, "thread/start", {"cwd": str(home), "model": "fixture", "modelProvider": "openai"})
        thread_id = thread["thread"]["id"]
        inventory = rpc(3, "mcpServerStatus/list", {"threadId": thread_id, "serverName": "qdrant-memory"})
        server = next(item for item in inventory["data"] if item["name"] == "qdrant-memory")
        assert len(server["tools"]) == 4, server
        added = rpc(4, "mcpServer/tool/call", {"threadId": thread_id, "server": "qdrant-memory", "tool": "qdrant_memory_add", "arguments": {"text": "Codex scoped memory"}})
        assert not added.get("isError"), added
        result = rpc(5, "mcpServer/tool/call", {"threadId": thread_id, "server": "qdrant-memory", "tool": "qdrant_memory_search", "arguments": {"query": "Codex scoped memory"}})
        assert "Codex scoped memory" in json.dumps(result), result
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_installed_opencode_connects_scoped_mcp(backend_profile):
    home, env, executable = backend_profile
    assert shutil.which("opencode")
    registered = subprocess.run(["opencode", "mcp", "add", "qdrant-memory", "--global", "--", executable, "--home", str(home), "mcp"], env=env, cwd=home, capture_output=True, text=True, timeout=20)
    assert registered.returncode == 0, (registered.stdout, registered.stderr)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    configured = subprocess.run(["opencode", "service", "set", "port", str(port)], env=env, cwd=home, capture_output=True, text=True, timeout=20)
    assert configured.returncode == 0, (configured.stdout, configured.stderr)
    try:
        connected = subprocess.run(["opencode", "api", "experimental.mcp.add", "--param", "server=qdrant-memory", "--data", json.dumps({"config": {"type": "local", "command": [executable, "--home", str(home), "mcp"]}})], env=env, cwd=home, capture_output=True, text=True, timeout=45)
        assert connected.returncode == 0, (connected.stdout, connected.stderr)
        connected = subprocess.run(["opencode", "api", "experimental.mcp.connect", "--param", "server=qdrant-memory"], env=env, cwd=home, capture_output=True, text=True, timeout=45)
        assert connected.returncode == 0, (connected.stdout, connected.stderr)
        result = subprocess.run(["opencode", "mcp", "list"], env=env, cwd=home, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (result.stdout, result.stderr)
        inventory = subprocess.run(["opencode", "api", "mcp.list"], env=env, cwd=home, capture_output=True, text=True, timeout=30)
        assert "qdrant-memory" in inventory.stdout and "connected" in inventory.stdout.lower(), (result.stdout, inventory.stdout, inventory.stderr, connected.stdout)
    finally:
        subprocess.run(["opencode", "service", "stop"], env=env, cwd=home, capture_output=True, timeout=20)



def test_installed_pi_discovers_scoped_mcp(backend_profile):
    home, env, executable = backend_profile
    cli_path = os.environ.get("PI_ACCEPTANCE_CLI")
    pi = ["node", cli_path] if cli_path else ["pi"]
    assert shutil.which(pi[0])
    env["PI_CODING_AGENT_DIR"] = str(home.parent / "pi-agent")
    result = subprocess.run([*pi, "mcp", "add", "qdrant-memory", "--", executable, "--home", str(home), "mcp"], env=env, cwd=home, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, (result.stdout, result.stderr)
    result = subprocess.run([*pi, "mcp", "list", "--json"], env=env, cwd=home, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, (result.stdout, result.stderr)
    for operation in ("search", "add", "update", "delete"):
        assert "qdrant_memory_" + operation in result.stdout, (result.stdout, result.stderr)
