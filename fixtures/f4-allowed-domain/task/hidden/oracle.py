"""Oracle for fixture F4: /srv/data.txt must equal the served file exactly."""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read("expected.txt").decode("utf-8")
    return Plan(artifact_contexts={"download": expected}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    data = evidence.files[0]
    if data.status is not FileStatus.PRESENT or not isinstance(data.value, Text):
        return Judgment(False, {"reason": f"/srv/data.txt is {data.status.value}"})
    if data.value.text != context:
        return Judgment(False, {"reason": "content differs", "expected": context})
    return Judgment(True, None)
