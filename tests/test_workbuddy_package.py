"""WorkBuddy distribution invariants in disposable repositories."""
import importlib.util
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
VERSION = yaml.safe_load((ROOT / 'qdrant-memory/SKILL.md').read_text().split('---', 2)[1])['metadata']['version']
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_skills import SKILLS


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'integrations/workbuddy' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    for name in (*SKILLS, 'integrations', 'scripts'):
        for relative in git(ROOT, 'ls-files', name).splitlines():
            dest = root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, dest)
    subprocess.run(['git', 'init', '-b', 'main', str(root)], check=True, capture_output=True)
    git(root, 'add', '.')
    git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '-m', 'fixture')
    return root


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def test_reproducible_complete_package_and_canonical_integrity(repo, tmp_path):
    b = load('build')
    before = (repo / 'qdrant-memory/SKILL.md').read_bytes()
    first, checksum = b.build(repo, tmp_path / 'one', skill_name='qdrant-memory')
    second, _ = b.build(repo, tmp_path / 'two', skill_name='qdrant-memory')
    assert first.read_bytes() == second.read_bytes()
    assert checksum.read_text() == f'{b.digest(first)}  {first.name}\n'
    assert f'v{VERSION}-preview.zip' in first.name
    assert before == (repo / 'qdrant-memory/SKILL.md').read_bytes()
    with zipfile.ZipFile(first) as z:
        names = z.namelist()
        assert all(n.startswith('qdrant-memory/') for n in names)
        assert sum(n.endswith('SKILL.md') for n in names) == 1
        assert 'qdrant-memory/LICENSE' in names
        generated = z.read('qdrant-memory/SKILL.md')
        data, body = b.parse_skill(generated)
        committed = subprocess.check_output(['git', '-C', str(repo), 'show', ':qdrant-memory/SKILL.md'])
        canonical, original_body = b.parse_skill(committed)
        assert body == original_body
        assert data['description'] == data['description_en'] == canonical['description']
        assert data['version'] == canonical['metadata']['version']
        assert all(data[k] for k in ('author', 'description_zh'))
        for path in (repo / 'qdrant-memory').rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.name != 'SKILL.md':
                source = subprocess.check_output(['git', '-C', str(repo), 'show', ':' + path.relative_to(repo).as_posix()])
                assert z.read(path.relative_to(repo).as_posix()) == source
    b.verify_archive(first, b.package_files(repo, 'qdrant-memory'))


def test_local_junk_never_enters_package(repo, tmp_path):
    for name in ('.env', 'scripts/key.pem', 'scripts/state.db', 'scripts/private-config.json'):
        (repo / 'qdrant-memory' / name).write_text('secret')
    archive, _ = load('build').build(repo, tmp_path / 'out', skill_name='qdrant-memory')
    with zipfile.ZipFile(archive) as z:
        assert not any(n.endswith(('.env', '.pem', '.db', 'private-config.json')) for n in z.namelist())


@pytest.mark.parametrize('mutation', ['version', 'link', 'symlink', 'missing', 'tracked-secret'])
def test_invalid_sources_fail_closed(repo, tmp_path, mutation):
    p = repo / 'qdrant-memory/SKILL.md'
    if mutation == 'version':
        p.write_text(p.read_text().replace(f'"{VERSION}"', '"../bad"'))
    elif mutation == 'link':
        p.write_text(p.read_text() + '\n[escape](../outside.md)\n')
    elif mutation == 'symlink':
        resource = repo / 'qdrant-memory/references/usage.md'
        resource.unlink()
        resource.symlink_to(p)
    elif mutation == 'missing':
        (repo / 'qdrant-memory/references/usage.md').unlink()
    else:
        (repo / 'qdrant-memory/scripts/key.pem').write_text('private')
        git(repo, 'add', 'qdrant-memory/scripts/key.pem')
    with pytest.raises(ValueError):
        load('build').build(repo, tmp_path / 'out', skill_name='qdrant-memory')


@pytest.mark.parametrize('tag', ['skills-20260230.1', 'skills-20261014.0', 'skills-20261014.01', '../bad', 'v0.2.4'])
def test_invalid_snapshot_tags(tag):
    with pytest.raises(ValueError):
        load('build').validate_tag(tag)


