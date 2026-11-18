"""Oracle of hf-model-inference: upstream's four tests, judged from typed reports.

Each case's challenge and expected values live in hidden/cases.json. The
adapters report the type and value of every response field the upstream tests
assert on; this module applies the tests' assertions to them.
"""

import math

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, Case, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

CHECKS = ("model-loads", "api")


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    if not isinstance(cases, dict):
        raise ValueError("hidden/cases.json must hold an object")
    return Plan(
        artifact_contexts={},
        cases={check: (Case(cases[check]["challenge"], cases[check]["context"]),) for check in CHECKS},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == "model-loads":
        failures = judge_model(observation)
    elif check_id == "api":
        failures = judge_api(context, observation)
    else:
        return Judgment(False, {"reason": f"unknown check {check_id}"})
    if failures:
        return Judgment(False, {"failures": failures})
    return Judgment(True, None)


def judge_model(observation: dict) -> list:
    """test_model_downloaded: the directory exists, and model and tokenizer load to something."""
    if observation.get("path_exists") is not True:
        return ["model directory not found"]
    failures = []
    for part in ("model", "tokenizer"):
        report = observation.get(part)
        if not isinstance(report, dict):
            failures.append(f"{part} was not loaded")
        elif "error" in report:
            failures.append(f"{part} failed to load: {report['error']}")
        elif report.get("is_none") is not False:
            failures.append(f"{part} loaded as None")
    return failures


def judge_api(context: dict, observation: dict) -> list:
    failures = []

    # test_flask_api_running: the GET must not raise; any status passes.
    root = observation.get("root")
    if not isinstance(root, dict) or "error" in root or not isinstance(root.get("status"), int):
        failures.append({"test": "flask_api_running", "reason": "could not connect to port 5000 on 0.0.0.0"})

    # test_sentiment_endpoint.
    expected = context["expected_positive"]
    reports = observation.get("sentiment")
    if not isinstance(reports, list) or len(reports) != len(expected):
        failures.append({"test": "sentiment_endpoint", "reason": "wrong number of responses"})
    else:
        for index, (report, is_positive) in enumerate(zip(reports, expected)):
            reason = judge_sentiment(context, report, is_positive)
            if reason is not None:
                failures.append({"test": "sentiment_endpoint", "text": index, "reason": reason})

    # test_api_error_handling.
    invalid = observation.get("invalid_request")
    if not isinstance(invalid, dict) or "error" in invalid:
        failures.append({"test": "api_error_handling", "reason": "request failed"})
    elif invalid.get("status") != context["error_status"]:
        failures.append({"test": "api_error_handling", "reason": f"status {invalid.get('status')}"})
    elif invalid.get("json") in (None, "invalid"):
        failures.append({"test": "api_error_handling", "reason": "response is not JSON"})
    elif invalid.get("has_member") is not True:
        failures.append({"test": "api_error_handling", "reason": "response has no 'error' field"})
    return failures


def score(report: object) -> float | None:
    """A reported float, or None when the field is not a JSON float."""
    if not isinstance(report, dict) or report.get("type") != "float":
        return None
    if "number" in report and "nonfinite" not in report:
        number = report["number"]
        return float(number) if isinstance(number, (int, float)) and not isinstance(number, bool) else None
    special = report.get("nonfinite")
    if "number" in report or special is None:
        return None
    return {"inf": math.inf, "-inf": -math.inf, "nan": math.nan}.get(special)


def judge_sentiment(context: dict, report: object, is_positive: bool) -> str | None:
    if not isinstance(report, dict) or "error" in report:
        return "request failed"
    if report.get("status") != context["ok_status"]:
        return f"status {report.get('status')}"
    if report.get("json") != "dict":
        return "response is not a JSON object"
    sentiment = report.get("sentiment")
    confidence = report.get("confidence")
    if not isinstance(sentiment, dict) or sentiment.get("type") == "absent":
        return "missing 'sentiment'"
    if not isinstance(confidence, dict) or confidence.get("type") != "dict":
        return "missing 'confidence' object"
    positive = score(report.get("positive"))
    negative = score(report.get("negative"))
    if sentiment.get("type") != "str" or positive is None or negative is None:
        return "wrong field types"
    label = sentiment.get("string")
    if not isinstance(label, str):
        return "sentiment is not a label"
    # Upstream: a "positive" label needs positive > negative; any other label
    # needs negative > positive.
    if label == context["positive_label"]:
        if not positive > negative:
            return "positive label without higher positive confidence"
    elif not negative > positive:
        return "negative label without higher negative confidence"
    wanted = context["positive_label"] if is_positive else context["negative_label"]
    if label != wanted:
        return f"expected {wanted}"
    return None
