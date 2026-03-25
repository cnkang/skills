from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterable, Optional

import requests


class SonarCloudClient:
    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        api_base_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_backoff_seconds: Optional[float] = None,
    ) -> None:
        self.token = token or os.environ.get("SONARCLOUD_TOKEN") or None

        default_base = os.environ.get("SONARCLOUD_BASE_URL", "https://sonarcloud.io")
        self.base_url = (base_url or default_base).rstrip("/")
        self.api_base_url = (api_base_url or os.environ.get("SONARCLOUD_API_BASE_URL", self.base_url)).rstrip("/")
        self.timeout_seconds = timeout_seconds or int(os.environ.get("SONARCLOUD_TIMEOUT_SECONDS", "20"))
        self.max_retries = max_retries if max_retries is not None else int(os.environ.get("SONARCLOUD_MAX_RETRIES", "2"))
        self.retry_backoff_seconds = retry_backoff_seconds if retry_backoff_seconds is not None else float(
            os.environ.get("SONARCLOUD_RETRY_BACKOFF_SECONDS", "1.5")
        )
        self.default_organization = os.environ.get("SONARCLOUD_DEFAULT_ORGANIZATION")
        self.default_project = os.environ.get("SONARCLOUD_DEFAULT_PROJECT")

        self.session = requests.Session()
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.api_base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, params=params or {}, timeout=self.timeout_seconds)
                if response.status_code == 429 and attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                if response.status_code in (401, 403) and not self.token:
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}: Authentication required. "
                        "This project may be private. Set SONARCLOUD_TOKEN to access it.",
                        response=response,
                    )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_backoff_seconds * (attempt + 1))

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Unexpected request failure without exception")

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", path, params=params)

    def search_issues(self, **params: Any) -> Dict[str, Any]:
        return self.get("/api/issues/search", params=params)

    def get_rule(self, rule_key: str) -> Dict[str, Any]:
        return self.get("/api/rules/show", params={"key": rule_key})

    def search_hotspots(self, **params: Any) -> Dict[str, Any]:
        return self.get("/api/hotspots/search", params=params)

    def get_hotspot(self, hotspot_key: str) -> Dict[str, Any]:
        return self.get("/api/hotspots/show", params={"hotspot": hotspot_key})

    def get_component_measures(self, component: str, metric_keys: Iterable[str], **extra_params: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "component": component,
            "metricKeys": ",".join(metric_keys),
        }
        params.update({k: v for k, v in extra_params.items() if v not in (None, "")})
        return self.get("/api/measures/component", params=params)

    def get_quality_gate_status(self, project_key: str, **extra_params: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {"projectKey": project_key}
        params.update({k: v for k, v in extra_params.items() if v not in (None, "")})
        return self.get("/api/qualitygates/project_status", params=params)

    def search_hotspots_for_project(
        self,
        project_key: str,
        *,
        branch: str | None = None,
        pull_request: str | None = None,
        ps: int = 10,
        status: str | None = None,
        only_to_review: bool = False,
    ) -> Dict[str, Any]:
        candidate_params = [
            {
                "projectKey": project_key,
                "branch": branch,
                "pullRequest": pull_request,
                "ps": ps,
                "status": status,
                "onlyToReview": str(only_to_review).lower() if only_to_review else None,
            },
            {
                "project": project_key,
                "branch": branch,
                "pullRequest": pull_request,
                "ps": ps,
                "status": status,
                "onlyToReview": str(only_to_review).lower() if only_to_review else None,
            },
            {
                "componentKeys": project_key,
                "branch": branch,
                "pullRequest": pull_request,
                "ps": ps,
                "status": status,
                "onlyToReview": str(only_to_review).lower() if only_to_review else None,
            },
        ]

        last_exc: Exception | None = None
        for params in candidate_params:
            filtered = {k: v for k, v in params.items() if v not in (None, "")}
            try:
                payload = self.search_hotspots(**filtered)
                payload.setdefault("_request_params", filtered)
                return payload
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                continue

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Unable to search hotspots for project")
