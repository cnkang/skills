from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
from urllib.parse import ParseResult, parse_qs, urlparse


@dataclass
class ParsedSonarLink:
    source_url: str
    host: str
    path: str
    resource_type: str
    organization_key: Optional[str] = None
    project_key: Optional[str] = None
    issue_key: Optional[str] = None
    hotspot_key: Optional[str] = None
    branch: Optional[str] = None
    pull_request: Optional[str] = None
    file_path: Optional[str] = None
    line: Optional[int] = None
    query: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _first(query: Dict[str, list[str]], *names: str) -> Optional[str]:
    for name in names:
        values = query.get(name)
        if values:
            return values[0]
    return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _validate_source_url(parsed: ParseResult) -> None:
    """Reject non-HTTPS, foreign-host, or credential-bearing source URLs."""
    if parsed.scheme != "https" or parsed.hostname not in {"sonarcloud.io", "sonarqube.us"}:
        raise ValueError("Expected an HTTPS SonarQube Cloud EU or US URL")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Credentials and non-HTTPS ports are not allowed in source URLs")


def _is_project_path(path_lower: str) -> bool:
    """Return True when the path points at a project-level page."""
    return (
        "/project/" in path_lower
        or "/dashboard" in path_lower
        or "/summary/" in path_lower
        or "/overview" in path_lower
        or "/code" in path_lower
        or "/activity" in path_lower
    )


def _detect_resource_type(path_lower: str, issue_key: Optional[str], hotspot_key: Optional[str], project_key: Optional[str]) -> str:
    """Classify the link from its path shape and the keys carried in the query."""
    if issue_key:
        return "issue"
    if hotspot_key:
        return "security_hotspot"
    # A hotspot list page (security_hotspots path without a specific hotspot key)
    # should be treated as a project-level hotspot listing, not a single hotspot lookup.
    if "security_hotspots" in path_lower or "security-hotspots" in path_lower:
        return "project_hotspot_list"
    if _is_project_path(path_lower) or project_key:
        return "project"
    return "unknown"


def parse_sonarcloud_url(url: str) -> ParsedSonarLink:
    parsed = urlparse(url)
    _validate_source_url(parsed)
    query = parse_qs(parsed.query)
    if any(k.lower() in {"token", "sonarcloud_token", "password", "api_key", "authorization", "secret"} for k in query):
        raise ValueError("Credentials must be supplied through the environment, not URLs")
    if _first(query, "branch") and _first(query, "pullRequest", "pull_request", "pr"):
        raise ValueError("Specify either branch or pull request, not both")

    issue_key = _first(query, "issues", "issueKey", "issue", "open")
    hotspot_key = _first(query, "hotspots", "hotspot", "hotspotKey")
    project_key = _first(query, "id", "project", "projectKey", "component", "componentKey")
    organization_key = _first(query, "organization", "org")
    branch = _first(query, "branch")
    pull_request = _first(query, "pullRequest", "pull_request", "pr")
    file_path = _first(query, "path", "file")
    line = _parse_int(_first(query, "line"))

    resource_type = _detect_resource_type(parsed.path.lower(), issue_key, hotspot_key, project_key)

    return ParsedSonarLink(
        source_url=url,
        host=parsed.hostname or "",
        path=parsed.path,
        resource_type=resource_type,
        organization_key=organization_key,
        project_key=project_key,
        issue_key=issue_key,
        hotspot_key=hotspot_key,
        branch=branch,
        pull_request=pull_request,
        file_path=file_path,
        line=line,
        query={k: v if len(v) > 1 else v[0] for k, v in query.items()},
    )
