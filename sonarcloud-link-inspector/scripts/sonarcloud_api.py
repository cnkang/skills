from __future__ import annotations

import os
import time
import math
from urllib.parse import urlparse
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
        for endpoint in (self.base_url, self.api_base_url):
            parsed = urlparse(endpoint)
            if parsed.scheme != "https" or parsed.hostname not in {"sonarcloud.io", "sonarqube.us"} or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
                raise ValueError("Endpoint must be an HTTPS SonarQube Cloud EU or US origin")
        if urlparse(self.base_url).hostname != urlparse(self.api_base_url).hostname:
            raise ValueError("Base URL and API URL must use the same region")
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else int(os.environ.get("SONARCLOUD_TIMEOUT_SECONDS", "20"))
        self.max_retries = max_retries if max_retries is not None else int(os.environ.get("SONARCLOUD_MAX_RETRIES", "2"))
        self.retry_backoff_seconds = retry_backoff_seconds if retry_backoff_seconds is not None else float(os.environ.get("SONARCLOUD_RETRY_BACKOFF_SECONDS", "1.5"))
        if not 0 < self.timeout_seconds <= 120 or not 0 <= self.max_retries <= 5 or not math.isfinite(self.retry_backoff_seconds) or not 0 <= self.retry_backoff_seconds <= 60:
            raise ValueError("Invalid timeout/retry configuration (timeout 1-120s, retries 0-5, backoff 0-60s)")
        self.default_organization = os.environ.get("SONARCLOUD_DEFAULT_ORGANIZATION")
        self.default_project = os.environ.get("SONARCLOUD_DEFAULT_PROJECT")

        self.session = requests.Session()
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if method != "GET" or not path.startswith("/api/"):
            raise ValueError("Only read-only API GET requests are supported")
        url = f"{self.api_base_url}{path}"
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, params=params or {}, timeout=self.timeout_seconds, allow_redirects=False)
                retryable = response.status_code == 429 or 500 <= response.status_code < 600
                if retryable and attempt < self.max_retries:
                    delay = self.retry_backoff_seconds * (attempt + 1)
                    if response.status_code == 429:
                        try:
                            delay = max(delay, min(60.0, float(response.headers.get("Retry-After", "0"))))
                        except (TypeError, ValueError):
                            pass
                    time.sleep(delay)
                    continue
                if 300 <= response.status_code < 400:
                    raise requests.HTTPError("API redirects are not followed", response=response)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Expected a JSON object from the API")
                return payload
            except (requests.Timeout, requests.ConnectionError):
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.retry_backoff_seconds * (attempt + 1))
        raise RuntimeError("Request retry budget exhausted")

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
            except requests.HTTPError as exc:
                # Only parameter incompatibility justifies trying a legacy parameter name.
                if exc.response is None or exc.response.status_code != 400:
                    raise
                last_exc = exc
                continue

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Unable to search hotspots for project")
