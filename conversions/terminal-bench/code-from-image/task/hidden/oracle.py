"""Oracle for code-from-image: /app/output.txt, stripped, equals upstream's literal.

Upstream's tests (tests/test_outputs.py) assert that the file exists, that its
text after `str.strip()` starts with the hint prefix, and that it equals the
full hash. Both literals are in hidden/expected.json.
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
    return Plan(artifact_contexts={"output": resources.read_json("expected.json")}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "output" or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    prefix = context.get("prefix")
    expected = context.get("output")
    if not isinstance(prefix, str) or not isinstance(expected, str):
        return Judgment(False, {"reason": "malformed context"})
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    # test_output_file_exists; upstream then opens the file as UTF-8 text,
    # which fails on anything that is not a readable regular file.
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"/app/output.txt is {found.status.value}"})
    if not isinstance(found.value, Text):
        return Judgment(False, {"reason": "output is not text"})
    # Python's str.strip(), as in test_output_is_correct.
    output = found.value.text.strip()
    if not output.startswith(prefix):
        return Judgment(False, {"reason": "output does not start with the hint prefix"})
    if output != expected:
        return Judgment(False, {"reason": "output is not the expected hash"})
    return Judgment(True, None)
