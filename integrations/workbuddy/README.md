# WorkBuddy Skill distribution

WorkBuddy requires bilingual platform metadata. The English-first canonical
`<skill>/SKILL.md` remains each skill's single instruction source for Codex, Claude
Code, OpenCode, Pi and Hermes. This adapter creates a temporary frontmatter with
`description_zh`, `description_en`, `version` and `author`. The Markdown body is
preserved byte for byte. It creates no second discoverable skill entrypoint.
Per-skill Chinese descriptions and author overrides are maintained in `metadata.json`.
An existing canonical author is inherited when no override is needed. English
description, compatibility, license and independent skill version come from the
canonical file. Adding this distribution adapter does not bump the skill version
or the separately distributed runtime/MCP version.

See the [Chinese](https://open.workbuddy.cn/docs/skill)
and [English](https://open.workbuddy.cn/en/docs/skill) official documentation.
Required fields are `description`, `description_zh`,
`description_en`, `version`, `author`. `name` is preserved. Optional example
fields such as category and display name are not imposed as requirements.

## Build and inspect a preview

Use Python 3.10 or newer with the repository development dependencies (PyYAML,
requests and pytest). This builds instructions and scripts. It never runs the
runtime installer or installs Python, Ollama or Qdrant.

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_skills.py
python3 integrations/workbuddy/build.py --check
python3 integrations/workbuddy/build.py --output-dir dist/workbuddy
python3 -m pytest -q tests/test_workbuddy_package.py tests/test_workbuddy_release.py
python3 integrations/workbuddy/build.py --skill qdrant-memory  # optional selection
python3 -m zipfile -l dist/workbuddy/qdrant-memory-workbuddy-skill-v0.2.4-preview.zip
cd dist/workbuddy
sha256sum --check ./*-preview.zip.sha256
```

On macOS use `shasum -a 256 -c FILE.zip.sha256`. The version shown above is an
example. The builder always reads the current canonical version. Unpack only
into a disposable directory outside the repository, so extracted `SKILL.md`
does not become another discoverable skill. By default every controlled catalog
skill gets its own ZIP and checksum. Use repeated `--skill NAME` options to
select a subset for local preview. Each archive has one independent root:

```text
<skill-name>/
  SKILL.md                  # generated UTF-8 frontmatter, unchanged body
  LICENSE                   # canonical MIT license
  references/               # tracked references, when present
  scripts/                  # tracked scripts, when present
  assets/                   # tracked adapters/assets, when present
  agents/                   # canonical host UI metadata, when present
  examples/                 # tracked examples, when present
  templates/                # tracked templates, when present
  README.md                 # when present
  requirements.txt          # when present
```

There is no `integrations/workbuddy/` directory, other skill, runtime binary,
database or account configuration in the ZIP. Root `.gitignore` files are omitted.
Only tracked regular resources in approved directories/extensions are accepted.
Development tests stay outside skill directories; test files and `tests/`
directories are rejected from packages. Text is UTF-8 and supported binary
assets retain their exact bytes. Unapproved tracked resources fail the build. Untracked local files are omitted. Symlinks,
unresolved index entries, missing or escaping references and unsafe output paths
are rejected. Sources are read from Git index blobs, avoiding Windows checkout
CRLF conversion. Stage intentional resource edits before previewing. Unstaged
content changes fail rather than being silently ignored. Official builds require
a clean exact-tag checkout, so its index matches the approved commit. Sorted
entries, fixed timestamps/modes and uncompressed ZIP data
avoid platform/compression-library variation. Existing different outputs are
never overwritten. Use a fresh output directory after intentional source edits.

## Add a future skill

1. Add an independently valid canonical skill folder and register it in the
   existing `SKILLS` catalog in `scripts/validate_skills.py`, following the
   repository's normal distribution/host acceptance conventions.
2. Add an entry under its exact name in `metadata.json` with `description_zh`.
   Set `author` only when the canonical frontmatter/metadata supplies no author
   or an intentional WorkBuddy override is required. Do not duplicate its
   English description or version.
3. Stage reviewed resource files and run `build.py --check` plus repository CI.
   No builder or workflow skill list needs editing. The same catalog controls
   preview packages, release packages and annotation requirements.

Metadata must cover exactly the controlled catalog. Missing/stale entries fail
CI rather than silently omitting a skill. Filesystem fixtures and nested skills
are never automatically discovered. New resource formats outside the supported
allowlist need a deliberate builder/test update. Each new skill retains its
own version. Adding one never changes the versions of existing skills.

## Official release packages

Follow [repository release guidance](../../docs/releasing.md). Versions remain
independent: the skill supplies `metadata.version`. The repository snapshot tag
must be an annotated `skills-YYYYMMDD.N` with a valid date and positive integer
sequence without leading zeroes. Its annotation must list every controlled
catalog skill and version, and its commit must already be merged into `main`.

For example, the package from `skills-20261020.1` at skill version `0.2.4` is
`qdrant-memory-workbuddy-skill-v0.2.4-skills-20261020.1.zip`, with a same-name
`.zip.sha256` companion. Different snapshots retain distinct names even when
the skill version is unchanged. A local packaging command is:

```bash
python3 integrations/workbuddy/build.py --snapshot-tag skills-20261020.1
```

This command validates naming, not Git release authorization. Official source
checks use `release.py --snapshot-tag TAG --check-source` in a clean exact-tag
checkout with `origin/main` available. Actions runs those checks automatically.

`workbuddy-preview.yml` runs on PRs, `codex/**` pushes and manual dispatch, using
read-only permissions. A manual run can build one selected catalog skill through
the `skill` input. An empty input builds every catalog skill. Its 14-day
artifact explicitly says `preview`. Existing
required package CI also executes these tests through the `tests` directory.
The existing required job dependencies remain intact.

`workbuddy-release.yml` runs only on `skills-*` tag pushes. A read-only job
validates the annotated exact checkout, merged ancestry, catalog annotation,
canonical package, tests and deterministic ZIP. A dependent job with
`contents: write` repeats source validation, rebuilds and compares the downloaded
artifact, then uses `GITHUB_TOKEN` to create or reuse a Draft Release. English
release notes come from the tag annotation. An existing draft's notes remain
unchanged. The job prepares every catalog skill independently, checks all
existing ZIP/checksum assets before any upload, and downloads every asset again
for byte checks. Currently five skills produce ten release assets.
Per-tag concurrency prevents competing workflow uploads. No PAT is required.
There is no ordinary-main-push or PR path to release writes.

The workflow **never publishes**. A maintainer checks every ZIP/checksum pair, keeps the
release as Draft until all assets and notes are ready, then manually publishes.
This follows [GitHub immutable release guidance](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases).
Do not publish a draft while the upload job is running.

## Download and submit

Open the [GitHub Releases page](https://github.com/cnkang/skills/releases), select
the approved snapshot and download the selected skill's WorkBuddy ZIP and
checksum under Assets. Submit each skill ZIP as its own platform Skill entry.
Check the checksum before use. This ZIP is specifically for WorkBuddy. Use
normal skill installation for other agents.

Sign in to the [WorkBuddy Open Platform](https://open.workbuddy.cn) and
complete the platform's partner onboarding if required. Then create a Skill
entry, upload this ZIP and complete the platform's submission/review process. Preview artifacts
are for review and testing, not approved marketplace releases. Submission,
marketplace approval, and installation/invocation in the actual WorkBuddy client
are separate manual acceptance steps. Structural tests do not establish them.

## Runtime prerequisites and limitations

Every skill keeps its own canonical prerequisites and authorization boundaries.
These include Git/Python for commit checks, optional Jev configuration for dev-jev,
project toolchains for quality gates, and Python/requests/network access for
SonarCloud. Packaging does not install those dependencies.

The Qdrant Skill ZIP does not bundle the standalone runtime or MCP server. Configure
the supported Qdrant memory runtime, embedding service, credentials and trusted
scope separately using the packaged `references/runtime.md`, `mcp.md` and
`agent-setup.md`. Install/configure only within user authorization. Loading the
skill grants no permission to save, import, delete or modify configuration.
Scope isolation, WriterLease, Mem0 migration and recovery boundaries remain the
canonical instructions. For Hermes, retain one memory interface per profile.
Do not register duplicate plugin/MCP memory interfaces.

Official documentation currently describes layout and required frontmatter,
without a specific ZIP encoding or size limit. We emit UTF-8 text and validate
all packaged source bytes, local links, ZIP entries and CRCs. Platform parser
acceptance, tool availability and real-model behavior still require manual
verification. This implementation targets github.com and its hosted runners.

## Failure recovery

1. Inspect the failing job. Invalid date, lightweight tag, missing catalog
   annotation, unmerged commit, dirty checkout or broken resource stops release
   preparation. Do not move an existing published tag. Use a new approved
   snapshot if source/tag repair is required.
2. On a transient API/upload failure, inspect the draft and rerun the same tag
   workflow. Matching assets are verified and skipped. A partially uploaded
   draft can safely gain only its missing asset. No asset is deleted/replaced.
3. On a content mismatch, stop and investigate exact source and toolchain.
   Download and preserve existing assets. Never use `--clobber` to hide a
   mismatch. Resolve manually or prepare a new approved snapshot.
4. A published release is read-only to this adapter. Existing matching assets
   pass verification. Missing/different assets produce an explicit error.
   Prepare a new approved snapshot and draft rather than attempting to mutate
   an immutable release. Do not create another release for the same tag.
5. Do not publish a partial draft. Confirm successful workflow completion, all
   downloads/checksums, notes and manual platform acceptance before publication.
