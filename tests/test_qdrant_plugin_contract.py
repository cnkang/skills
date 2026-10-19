"""Offline public-parser/tool contracts; no production services or host lifecycle.

Set QDRANT_MEMORY_PLUGIN_ROOT to a checkout with its declared dependencies installed.
CI checks the pinned Runtime source; an absent opt-in is an explicit skip.
"""
import argparse
import importlib
import json
import os
import sys
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

PLUGIN_RELEASE_SHA = "c85d2bce788b117dddd854bb124971f7de8e564c"


def test_ci_contract_uses_immutable_release():
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/validate.yml").read_text())
    checkouts = [step["with"] for step in workflow["jobs"]["qdrant-contract"]["steps"]
                 if step.get("with", {}).get("repository") == "cnkang/hermes-plugin-qdrant-memory"]
    assert len(checkouts) == 1
    assert checkouts[0]["ref"] == PLUGIN_RELEASE_SHA
    assert checkouts[0]["persist-credentials"] is False


def require_plugin(path):
    if path is None:
        raise FileNotFoundError("Qdrant plugin not supplied; install/connect it before memory operations")
    root = Path(path).resolve()
    if not (root / "qdrant_memory" / "cli.py").is_file():
        raise FileNotFoundError("Qdrant plugin public CLI module missing")
    return root


def test_missing_plugin_is_an_explicit_failure(tmp_path):
    for path in (None, tmp_path):
        with pytest.raises(FileNotFoundError):
            require_plugin(path)


@pytest.fixture(scope="module")
def plugin():
    configured = os.environ.get("QDRANT_MEMORY_PLUGIN_ROOT")
    if not configured:
        pytest.skip("Offline plugin contract needs QDRANT_MEMORY_PLUGIN_ROOT; not host E2E")
    root = require_plugin(configured)
    sys.path.insert(0, str(root))
    try:
        cli = importlib.import_module("qdrant_memory.cli")
        tools = importlib.import_module("qdrant_memory.tools")
        assert Path(cli.__file__).resolve().is_relative_to(root)
        yield SimpleNamespace(cli=cli, tools=tools)
    finally:
        sys.path.remove(str(root))


def parser_for(plugin):
    parser = argparse.ArgumentParser()
    plugin.cli.register_cli(parser)
    return parser


def test_tool_names_and_schemas(plugin):
    expected = {
        "qdrant_memory_search": ({"query", "category"}, {"query"}),
        "qdrant_memory_add": ({"text"}, {"text"}),
        "qdrant_memory_update": ({"id", "text"}, {"id", "text"}),
        "qdrant_memory_delete": ({"id"}, {"id"}),
    }
    schemas = plugin.tools.schemas()
    assert len(schemas) == len(expected)
    assert {item["name"] for item in schemas} == set(expected)
    for item in schemas:
        properties, required = expected[item["name"]]
        params = item["parameters"]
        assert params["type"] == "object" and params["additionalProperties"] is False
        assert set(params["properties"]) == properties
        assert set(params["required"]) == required
        assert all(value == {"type": "string"} for value in params["properties"].values())


@pytest.mark.parametrize("argv", [
    [command, "--collection", "fixture"]
    for command in ("status", "doctor", "stats", "verify", "retry")
] + [
    ["list", "--user", "u", "--agent", "a", "--limit", "20"],
    ["export", "--user", "u", "--agent", "a", "--output", "fixture.json", "--force"],
    ["delete-all", "--user", "u", "--agent", "a", "--dry-run"],
    ["delete-all", "--user", "u", "--all-agents", "--confirm"],
    ["delete-all", "--user", "u", "--resolve-legacy", "single_agent", "--confirm"],
    ["migrate", "mem0", "--source-json", "fixture.json", "--target-collection", "target",
     "--reembed", "--resume", "--retry-failed", "--verify", "--quiet", "--oversize", "reject"],
    ["migrate", "mem0", "--source-qdrant-collection", "source", "--source-config", "source.json", "--dry-run"],
])
def test_cli_argument_support(plugin, argv):
    args = parser_for(plugin).parse_args(argv)
    assert args.qdrant_command == argv[0]
    assert args.func is plugin.cli.main


def test_scope_selection_and_required_arguments(plugin):
    parser = parser_for(plugin)
    assert plugin.cli.scope_from(parser.parse_args(["list"])) is None
    scope = plugin.cli.scope_from(parser.parse_args(["list", "--user", "u"]))
    assert scope.as_dict() == {"user_id": "u", "agent_id": None}
    scope = plugin.cli.scope_from(parser.parse_args(["list", "--user", "u", "--agent", "*"]))
    assert scope.agent_id == "*"
    with pytest.raises(plugin.cli.ScopeSelectionError):
        plugin.cli.scope_from(parser.parse_args(["list", "--agent", "a"]))
    for argv in (["export"], ["migrate", "mem0"],
                 ["migrate", "mem0", "--source-json", "a", "--source-qdrant-collection", "b"],
                 ["migrate", "mem0", "--source-json", "a", "--user", "u"]):
        with pytest.raises(SystemExit):
            parser.parse_args(argv)


def no_service(*args, **kwargs):
    raise AssertionError("Offline contract must not contact target or embedding services")


