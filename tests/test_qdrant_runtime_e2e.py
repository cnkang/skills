"""Real host discovery/provider, HTTP embedding and embedded storage across processes.

Opt in with QDRANT_RUNTIME_E2E=1 and the two source-root variables. The model
service is deterministic localhost transport; this is not agent/model judgment.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests/fixtures/qdrant_host_driver.py"


@pytest.fixture
def runtime(tmp_path):
    if os.environ.get("QDRANT_RUNTIME_E2E") != "1":
        pytest.skip("Disposable runtime E2E requires QDRANT_RUNTIME_E2E=1")
    host = Path(os.environ["HERMES_SKILL_HOST_ROOT"]).resolve()
    plugin = Path(os.environ["QDRANT_MEMORY_PLUGIN_ROOT"]).resolve()
    assert (host / "agent/memory_provider.py").is_file()
    assert (plugin / "plugin.yaml").is_file()
    keys = ("PATH", "SystemRoot", "SYSTEMROOT", "COMSPEC", "PATHEXT", "TEMP", "TMP")
    env = {key: os.environ[key] for key in keys if key in os.environ}
    home = tmp_path / "profile"
    home.mkdir()
    env.update({"HOME": str(home), "USERPROFILE": str(home), "HERMES_HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"), "XDG_STATE_HOME": str(home / ".state"),
                "PYTHONPATH": str(host), "PYTHONDONTWRITEBYTECODE": "1",
                "DO_NOT_TRACK": "1", "DISABLE_TELEMETRY": "1", "NO_PROXY": "127.0.0.1,localhost"})
    shutil.copytree(plugin, home / "plugins/qdrant-memory", ignore=shutil.ignore_patterns(
        ".git", ".venv", ".test-env", ".hermes-test-env", "__pycache__", ".pytest_cache"))
    (home / "config.yaml").write_text("memory:\n  provider: qdrant-memory\nplugins:\n  isolation: in_process\n", encoding="utf-8")
    requests = []
    service = {"fail_text": None}
    class Embeddings(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.path == "/api/embed"
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert body["truncate"] is False
            assert "Authorization" not in self.headers
            requests.append(body["input"])
            if service["fail_text"] and service["fail_text"] in body["input"]:
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            vectors = [[(byte + 1) / 256 for byte in hashlib.sha256(text.encode()).digest()[:8]]
                       for text in body["input"]]
            result = json.dumps({"embeddings": vectors}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(result)))
            self.end_headers()
            self.wfile.write(result)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Embeddings)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    cfg = {"scope": {"user_id": "alice", "agent_id": "fixture"},
           "qdrant": {"mode": "embedded", "collection": "fixture"},
           "embedding": {"provider": "ollama", "model": "deterministic-fixture", "dimensions": 8,
                         "base_url": f"http://127.0.0.1:{server.server_port}", "timeout_seconds": 3},
           "write": {"max_attempts": 1, "shutdown_timeout_seconds": 5}}
    (home / "qdrant-memory.json").write_text(json.dumps(cfg), encoding="utf-8")
    def invoke(*argv, code=0):
        result = subprocess.run([sys.executable, str(DRIVER), *argv], cwd=tmp_path,
                                env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert result.returncode == code, result.stderr[-2000:] + result.stdout[-2000:]
        return json.loads(result.stdout)
    try:
        yield home, invoke, requests, service
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_explicit_tools_scope_and_restart_persistence(runtime):
    home, invoke, requests, service = runtime
    saved = invoke("write")
    assert saved["scope_denied"] and saved["deduplicated"]
    result = invoke("read-delete", saved["id"])
    assert result == {"restarted": True, "deleted": True}
    assert (home / "qdrant-memory/state.db").is_file()
    assert requests  # Real HTTP embedding client reached the local service.


def test_discovered_cli_maintenance_migration_and_scoped_deletion(runtime):
    home, invoke, requests, service = runtime
    def cli(*argv, code=0):
        return invoke("cli", "qdrant-memory", *argv, code=code)
    assert cli("status")["ledger_exists"] is False
    source = home / "source.json"
    source.write_text(json.dumps([
        {"id": "alice-source", "memory": "Disposable alice fact", "user_id": "alice", "agent_id": "fixture"},
        {"id": "bob-source", "memory": "Disposable bob fact", "user_id": "bob", "agent_id": "fixture"},
    ]), encoding="utf-8")
    migrate = ("migrate", "mem0", "--source-json", str(source), "--quiet")
    planned = cli(*migrate, "--dry-run")
    assert planned["source_unique_count"] == 2
    assert not (home / "qdrant-memory").exists() and not requests
    cli(*migrate, "--reuse-vectors", code=1)
    assert not (home / "qdrant-memory").exists()
    imported = cli(*migrate, "--resume", "--verify")
    assert imported["processed"] == 2
    assert cli(*migrate, "--resume", "--verify")["processed"] == 2
    assert cli("stats")["points_count"] == 2
    assert cli("doctor")["ok"] and cli("verify")["ok"]
    assert cli("list")["count"]["total"] == 2
    assert cli("list", "--user", "alice", "--agent", "fixture")["count"]["total"] == 1
    output = home / "export.json"
    assert cli("export", "--user", "alice", "--agent", "fixture", "--output", str(output))["count"] == 1
    assert cli("export", "--output", str(output), code=1)["error"]["code"] == "export_target_exists"
    assert cli("retry")["points_count"] == 2
    preview = cli("delete-all", "--user", "alice", "--agent", "fixture", "--dry-run")
    assert preview["would_delete"] == 1
    assert cli("delete-all", "--user", "alice", "--agent", "fixture", code=1)["error"]["code"] == "delete_confirmation_required"
    cli("delete-all", "--user", "alice", "--agent", "fixture", "--confirm")
    assert cli("list", "--user", "alice", "--agent", "fixture")["count"]["total"] == 0
    assert cli("list", "--user", "bob", "--agent", "fixture")["count"]["total"] == 1
    verification = cli("verify", code=1)
    assert verification["ok"] is False
    assert verification["migration"]["ok"] is False
    # Resume must not silently restore the deliberately deleted source record.
    assert cli(*migrate, "--resume", "--verify", code=1)["error"]["code"] == "migration_superseded"


def test_failed_migration_survives_process_and_recovers(runtime):
    home, invoke, requests, service = runtime
    source = home / "failure-source.json"
    source.write_text('[{"id":"retry-fixture","memory":"Temporary migration fact"}]', encoding="utf-8")
    argv = ("cli", "qdrant-memory", "migrate", "mem0", "--source-json", str(source), "--quiet")
    service["fail_text"] = "Temporary migration fact"
    failed = invoke(*argv, "--resume", "--verify", code=1)
    assert failed["error"] == {"type": "HTTPStatusError", "retryable": True}
    assert (home / "qdrant-memory/state.db").is_file()
    verification = invoke("cli", "qdrant-memory", "verify", code=1)
    assert verification["migration"]["ok"] is False
    stats = invoke("cli", "qdrant-memory", "stats")
    assert stats["ledger"]["operations"]["FAILED"] >= 1, stats
    service["fail_text"] = None
    recovered = invoke(*argv, "--resume", "--retry-failed", "--verify")
    assert recovered["processed"] == 1
    assert invoke("cli", "qdrant-memory", "verify")["ok"]
    assert invoke("cli", "qdrant-memory", "stats")["points_count"] == 1
