"""Oracle for fixture F1: the answer file must hold the expected sum."""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Plan,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    return Plan(artifact_contexts={"answer": expected}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, ArtifactEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    answer = evidence.files[0]
    if answer.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"answer file is {answer.status.value}"})
    value = answer.value
    expected = context["sum"]
    if not isinstance(value, dict) or set(value) != {"sum"} or type(value["sum"]) is not int:
        return Judgment(False, {"reason": "answer must be an object with one integer 'sum'"})
    if value["sum"] != expected:
        return Judgment(False, {"reason": "wrong sum", "expected": expected, "got": value["sum"]})
    return Judgment(True, {"sum": expected})
