"""Oracle for regex-log.

The upstream test passes when re.findall(regex, log_text, re.MULTILINE) is
exactly equal to its list of expected dates. The adapter reports what findall
returned; we compare it with the expected list from hidden/cases.json.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

CHECK_ID = "findall"


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    cases = tuple(
        Case(challenge=case["challenge"], context={"expected_matches": case["expected_matches"]})
        for case in data["cases"]
    )
    return Plan(artifact_contexts={}, cases={CHECK_ID: cases})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK_ID or not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    groups = observation.get("groups")
    matches = observation.get("matches")
    if not isinstance(groups, int) or isinstance(groups, bool) or not isinstance(matches, list):
        return Judgment(False, {"reason": "observation lacks groups or matches"})

    # With two or more groups findall returns tuples, and upstream's
    # `matches == expected_dates` never finds a tuple equal to a string. An
    # empty result has no tuples in it and goes on to the comparison below.
    if groups > 1 and matches:
        return Judgment(False, {"reason": "findall returned tuples", "groups": groups})

    found: list[str] = []
    for item in matches:
        if not isinstance(item, list) or len(item) != 1 or not isinstance(item[0], str):
            return Judgment(False, {"reason": "findall element is not a single string"})
        found.append(item[0])

    expected = context["expected_matches"] if isinstance(context, dict) else None
    if not isinstance(expected, list):
        return Judgment(False, {"reason": "bad context"})
    if found != expected:
        return Judgment(False, {"reason": "matches differ from the expected dates", "match_count": len(found)})
    return Judgment(True, None)
