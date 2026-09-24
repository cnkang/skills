#!/usr/bin/env python3
"""Local, privacy-minimizing telemetry and benchmark helper for dev-jev.

This script never calls Jev and accepts no prompt/source payload fields.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

MODES = {"off", "shadow", "advisory"}
PRIMITIVES = {"noul", "choice", "score"}
SAFE_LABEL = re.compile(r"^[A-Za-z0-9_.:/+-]{1,96}$")
OPAQUE_TOKEN = re.compile(r"^[A-Za-z0-9_-]{32,}$")
SECRET_MARKER = re.compile(
    r"(?i)(?:\b(?:api[_-]?key|password|secret|bearer|authorization|token)\b\s*[:=]|"
    r"\b(?:sk|rk|ghp|gho|ghu|ghs|ghr|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{8,}|"
    r"\bAKIA[A-Z0-9]{16}\b|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.)"
)


def resolve_mode(value: str | None) -> str:
    """Unset means shadow; invalid values fail safe to off."""
    if value is None or not value.strip():
        return "shadow"
    normalized = value.strip().lower()
    return normalized if normalized in MODES else "off"


def _valid_probability(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def _valid_nonnegative(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0.0
    )


def confidence_band(primitive: str, confidence: Any = None, probability: Any = None) -> str:
    """Apply the skill's conservative, primitive-aware initial routing bands."""
    if primitive in {"choice", "score"}:
        if not _valid_probability(confidence):
            return "LOW"
        value = float(confidence)
        if value >= 0.90:
            return "HIGH"
        if value >= 0.50:
            return "MEDIUM"
        return "LOW"
    if primitive == "noul":
        if not _valid_probability(probability):
            return "LOW"
        top_outcome_probability = max(float(probability), 1.0 - float(probability))
        if top_outcome_probability >= 0.90:
            return "HIGH"
        if top_outcome_probability >= 0.75:
            return "MEDIUM"
        return "LOW"
    return "LOW"


