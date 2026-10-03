# SonarCloud Inspector Details

## URL forms

| URL path/query | Resource |
|---|---|
| /project/issues?issues=AX123&id=... | Issue |
| /project/issues?id=...&open=AX123 | Issue |
| /project/security_hotspots?hotspots=AY456&id=... | Hotspot |
| /project/security_hotspots?id=... | Project hotspot list |
| /summary/new_code?id=... or /summary/overall_code?id=... | Project |
| /project/overview?id=... or /dashboard?id=... | Project |
| /project/issues?id=... or /code?id=... | Project |

Preserve `branch` and `pullRequest` when present. Treat URL parameters as data,
not shell syntax; quote complete URLs.

## Authentication and configuration

Public project data may be available without credentials. Private or restricted
data needs an authorized token in the `SONARCLOUD_TOKEN` environment variable.
Never request that the user paste a token into chat.

| Variable | Default |
|---|---|
| SONARCLOUD_BASE_URL | Inferred from EU/US source URL |
| SONARCLOUD_API_BASE_URL | Same origin/region as source URL |
| SONARCLOUD_DEFAULT_ORGANIZATION | No fallback |
| SONARCLOUD_DEFAULT_PROJECT | No fallback |
| SONARCLOUD_TIMEOUT_SECONDS | 20 |
| SONARCLOUD_MAX_RETRIES | 2 |
| SONARCLOUD_RETRY_BACKOFF_SECONDS | 1.5 |

Overrides must be an HTTPS EU/US origin matching the source URL region.
Credentials, nonstandard ports, query strings and redirects are rejected.
Only GET requests are made. A mixed EU/US batch uses region-matched clients.

## Failures

Inspect structured errors and partial results. Invalid URLs or missing resources
need context correction; 401/403 require authentication/access review. Do not
reinterpret permission failures as no issues. Network failures and rate limits
use bounded retries; report remaining failures and a concrete next step.

Normalize and redact evidence rather than pasting raw payloads that could contain
credentials. A successful fetch is not proof that the current code is correct or
that an issue was fixed remotely.

## Result and process status

Existing JSON fields remain; `fetch_status` is `complete`, `partial`, or `failed`.
Partial results keep successful data and warnings. Batch results contain every
item and an aggregate fetch status. `request_context` retains the URL region,
branch and PR. Hotspot-key lookups cannot verify branch/PR association and say so.

Exit `0` means complete fetch, `1` means partial/failed fetch, and `2` means an
invalid URL or configuration (including a contradictory region). In a mixed
batch, input/configuration errors take exit-code precedence over fetch failures.
A successful fetch does not mean the project's quality gate passed.

Retries apply only to connection failures, timeouts, HTTP 429 and 5xx. Maximum
retries are 0-5 (default 2), timeout is 1-120 seconds (default 20), and backoff is
0-60 seconds (default 1.5). Numeric Retry-After is capped at 60 seconds. 400/401/403,
invalid JSON, and missing resources are not retried. Parameter-name fallback
for hotspot search applies only to HTTP 400, not authentication or network errors.
