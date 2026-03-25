from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, List

# Allow running from any working directory by ensuring the scripts directory is on sys.path.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from normalize import hotspot_brief, issue_brief, normalize_hotspot, normalize_issue, normalize_project_summary
from render_markdown import render_markdown
from sonarcloud_api import SonarCloudClient
from url_parser import parse_sonarcloud_url

PROJECT_METRIC_KEYS = [
    "alert_status",
    "bugs",
    "vulnerabilities",
    "code_smells",
    "security_hotspots",
    "security_hotspots_reviewed",
    "coverage",
    "duplicated_lines_density",
    "ncloc",
    "reliability_rating",
    "security_rating",
    "sqale_rating",
]


def _safe_get_rule(client: SonarCloudClient, rule_key: str | None) -> Dict[str, Any]:
    if not rule_key:
        return {}
    try:
        payload = client.get_rule(rule_key)
        return payload.get("rule", payload)
    except Exception as exc:  # noqa: BLE001
        return {"_rule_fetch_error": str(exc), "key": rule_key}


def _measure_list_to_map(payload: Dict[str, Any]) -> Dict[str, Any]:
    component = payload.get("component", {})
    measures = component.get("measures", [])
    return {item.get("metric"): item.get("value") for item in measures if item.get("metric")}


def _normalize_quality_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    project_status = payload.get("projectStatus", {})
    conditions = project_status.get("conditions", []) or []
    failing_conditions = [item for item in conditions if item.get("status") == "ERROR"]
    return {
        "status": project_status.get("status"),
        "ignored_conditions": project_status.get("ignoredConditions"),
        "cayc_status": project_status.get("caycStatus"),
        "failing_conditions": failing_conditions,
        "period": project_status.get("period"),
    }


