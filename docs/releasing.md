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
