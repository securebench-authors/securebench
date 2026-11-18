"""Oracle for mteb-retrieve: /app/result.txt holds exactly the expected line.

Upstream's test reads the file with `open(...).readlines()`, requires exactly
one line, and compares that line after `str.strip()` with the expected text.
"""

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
    return Plan(artifact_contexts={"result": resources.read_json("expected.json")}, cases={})


def readlines(text: str) -> list[str]:
    # Python's text mode uses universal newlines, so `readlines` ends a line at
    # "\r\n", "\r" or "\n". The SecureBench text parser splits on "\n" only,
    # so the lines are recounted from the full text.
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = unified.split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "result" or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(context, dict) or not isinstance(context.get("line"), str):
        return Judgment(False, {"reason": "malformed context"})
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "unexpected number of files"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return Judgment(False, {"reason": f"result.txt is {found.status.value}"})
    lines = readlines(found.value.text)
    if len(lines) != 1:
        return Judgment(False, {"reason": f"result.txt has {len(lines)} lines, expected exactly one"})
    if lines[0].strip() != context["line"]:
        return Judgment(False, {"reason": "result.txt contains unexpected value"})
    return Judgment(True, None)
