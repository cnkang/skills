from __future__ import annotations

from typing import Any, Dict, Iterable


def _bullet_lines(items: Iterable[str]) -> list[str]:
    return [f"- {item}" for item in items if item]


def _render_rule(rule: Dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if not rule:
        return lines
    if rule.get("key") or rule.get("name"):
        lines.append(f"- Rule: `{rule.get('key')}` — {rule.get('name') or 'Unknown rule'}")
    if rule.get("impacts"):
        impacts = ", ".join(
            f"{impact.get('softwareQuality')}={impact.get('severity')}" for impact in rule.get("impacts", []) if impact
        )
        if impacts:
            lines.append(f"- Rule impacts: {impacts}")
    return lines


def _render_location(location: Dict[str, Any]) -> str:
    file_path = location.get("file_path") or location.get("component") or "Unknown location"
    line = location.get("line")
    return f"{file_path}:{line}" if line else file_path


def render_markdown(result: Dict[str, Any]) -> str:
    resource_type = result.get("resource_type")
    if resource_type == "issue":
        return render_issue_markdown(result)
    if resource_type == "security_hotspot":
        return render_hotspot_markdown(result)
    if resource_type == "project":
        return render_project_markdown(result)
    return render_unknown_markdown(result)


def render_issue_markdown(result: Dict[str, Any]) -> str:
    lines = [
        f"# SonarCloud Issue: `{result.get('resource_key')}`",
        "",
        f"- Project: `{result.get('project_key')}`",
        f"- Status: `{result.get('status')}`",
        f"- Severity: `{result.get('severity')}`",
        f"- Type: `{result.get('type')}`",
        f"- Location: `{_render_location(result.get('location', {}))}`",
        f"- Source URL: {result.get('source_url')}",
        "",
        "## Finding",
        "",
        result.get("message") or "No message provided.",
        "",
        "## Rule",
        "",
    ]
    lines.extend(_render_rule(result.get("rule", {})))

    summary = result.get("agent_summary", {})
    if summary.get("why_it_matters"):
        lines.extend(["", "## Why it matters", "", summary["why_it_matters"]])
    if summary.get("how_to_fix"):
        lines.extend(["", "## Likely fix direction", "", summary["how_to_fix"]])

    details = result.get("details", {})
    if details.get("secondary_locations"):
        lines.extend(["", "## Secondary locations", ""])
        for item in details["secondary_locations"]:
            location = item.get("textRange") or {}
            line = location.get("startLine")
            message = item.get("message") or "Related location"
            component = item.get("component") or "Unknown component"
            lines.append(f"- {component}:{line or '?'} — {message}")

    return "\n".join(lines).strip() + "\n"


def render_hotspot_markdown(result: Dict[str, Any]) -> str:
    lines = [
        f"# SonarCloud Security Hotspot: `{result.get('resource_key')}`",
        "",
        f"- Project: `{result.get('project_key')}`",
        f"- Status: `{result.get('status')}`",
        f"- Resolution: `{result.get('resolution')}`",
        f"- Location: `{_render_location(result.get('location', {}))}`",
        f"- Source URL: {result.get('source_url')}",
        "",
        "## Finding",
        "",
        result.get("message") or "No message provided.",
        "",
        "## Rule",
        "",
    ]
    lines.extend(_render_rule(result.get("rule", {})))

    summary = result.get("agent_summary", {})
    if summary.get("why_it_matters"):
        lines.extend(["", "## Why this is security-sensitive", "", summary["why_it_matters"]])
    if summary.get("how_to_review_or_fix"):
        lines.extend(["", "## Review or fix direction", "", summary["how_to_review_or_fix"]])

    return "\n".join(lines).strip() + "\n"


def render_project_markdown(result: Dict[str, Any]) -> str:
    summary = result.get("summary", {})
    metrics = summary.get("metrics", {})
    counts = summary.get("counts", {})
    qg = summary.get("quality_gate", {})
    lines = [
        f"# SonarCloud Project Summary: `{result.get('project_key')}`",
        "",
        f"- Organization: `{result.get('organization_key')}`",
        f"- Quality Gate: `{qg.get('status') or 'unknown'}`",
        f"- Source URL: {result.get('source_url')}",
        "",
        "## Snapshot",
        "",
    ]

    snapshot_lines = [
        f"Bugs: {counts.get('bugs')}",
        f"Vulnerabilities: {counts.get('vulnerabilities')}",
        f"Code smells: {counts.get('code_smells')}",
        f"Security hotspots: {counts.get('security_hotspots')}",
        f"Security hotspots reviewed: {counts.get('security_hotspots_reviewed')}%",
        f"Coverage: {metrics.get('coverage')}",
        f"Duplicated lines density: {metrics.get('duplicated_lines_density')}",
        f"ncloc: {counts.get('ncloc')}",
    ]
    lines.extend(_bullet_lines(snapshot_lines))

    if qg.get("failing_conditions"):
        lines.extend(["", "## Quality Gate failing conditions", ""])
        for item in qg.get("failing_conditions", []):
            lines.append(
                f"- {item.get('metricKey')}: actual={item.get('actualValue')} comparator={item.get('comparator')} error={item.get('errorThreshold')}"
            )

    if summary.get("top_issues"):
        lines.extend(["", "## Top issues to address first", ""])
        for item in summary["top_issues"]:
            lines.append(
                f"- `{item.get('key')}` [{item.get('severity')}/{item.get('type')}] {item.get('file_path') or item.get('component')}:{item.get('line') or '?'} — {item.get('message')}"
            )

    if summary.get("top_hotspots"):
        lines.extend(["", "## Security hotspots to review first", ""])
        for item in summary["top_hotspots"]:
            lines.append(
                f"- `{item.get('key')}` [{item.get('status')}] {item.get('file_path') or item.get('component')}:{item.get('line') or '?'} — {item.get('message')}"
            )

    if summary.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(_bullet_lines(summary["warnings"]))

    return "\n".join(lines).strip() + "\n"


def render_unknown_markdown(result: Dict[str, Any]) -> str:
    lines = [
        "# SonarCloud Link Inspection Result",
        "",
        f"- Resource type: `{result.get('resource_type')}`",
        f"- Source URL: {result.get('source_url')}",
    ]
    if result.get("error"):
        lines.extend(["", "## Error", "", result["error"]])
    return "\n".join(lines).strip() + "\n"
