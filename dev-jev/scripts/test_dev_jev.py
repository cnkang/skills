#!/usr/bin/env python3
"""Offline tests for dev-jev mode, confidence policy, telemetry, and benchmarks."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import telemetry


class ModePolicyTests(unittest.TestCase):
    def test_default_is_shadow(self):
        self.assertEqual(telemetry.resolve_mode(None), "shadow")
        self.assertEqual(telemetry.resolve_mode(""), "shadow")

    def test_supported_modes_and_invalid_fails_safe(self):
        for mode in ("off", "shadow", "advisory"):
            self.assertEqual(telemetry.resolve_mode(mode), mode)
        self.assertEqual(telemetry.resolve_mode("unknown"), "off")

    def test_cli_reports_environment_mode(self):
        out = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(out):
            self.assertEqual(telemetry.main(["mode"]), 0)
        self.assertEqual(out.getvalue().strip(), "shadow")


class ConfidencePolicyTests(unittest.TestCase):
    def test_choice_score_bands(self):
        self.assertEqual(telemetry.confidence_band("choice", 0.90), "HIGH")
        self.assertEqual(telemetry.confidence_band("score", 0.50), "MEDIUM")
        self.assertEqual(telemetry.confidence_band("choice", 0.49), "LOW")
        self.assertEqual(telemetry.confidence_band("score", None), "LOW")

    def test_noul_uses_top_outcome_probability_not_yes_probability_as_confidence(self):
        self.assertEqual(telemetry.confidence_band("noul", probability=0.95), "HIGH")
        self.assertEqual(telemetry.confidence_band("noul", probability=0.80), "MEDIUM")
        self.assertEqual(telemetry.confidence_band("noul", probability=0.50), "LOW")
        self.assertEqual(telemetry.confidence_band("noul", probability=0.05), "HIGH")
        self.assertEqual(telemetry.confidence_band("noul", probability=2), "LOW")


class TelemetryTests(unittest.TestCase):
    def record(self, path: Path, *args: str) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(telemetry.main(["record", *args, "--log", str(path)]), 0)

    def test_default_log_is_profile_local_and_overridable(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "profile-home"
            self.assertEqual(telemetry.default_log_path({"HERMES_HOME": str(home)}), home / "logs" / "dev-jev.jsonl")
            override = Path(tmp) / "custom-events.jsonl"
            self.assertEqual(telemetry.default_log_path({"DEV_JEV_LOG": str(override)}), override)

    def test_records_whitelisted_fields_without_prompt_or_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            self.record(path,
                "--workflow", "ci_failure", "--decision-type", "worth_retrying",
                "--question-id", "retry", "--primitive", "noul", "--result", "uncertain",
                "--probability", "0.68", "--latency-ms", "420", "--fallback-used", "false",
                "--final-hermes-action", "inspect-current-diff", "--mode", "shadow",
                "--request-id", "req-1")
            event = json.loads(path.read_text().strip())
            self.assertEqual(event["schema_version"], 1)
            self.assertEqual(event["confidence_band"], "LOW")
            self.assertEqual(event["probability"], 0.68)
            self.assertEqual(event["timestamp"][-1], "Z")
            self.assertNotIn("state", event)
            self.assertNotIn("prompt", event)
            self.assertNotIn("source", event)
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_external_policy_can_force_low_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            self.record(path,
                "--workflow", "task_triage", "--decision-type", "category",
                "--question-id", "type", "--primitive", "noul", "--result", "yes",
                "--probability", "0.98", "--force-low-confidence", "true",
                "--final-hermes-action", "inspect-repository")
            event = json.loads(path.read_text().strip())
            self.assertEqual(event["confidence_band"], "LOW")
            self.assertEqual(event["probability"], 0.98)

    def test_rejects_structured_payload_and_opaque_labels(self):
        opaque_label = "a" * 32
        self.assertTrue(telemetry.OPAQUE_TOKEN.fullmatch(opaque_label))
        for value in ('{"private":1}', opaque_label):
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
                telemetry.main(["record", "--workflow", "ci", "--decision-type", "retry",
                    "--question-id", "q1", "--primitive", "noul", "--result", value,
                    "--probability", "0.5", "--final-hermes-action", "debug"])

    def test_benchmark_is_separate_per_workflow_and_decision(self):
        sample = [
            {"schema_version": 1, "workflow": "ci_failure", "decision_type": "retry",
             "primitive": "noul", "result": "yes", "probability": 0.80, "confidence_band": "MEDIUM",
             "ground_truth": True, "latency_ms": 100, "request_id": "a", "fallback_used": False,
             "hermes_agreed": True},
            {"schema_version": 1, "workflow": "ci_failure", "decision_type": "retry",
             "primitive": "noul", "result": "no", "probability": 0.20, "confidence_band": "MEDIUM",
             "ground_truth": True, "latency_ms": 300, "request_id": "b", "fallback_used": True,
             "hermes_agreed": False},
            {"schema_version": 1, "workflow": "task_triage", "decision_type": "category",
             "primitive": "choice", "result": "bugfix", "confidence": 0.95, "confidence_band": "HIGH",
             "ground_truth": "bugfix", "latency_ms": 1000, "request_id": "c", "fallback_used": False},
        ]
        summary = telemetry.summarize(sample, noul_threshold=0.75)
        ci = summary["workflows"]["ci_failure"]["retry"]
        triage = summary["workflows"]["task_triage"]["category"]
        self.assertEqual(ci["decision_accuracy"], 0.5)
        self.assertEqual(ci["false_negative_cases"], 1)
        self.assertEqual(ci["false_negative_rate"], 0.5)
        self.assertEqual(ci["latency_ms_p50"], 200.0)
        self.assertEqual(ci["latency_ms_p95"], 290.0)
        self.assertEqual(ci["fallback_rate"], 0.5)
        self.assertEqual(triage["decision_accuracy"], 1.0)
        self.assertEqual(len(summary["workflows"]), 2)

    def test_benchmark_cli_reads_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            self.record(path,
                "--workflow", "task_triage", "--decision-type", "category",
                "--question-id", "type", "--primitive", "choice", "--result", "bugfix",
                "--confidence", "0.95", "--ground-truth", "bugfix",
                "--final-hermes-action", "inspect-python-module")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(telemetry.main(["benchmark", "--log", str(path)]), 0)
            report = json.loads(out.getvalue())
            metric = report["workflows"]["task_triage"]["category"]
            self.assertEqual(metric["decision_accuracy"], 1.0)
            self.assertEqual(report["measurement"]["noul_yes_threshold"], 0.75)

    def test_request_metrics_are_not_multiplied_per_answer(self):
        rows = [
            {"workflow": "review", "decision_type": "risk", "primitive": "noul", "call_status": "success",
             "probability": 0.8, "confidence_band": "MEDIUM", "request_id": "same", "latency_ms": 90,
             "provider_cost_usd": 0.01, "main_model_tokens_avoided": 30, "fallback_used": False},
            {"workflow": "review", "decision_type": "risk", "primitive": "noul", "call_status": "success",
             "probability": 0.9, "confidence_band": "HIGH", "request_id": "same", "latency_ms": 90,
             "provider_cost_usd": 0.01, "main_model_tokens_avoided": 30, "fallback_used": False},
        ]
        metrics = telemetry.summarize(rows)["workflows"]["review"]["risk"]
        self.assertEqual(metrics["call_count"], 2)
        self.assertEqual(metrics["latency_ms_p50"], 90.0)
        self.assertEqual(metrics["provider_cost_usd_known_total"], 0.01)
        self.assertEqual(metrics["main_model_tokens_avoided_known_total"], 30)
        self.assertEqual(metrics["fallback_rate"], 0.0)

    def test_unavailable_jev_is_recorded_as_fallback_without_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                result = telemetry.main(["record", "--workflow", "loop_control", "--decision-type", "next_step",
                    "--question-id", "next", "--primitive", "choice", "--result", "unavailable",
                    "--fallback-used", "true", "--call-status", "unavailable",
                    "--final-hermes-action", "replan-with-hermes", "--mode", "shadow", "--log", str(path)])
            self.assertEqual(result, 0)
            event = json.loads(path.read_text().strip())
            self.assertTrue(event["fallback_used"])
            self.assertEqual(event["call_status"], "unavailable")
            self.assertEqual(event["confidence_band"], "LOW")
            self.assertIsNone(event["confidence"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
