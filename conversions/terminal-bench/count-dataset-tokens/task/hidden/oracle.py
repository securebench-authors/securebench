"""Oracle for count-dataset-tokens.

Upstream's only test reads /app/answer.txt with `Path.read_text()` and asserts
that its expected string occurs in the text. This Oracle makes the same
substring test on the text the artifact check decoded, with the expected
string from hidden/expected.json. The file is bounded by the artifact check
(16 MiB), so the work is one substring search over at most 16 MiB of text.
"""

from securebench.core.errors import Rejected
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

CHECK = "answer"
PATH = "/app/answer.txt"


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if not isinstance(expected, dict) or not _usable(expected.get("expected_output")):
        raise Rejected("hidden/expected.json must hold a non-empty string expected_output")
    return Plan(artifact_contexts={CHECK: expected["expected_output"]}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected check"})
    if not _usable(context):
        return Judgment(False, {"reason": "malformed context"})
    if len(evidence.files) != 1 or evidence.files[0].path != PATH or evidence.listings:
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"{PATH} is {found.status.value}"})
    if not isinstance(found.value, Text):
        return Judgment(False, {"reason": "unexpected evidence"})
    if context not in found.value.text:
        return Judgment(False, {"reason": "the expected count does not occur in the answer"})
    return Judgment(True, None)


def _usable(value: JsonValue) -> bool:
    # An empty string occurs in every text, so it would pass anything.
    return isinstance(value, str) and value != ""
