"""Oracle for gcode-to-text.

Upstream asserts that `Path("/app/out.txt").read_text().strip()` equals the
flag. The artifact check reads the file with the `text` parser (strict UTF-8,
at most 1 MiB), and `judge` applies the same `str.strip()` and the same
equality. The work is one pass over at most 1 MiB of text.
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
PATH = "/app/out.txt"
SHOWN = 256


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if not isinstance(expected, dict) or not _flag(expected.get("text")):
        raise Rejected("hidden/expected.json must hold a non-empty stripped text")
    return Plan(artifact_contexts={CHECK: expected["text"]}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected check"})
    if not isinstance(context, str) or not _flag(context):
        return Judgment(False, {"reason": "malformed context"})
    if len(evidence.files) != 1 or evidence.files[0].path != PATH or evidence.listings:
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"{PATH} is {found.status.value}"})
    if not isinstance(found.value, Text):
        return Judgment(False, {"reason": "unexpected evidence"})
    got = found.value.text.strip()
    if got != context:
        return Judgment(False, {"reason": "wrong text", "got": got[:SHOWN]})
    return Judgment(True, None)


def _flag(value: JsonValue) -> bool:
    return isinstance(value, str) and value != "" and value == value.strip()
