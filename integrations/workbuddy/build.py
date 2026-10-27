#!/usr/bin/env python3
"""Build and verify a reproducible WorkBuddy Skill ZIP; never install a runtime."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_skills import SKILLS, validate_skill, check_target, LINK, RESOURCE


def validate_tag(tag: str) -> str:
    match = re.fullmatch(r'skills-([0-9]{8})\.([1-9][0-9]*)', tag)
    if not match:
        raise ValueError('Snapshot tag must be skills-YYYYMMDD.N, N >= 1')
    try:
        datetime.datetime.strptime(match[1], '%Y%m%d')
    except ValueError as exc:
        raise ValueError('Snapshot tag has an invalid calendar date') from exc
    return tag


def parse_skill(raw: bytes) -> tuple[dict, bytes]:
    raw.decode('utf-8', errors='strict')
    if not raw.startswith(b'---\n') or b'\n---\n' not in raw[4:]:
        raise ValueError('Missing YAML frontmatter')
    header, body = raw[4:].split(b'\n---\n', 1)
    data = yaml.safe_load(header.decode('utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Frontmatter must be a mapping')
    version = data.get('metadata', {}).get('version')
    if not isinstance(version, str) or not re.fullmatch(
        r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?', version
    ):
        raise ValueError('Invalid canonical metadata.version')
    # SemVer numeric prerelease identifiers may not have leading zeroes.
    for part in version.split('+', 1)[0].partition('-')[2].split('.'):
        if part.isdigit() and len(part) > 1 and part.startswith('0'):
            raise ValueError('Invalid canonical metadata.version prerelease')
    return data, body


def safe_resource(name: str) -> bool:
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name:
        return False
    if any(p.startswith('.') or p in {'__pycache__', 'node_modules', 'venv', 'secrets'} for p in path.parts):
        return False
    if name in {'SKILL.md', 'LICENSE', 'README.md', 'requirements.txt'}:
        return True
    if path.name.startswith('test_') or path.name == 'conftest.py':
        return False
    return (path.parts[0] in {'references', 'scripts', 'assets', 'agents', 'examples', 'templates'} and
            path.suffix in {'.md', '.py', '.sh', '.js', '.ts', '.json', '.yaml', '.yml', '.toml', '.txt', '.template', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.csv', '.sql', '.css', '.html'} and
            not any(word in path.stem.lower() for word in ('secret', 'credential', 'private-key')))


def indexed_resources(root: Path, skill_name: str) -> dict[str, tuple[bytes, int]]:
    records = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--stage', '-z', '--', skill_name])
    selected = []
    for record in records.split(b'\0'):
        if not record:
            continue
        info, path_bytes = record.split(b'\t', 1)
        mode, oid, stage = info.decode().split()
        name = path_bytes.decode('utf-8')
        relative = PurePosixPath(name).relative_to(skill_name).as_posix()
        if relative == '.gitignore':
            continue  # Git development configuration is not a runtime resource.
        if stage != '0' or mode not in {'100644', '100755'}:
            raise ValueError(f'Nonregular or unresolved tracked resource: {name}')
        if not safe_resource(relative):
            raise ValueError(f'Unapproved tracked resource: {name}')
        path = root / name
        if any(p.is_symlink() for p in [path, *path.parents]) or not path.is_file():
            raise ValueError(f'Missing or symlink resource: {name}')
        selected.append((name, mode, oid))
    if not selected:
        raise ValueError('No tracked canonical resources')
    batch = subprocess.check_output(['git', '-C', str(root), 'cat-file', '--batch'],
                                    input=''.join(oid + '\n' for _, _, oid in selected).encode('ascii'))
    stream = io.BytesIO(batch)
    files = {}
    for name, mode, oid in selected:
        header = stream.readline().decode('ascii').split()
        if len(header) != 3 or header[:2] != [oid, 'blob']:
            raise ValueError(f'Invalid Git source blob: {name}')
        content = stream.read(int(header[2]))
        if stream.read(1) != b'\n':
            raise ValueError('Invalid Git batch response')
        binary = Path(name).suffix in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf'}
        if not binary:
            content.decode('utf-8', errors='strict')
        # Ignore only the checkout's LF/CRLF translation, never actual edits.
        working = (root / name).read_bytes()
        if (working if binary else working.replace(b'\r\n', b'\n')) != (content if binary else content.replace(b'\r\n', b'\n')):
            raise ValueError(f'Unstaged canonical resource change: {name}; stage reviewed edits before previewing')
        files[name] = (content, 0o755 if mode == '100755' else 0o644)
    return files


def adapter_metadata(root: Path) -> dict:
    path = root / 'integrations/workbuddy/metadata.json'
    if path.is_symlink():
        raise ValueError('Adapter metadata may not be a symlink')
    metadata = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(metadata, dict) or set(metadata) != set(SKILLS):
        raise ValueError('WorkBuddy metadata must cover exactly the controlled skill catalog; add per-skill description_zh and author')
    for name, adapter in metadata.items():
        if not isinstance(adapter, dict) or 'description_zh' not in adapter or set(adapter) - {'description_zh', 'author'} or not all(
            isinstance(v, str) and v.strip() for v in adapter.values()
        ):
            raise ValueError(f'{name}: adapter requires description_zh and permits only an optional author override')
        if not re.search('[\u3400-\u9fff]', adapter['description_zh']):
            raise ValueError(f'{name}: description_zh must contain Chinese text')
    return metadata


def package_files(root: Path, skill_name: str) -> dict[str, tuple[bytes, int]]:
    if skill_name not in SKILLS:
        raise ValueError(f'Skill is not in the controlled catalog: {skill_name}')
    adapter = adapter_metadata(root)[skill_name]
    skill = root / skill_name
    errors = validate_skill(skill)
    if errors:
        raise ValueError('\n'.join(errors))
    files = indexed_resources(root, skill_name)
    if not {f'{skill_name}/SKILL.md', f'{skill_name}/LICENSE'} <= files.keys():
        raise ValueError('Canonical SKILL.md and LICENSE must be tracked')
    raw = files[f'{skill_name}/SKILL.md'][0]
    data, body = parse_skill(raw)
    author = adapter.get('author', data.get('author', data['metadata'].get('author')))
    if not isinstance(author, str) or not author.strip():
        raise ValueError(f'{skill_name}: author must come from canonical metadata or WorkBuddy adapter')
    data.update(adapter)
    data['author'] = author
    data['description_en'] = data['description']
    data['version'] = data['metadata']['version']
    generated = b'---\n' + yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode('utf-8') + b'---\n' + body
    files[f'{skill_name}/SKILL.md'] = (generated, files[f'{skill_name}/SKILL.md'][1])
    # Validate links against only the selected package, not excluded local files.
    with tempfile.TemporaryDirectory() as temp:
        extracted = Path(temp) / skill_name
        for name, (content, _) in files.items():
            p = Path(temp) / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
        errors = []
        for p in extracted.rglob('*.md'):
            text = p.read_text(encoding='utf-8')
            for target in LINK.findall(text):
                check_target(extracted, p, target, errors)
            if p.name == 'SKILL.md':
                for target in RESOURCE.findall(text):
                    check_target(extracted, p, target.rstrip('.'), errors)
        if errors:
            raise ValueError('\n'.join(errors))
    if parse_skill(files[f'{skill_name}/SKILL.md'][0])[1] != body:
        raise ValueError('Canonical Markdown body changed')
    return files


def archive_bytes(files: dict) -> bytes:
    stream = io.BytesIO()
    # STORE avoids differences between zlib versions across runners.
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, (content, mode) in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100000 | mode) << 16
            archive.writestr(info, content)
    return stream.getvalue()


def verify_archive(path: Path, files: dict) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(files) or archive.testzip():
            raise ValueError('ZIP manifest or CRC differs from expected source')
        for entry in archive.infolist():
            content, mode = files[entry.filename]
            if archive.read(entry) != content or entry.external_attr >> 16 != 0o100000 | mode:
                raise ValueError(f'ZIP resource differs: {entry.filename}')
    if path.read_bytes() != archive_bytes(files):
        raise ValueError('ZIP is not the deterministic source archive')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, content: bytes) -> None:
    if path.is_symlink():
        raise ValueError(f'Refusing output symlink: {path}')
    try:
        with path.open('xb') as stream:
            stream.write(content)
    except FileExistsError:
        if path.read_bytes() != content:
            raise ValueError(f'Refusing to overwrite different output: {path}')


def build(root: Path, output: Path, snapshot_tag: str | None = None, *, skill_name: str) -> tuple[Path, Path]:
    suffix = validate_tag(snapshot_tag) if snapshot_tag else 'preview'
    files = package_files(root, skill_name)
    return write_package(root, output, suffix, skill_name, files)


def write_package(root: Path, output: Path, suffix: str, skill_name: str, files: dict) -> tuple[Path, Path]:
    data, _ = parse_skill(files[f'{skill_name}/SKILL.md'][0])
    output = output.absolute()
    if any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError('Output directory must not traverse symlinks')
    # Generated SKILL.md must never become another discoverable repository skill.
    if output.is_relative_to(root.resolve()) and output != root.resolve() / 'dist/workbuddy':
        raise ValueError('Repository output must be dist/workbuddy')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'{skill_name}-workbuddy-skill-v{data["version"]}-{suffix}.zip'
    checksum = archive.with_suffix('.zip.sha256')
    write_once(archive, archive_bytes(files))
    verify_archive(archive, files)
    write_once(checksum, f'{digest(archive)}  {archive.name}\n'.encode('utf-8'))
    return archive, checksum


def build_all(root: Path, output: Path, snapshot_tag: str | None = None, skill_names=None) -> list[Path]:
    suffix = validate_tag(snapshot_tag) if snapshot_tag else 'preview'
    names = list(SKILLS if skill_names is None else skill_names)
    if not names or len(names) != len(set(names)):
        raise ValueError('Select at least one unique catalog skill')
    # Validate every selected source before creating output or contacting GitHub.
    prepared = [(name, package_files(root, name)) for name in names]
    return [path for name, files in prepared for path in write_package(root, output, suffix, name, files)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Build and verify in a disposable directory')
    parser.add_argument('--snapshot-tag')
    parser.add_argument('--skill', action='append', choices=SKILLS, help='Build only this catalog skill; repeat to select several. Default: all skills')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist/workbuddy')
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory() as temp:
            build_all(ROOT, Path(temp).resolve(), args.snapshot_tag, args.skill)
        print('WorkBuddy packages, canonical bodies and checksums verified')
    else:
        for path in build_all(ROOT, args.output_dir, args.snapshot_tag, args.skill):
            print(path)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, yaml.YAMLError, zipfile.BadZipFile) as exc:
        raise SystemExit(f'WorkBuddy build failed: {exc}')