def test_output_collision_and_corrupt_archive(repo, tmp_path):
    b = load('build')
    archive, _ = b.build(repo, tmp_path / 'out', 'skills-20261014.1', skill_name='qdrant-memory')
    assert archive.name == f'qdrant-memory-workbuddy-skill-v{VERSION}-skills-20261014.1.zip'
    b.build(repo, tmp_path / 'out', 'skills-20261014.1', skill_name='qdrant-memory')
    archive.write_bytes(b'corrupt')
    with pytest.raises(ValueError):
        b.build(repo, tmp_path / 'out', 'skills-20261014.1', skill_name='qdrant-memory')


def test_workflow_permissions_and_triggers():
    def workflow(name):
        return yaml.load((ROOT / '.github/workflows' / name).read_text(), Loader=yaml.BaseLoader)
    preview = workflow('workbuddy-preview.yml')
    release = workflow('workbuddy-release.yml')
    assert preview['permissions'] == {'contents': 'read'}
    assert set(preview['on']) == {'push', 'pull_request', 'workflow_dispatch'}
    assert preview['on']['workflow_dispatch']['inputs']['skill'] == {
        'description': 'Build one catalog skill only (empty builds all catalog skills)',
        'required': 'false', 'default': '', 'type': 'string'}
    assert release['on'] == {'push': {'tags': ['skills-*']}}
    assert release['permissions'] == {'contents': 'read'}
    assert release['jobs']['draft']['permissions'] == {'contents': 'write'}
    assert release['jobs']['draft']['needs'] == 'build'
    assert release['concurrency']['cancel-in-progress'] == 'false'
    assert 'published' not in release['on']


@pytest.mark.parametrize('mutation', ['encoding', 'untracked-link', 'escape-link', 'invalid-adapter'])
def test_encoding_and_packaged_reference_checks(repo, tmp_path, mutation):
    p = repo / 'qdrant-memory/references/usage.md'
    if mutation == 'encoding':
        p.write_bytes(b'\xff')
    elif mutation == 'untracked-link':
        (p.parent / 'local.md').write_text('not tracked')
        p.write_text(p.read_text() + '\n[local](local.md)\n')
    elif mutation == 'escape-link':
        p.write_text(p.read_text() + '\n[escape](%2e%2e/%2e%2e/outside.md)\n')
    else:
        (repo / 'integrations/workbuddy/metadata.json').write_text('{"author": "cnkang", "version": "9.9.9"}')
    with pytest.raises(ValueError):
        load('build').build(repo, tmp_path / 'out', skill_name='qdrant-memory')


def test_archive_tampering_and_output_symlink(repo, tmp_path):
    b = load('build')
    archive, _ = b.build(repo, tmp_path / 'out', skill_name='qdrant-memory')
    with zipfile.ZipFile(archive, 'a') as z:
        z.writestr('../escape', b'bad')
    with pytest.raises(ValueError):
        b.verify_archive(archive, b.package_files(repo, 'qdrant-memory'))
    linked = tmp_path / 'linked'
    linked.symlink_to(tmp_path / 'out', target_is_directory=True)
    with pytest.raises(ValueError):
        b.build(repo, linked, skill_name='qdrant-memory')


