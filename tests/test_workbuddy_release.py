"""Exercise release state transitions without making real tags or releases."""
import subprocess

import pytest

from test_workbuddy_package import ROOT, VERSION, git, load, repo


def tag_repo(root, annotation='qdrant-memory 0.2.4'):
    # Include every catalog version from this fixture's checkout.
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    from validate_skills import SKILLS, frontmatter
    notes = '\n'.join(f'{name} {frontmatter(ROOT / name / "SKILL.md")["metadata"]["version"]}' for name in SKILLS)
    for name in SKILLS:
        if not (root / name).exists():
            import shutil
            shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns('__pycache__'))
    git(root, 'add', '.')
    git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '--allow-empty', '-m', 'catalog')
    git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'tag', '-a', 'skills-20261014.1', '-m', notes if annotation else 'no versions')


def test_exact_annotated_merged_source(repo):
    tag_repo(repo)
    r = load('release')
    sha, notes = r.validate_source(repo, 'skills-20261014.1', 'refs/heads/main')
    assert sha == git(repo, 'rev-parse', 'HEAD')
    assert f'qdrant-memory {VERSION}' in notes
    git(repo, 'switch', '-c', 'unmerged')
    (repo / 'extra').write_text('change')
    git(repo, 'add', '.')
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '-m', 'unmerged')
    with pytest.raises(ValueError, match='checkout'):
        r.validate_source(repo, 'skills-20261014.1', 'refs/heads/main')


def test_unmerged_lightweight_and_bad_annotation(repo):
    r = load('release')
    git(repo, 'tag', 'skills-20261014.1')
    with pytest.raises(ValueError, match='annotated'):
        r.validate_source(repo, 'skills-20261014.1', 'refs/heads/main')
    git(repo, 'tag', '-d', 'skills-20261014.1')
    tag_repo(repo, annotation='')
    with pytest.raises(ValueError, match='annotation'):
        r.validate_source(repo, 'skills-20261014.1', 'refs/heads/main')
    git(repo, 'update-ref', 'refs/heads/old-main', 'HEAD~1')
    with pytest.raises(ValueError, match='main'):
        r.validate_source(repo, 'skills-20261014.1', 'refs/heads/old-main')


class FakeAPI:
    def __init__(self, draft=True, exists=True):
        self.release = {'id': 1, 'draft': draft, 'tag_name': 'skills-20261014.1'} if exists else None
        self.assets = {}
        self.created = 0
        self.uploaded = []

    def find_release(self, tag): return self.release
    def create_draft(self, tag, sha, notes):
        self.created += 1
        self.release = {'id': 1, 'draft': True, 'tag_name': tag}
        return self.release
    def get_release(self, release_id): return self.release
    def list_assets(self, release_id): return [{'id': name, 'name': name} for name in self.assets]
    def download_asset(self, asset): return self.assets[asset['id']]
    def upload_asset(self, release, path):
        self.uploaded.append(path.name)
        self.assets[path.name] = path.read_bytes()


def test_create_draft_and_idempotent_retry(tmp_path):
    paths = [tmp_path / 'a.zip', tmp_path / 'a.zip.sha256']
    for p in paths: p.write_bytes(b'data')
    api = FakeAPI(exists=False)
    r = load('release')
    r.attach_assets(api, 'skills-20261014.1', 'sha', 'notes', paths)
    r.attach_assets(api, 'skills-20261014.1', 'sha', 'notes', paths)
    assert api.created == 1 and len(api.uploaded) == 2 and api.release['draft']


@pytest.mark.parametrize('draft', [True, False])
def test_mismatch_never_modifies_assets(tmp_path, draft):
    p = tmp_path / 'a.zip'
    p.write_bytes(b'expected')
    api = FakeAPI(draft=draft)
    api.assets[p.name] = b'original'
    with pytest.raises(ValueError, match='differs'):
        load('release').attach_assets(api, 'skills-20261014.1', 'sha', 'notes', [p])
    assert api.assets[p.name] == b'original' and not api.uploaded


