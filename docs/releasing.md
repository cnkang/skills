# Release and rollback

Each skill is an independently installable folder. Keep its name and top-level
path stable. Runtime scripts/references/licenses belong inside that folder.
Repository development tooling is not a runtime dependency. Never add mandatory
cross-skill dependencies or automatic installation chains.

## Release checks

1. Run repository validation, unit regressions, fixed/latest CLI jobs, the pinned
   plugin contract, three-platform Hermes Hub/disposable runtime E2E jobs and
   Pi skill host acceptance and three-platform no-Hermes CLI/MCP acceptance.
   See `agent-host-acceptance.md` for Pi reproduction
   and its pinned npm dependency upgrade procedure.
   Inspect failures against the recorded Node, Python and CLI versions. CI installs
   only into disposable directories and never uses account tokens for fixtures.
2. Update `metadata.version` only for changed skills, sync the README catalog, and
   add concrete behavior, migration and validation notes to `CHANGELOG.md`.
   Use semantic versions. Breaking adapters/interfaces need a major version,
   additive capabilities need a minor version, and compatible fixes need a
   patch version.
3. Review manual behavior scenarios when changing routing or authorization.
   Record actual results separately from installation and script test coverage.
4. Merge only after `Required checks` passes. Dedicated contract/E2E jobs reject
   skipped or empty acceptance and upload JUnit artifacts even on failure.
   Maintainers configure branch protection
   as appropriate. This repository does not modify remote settings automatically.

The default branch is the continuous-update channel. CLI updates follow recorded
source/path/ref and folder content, not `metadata.version` ordering. Documentation
outside a skill does not change that skill's runtime package hash.

## Snapshot tags

After an approved merge, create an annotated repository snapshot tag named
`skills-YYYYMMDD.N` (N starts at 1 for that UTC date), pointing to the merged SHA.
The tag annotation lists every version in the controlled `SKILLS` catalog in
`scripts/validate_skills.py`. Publish the tag and English
release notes only as part of an authorized release. No tag is created by tests
or ordinary skill installation. Use GitHub tree URLs at that tag to deliberately
pin a snapshot. Verify the resulting lock's ref in a disposable project.

A ref-pinned installation remains on that ref during update. To follow the default
branch again, explicitly re-add the selected skills from `cnkang/skills` with the
intended agent/scope. Updating or editing a local version does not migrate source.

The Qdrant package has its own version. Adding it does not bump the four
existing packages. Check `tests/test_qdrant_plugin_contract.py` against the pinned
plugin release before updating interface instructions. Keep its immutable CI ref
aligned when deliberately adopting a newer contract. Update the pinned Hermes
source and acceptance assertions together when deliberately adopting a new host.
Use `requirements-runtime-tests.txt` plus the pinned plugin for local E2E.
See `qdrant-memory-compatibility.md` for commands. Automated runtime acceptance uses
synthetic data, real embedded storage and a deterministic localhost embedding
service. Live model routing remains a separate manual acceptance layer.

## WorkBuddy Skill release asset

The WorkBuddy adapter packages every skill in the controlled `SKILLS` catalog
as a separate ZIP and checksum, preserving each English-first canonical skill
and independent version. See [build, inspection and future-skill registration](../integrations/workbuddy/README.md).

1. Complete the PR and all existing required CI, including WorkBuddy package
   tests and the preview ZIP/checksum artifact. Review the preview.
2. Merge the reviewed source into `main`.
3. Create an annotated `skills-YYYYMMDD.N` snapshot tag at that merged SHA using
   the existing UTC-date convention; list all catalog skill versions in its
   English annotation. Do not bump unrelated skills or convert to unified SemVer.
4. Push the approved tag and wait for **WorkBuddy draft release assets** to
   validate exact tag source, build and attach every skill's assets to a Draft Release.
   Do not publish while this job runs. A new draft uses the English annotation
   as release notes; existing draft notes and unrelated assets are preserved.
5. Download and inspect each ZIP and verify its `.zip.sha256` checksum. Its name
   includes both the canonical skill version and repository snapshot, for example
   `qdrant-memory-workbuddy-skill-v0.2.4-skills-20261020.1.zip`.
6. The maintainer manually publishes the complete Draft Release after review.
   The workflow never publishes. Attaching assets first supports Immutable
   Releases; published releases are only verified, never repaired in place.
7. Download the desired skill ZIPs from Release Assets and submit each separately
   to the WorkBuddy Open Platform through its manual review process. Actual marketplace/client
   acceptance remains distinct from automated structural validation.

The workflow uses only `GITHUB_TOKEN`, read-only build permissions and a separate
`contents: write` draft job, serialized by tag. A rerun verifies matching assets
and uploads only missing draft assets. Content mismatch fails without deletion
or replacement. Failed partial drafts remain drafts for investigation/retry;
   never publish one. If a published release lacks assets, prepare a new approved
snapshot instead of moving its tag or trying to overwrite immutable attachments.

## Recovery

For a broken default-branch change, revert the offending change through review,
rerun affected checks, and let users update the selected skills. Do not rewrite
published tags or downgrade unrelated skills. Users who need a known snapshot
can explicitly re-add only the affected skills from that tag, preserving backups
of customizations. Reinstall with `--copy` when link topology is unsuitable.

Old externally deployed command/hook templates are user configuration.
Package updates do not remove or overwrite them. Legacy logs remain readable with an
explicit telemetry path. Track upstream CLI compatibility failures separately
from skill behavior changes and update the baseline only after the matrix passes.
