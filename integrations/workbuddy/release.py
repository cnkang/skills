#!/usr/bin/env python3
"""Validate a merged annotated snapshot and attach assets before publication."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import ROOT, build_all, validate_tag
from validate_skills import SKILLS, frontmatter


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def validate_source(root: Path, tag: str, main_ref: str = 'refs/remotes/origin/main') -> tuple[str, str]:
    validate_tag(tag)
    ref = f'refs/tags/{tag}'
    if git(root, 'cat-file', '-t', ref) != 'tag':
        raise ValueError('Snapshot must use an annotated tag')
    sha = git(root, 'rev-parse', f'{ref}^{{commit}}')
    if git(root, 'rev-parse', 'HEAD') != sha:
        raise ValueError('Current checkout does not match snapshot commit')
    if subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', sha, main_ref], capture_output=True).returncode:
        raise ValueError('Snapshot commit is not merged into main')
    if git(root, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Release checkout has tracked changes')
    notes = git(root, 'for-each-ref', '--format=%(contents)', ref)
    for name in SKILLS:
        version = frontmatter(root / name / 'SKILL.md')['metadata']['version']
        # Accept a catalog line in prose/bullets/tables without accepting a
        # substring version (e.g. 0.2.4 must not match 0.2.40).
        if not any(re.search(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])', line) and
                   re.search(r'(?<![\w.+-])v?' + re.escape(version) + r'(?![\w.+-])', line)
                   for line in notes.splitlines()):
            raise ValueError(f'Tag annotation must list {name} {version}')
    return sha, notes


class GitHubAPI:
    """Small REST adapter; only create-draft and upload are write operations."""
    def __init__(self, repository: str, token: str):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid GitHub repository')
        self.base = f'https://api.github.com/repos/{repository}'
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {token}',
                                     'Accept': 'application/vnd.github+json',
                                     'X-GitHub-Api-Version': '2022-11-28'})

    def request(self, method, url, **kwargs):
        response = self.session.request(method, url, timeout=120, **kwargs)
        if not response.ok:
            # Do not print response bodies, authentication or release contents.
            raise ValueError(f'GitHub {method} failed: HTTP {response.status_code}; inspect the workflow and retry without replacing assets')
        return response

    def pages(self, url):
        page = 1
        result = []
        while True:
            items = self.request('GET', url, params={'per_page': 100, 'page': page}).json()
            result.extend(items)
            if len(items) < 100:
                return result
            page += 1

    def find_release(self, tag):
        matches = [r for r in self.pages(f'{self.base}/releases') if r['tag_name'] == tag]
        if len(matches) > 1:
            raise ValueError('Multiple releases for this tag; maintainer must resolve manually')
        return matches[0] if matches else None

    def create_draft(self, tag, sha, notes):
        return self.request('POST', f'{self.base}/releases', json={
            'tag_name': tag, 'target_commitish': sha, 'name': tag,
            'body': notes, 'draft': True, 'prerelease': False,
        }).json()

    def get_release(self, release_id):
        return self.request('GET', f'{self.base}/releases/{release_id}').json()

    def list_assets(self, release_id):
        return self.pages(f'{self.base}/releases/{release_id}/assets')

    def download_asset(self, asset):
        # API asset URLs are derived from IDs, not release-supplied arbitrary URLs.
        return self.request('GET', f'{self.base}/releases/assets/{asset["id"]}',
                            headers={'Accept': 'application/octet-stream'}).content

    def upload_asset(self, release, path):
        url = self.base.replace('api.github.com', 'uploads.github.com')
        url += f'/releases/{release["id"]}/assets?name={quote(path.name, safe="")}'
        with path.open('rb') as stream:
            self.request('POST', url, data=stream, headers={'Content-Type': 'application/octet-stream'})


def attach_assets(api, tag: str, sha: str, notes: str, paths: list[Path]) -> None:
    release = api.find_release(tag)
    if release is None:
        release = api.create_draft(tag, sha, notes)
    if release['tag_name'] != tag:
        raise ValueError('Release tag mismatch')
    assets = api.list_assets(release['id'])
    missing = []
    # Preflight the entire catalog before uploading any missing asset.
    for path in paths:
        matches = [a for a in assets if a['name'] == path.name]
        if len(matches) > 1:
            raise ValueError(f'Duplicate release asset: {path.name}')
        if matches:
            if api.download_asset(matches[0]) != path.read_bytes():
                raise ValueError(f'Release asset differs: {path.name}; preserve it and investigate source/toolchain; use a new approved snapshot if necessary')
        else:
            missing.append(path)
    if missing and not release['draft']:
        raise ValueError('Published release is missing WorkBuddy assets; do not overwrite or move its tag. Prepare a new approved snapshot and draft release')
    for path in missing:
        # A maintainer may have published since the preflight. Never knowingly
        # add assets after publication, even when immutability is disabled.
        current = api.get_release(release['id'])
        if not current['draft'] or current['tag_name'] != tag:
            raise ValueError('Release left Draft state during upload; inspect manually')
        api.upload_asset(current, path)
    final = api.list_assets(release['id'])
    for path in paths:
        matches = [a for a in final if a['name'] == path.name]
        if len(matches) != 1 or api.download_asset(matches[0]) != path.read_bytes():
            raise ValueError(f'Uploaded asset verification failed: {path.name}; retry the same tag after investigating')
    print(f'All {len(paths)} release assets verified; publication remains a maintainer decision')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-tag', required=True)
    parser.add_argument('--check-source', action='store_true')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist/workbuddy')
    args = parser.parse_args()
    sha, notes = validate_source(ROOT, args.snapshot_tag)
    if args.check_source:
        print(f'Validated merged annotated snapshot: {args.snapshot_tag} ({sha})')
        return 0
    paths = build_all(ROOT, args.output_dir, args.snapshot_tag)
    api = GitHubAPI(os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN'])
    attach_assets(api, args.snapshot_tag, sha, notes, list(paths))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError, requests.RequestException) as exc:
        raise SystemExit(f'WorkBuddy release failed: {exc}')
