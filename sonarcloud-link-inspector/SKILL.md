---
name: sonarcloud-link-inspector
description: Inspect SonarCloud issue, hotspot, or project URLs and fetch read-only details for diagnosis or requested code remediation.
---

# SonarCloud Link Inspector

Fetch the details needed to answer the user's question. A pasted URL alone does
not authorize code changes. Keep inspection read-only unless the task explicitly
includes remediation. This tool never changes SonarCloud state.

## Fetch

From any working directory, use the actual installed skill path:

```bash
python3 <skill-dir>/scripts/inspect_sonarcloud_link.py "<url>"
```

Multiple quoted URLs are supported. Output defaults to JSON; add
`--format markdown` for a readable report. Preserve the URL's branch or PR
context; do not silently substitute the default branch.

## Interpret and act

Use normalized issue/hotspot details, rule explanations, and project metrics.
Treat `agent_summary` suggestions as leads, not proof a fix is necessary.
Verify against current source when available and distinguish stale findings,
false positives, and genuine issues.

For inspection, explain the finding and any uncertainty without editing files.
For requested remediation, make a scoped fix and validate affected behavior.
Neither request authorizes posting comments, reviewing hotspots, or transitioning
issues on SonarCloud.

Use `SONARCLOUD_TOKEN` via the environment when authentication is needed; never
print or copy its value into files or the conversation. Report API failures as
limitations, not empty findings or passed gates.

Read [API details](references/api-details.md) only for URL variants,
authentication/configuration, or error handling. See
[example outputs](examples/example-outputs.md) when output shape is unclear.
