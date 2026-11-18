"""Oracle for raman-fitting: upstream's three tests, one case each.

The expected values, tolerances and comparison forms come from hidden/cases.json, which
copies them from upstream's tests/test_outputs.py. The comparisons below are upstream's
expressions: `abs(value - expected) < tolerance` and `abs(1 - value / expected) < tolerance`.
"""

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.evidence import Case
from securebench.core.jsondata import JsonValue

CHECK = "results"


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    assert isinstance(data, dict) and isinstance(data["cases"], list)
    cases = tuple(
        Case(challenge=entry["challenge"], context={"test": entry["test"], "expected": entry["expected"]})
        for entry in data["cases"]
    )
    return Plan(artifact_contexts={}, cases={CHECK: cases})


def _fail(test: JsonValue, reason: str, **details: JsonValue) -> Judgment:
    return Judgment(False, {"test": test, "reason": reason, **details})


def _as_float(value: JsonValue) -> float | None:
    if type(value) is float:
        return value
    if type(value) is int:
        # The observation schema bounds numbers to the float range, but a forged
        # observation is not trusted to respect it.
        try:
            return float(value)
        except OverflowError:
            return None
    return None


def _within(value: float, expected: float, comparison: str, tolerance: float) -> bool:
    if comparison == "absolute":
        return abs(value - expected) < tolerance
    if comparison == "relative":
        return abs(1 - value / expected) < tolerance
    return False


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return _fail(None, "unexpected check or evidence")
    test = context.get("test")
    if not isinstance(evidence.outcome, Observed):
        return _fail(test, "no observation")
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return _fail(test, "observation is not an object")

    expected = context.get("expected")
    if expected is None:
        # test_result_file_exists: `assert result_path.exists()`.
        if observation.get("exists") is not True:
            return _fail(test, "/app/results.json does not exist")
        return Judgment(True, {"test": test})

    if not isinstance(expected, dict):
        return _fail(test, "malformed context")
    if observation.get("loaded") is not True:
        return _fail(test, "/app/results.json could not be read as JSON")
    fields = observation.get("fields")
    if not isinstance(fields, dict):
        return _fail(test, "the peak is missing from /app/results.json")

    wrong: dict[str, JsonValue] = {}
    for name, spec in expected.items():
        if not isinstance(spec, dict):
            return _fail(test, "malformed context")
        report = fields.get(name)
        if not isinstance(report, dict):
            wrong[name] = "not reported"
            continue
        value = _as_float(report.get("value"))
        if value is None:
            # Missing keys, strings, null, containers, NaN, infinities and ints beyond the
            # float range all make upstream's test raise or compare false.
            wrong[name] = {"kind": report.get("kind")}
            continue
        target = spec.get("value")
        tolerance = spec.get("tolerance")
        comparison = spec.get("comparison")
        if not (type(target) is float and type(tolerance) in (int, float) and isinstance(comparison, str)):
            return _fail(test, "malformed context")
        if not _within(value, target, comparison, tolerance):
            wrong[name] = {"kind": report.get("kind"), "value": value}
    if wrong:
        return _fail(test, "fields outside upstream's tolerance", fields=wrong)
    return Judgment(True, {"test": test})
