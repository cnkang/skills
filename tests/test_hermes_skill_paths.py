"""Optional real Hermes Hub parser/install pipeline with local GitHub transport.

No GitHub publication, live provider or personal profile is involved.
"""
import importlib
import io
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def host(tmp_path, monkeypatch):
    configured = os.environ.get("HERMES_SKILL_HOST_ROOT")
    if not configured:
        pytest.skip("Optional Hermes Hub fixture needs HERMES_SKILL_HOST_ROOT; no live host claim")
    for key in ("HOME", "USERPROFILE", "HERMES_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    monkeypatch.syspath_prepend(configured)
    github = importlib.import_module("tools.skills_hub_github")
    hub = importlib.import_module("tools.skills_hub")
    cli = importlib.import_module("hermes_cli.skills_hub")
    source = github.GitHubSource(auth=None)
    source.taps = [{"repo": "cnkang/skills", "path": ""}]
    entries = [{"path": path.relative_to(ROOT).as_posix(), "type": "blob", "mode": "100644"}
               for name in ("qdrant-memory",)
               for path in (ROOT / name).rglob("*") if path.is_file()]

    def tree(repo):
        assert repo == "cnkang/skills"
        source._tree_revisions[repo] = "local-fixture"
        return "local-fixture", entries

    def read_bytes(repo, path, **kwargs):
        assert repo == "cnkang/skills"
        file = ROOT / path
        return file.read_bytes() if file.is_file() else None

    def contents(url, **kwargs):
        import httpx
        prefix = "https://api.github.com/repos/cnkang/skills/contents/"
        assert url.startswith(prefix)
        path = ROOT / url[len(prefix):]
        if path.is_dir():
            return httpx.Response(200, json=[{"name": p.name, "type": "dir"}
                                            for p in path.iterdir() if p.is_dir()])
        return httpx.Response(404)

    monkeypatch.setattr(source, "_get_repo_tree", tree)
    monkeypatch.setattr(source, "_fetch_file_bytes", read_bytes)
    monkeypatch.setattr(source, "_fetch_file_content", lambda repo, path, **kw:
                        read_bytes(repo, path).decode() if (ROOT / path).is_file() else None)
    monkeypatch.setattr(source, "_github_get", contents)
    monkeypatch.setattr(cli, "_sources", lambda: [source])
    # Optional remote advisory is outside offline install acceptance. The actual
    # local quarantine/security scan and installation remain enabled.
    monkeypatch.setattr(cli, "_print_tier1_advisory", lambda *args: None)
    return source, hub, cli


@pytest.mark.parametrize("name", ["qdrant-memory"])
def test_direct_root_path_install(host, name):
    from rich.console import Console
    source, hub, cli = host
    identifier = "cnkang/skills/" + name
    assert source.fetch(identifier).name == name
    output = io.StringIO()
    assert cli.do_install(identifier, console=Console(file=output),
                          skip_confirm=True, invalidate_cache=False, source_id="github") is True, output.getvalue()
    installed = hub._skills_dir() / name
    assert (installed / "LICENSE").read_bytes() == (ROOT / name / "LICENSE").read_bytes()
    assert (installed / "SKILL.md").read_bytes() == (ROOT / name / "SKILL.md").read_bytes()
    for path in (ROOT / name / "references").glob("*.md"):
        assert (installed / "references" / path.name).read_bytes() == path.read_bytes()
    for path in (ROOT / name / "scripts").glob("*.py"):
        assert (installed / "scripts" / path.name).read_bytes() == path.read_bytes()
    assert hub.HubLockFile().get_installed(name)["identifier"] == identifier


def test_default_tap_misses_root_and_empty_path_discovers(host):
    source, hub, cli = host
    manager = hub.TapsManager()
    assert manager.add("cnkang/skills")
    assert manager.load() == [{"repo": "cnkang/skills", "path": "skills/"}]
    assert source._list_skills_in_repo("cnkang/skills", "skills/") == []
    manager.save([{"repo": "cnkang/skills", "path": ""}])
    assert manager.load()[0]["path"] == ""
    found = source._list_skills_in_repo("cnkang/skills", "")
    assert "qdrant-memory" in {item.name for item in found}
