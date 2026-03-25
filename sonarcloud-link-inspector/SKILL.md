---
name: sonarcloud-link-inspector
description: Parse SonarCloud project, issue, and security hotspot links, then fetch normalized read-only details for agent analysis and code-fix workflows. Use this skill whenever the user pastes or mentions any sonarcloud.io URL, asks about SonarCloud findings, wants to understand or fix a SonarCloud issue or security hotspot, or shares a link that looks like it points to a SonarCloud project dashboard, issue page, or security hotspot page — even if they don't explicitly say "SonarCloud".
---

# SonarCloud Link Inspector

When a user gives you one or more SonarCloud links, use this skill to fetch the details behind those links so you can understand the findings and help fix them in code.

This skill is strictly read-only — it never modifies anything on SonarCloud (no issue transitions, no hotspot reviews, no comments, no assignments).

## How to use

### Step 1: Run the inspector script

From the skill root directory, run:

```bash
python scripts/inspect_sonarcloud_link.py "<url>"
```

For multiple links in one call:

```bash
python scripts/inspect_sonarcloud_link.py "<url1>" "<url2>" "<url3>"
```

Add `--format markdown` for human-readable output (recommended when summarizing for the user):

```bash
python scripts/inspect_sonarcloud_link.py --format markdown "<url>"
```

The default output is JSON, which is better for programmatic downstream use.

### Step 2: Use the output

The script returns normalized details depending on the link type:

- **Issue link** → issue status, severity, type, file location, rule explanation, why it matters, how to fix it
- **Security hotspot link** → hotspot status, resolution, file location, rule explanation, why it's security-sensitive, review/fix direction
- **Project link** → quality gate status, key metrics (bugs, vulnerabilities, code smells, coverage), top priority issues, hotspots needing review

Use this information to:
- Explain the finding to the user
- Locate the affected file and line in the codebase
- Understand the root cause from the rule explanation
- Propose or implement a code fix
- Prioritize which findings to address first (for project links)

### Step 3: Act on the findings

After fetching the details, read the relevant source files in the user's codebase and work on fixing the issues. The normalized output includes `agent_summary` with `why_it_matters` and `how_to_fix` (or `how_to_review_or_fix` for hotspots) — use these as starting guidance for your fix.

## Supported URL shapes

The parser recognizes these common SonarCloud URL patterns:

| Pattern | Resource type |
|---|---|
| `sonarcloud.io/project/issues?issues=AX123&id=...` | issue |
| `sonarcloud.io/project/issues?id=...&open=AX123` | issue |
| `sonarcloud.io/project/security_hotspots?hotspots=AY456&id=...` | security_hotspot (single) |
| `sonarcloud.io/project/security_hotspots?id=...` (no specific hotspot) | project_hotspot_list |
| `sonarcloud.io/summary/new_code?id=...` | project |
| `sonarcloud.io/summary/overall_code?id=...` | project |
| `sonarcloud.io/project/overview?id=...` | project |
| `sonarcloud.io/dashboard?id=...` | project |
| `sonarcloud.io/project/issues?id=...` (no specific issue) | project |
| `sonarcloud.io/code?id=...` | project |

Branch and pull request context are preserved when present in the URL (`&branch=...`, `&pullRequest=...`).

## Authentication

The script needs a SonarCloud API token via environment variable:

```
SONARCLOUD_TOKEN=<token>
```

Optional environment variables for customization:
- `SONARCLOUD_BASE_URL` — default: `https://sonarcloud.io`
- `SONARCLOUD_API_BASE_URL` — default: same as base URL
- `SONARCLOUD_DEFAULT_ORGANIZATION` — fallback org when not in the URL
- `SONARCLOUD_DEFAULT_PROJECT` — fallback project when not in the URL
- `SONARCLOUD_TIMEOUT_SECONDS` — default: `20`
- `SONARCLOUD_MAX_RETRIES` — default: `2`
- `SONARCLOUD_RETRY_BACKOFF_SECONDS` — default: `1.5`

If the token is missing, the script will raise a clear error. If the token lacks permissions for a private project, the API will return 403 — tell the user to check their token scope.

## Error handling

When something goes wrong, the script returns a structured error object instead of crashing. Common scenarios:

- **Invalid URL** → returns parsed context with an error message explaining what couldn't be determined
- **Resource not found** → returns the fetch attempt parameters so you can see what was tried
- **Permission denied** → suggest the user check their `SONARCLOUD_TOKEN` scope
- **Rate limited (HTTP 429)** → the client retries automatically with backoff
- **Network failure** → retries up to `max_retries` times

In all error cases, relay the error to the user clearly and suggest a concrete next step.

## Guardrails

- Never expose the token value in output or conversation
- Never attempt to modify SonarCloud state (this skill has no write endpoints)
- Treat the URL as the source of truth — preserve branch/PR context from it
- Prefer the normalized output over raw API payloads for reasoning