@pytest.fixture
def offline_home(plugin, tmp_path, monkeypatch):
    # Replace host profile/config loading only; validate the fixture with the
    # real plugin validator. This is deliberately not Hermes host acceptance.
    monkeypatch.setattr(plugin.cli, "active_home", lambda: tmp_path)
    config = importlib.import_module("qdrant_memory.config")
    def fixture_config(home, overrides=None, **kwargs):
        cfg = deepcopy(config.DEFAULTS)
        cfg["qdrant"]["path"] = str(tmp_path / "embedded")
        cfg = config.merge(cfg, overrides or {})
        config.validate(cfg)
        return cfg
    monkeypatch.setattr(plugin.cli, "load_config", fixture_config)
    monkeypatch.setattr(plugin.cli, "build_client", no_service)
    monkeypatch.setattr(plugin.cli, "build_embedder", no_service)
    return tmp_path


def test_local_status_json_without_service_access(plugin, offline_home, capsys):
    args = parser_for(plugin).parse_args(["status"])
    assert plugin.cli.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["provider"] == "qdrant-memory"
    assert result["mode"] == "embedded"
    assert result["ledger_exists"] is False
    assert set(result["embedding"]) == {"provider", "model", "dimensions"}
    assert not (offline_home / "qdrant-memory").exists()


def test_migration_dry_run_and_vector_reuse_refusal(plugin, offline_home, capsys):
    source = offline_home / "source.json"
    source.write_text(json.dumps([{"id": "fixture", "memory": "Disposable fact", "user_id": "u"}]))
    parser = parser_for(plugin)
    args = parser.parse_args(["migrate", "mem0", "--source-json", str(source), "--dry-run", "--quiet"])
    assert plugin.cli.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["dry_run"] is True and result["source_unique_count"] == 1
    assert len(result["target_ids"]) == 1
    assert not (offline_home / "qdrant-memory").exists()
    args.reuse_vectors = True
    assert plugin.cli.main(args) == 1
    assert json.loads(capsys.readouterr().out)["error"]["type"] == "ValueError"


@pytest.mark.parametrize("command", ["retry", "delete-all", "migrate"])
def test_busy_writer_is_refused_before_services(plugin, offline_home, monkeypatch, capsys, command):
    def busy(*args, **kwargs):
        raise plugin.cli.WriterBusyError("private detail must not be exposed")
    monkeypatch.setattr(plugin.cli.WriterLease, "for_config", busy)
    argv = [command]
    if command == "delete-all":
        argv += ["--user", "u", "--dry-run"]
    if command == "migrate":
        source = offline_home / "source.json"
        source.write_text('[{"id":"fixture","memory":"Disposable fact"}]')
        argv += ["mem0", "--source-json", str(source), "--quiet"]
    assert plugin.cli.main(parser_for(plugin).parse_args(argv)) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["error"]["code"] == "writer_busy"
    assert "private detail" not in json.dumps(result)


@pytest.mark.parametrize("tool", ["qdrant_memory_update", "qdrant_memory_delete"])
def test_exact_id_is_not_scope_authorization(plugin, tool):
    runtime = SimpleNamespace(lock=nullcontext(), store=SimpleNamespace(get=lambda identifier, scope: None))
    with pytest.raises(ValueError, match="caller scope"):
        arguments = {"id": "foreign"}
        if tool.endswith("update"):
            arguments["text"] = "replacement"
        plugin.tools.dispatch(runtime, tool, arguments, object(), "session")


def test_real_writer_lease_excludes_same_home_destination(plugin, tmp_path):
    cfg = {"qdrant": {"mode": "embedded", "path": str(tmp_path / "data"), "collection": "fixture"}}
    lease = plugin.cli.WriterLease.for_config(tmp_path / "profile", cfg)
    try:
        with pytest.raises(plugin.cli.WriterBusyError):
            plugin.cli.WriterLease.for_config(tmp_path / "profile", cfg)
        # Different homes have different leases: this is not a distributed lock.
        other = plugin.cli.WriterLease.for_config(tmp_path / "other-profile", cfg)
        other.close()
    finally:
        lease.close()
    recovered = plugin.cli.WriterLease.for_config(tmp_path / "profile", cfg)
    recovered.close()


def test_inventory_result_shapes_and_export_are_scoped(plugin, tmp_path):
    seen = []
    def count(scope):
        seen.append(scope.as_dict() if scope else None)
        return 0
    runtime = SimpleNamespace(
        store=SimpleNamespace(collection="fixture", count=count, scroll=lambda scope: iter(())),
        ledger=SimpleNamespace(stats=lambda: {"operations": {"PENDING": 2, "FAILED": 1}}),
    )
    args = parser_for(plugin).parse_args(["list", "--user", "u", "--agent", "a"])
    result = plugin.cli.inventory_list(runtime, args)
    assert seen == [{"user_id": "u", "agent_id": "a"}]
    assert result["scope"] == seen[0]
    assert result["count"] == {"total": 0, "returned": 0, "truncated": False}
    assert result["ledger"] == {"pending_operations": 2, "failed_operations": 1}
    assert result["memories"] == []
    output = tmp_path / "export.json"
    args = parser_for(plugin).parse_args(["export", "--user", "u", "--output", str(output)])
    result = plugin.cli.inventory_export(runtime, args)
    assert result == {"collection": "fixture", "scope": {"user_id": "u", "agent_id": None},
                      "count": 0, "output": str(output)}
    assert output.is_file()
    with pytest.raises(plugin.cli.ExportTargetExistsError):
        plugin.cli.inventory_export(runtime, args)
