# Example outputs

## Single issue as JSON

```json
{
  "resource_type": "issue",
  "platform": "sonarcloud",
  "project_key": "my_org_my_project",
  "resource_key": "AX123",
  "status": "OPEN",
  "severity": "CRITICAL",
  "type": "VULNERABILITY",
  "message": "Change this code to not construct SQL queries directly from user-controlled data.",
  "location": {
    "file_path": "src/db/query.ts",
    "line": 42
  },
  "agent_summary": {
    "what": "Change this code to not construct SQL queries directly from user-controlled data.",
    "why_it_matters": "User-controlled input may reach the database query and enable injection.",
    "how_to_fix": "Use parameterized queries or prepared statements and keep user input out of raw SQL strings."
  }
}
```

## Single issue as markdown

```markdown
# SonarCloud Issue: `AX123`

- Project: `my_org_my_project`
- Status: `OPEN`
- Severity: `CRITICAL`
- Type: `VULNERABILITY`
- Location: `src/db/query.ts:42`
- Source URL: https://sonarcloud.io/project/issues?issues=AX123&id=my_org_my_project

## Finding

Change this code to not construct SQL queries directly from user-controlled data.

## Rule

- Rule: `typescript:S3649` — Database queries should not be vulnerable to injection attacks

## Why it matters

User-controlled input may reach the database query and enable injection.

## Likely fix direction

Use parameterized queries or prepared statements and keep user input out of raw SQL strings.
```

## Project summary as markdown

```markdown
# SonarCloud Project Summary: `my_org_my_project`

- Organization: `my_org`
- Quality Gate: `ERROR`
- Source URL: https://sonarcloud.io/summary/new_code?id=my_org_my_project

## Snapshot

- Bugs: 3
- Vulnerabilities: 2
- Code smells: 48
- Security hotspots: 5
- Security hotspots reviewed: 20%
- Coverage: 76.5
- Duplicated lines density: 1.8
- ncloc: 18420

## Quality Gate failing conditions

- new_security_rating: actual=4 comparator=GT error=1
- coverage: actual=76.5 comparator=LT error=80

## Top issues to address first

- `AX123` [CRITICAL/VULNERABILITY] src/db/query.ts:42 — Change this code to not construct SQL queries directly from user-controlled data.
- `AX124` [BLOCKER/BUG] src/auth/token.ts:19 — Change this code so that it does not always evaluate to "true".

## Security hotspots to review first

- `AY456` [TO_REVIEW] src/crypto/random.ts:11 — Make sure that using this pseudorandom number generator is safe here.
```

## Batch output as markdown

```markdown
# SonarCloud Batch Inspection

- Total links: 2
- By type: {'project': 1, 'issue': 1, 'security_hotspot': 0, 'unknown': 0}

---

## Item 1

# SonarCloud Project Summary: `my_org_my_project`
...

---

## Item 2

# SonarCloud Issue: `AX123`
...
```