def _issue_search_params(client: SonarCloudClient, parsed: Dict[str, Any], *, ps: int = 10, issues: str | None = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {"ps": ps}
    if parsed.get("organization_key"):
        params["organization"] = parsed["organization_key"]
    elif client.default_organization:
        params["organization"] = client.default_organization

    if parsed.get("project_key"):
        params["componentKeys"] = parsed["project_key"]
    elif client.default_project:
        params["componentKeys"] = client.default_project

    if issues:
        params["issues"] = issues
    if parsed.get("branch"):
        params["branch"] = parsed["branch"]
    if parsed.get("pull_request"):
        params["pullRequest"] = parsed["pull_request"]
    return params


def _inspect_issue(client: SonarCloudClient, parsed: Dict[str, Any]) -> Dict[str, Any]:
    issue_key = parsed.get("issue_key")
    if not issue_key:
        raise ValueError("Issue key missing from link")

    params = _issue_search_params(client, parsed, ps=1, issues=issue_key)
    payload = client.search_issues(**params)
    issues = payload.get("issues", [])
    if not issues:
        return {
            "resource_type": "issue",
            "source_url": parsed["source_url"],
            "parsed": parsed,
            "error": "Issue not found",
            "fetch_attempt": params,
        }

    issue = issues[0]
    rule = _safe_get_rule(client, issue.get("rule"))
    return normalize_issue(parsed["source_url"], parsed, issue, rule)


def _inspect_hotspot(client: SonarCloudClient, parsed: Dict[str, Any]) -> Dict[str, Any]:
    hotspot_key = parsed.get("hotspot_key")
    if not hotspot_key:
        raise ValueError("Hotspot key missing from link")

    payload = client.get_hotspot(hotspot_key)
    hotspot = payload.get("hotspot", payload)
    rule = _safe_get_rule(client, hotspot.get("ruleKey") or hotspot.get("rule"))
    return normalize_hotspot(parsed["source_url"], parsed, hotspot, rule)


def _inspect_project(client: SonarCloudClient, parsed: Dict[str, Any]) -> Dict[str, Any]:
    project_key = parsed.get("project_key") or client.default_project
    organization_key = parsed.get("organization_key") or client.default_organization

    summary: Dict[str, Any] = {
        "metrics": {},
        "quality_gate": {},
        "counts": {},
        "top_issues": [],
        "top_hotspots": [],
        "warnings": [],
        "notes": [
            "Project link parsed successfully.",
            "This summary combines measures, quality gate status, top issues, and hotspots.",
        ],
        "request_context": {
            "organization": organization_key,
            "project": project_key,
            "branch": parsed.get("branch"),
            "pull_request": parsed.get("pull_request"),
        },
    }

    if not project_key:
        summary["warnings"].append("Project key missing from link and no default project configured.")
        return normalize_project_summary(parsed["source_url"], parsed, summary)

    try:
        measure_payload = client.get_component_measures(
            project_key,
            PROJECT_METRIC_KEYS,
            branch=parsed.get("branch"),
            pullRequest=parsed.get("pull_request"),
        )
        metrics = _measure_list_to_map(measure_payload)
        summary["metrics"] = metrics
        summary["counts"] = {
            "bugs": metrics.get("bugs"),
            "vulnerabilities": metrics.get("vulnerabilities"),
            "code_smells": metrics.get("code_smells"),
            "security_hotspots": metrics.get("security_hotspots"),
            "security_hotspots_reviewed": metrics.get("security_hotspots_reviewed"),
            "ncloc": metrics.get("ncloc"),
        }
    except Exception as exc:  # noqa: BLE001
        summary["warnings"].append(f"Project measures fetch failed: {exc}")

    try:
        qg_payload = client.get_quality_gate_status(
            project_key,
            branch=parsed.get("branch"),
            pullRequest=parsed.get("pull_request"),
        )
        summary["quality_gate"] = _normalize_quality_gate(qg_payload)
    except Exception as exc:  # noqa: BLE001
        summary["warnings"].append(f"Quality gate status fetch failed: {exc}")

    try:
        issue_params = _issue_search_params(client, parsed, ps=10)
        issue_payload = client.search_issues(**issue_params)
        summary["top_issues"] = [issue_brief(item) for item in issue_payload.get("issues", [])]
    except Exception as exc:  # noqa: BLE001
        summary["warnings"].append(f"Issue sampling failed: {exc}")

    try:
        hotspot_payload = client.search_hotspots_for_project(
            project_key,
            branch=parsed.get("branch"),
            pull_request=parsed.get("pull_request"),
            ps=10,
            only_to_review=True,
        )
        summary["top_hotspots"] = [hotspot_brief(item) for item in hotspot_payload.get("hotspots", [])]
        summary["request_context"]["hotspot_search_params"] = hotspot_payload.get("_request_params")
    except Exception as exc:  # noqa: BLE001
        summary["warnings"].append(f"Hotspot sampling failed: {exc}")

    return normalize_project_summary(parsed["source_url"], parsed, summary)


def _inspect_project_hotspot_list(client: SonarCloudClient, parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Handle hotspot list pages that have no specific hotspot key.

    These are project-scoped views focused on security hotspots, so we fetch
    hotspots with a larger page size and include basic project metrics for context.
    """
    project_key = parsed.get("project_key") or client.default_project
    organization_key = parsed.get("organization_key") or client.default_organization

    summary: Dict[str, Any] = {
        "metrics": {},
        "quality_gate": {},
        "counts": {},
        "top_issues": [],
        "top_hotspots": [],
        "warnings": [],
        "notes": [
            "This link points to a project-level security hotspot list.",
            "Hotspot sampling uses a larger page size to surface more items.",
        ],
        "request_context": {
            "organization": organization_key,
            "project": project_key,
            "branch": parsed.get("branch"),
            "pull_request": parsed.get("pull_request"),
        },
    }

    if not project_key:
        summary["warnings"].append("Project key missing from link and no default project configured.")
        return normalize_project_summary(parsed["source_url"], parsed, summary)

    # Fetch basic project metrics for context
    try:
        measure_payload = client.get_component_measures(
            project_key,
            PROJECT_METRIC_KEYS,
            branch=parsed.get("branch"),
            pullRequest=parsed.get("pull_request"),
        )
        metrics = _measure_list_to_map(measure_payload)
        summary["metrics"] = metrics
        summary["counts"] = {
            "bugs": metrics.get("bugs"),
            "vulnerabilities": metrics.get("vulnerabilities"),
            "code_smells": metrics.get("code_smells"),
            "security_hotspots": metrics.get("security_hotspots"),
            "security_hotspots_reviewed": metrics.get("security_hotspots_reviewed"),
            "ncloc": metrics.get("ncloc"),
        }
    except Exception as exc:  # noqa: BLE001
        summary["warnings"].append(f"Project measures fetch failed: {exc}")

    # Fetch hotspots with a larger page size since this is a hotspot-focused view
    try:
        hotspot_payload = client.search_hotspots_for_project(
            project_key,
            branch=parsed.get("branch"),
            pull_request=parsed.get("pull_request"),
            ps=25,
            only_to_review=True,
        )
        summary["top_hotspots"] = [hotspot_brief(item) for item in hotspot_payload.get("hotspots", [])]
        summary["request_context"]["hotspot_search_params"] = hotspot_payload.get("_request_params")
    except Exception as exc:  # noqa: BLE001
        summary["warnings"].append(f"Hotspot sampling failed: {exc}")

    return normalize_project_summary(parsed["source_url"], parsed, summary)


def inspect_link(url: str, *, client: SonarCloudClient | None = None) -> Dict[str, Any]:
    parsed_obj = parse_sonarcloud_url(url)
    parsed = parsed_obj.to_dict()

    if parsed["host"] and "sonarcloud" not in parsed["host"] and "sonarqube.us" not in parsed["host"]:
        return {
            "resource_type": "unknown",
            "source_url": url,
            "parsed": parsed,
            "error": "Host does not look like SonarCloud or SonarQube Cloud US",
        }

    current_client = client or SonarCloudClient()

    if parsed["resource_type"] == "issue":
        return _inspect_issue(current_client, parsed)
    if parsed["resource_type"] == "security_hotspot":
        return _inspect_hotspot(current_client, parsed)
    if parsed["resource_type"] == "project_hotspot_list":
        return _inspect_project_hotspot_list(current_client, parsed)
    if parsed["resource_type"] == "project":
        return _inspect_project(current_client, parsed)

    return {
        "resource_type": "unknown",
        "source_url": url,
        "parsed": parsed,
        "error": "Could not determine SonarCloud resource type from URL",
    }


def inspect_links(urls: Iterable[str]) -> Dict[str, Any]:
    client = SonarCloudClient()
    results: List[Dict[str, Any]] = []
    counts = {"project": 0, "issue": 0, "security_hotspot": 0, "project_hotspot_list": 0, "unknown": 0}

    for url in urls:
        result = inspect_link(url, client=client)
        counts[result.get("resource_type") or "unknown"] = counts.get(result.get("resource_type") or "unknown", 0) + 1
        results.append(result)

    return {
        "resource_type": "batch",
        "platform": "sonarcloud",
        "count": len(results),
        "counts_by_type": counts,
        "results": results,
    }


def format_output(result: Dict[str, Any], output_format: str) -> str:
    if output_format == "markdown":
        if result.get("resource_type") == "batch":
            parts = [
                "# SonarCloud Batch Inspection",
                "",
                f"- Total links: {result.get('count')}",
                f"- By type: {result.get('counts_by_type')}",
                "",
            ]
            for index, item in enumerate(result.get("results", []), start=1):
                parts.extend([f"---\n\n## Item {index}\n", render_markdown(item).rstrip(), ""])
            return "\n".join(parts).rstrip() + "\n"
        return render_markdown(result)
    return json.dumps(result, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect SonarCloud link(s) and return normalized details")
    parser.add_argument("urls", nargs="+", help="One or more SonarCloud URLs")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if len(args.urls) == 1:
        result = inspect_link(args.urls[0])
    else:
        result = inspect_links(args.urls)

    print(format_output(result, args.format))


if __name__ == "__main__":
    main()
