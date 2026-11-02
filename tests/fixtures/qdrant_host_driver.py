"""Subprocess entrypoint for actual Hermes-discovered plugin interfaces."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

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
    if sys.argv[1] == "hold-writer":
        provider = load_memory_provider("qdrant-memory")
        assert provider is not None and provider.is_available()
        provider.initialize("fixture", user_id="alice")
        assert provider.lifecycle_state == "READY"
        home = Path(os.environ["HERMES_HOME"])
        ready = home / "writer-holder.ready"
        release = home / "writer-holder.release"
        try:
            ready.write_text("ready", encoding="utf-8")
            deadline = time.monotonic() + 45
            while not release.exists():
                if time.monotonic() >= deadline:
                    raise TimeoutError("test holder was not released")
                time.sleep(0.05)
        finally:
            provider.shutdown()
        return 0
    if sys.argv[1] == "busy-recovery":
        home = Path(os.environ["HERMES_HOME"])
        ready = home / "writer-holder.ready"
        release = home / "writer-holder.release"
        holder = subprocess.Popen(
            [sys.executable, __file__, "hold-writer"],
            cwd=home,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        provider = None
        try:
            deadline = time.monotonic() + 20
            while not ready.exists():
                if holder.poll() is not None:
                    _, error = holder.communicate()
                    raise AssertionError(f"cross-process writer did not start: {error[-2000:]}")
                if time.monotonic() >= deadline:
                    raise TimeoutError("cross-process WriterLease holder did not become ready")
                time.sleep(0.05)

            provider = load_memory_provider("qdrant-memory")
            assert provider is not None and provider.is_available()
            try:
                provider.initialize("fixture", user_id="alice")
            except Exception as exc:
                assert type(exc).__name__ == "WriterBusyError", type(exc).__name__
            else:
                raise AssertionError("second process unexpectedly acquired the active WriterLease")
            failed_state = provider.lifecycle_state
            failure = provider.initialization_error
            assert failed_state == "FAILED"
            assert failure == {"code": "writer_busy", "type": "WriterBusyError"}
            assert provider._cleanup_complete
            assert provider._accepting is False and provider._cache == {}

            # Context/cache hooks may safely no-op, while durable writes and a
            # required compression checkpoint must report unavailable state.
            provider.on_turn_start(1, {}, session_id="fixture", author_id="alice")
            assert provider.prefetch("Disposable recovered writer fact", session_id="fixture") == ""
            retryable_callbacks = []
            for callback in (
                lambda: provider.sync_turn("unpersisted user", "unpersisted assistant", session_id="fixture"),
                lambda: provider.on_session_end([{"role": "user", "content": "unpersisted"}]),
                lambda: provider.on_pre_compress(
                    [{"role": "user", "content": "required evidence"}], require_checkpoint=True
                ),
            ):
                try:
                    callback()
                except RuntimeError as exc:
                    assert getattr(exc, "code", None) == "writer_busy"
                    assert getattr(exc, "retryable", False) is True
                    retryable_callbacks.append(exc.retryable)
                else:
                    raise AssertionError("durable lifecycle callback hid the WriterBusy failure")
            tool_error = json.loads(
                provider.handle_tool_call("qdrant_memory_add", {"text": "must not be written"}, session_id="fixture")
            )
            assert tool_error["error"]["code"] == "writer_busy"
            assert tool_error["error"]["retryable"] is True
            provider.shutdown()

            release.write_text("release", encoding="utf-8")
            _, holder_error = holder.communicate(timeout=20)
            assert holder.returncode == 0, holder_error[-2000:]

            # Recovery is explicit on the same instance, only after the other
            # process has completed shutdown and released its real OS lease.
            provider.initialize("fixture", user_id="alice")
            assert provider.lifecycle_state == "READY"
            event_high_watermark = provider.ledger.high_watermark("events")
            assert event_high_watermark == 0
            first = json.loads(
                provider.handle_tool_call(
                    "qdrant_memory_add", {"text": "Disposable recovered writer fact"}, session_id="fixture"
                )
            )
            assert "error" not in first
            assert provider.wait_idle(10)
            duplicate = json.loads(
                provider.handle_tool_call(
                    "qdrant_memory_add", {"text": "Disposable recovered writer fact"}, session_id="fixture"
                )
            )
            assert duplicate == {"action": "SKIP", "id": first["id"]}
            hits = json.loads(
                provider.handle_tool_call(
                    "qdrant_memory_search", {"query": "Disposable recovered writer fact"}, session_id="fixture"
                )
            )["memories"]
            assert [hit["id"] for hit in hits] == [first["id"]]
            provider.shutdown()
            return_value = {
                "retryable": failure["code"] == "writer_busy" and all(retryable_callbacks),
                "failed_state": failed_state,
                "event_high_watermark": event_high_watermark,
                "written_once": True,
            }
            print(json.dumps(return_value))
            return 0
        finally:
            release.write_text("release", encoding="utf-8")
            if holder.poll() is None:
                try:
                    holder.communicate(timeout=20)
                except subprocess.TimeoutExpired:
                    holder.terminate()
                    holder.communicate(timeout=5)
            if provider is not None and provider.lifecycle_state == "READY":
                provider.shutdown()

    provider = load_memory_provider("qdrant-memory")
    assert provider is not None
    assert provider.is_available()
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
