from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


ISSUE_SEVERITY_ORDER = {
    "BLOCKER": 5,
    "CRITICAL": 4,
    "MAJOR": 3,
    "MINOR": 2,
    "INFO": 1,
}


def _extract_file_path(component: Optional[str]) -> Optional[str]:
    if not component:
        return None
    if ":" in component:
        return component.split(":", 1)[1]
    return component


def _extract_description_sections(rule: Dict[str, Any]) -> Dict[str, str]:
    extracted: Dict[str, str] = {}
    for section in rule.get("descriptionSections", []) or []:
        key = (section.get("key") or section.get("name") or "").strip().lower().replace(" ", "_")
        content = (section.get("content") or "").strip()
        if key and content:
            extracted[key] = content
    return extracted


def issue_brief(issue: Dict[str, Any]) -> Dict[str, Any]:
    component = issue.get("component")
    return {
        "key": issue.get("key"),
        "status": issue.get("status"),
        "severity": issue.get("severity"),
        "type": issue.get("type"),
        "message": issue.get("message"),
        "component": component,
        "file_path": _extract_file_path(component),
        "line": issue.get("line"),
        "rule_key": issue.get("rule"),
        "priority_score": ISSUE_SEVERITY_ORDER.get(issue.get("severity") or "", 0),
    }


def hotspot_brief(hotspot: Dict[str, Any]) -> Dict[str, Any]:
    component = hotspot.get("component")
    status = hotspot.get("status")
    unresolved_bias = 2 if status in {None, "TO_REVIEW", "OPEN"} else 0
    return {
        "key": hotspot.get("key"),
        "status": status,
        "resolution": hotspot.get("resolution"),
        "message": hotspot.get("message") or hotspot.get("vulnerabilityMessage"),
        "component": component,
        "file_path": _extract_file_path(component),
        "line": hotspot.get("line"),
        "rule_key": hotspot.get("ruleKey") or hotspot.get("rule"),
        "review_priority": hotspot.get("reviewPriority"),
        "priority_score": unresolved_bias + (1 if hotspot.get("reviewPriority") else 0),
    }


def _top_n_sorted(items: Iterable[Dict[str, Any]], n: int = 5) -> list[Dict[str, Any]]:
    return sorted(items, key=lambda item: item.get("priority_score", 0), reverse=True)[:n]


def normalize_issue(source_url: str, parsed: Dict[str, Any], issue: Dict[str, Any], rule: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rule = rule or {}
    component = issue.get("component")
    description_sections = _extract_description_sections(rule)
    return {
        "resource_type": "issue",
        "platform": "sonarcloud",
        "source_url": source_url,
        "organization_key": parsed.get("organization_key"),
        "project_key": parsed.get("project_key"),
        "resource_key": issue.get("key"),
        "status": issue.get("status"),
        "severity": issue.get("severity"),
        "type": issue.get("type"),
        "message": issue.get("message"),
        "location": {
            "component": component,
            "file_path": _extract_file_path(component) or parsed.get("file_path"),
            "line": issue.get("line") or parsed.get("line"),
        },
        "rule": {
            "key": rule.get("key") or issue.get("rule"),
            "name": rule.get("name"),
            "description_sections": rule.get("descriptionSections", []),
            "description_by_key": description_sections,
            "impacts": rule.get("impacts", []),
            "clean_code_attribute": rule.get("cleanCodeAttribute"),
            "security_standards": rule.get("securityStandards", {}),
        },
        "details": {
            "assignee": issue.get("assignee"),
            "author": issue.get("author"),
            "creation_date": issue.get("creationDate"),
            "update_date": issue.get("updateDate"),
            "effort": issue.get("effort"),
            "secondary_locations": issue.get("secondaryLocations", []),
            "flows": issue.get("flows", []),
            "tags": issue.get("tags", []),
        },
        "agent_summary": {
            "what": issue.get("message"),
            "why_it_matters": description_sections.get("why_this_is_an_issue") or description_sections.get("why_is_this_an_issue"),
            "how_to_fix": description_sections.get("how_to_fix_it") or description_sections.get("recommended_way_to_fix_it"),
        },
    }


def normalize_hotspot(source_url: str, parsed: Dict[str, Any], hotspot: Dict[str, Any], rule: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rule = rule or {}
    component = hotspot.get("component")
    description_sections = _extract_description_sections(rule)
    return {
        "resource_type": "security_hotspot",
        "platform": "sonarcloud",
        "source_url": source_url,
        "organization_key": parsed.get("organization_key"),
        "project_key": parsed.get("project_key"),
        "resource_key": hotspot.get("key"),
        "status": hotspot.get("status"),
        "resolution": hotspot.get("resolution"),
        "message": hotspot.get("message") or hotspot.get("vulnerabilityMessage"),
        "location": {
            "component": component,
            "file_path": _extract_file_path(component) or parsed.get("file_path"),
            "line": hotspot.get("line") or parsed.get("line"),
        },
        "rule": {
            "key": rule.get("key") or hotspot.get("ruleKey") or hotspot.get("rule"),
            "name": rule.get("name"),
            "description_sections": rule.get("descriptionSections", []),
            "description_by_key": description_sections,
            "impacts": rule.get("impacts", []),
            "security_standards": rule.get("securityStandards", {}),
        },
        "details": {
            "author": hotspot.get("author"),
            "creation_date": hotspot.get("creationDate"),
            "update_date": hotspot.get("updateDate"),
            "vulnerability_probability": hotspot.get("vulnerabilityProbability"),
            "review_priority": hotspot.get("reviewPriority"),
        },
        "agent_summary": {
            "what": hotspot.get("message") or hotspot.get("vulnerabilityMessage"),
            "why_it_matters": description_sections.get("why_is_this_security-sensitive")
            or description_sections.get("why_is_this_security_sensitive")
            or description_sections.get("why_is_this_an_issue"),
            "how_to_review_or_fix": description_sections.get("how_can_i_fix_it")
            or description_sections.get("how_to_fix_it")
            or description_sections.get("ask_whether_this_is_safe_here"),
        },
    }


def normalize_project_summary(source_url: str, parsed: Dict[str, Any], summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    summary = summary or {}
    top_issues = _top_n_sorted(summary.get("top_issues", []), n=5)
    top_hotspots = _top_n_sorted(summary.get("top_hotspots", []), n=5)
    return {
        "resource_type": "project",
        "platform": "sonarcloud",
        "source_url": source_url,
        "organization_key": parsed.get("organization_key"),
        "project_key": parsed.get("project_key"),
        "summary": {
            "metrics": summary.get("metrics", {}),
            "quality_gate": summary.get("quality_gate", {}),
            "counts": summary.get("counts", {}),
            "top_issues": top_issues,
            "top_hotspots": top_hotspots,
            "warnings": summary.get("warnings", []),
            "notes": summary.get("notes", []),
            "request_context": summary.get("request_context", {}),
        },
        "agent_summary": {
            "quality_gate_status": (summary.get("quality_gate") or {}).get("status"),
            "highest_priority_issues": top_issues,
            "hotspots_to_review": top_hotspots,
        },
    }
