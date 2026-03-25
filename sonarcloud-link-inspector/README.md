# sonarcloud-link-inspector

A read-only Skill scaffold for SonarCloud links.

Its job is simple:
- accept one or more SonarCloud project / issue / security hotspot links
- parse the link shape and preserve branch / PR context
- fetch richer detail from SonarCloud APIs
- normalize the result into an agent-friendly structure
- optionally render a concise markdown report for downstream agent use

This scaffold is intentionally conservative:
- no write operations
- no issue transitions
- no hotspot review changes
- no comments or assignments

## Suggested skill name

Primary recommendation:
- **sonarcloud-link-inspector**

Alternative names:
- `sonarcloud-finding-inspector`
- `sonarcloud-link-reader`
- `sonarcloud-triage-helper`

## Included files

- `SKILL.md` — trigger and behavior definition for the Skill
- `scripts/inspect_sonarcloud_link.py` — main entry point, supports one or many URLs
- `scripts/inspect_sonarcloud_links.py` — thin wrapper for batch invocation
- `scripts/sonarcloud_api.py` — API client wrapper
- `scripts/url_parser.py` — SonarCloud link parsing and classification
- `scripts/normalize.py` — normalized output helpers
- `scripts/render_markdown.py` — markdown renderer for agent-friendly summaries
- `examples/example-outputs.md` — sample JSON and markdown outputs
- `NEXT_STEPS.md` — recommended follow-up improvements

## What this scaffold now does better

### 1. Stronger project summary

Project inspection now combines four read-only signals:
- `measures/component` metrics such as bugs, vulnerabilities, code smells, hotspots, coverage, duplicated lines density, and quality gate status metric
- `qualitygates/project_status` for actual gate outcome and failing conditions
- `issues/search` sampling for the highest-priority issue list
- `hotspots/search` sampling for hotspots that still look worth review

That gives an agent a much better starting point than a plain project key echo.

### 2. Batch processing

You can now pass multiple SonarCloud links in one call. The script returns:
- total number of inspected links
- counts by resource type
- per-link normalized results

This is useful when a user pastes several issue / hotspot links at once.

### 3. Agent-friendly markdown output

Use `--format markdown` to render a compact report that is easier for an agent to ingest than raw JSON.

## Example usage

Single link as JSON:

```bash
export SONARCLOUD_TOKEN="..."
python scripts/inspect_sonarcloud_link.py "https://sonarcloud.io/project/issues?issues=AX123&id=my_project&organization=my_org"
```

Single link as markdown:

```bash
export SONARCLOUD_TOKEN="..."
python scripts/inspect_sonarcloud_link.py --format markdown "https://sonarcloud.io/project/issues?issues=AX123&id=my_project&organization=my_org"
```

Batch mode:

```bash
export SONARCLOUD_TOKEN="..."
python scripts/inspect_sonarcloud_link.py --format markdown \
  "https://sonarcloud.io/project/issues?issues=AX123&id=my_project&organization=my_org" \
  "https://sonarcloud.io/project/security_hotspots?id=my_project&hotspots=AY456&organization=my_org"
```

## Normalized output philosophy

The goal is not to mirror SonarCloud payloads one-to-one.
The goal is to return a stable object that gives an agent what it needs to reason and act in code:
- what this finding is
- where it is
- how serious it is
- what rule it came from
- why it matters
- what likely remediation direction applies

That is why the scaffold enriches issue and hotspot data with rule details whenever possible and why the project view now includes a triage-oriented summary.

## Practical notes

- SonarQube Cloud’s Web API v2 does not yet cover all capabilities, so this scaffold still assumes selected Web API v1 endpoints may be required.
- Some SonarQube Cloud APIs are rate-limited and can return HTTP 429, so the client now includes a small retry/backoff loop.
- Hotspot search parameter shapes may differ, so the client tries a few common parameter variants before failing.