def test_check_cli_uses_disposable_output():
    result = subprocess.run([sys.executable, str(ROOT / 'integrations/workbuddy/build.py'), '--check'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_crlf_checkout_does_not_change_archive(repo, tmp_path):
    b = load('build')
    first, _ = b.build(repo, tmp_path / 'lf', skill_name='qdrant-memory')
    for p in (repo / 'qdrant-memory').rglob('*'):
        if p.is_file():
            p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    before = (repo / 'qdrant-memory/SKILL.md').read_bytes()
    second, _ = b.build(repo, tmp_path / 'crlf', skill_name='qdrant-memory')
    assert first.read_bytes() == second.read_bytes()
    assert (repo / 'qdrant-memory/SKILL.md').read_bytes() == before


def test_unstaged_resource_change_is_not_silently_ignored(repo, tmp_path):
    p = repo / 'qdrant-memory/references/usage.md'
    p.write_bytes(p.read_bytes() + b'\nNew instruction\n')
    with pytest.raises(ValueError, match='Unstaged'):
        load('build').build(repo, tmp_path / 'out', skill_name='qdrant-memory')


def test_entire_catalog_has_independent_complete_packages(repo, tmp_path):
    b = load('build')
    first = b.build_all(repo, tmp_path / 'one', 'skills-20261014.1')
    second = b.build_all(repo, tmp_path / 'two', 'skills-20261014.1')
    assert len(first) == len(SKILLS) * 2
    assert [p.read_bytes() for p in first] == [p.read_bytes() for p in second]
    for name in SKILLS:
        source = subprocess.check_output(['git', '-C', str(repo), 'show', f':{name}/SKILL.md'])
        canonical, body = b.parse_skill(source)
        filename = f'{name}-workbuddy-skill-v{canonical["metadata"]["version"]}-skills-20261014.1.zip'
        archive = tmp_path / 'one' / filename
        with zipfile.ZipFile(archive) as z:
            assert all(p.startswith(name + '/') for p in z.namelist())
            generated, generated_body = b.parse_skill(z.read(f'{name}/SKILL.md'))
            assert generated_body == body
            assert generated['version'] == canonical['metadata']['version']
            assert generated['description_en'] == canonical['description']
            tracked = git(repo, 'ls-files', name).splitlines()
            expected = {p for p in tracked if not p.endswith('/.gitignore')}
            assert set(z.namelist()) == expected
            for path in expected - {f'{name}/SKILL.md'}:
                assert z.read(path) == subprocess.check_output(['git', '-C', str(repo), 'show', ':' + path])
        assert archive.with_suffix('.zip.sha256').read_text() == f'{b.digest(archive)}  {filename}\n'


def test_new_catalog_skill_needs_no_builder_or_workflow_edit(repo, tmp_path, monkeypatch):
    import json
    b = load('build')
    name = 'future-skill'
    shutil.copytree(repo / 'qdrant-memory', repo / name)
    p = repo / name / 'SKILL.md'
    p.write_bytes(p.read_bytes().replace(b'name: qdrant-memory', b'name: future-skill'))
    git(repo, 'add', name)
    monkeypatch.setattr(b, 'SKILLS', (*SKILLS, name))
    metadata = repo / 'integrations/workbuddy/metadata.json'
    data = json.loads(metadata.read_text(encoding='utf-8'))
    data[name] = {'description_zh': '未来技能说明', 'author': 'cnkang'}
    metadata.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    paths = b.build_all(repo, tmp_path / 'out')
    assert len(paths) == (len(SKILLS) + 1) * 2
    assert any(p.name.startswith('future-skill-workbuddy-') for p in paths)


@pytest.mark.parametrize('change', ['missing', 'extra'])
def test_adapter_coverage_fails_before_any_package_is_written(repo, tmp_path, change):
    import json
    b = load('build')
    p = repo / 'integrations/workbuddy/metadata.json'
    metadata = json.loads(p.read_text(encoding='utf-8'))
    if change == 'missing':
        metadata.pop(SKILLS[-1])
    else:
        metadata['unknown-skill'] = {'description_zh': '未知技能', 'author': 'cnkang'}
    p.write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(ValueError, match='catalog'):
        b.build_all(repo, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_selection_and_inherited_author(repo, tmp_path):
    b = load('build')
    paths = b.build_all(repo, tmp_path / 'out', skill_names=['dev-jev', 'sonarcloud-link-inspector'])
    assert len(paths) == 4
    assert not any(p.name.startswith('qdrant-memory') for p in paths)
    with zipfile.ZipFile(paths[0]) as z:
        data, _ = b.parse_skill(z.read('dev-jev/SKILL.md'))
        assert data['author'] == 'Kang, Hermes Agent'
    for names in (['../escape'], ['dev-jev', 'dev-jev'], []):
        with pytest.raises(ValueError):
            b.build_all(repo, tmp_path / 'invalid', skill_names=names)


def test_binary_assets_preserve_bytes_and_reject_unstaged_changes(repo, tmp_path):
    b = load('build')
    p = repo / 'qdrant-memory/assets/diagram.png'
    p.parent.mkdir()
    content = b'\x89PNG\r\n\xff\x00\n'
    p.write_bytes(content)
    git(repo, 'add', str(p.relative_to(repo)))
    archive, _ = b.build(repo, tmp_path / 'out', skill_name='qdrant-memory')
    with zipfile.ZipFile(archive) as z:
        assert z.read('qdrant-memory/assets/diagram.png') == content
    p.write_bytes(content.replace(b'\r\n', b'\n'))
    with pytest.raises(ValueError, match='Unstaged'):
        b.build(repo, tmp_path / 'bad', skill_name='qdrant-memory')