def test_published_missing_assets_read_only(tmp_path):
    p = tmp_path / 'a.zip'
    p.write_bytes(b'data')
    api = FakeAPI(draft=False)
    with pytest.raises(ValueError, match='Published'):
        load('release').attach_assets(api, 'skills-20261014.1', 'sha', 'notes', [p])
    assert not api.uploaded
    api.assets[p.name] = p.read_bytes()
    load('release').attach_assets(api, 'skills-20261014.1', 'sha', 'notes', [p])
    assert not api.uploaded


def test_partial_upload_failure_is_recoverable(tmp_path):
    paths = [tmp_path / 'a.zip', tmp_path / 'a.zip.sha256']
    for p in paths: p.write_bytes(b'data')
    api = FakeAPI()
    normal_upload = api.upload_asset
    def failing_upload(release, path):
        if path.name.endswith('sha256'):
            raise RuntimeError('simulated upload interruption')
        normal_upload(release, path)
    api.upload_asset = failing_upload
    r = load('release')
    with pytest.raises(RuntimeError):
        r.attach_assets(api, 'skills-20261014.1', 'sha', 'notes', paths)
    assert api.assets == {'a.zip': b'data'} and api.release['draft']
    api.upload_asset = normal_upload
    r.attach_assets(api, 'skills-20261014.1', 'sha', 'notes', paths)
    assert api.uploaded == ['a.zip', 'a.zip.sha256']


def test_publication_during_preflight_stops_upload(tmp_path):
    p = tmp_path / 'a.zip'
    p.write_bytes(b'data')
    api = FakeAPI()
    api.get_release = lambda _: {**api.release, 'draft': False}
    with pytest.raises(ValueError, match='Draft'):
        load('release').attach_assets(api, 'skills-20261014.1', 'sha', 'notes', [p])
    assert not api.uploaded


def test_preflight_both_assets_before_any_upload(tmp_path):
    first, second = tmp_path / 'a.zip', tmp_path / 'a.zip.sha256'
    first.write_bytes(b'zip')
    second.write_bytes(b'sum')
    api = FakeAPI()
    api.assets[second.name] = b'mismatch'
    with pytest.raises(ValueError, match='differs'):
        load('release').attach_assets(api, 'skills-20261014.1', 'sha', 'notes', [first, second])
    assert not api.uploaded


def test_http_api_pagination_and_write_contract(tmp_path):
    r = load('release')
    api = r.GitHubAPI('cnkang/skills', 'test-token')
    calls = []
    class Response:
        def __init__(self, value): self.value = value
        def json(self): return self.value
    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == 'GET':
            page = kwargs['params']['page']
            return Response([{'tag_name': 'older', 'id': i} for i in range(100)] if page == 1 else [{'tag_name': 'skills-20261014.1', 'id': 101}])
        return Response({'id': 1, 'draft': True})
    api.request = request
    assert api.find_release('skills-20261014.1')['id'] == 101
    api.create_draft('skills-20261014.1', 'exact-sha', 'English annotation')
    assert calls[-1][2]['json'] == {'tag_name': 'skills-20261014.1', 'target_commitish': 'exact-sha', 'name': 'skills-20261014.1', 'body': 'English annotation', 'draft': True, 'prerelease': False}
    p = tmp_path / 'safe.zip'
    p.write_bytes(b'data')
    api.upload_asset({'id': 1}, p)
    assert calls[-1][0] == 'POST'
    assert calls[-1][1] == 'https://uploads.github.com/repos/cnkang/skills/releases/1/assets?name=safe.zip'
    assert all(method in {'GET', 'POST'} for method, _, _ in calls)


def test_full_catalog_release_assets_and_global_preflight(repo, tmp_path):
    b, r = load('build'), load('release')
    paths = b.build_all(repo, tmp_path / 'out', 'skills-20261014.1')
    api = FakeAPI(exists=False)
    r.attach_assets(api, 'skills-20261014.1', 'sha', 'notes', paths)
    r.attach_assets(api, 'skills-20261014.1', 'sha', 'notes', paths)
    assert len(api.assets) == len(paths) == len(b.SKILLS) * 2
    assert api.created == 1 and len(api.uploaded) == len(paths)
    mismatch = FakeAPI()
    mismatch.assets[paths[-1].name] = b'mismatch in final catalog asset'
    with pytest.raises(ValueError, match='differs'):
        r.attach_assets(mismatch, 'skills-20261014.1', 'sha', 'notes', paths)
    assert not mismatch.uploaded
