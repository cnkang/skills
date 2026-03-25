from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse


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


def parse_sonarcloud_url(url: str) -> ParsedSonarLink:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    issue_key = _first(query, "issues", "issueKey", "issue", "open")
    hotspot_key = _first(query, "hotspots", "hotspot", "hotspotKey")
    project_key = _first(query, "id", "project", "projectKey", "component", "componentKey")
    organization_key = _first(query, "organization", "org")
    branch = _first(query, "branch")
    pull_request = _first(query, "pullRequest", "pull_request", "pr")
    file_path = _first(query, "path", "file")
    line = _parse_int(_first(query, "line"))

    path_lower = parsed.path.lower()

    # A hotspot list page (security_hotspots path without a specific hotspot key)
    # should be treated as a project-level hotspot listing, not a single hotspot lookup.
    is_hotspot_path = "security_hotspots" in path_lower or "security-hotspots" in path_lower
    is_issue_path = "issue" in path_lower

    if issue_key and (is_issue_path or _first(query, "issues", "issueKey", "issue", "open")):
        resource_type = "issue"
    elif hotspot_key:
        resource_type = "security_hotspot"
    elif is_hotspot_path and not hotspot_key:
        # Hotspot list page for a project — treat as project-scoped hotspot listing
        resource_type = "project_hotspot_list"
    elif (
        "/project/" in path_lower
        or "/dashboard" in path_lower
        or "/summary/" in path_lower
        or "/overview" in path_lower
        or "/code" in path_lower
        or "/activity" in path_lower
        or (project_key and not issue_key and not hotspot_key)
    ):
        resource_type = "project"
    else:
        resource_type = "unknown"

    return ParsedSonarLink(
        source_url=url,
        host=parsed.netloc,
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
