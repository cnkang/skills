"""Offline tests: requests are mocked; no tokens or live projects are required."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inspect_sonarcloud_link as inspector
from sonarcloud_api import SonarCloudClient
from url_parser import parse_sonarcloud_url


@pytest.fixture(autouse=True)
def clean_sonar_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("SONARCLOUD_"):
            monkeypatch.delenv(key)


def response(status=200, payload=None):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps({} if payload is None else payload).encode()
    result.headers["Content-Type"] = "application/json"
    return result


@pytest.mark.parametrize("url", ["http://sonarcloud.io/dashboard?id=x", "https://sonarcloud.io.evil.invalid/dashboard?id=x", "https://evil-sonarcloud.io/dashboard?id=x", "https://sonarqube.us.evil.invalid/dashboard?id=x", "/dashboard?id=x", "https://u:p@sonarcloud.io/dashboard?id=x", "https://sonarcloud.io:8080/dashboard?id=x", "https://sonarcloud.io/dashboard?id=x&branch=a&pullRequest=1"])
def test_invalid_urls_are_input_errors(url):
    with patch.object(SonarCloudClient, "get") as get:
        result = inspector.inspect_link(url)
    assert result["error_kind"] == "input"
    assert result["fetch_status"] == "failed"
    get.assert_not_called()


@pytest.mark.parametrize("host", ["sonarcloud.io", "sonarqube.us"])
def test_region_and_pr_context(host):
    with patch.object(requests.Session, "request", return_value=response(payload={"issues": [{"key": "i", "message": "finding"}]})) as request:
        result = inspector.inspect_link(f"https://{host}/project/issues?id=p&issues=i&pullRequest=42")
    assert result["fetch_status"] == "complete"
    assert request.call_args.args[1] == f"https://{host}/api/issues/search"
    assert request.call_args.kwargs["params"]["pullRequest"] == "42"
    assert result["request_context"]["pull_request"] == "42"


def test_batch_uses_separate_regions_and_retains_each_error():
    def request(method, url, **kwargs):
        return response(403) if "sonarqube.us" in url else response(payload={"issues": [{"key": "i"}]})
    with patch.object(requests.Session, "request", side_effect=request) as call:
        result = inspector.inspect_links(["https://sonarcloud.io/project/issues?issues=i", "https://sonarqube.us/project/issues?issues=i"])
    assert result["fetch_status"] == "partial"
    assert [r["fetch_status"] for r in result["results"]] == ["complete", "failed"]
    assert call.call_count == 2


def test_endpoint_region_conflict(monkeypatch):
    monkeypatch.setenv("SONARCLOUD_BASE_URL", "https://sonarcloud.io")
    assert inspector.main(["https://sonarqube.us/dashboard?id=p"]) == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_permanent_http_failures_not_retried(status):
    client = SonarCloudClient()
    with patch.object(client.session, "request", return_value=response(status)) as call, patch("sonarcloud_api.time.sleep") as sleep:
        with pytest.raises(requests.HTTPError):
            client.get("/api/issues/search")
    assert call.call_count == 1
    sleep.assert_not_called()


@pytest.mark.parametrize("status", [429, 500, 503])
def test_transient_http_retried(status):
    client = SonarCloudClient()
    with patch.object(client.session, "request", side_effect=[response(status), response(payload={"ok": True})]) as call, patch("sonarcloud_api.time.sleep"):
        assert client.get("/api/issues/search") == {"ok": True}
    assert call.call_count == 2


def test_retry_after_is_bounded():
    limited = response(429)
    limited.headers["Retry-After"] = "9999"
    client = SonarCloudClient()
    with patch.object(client.session, "request", side_effect=[limited, response()]), patch("sonarcloud_api.time.sleep") as sleep:
        client.get("/api/issues/search")
    sleep.assert_called_once_with(60)


def test_timeout_budget_and_redacted_failure():
    with patch.object(requests.Session, "request", side_effect=requests.Timeout("credential=fixture-private-value")) as call, patch("sonarcloud_api.time.sleep"):
        result = inspector.inspect_link("https://sonarcloud.io/project/issues?issues=i")
    assert call.call_count == 3
    assert result["error"] == "Timeout"
    assert "fixture-private-value" not in json.dumps(result)


def test_invalid_json_is_fetch_error_not_retried():
    broken = response()
    broken._content = b"not json"
    with patch.object(requests.Session, "request", return_value=broken) as call:
        result = inspector.inspect_link("https://sonarcloud.io/project/issues?issues=i")
    assert result["error_kind"] == "fetch"
    assert result["fetch_status"] == "failed"
    assert call.call_count == 1


def test_missing_resource_and_exit_status(capsys):
    with patch.object(requests.Session, "request", return_value=response(payload={"issues": []})):
        assert inspector.main(["https://sonarcloud.io/project/issues?issues=i"]) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "Issue not found"


def test_project_partial_and_total_failure():
    def request(method, url, **kwargs):
        if url.endswith("/api/measures/component"):
            return response(payload={"component": {"measures": [{"metric": "ncloc", "value": "10"}]}})
        return response(403)
    with patch.object(requests.Session, "request", side_effect=request):
        partial = inspector.inspect_link("https://sonarcloud.io/dashboard?id=p&branch=feature")
    assert partial["fetch_status"] == "partial"
    assert partial["summary"]["metrics"]["ncloc"] == "10"
    with patch.object(requests.Session, "request", return_value=response(403)):
        failed = inspector.inspect_link("https://sonarcloud.io/dashboard?id=p")
    assert failed["fetch_status"] == "failed"


def test_partial_rule_fetch_keeps_issue():
    with patch.object(requests.Session, "request", side_effect=[response(payload={"issues": [{"key": "i", "rule": "r"}]}), response(403)]):
        result = inspector.inspect_link("https://sonarcloud.io/project/issues?issues=i")
    assert result["resource_key"] == "i"
    assert result["fetch_status"] == "partial"


def test_hotspot_context_is_retained_without_claiming_verification():
    with patch.object(requests.Session, "request", return_value=response(payload={"key": "h"})):
        result = inspector.inspect_link("https://sonarcloud.io/project/security_hotspots?hotspots=h&branch=feature")
    assert result["request_context"]["branch"] == "feature"
    assert result["fetch_status"] == "partial"
    assert "does not verify" in result["warnings"][0]


def test_no_token_or_redirect_leak():
    result = inspector.inspect_link("https://user:secret@sonarcloud.io/dashboard?id=p&token=fixture-private-value")
    assert "secret" not in result["source_url"]
    assert "fixture-private-value" not in json.dumps(result)
    with patch.object(requests.Session, "request", return_value=response(302)) as call:
        result = inspector.inspect_link("https://sonarcloud.io/project/issues?issues=i")
    assert result["fetch_status"] == "failed"
    assert call.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("kwargs", [{"max_retries": -1}, {"max_retries": 6}, {"timeout_seconds": 0}, {"retry_backoff_seconds": float("nan")}, {"base_url": "https://evil.invalid"}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        SonarCloudClient(**kwargs)


def test_batch_cli_exit_input_precedence_and_markdown(capsys):
    with patch.object(requests.Session, "request", return_value=response(403)):
        assert inspector.main(["https://sonarcloud.io/project/issues?issues=i", "invalid", "--format", "markdown"]) == 2
    output = capsys.readouterr().out
    assert "partial" not in output
    assert "failed" in output
    assert "HTTP 403" in output


def test_hotspot_embedded_rule_and_component_object():
    payload = {"key": "h", "component": {"key": "p:file", "path": "src/app.py"}, "rule": {"key": "r", "riskDescription": "Risk details", "fixRecommendations": "Review guidance"}}
    with patch.object(requests.Session, "request", side_effect=[response(payload=payload), response(payload={"rule": {"key": "r"}})]) as call:
        result = inspector.inspect_link("https://sonarcloud.io/project/security_hotspots?hotspots=h")
    assert call.call_args.kwargs["params"]["key"] == "r"
    assert result["fetch_status"] == "complete"
    assert result["location"]["file_path"] == "src/app.py"
    assert result["agent_summary"]["how_to_review_or_fix"] == "Review guidance"


def test_response_key_mismatch_is_not_a_complete_fetch():
    with patch.object(requests.Session, "request", return_value=response(payload={"issues": [{"key": "different"}]})):
        result = inspector.inspect_link("https://sonarcloud.io/project/issues?issues=i")
    assert result["fetch_status"] == "failed"
    assert result["error_kind"] == "fetch"