def default_log_path(environ: dict[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    override = env.get("DEV_JEV_LOG")
    if override:
        return Path(override).expanduser()
    home = Path(env.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()
    return home / "logs" / "dev-jev.jsonl"


def _safe_label(value: Any, field: str, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{field} is required")
        return None
    text = str(value)
    if not SAFE_LABEL.fullmatch(text) or SECRET_MARKER.search(text) or OPAQUE_TOKEN.fullmatch(text):
        raise ValueError(f"{field} must be a short, non-sensitive label (no spaces, payload text, or token-like value)")
    return text


def _number(value: Any, field: str, *, minimum: float = 0.0, maximum: float | None = None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < minimum or (maximum is not None and result > maximum):
        raise ValueError(f"{field} is outside its valid range")
    return result


def parse_scalar(text: str) -> Any:
    """Parse a short JSON scalar, or preserve a plain short label; reject objects."""
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = text
    if isinstance(value, (dict, list)) or value is None:
        raise argparse.ArgumentTypeError("use a short scalar label, not JSON objects, arrays, or null")
    if isinstance(value, str):
        try:
            _safe_label(value, "label", required=True)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from exc
    if isinstance(value, float) and not math.isfinite(value):
        raise argparse.ArgumentTypeError("number must be finite")
    return value


def parse_bool(text: str) -> bool:
    lowered = text.strip().lower()
    if lowered in {"true", "yes", "1"}:
        return True
    if lowered in {"false", "no", "0"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    if os.name != "nt":
        try:
            path.chmod(0o600)
        except OSError:
            pass


def _record(args: argparse.Namespace) -> int:
    primitive = args.primitive
    result = args.result
    if isinstance(result, str):
        result = _safe_label(result, "result", required=True)
    confidence = _number(args.confidence, "confidence", maximum=1.0)
    probability = _number(args.probability, "probability", maximum=1.0)
    latency_ms = _number(args.latency_ms, "latency_ms", maximum=3_600_000.0)
    cost = _number(args.provider_cost_usd, "provider_cost_usd")
    tokens = args.main_model_tokens_avoided
    if tokens is not None and tokens < 0:
        raise ValueError("main_model_tokens_avoided must be non-negative")
    if primitive == "noul" and probability is None and args.call_status == "success":
        raise ValueError("successful Noul records need --probability")
    if primitive in {"choice", "score"} and confidence is None and args.call_status == "success":
        # Missing confidence is allowed and intentionally maps to LOW.
        pass

    env_mode = resolve_mode(os.environ.get("DEV_JEV_MODE"))
    mode = args.mode or env_mode
    event = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "workflow": _safe_label(args.workflow, "workflow", required=True),
        "decision_type": _safe_label(args.decision_type, "decision_type", required=True),
        "question_id": _safe_label(args.question_id, "question_id", required=True),
        "primitive": primitive,
        "result": result,
        "confidence": confidence,
        "probability": probability,
        "confidence_band": "LOW" if args.force_low_confidence else confidence_band(primitive, confidence, probability),
        "latency_ms": latency_ms,
        "fallback_used": bool(args.fallback_used),
        "call_status": args.call_status,
        "final_hermes_action": _safe_label(args.final_hermes_action, "final_hermes_action", required=True),
        "mode": mode,
        "request_id": _safe_label(args.request_id, "request_id"),
        "ground_truth": args.ground_truth,
        "hermes_agreed": args.hermes_agreed,
        "provider_cost_usd": cost,
        "main_model_tokens_avoided": tokens,
        "model": _safe_label(args.model, "model"),
    }
    path = Path(args.log).expanduser() if args.log else default_log_path()
    _append_event(path, event)
    print(f"recorded 1 dev-jev event: {path}")
    return 0


def _bool_label(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"yes", "true", "1", "positive"}:
            return True
        if lowered in {"no", "false", "0", "negative"}:
            return False
    return None


def _same_label(actual: Any, expected: Any, primitive: str) -> bool:
    if primitive == "score":
        try:
            return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-6)
        except (TypeError, ValueError):
            return str(actual).strip().casefold() == str(expected).strip().casefold()
    return str(actual).strip().casefold() == str(expected).strip().casefold()


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _unique_request_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Avoid multiplying per-request measures when each question is logged."""
    selected: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events):
        key = event.get("request_id") or f"__row_{index}"
        selected.setdefault(str(key), event)
    return list(selected.values())


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def summarize(records: Iterable[dict[str, Any]], noul_threshold: float = 0.75) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in records:
        workflow = str(event.get("workflow", "unknown"))
        decision_type = str(event.get("decision_type", "unknown"))
        grouped[(workflow, decision_type)].append(event)

    by_workflow: dict[str, dict[str, Any]] = {}
    for (workflow, decision_type), events in sorted(grouped.items()):
        successful = [e for e in events if e.get("call_status", "success") == "success"]
        labelled = [e for e in successful if e.get("ground_truth") is not None]
        correct = 0
        false_negatives = 0
        positive_labels = 0
        noul_labelled = 0
        for event in labelled:
            primitive = event.get("primitive")
            truth = event.get("ground_truth")
            if primitive == "noul":
                label = _bool_label(truth)
                probability = event.get("probability")
                if label is None or not _valid_probability(probability):
                    continue
                noul_labelled += 1
                if label:
                    positive_labels += 1
                    if float(probability) < noul_threshold:
                        false_negatives += 1
                prediction = float(probability) >= noul_threshold
                if prediction == label:
                    correct += 1
            elif primitive in {"choice", "score"}:
                if _same_label(event.get("result"), truth, str(primitive)):
                    correct += 1

        accuracy_denominator = sum(
            1 for e in labelled
            if (e.get("primitive") == "noul" and _bool_label(e.get("ground_truth")) is not None and _valid_probability(e.get("probability")))
            or e.get("primitive") in {"choice", "score"}
        )
        low_count = sum(1 for e in successful if e.get("confidence_band", "LOW") == "LOW")
        disagreement = [e for e in successful if isinstance(e.get("hermes_agreed"), bool)]
        request_events = _unique_request_events(events)
        latencies = [float(e["latency_ms"]) for e in request_events if _valid_nonnegative(e.get("latency_ms"))]
        costs = [float(e["provider_cost_usd"]) for e in request_events if _valid_nonnegative(e.get("provider_cost_usd"))]
        saved_tokens = [int(e["main_model_tokens_avoided"]) for e in request_events if isinstance(e.get("main_model_tokens_avoided"), int) and not isinstance(e.get("main_model_tokens_avoided"), bool) and e["main_model_tokens_avoided"] >= 0]
        fallback_requests = [e for e in request_events if isinstance(e.get("fallback_used"), bool)]
        metrics = {
            "call_count": len(events),
            "successful_answers": len(successful),
            "labeled_answers": accuracy_denominator,
            "decision_accuracy": _ratio(correct, accuracy_denominator),
            "noul_labeled_answers": noul_labelled,
            "noul_positive_labels": positive_labels,
            "false_negative_cases": false_negatives,
            "false_negative_rate": _ratio(false_negatives, positive_labels),
            "low_confidence_answers": low_count,
            "low_confidence_rate": _ratio(low_count, len(successful)),
            "hermes_disagreements": sum(1 for e in disagreement if e.get("hermes_agreed") is False),
            "hermes_comparable_answers": len(disagreement),
            "hermes_disagreement_rate": _ratio(sum(1 for e in disagreement if e.get("hermes_agreed") is False), len(disagreement)),
            "latency_ms_p50": _percentile(latencies, 0.50),
            "latency_ms_p95": _percentile(latencies, 0.95),
            "provider_cost_usd_known_total": sum(costs) if costs else None,
            "main_model_tokens_avoided_known_total": sum(saved_tokens) if saved_tokens else None,
            "fallback_requests": sum(1 for e in fallback_requests if e.get("fallback_used") is True),
            "fallback_rate": _ratio(sum(1 for e in fallback_requests if e.get("fallback_used") is True), len(fallback_requests)),
        }
        by_workflow.setdefault(workflow, {})[decision_type] = metrics

    return {
        "measurement": {
            "noul_yes_threshold": noul_threshold,
            "accuracy_uses_only_verified_ground_truth": True,
            "groups_are_separate_by_workflow_and_decision_type": True,
        },
        "workflows": by_workflow,
    }


def _read_events(path: Path) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    invalid = 0
    if not path.exists():
        return events, invalid
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue
            if isinstance(event, dict) and event.get("schema_version") == 1:
                events.append(event)
            else:
                invalid += 1
    return events, invalid


def _benchmark(args: argparse.Namespace) -> int:
    path = Path(args.log).expanduser() if args.log else default_log_path()
    records, invalid = _read_events(path)
    if args.workflow:
        records = [e for e in records if e.get("workflow") == args.workflow]
    result = summarize(records, args.noul_threshold)
    result["source"] = str(path)
    result["invalid_lines_ignored"] = invalid
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("mode", help="print the effective mode (unset defaults to shadow)")

    record = sub.add_parser("record", help="append one short, sanitized judgment record")
    record.add_argument("--workflow", required=True)
    record.add_argument("--decision-type", required=True)
    record.add_argument("--question-id", required=True)
    record.add_argument("--primitive", required=True, choices=sorted(PRIMITIVES))
    record.add_argument("--result", required=True, type=parse_scalar)
    record.add_argument("--confidence", type=float)
    record.add_argument("--probability", type=float)
    record.add_argument("--latency-ms", type=float)
    record.add_argument("--fallback-used", type=parse_bool, default=False)
    record.add_argument("--force-low-confidence", type=parse_bool, default=False,
                        help="apply a conservative external policy override, e.g. unsupported language")
    record.add_argument("--call-status", choices=["success", "unavailable", "error"], default="success")
    record.add_argument("--final-hermes-action", required=True)
    record.add_argument("--mode", choices=sorted(MODES))
    record.add_argument("--request-id")
    record.add_argument("--ground-truth", type=parse_scalar)
    record.add_argument("--hermes-agreed", type=parse_bool)
    record.add_argument("--provider-cost-usd", type=float)
    record.add_argument("--main-model-tokens-avoided", type=int)
    record.add_argument("--model")
    record.add_argument("--log", help="override the JSONL destination")

    benchmark = sub.add_parser("benchmark", help="summarize labeled outcomes, split by workflow/question")
    benchmark.add_argument("--workflow")
    benchmark.add_argument("--noul-threshold", type=float, default=0.75)
    benchmark.add_argument("--log", help="read a specific JSONL file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "mode":
            raw = os.environ.get("DEV_JEV_MODE")
            resolved = resolve_mode(raw)
            if raw and raw.strip().lower() not in MODES:
                print("invalid DEV_JEV_MODE; failing safe to off", file=sys.stderr)
            print(resolved)
            return 0
        if args.command == "record":
            return _record(args)
        if args.command == "benchmark":
            if not _valid_probability(args.noul_threshold):
                raise ValueError("--noul-threshold must be between 0 and 1")
            return _benchmark(args)
        parser.error("unknown command")
    except (OSError, ValueError) as exc:
        print(f"dev-jev telemetry error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
