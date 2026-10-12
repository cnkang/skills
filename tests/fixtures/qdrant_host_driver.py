"""Subprocess entrypoint for actual Hermes-discovered plugin interfaces."""
import argparse
import json
import subprocess
import sys

from plugins.memory import discover_plugin_cli_commands, load_memory_provider


def main():
    if sys.argv[1] == "cli":
        parser = argparse.ArgumentParser(prog="hermes")
        subparsers = parser.add_subparsers(dest="command", required=True)
        command = next(item for item in discover_plugin_cli_commands() if item["name"] == "qdrant-memory")
        child = subparsers.add_parser(command["name"])
        command["setup_fn"](child)
        args = parser.parse_args(sys.argv[2:])
        return command["handler_fn"](args)
    provider = load_memory_provider("qdrant-memory")
    assert provider is not None and provider.is_available()
    provider.initialize("fixture", user_id="alice")
    try:
        assert provider.wait_idle(10)
        def call(name, **args):
            return json.loads(provider.handle_tool_call("qdrant_memory_" + name, args, session_id="fixture"))
        if sys.argv[1] == "write":
            saved = call("add", text="Disposable review preference")
            assert "error" not in saved
            identifier = saved["id"]
            changed = call("update", id=identifier, text="Disposable corrected preference")
            assert changed["action"] == "UPDATE"
            duplicate = call("add", text="Disposable corrected preference")
            assert duplicate == {"action": "SKIP", "id": identifier}
            provider.on_session_switch("fixture", user_id="bob", reset=True)
            assert call("search", query="Disposable corrected preference")["memories"] == []
            assert "error" in call("update", id=identifier, text="Denied foreign change")
            assert "error" in call("delete", id=identifier)
            competing = subprocess.run([sys.executable, __file__, "cli", "qdrant-memory", "retry"],
                                       capture_output=True, text=True, encoding="utf-8", timeout=15)
            assert competing.returncode == 1
            assert json.loads(competing.stdout)["error"]["code"] == "writer_busy"
            print(json.dumps({"id": identifier, "scope_denied": True, "deduplicated": True}))
        else:
            identifier = sys.argv[2]
            hits = call("search", query="Disposable corrected preference")["memories"]
            assert any(hit["id"] == identifier and hit["text"] == "Disposable corrected preference" for hit in hits)
            assert call("delete", id=identifier)["action"] == "DELETE"
            assert call("search", query="Disposable corrected preference")["memories"] == []
            print(json.dumps({"restarted": True, "deleted": True}))
    finally:
        provider.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
