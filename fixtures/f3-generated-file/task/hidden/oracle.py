"""Oracle for fixture F3: /srv/out.json must hold the challenge's numbers in ascending order."""

from random import Random

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    generator = Random(seed)
    cases: list[Case] = []
    for size in (0, 1, 5, 20):
        numbers: list[JsonValue] = [generator.randint(-1000, 1000) for _ in range(size)]
        expected: list[JsonValue] = [number for number in sorted(numbers)]  # type: ignore
        cases.append(Case({"numbers": numbers}, {"sorted": expected}))
    return Plan(artifact_contexts={}, cases={"sorting": tuple(cases)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or observation.get("exit_status") != 0:
        return Judgment(False, {"reason": "solve.py did not exit with status 0"})
    out = evidence.output_artifacts[0]
    if out.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"/srv/out.json is {out.status.value}"})
    value = out.value
    if not isinstance(value, dict) or set(value) != {"sorted"}:
        return Judgment(False, {"reason": "out.json must be an object with one key 'sorted'"})
    items = value["sorted"]
    if not isinstance(items, list) or any(type(item) is not int for item in items):
        return Judgment(False, {"reason": "'sorted' must be a list of integers"})
    if not isinstance(context, dict) or items != context["sorted"]:
        return Judgment(False, {"reason": "wrong order", "expected": context, "got": items})
    return Judgment(True, None)
