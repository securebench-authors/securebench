"""Oracle for feal-linear-cryptanalysis.

Upstream reads /app/plaintexts.txt as text and asserts that each plaintext
of its test's literal occurs in it as a substring, in decimal. This Oracle
makes the same test with the values of hidden/expected.json, which are those
of the literal (hidden/derive.py rederives and checks them). Order, separators
and extra text are free, as upstream. The file is bounded by the artifact
check (1 MiB), so the work here is one substring search over at most 1 MiB of
text per expected value.
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

CHECK = "plaintexts"
PATH = "/app/plaintexts.txt"


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if not isinstance(expected, dict) or not isinstance(expected.get("plaintexts"), list):
        raise Rejected("hidden/expected.json must hold a plaintexts list")
    return Plan(artifact_contexts={CHECK: expected["plaintexts"]}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected check"})
    expected = _expected(context)
    if expected is None:
        return Judgment(False, {"reason": "malformed context"})
    if len(evidence.files) != 1 or evidence.files[0].path != PATH:
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"{PATH} is {found.status.value}"})
    if not isinstance(found.value, Text):
        return Judgment(False, {"reason": "unexpected evidence"})
    text = found.value.text
    missing: list[JsonValue] = [index for index, value in enumerate(expected) if value not in text]
    if missing:
        return Judgment(False, {"reason": "plaintexts missing", "missing_indices": missing})
    return Judgment(True, None)


def _expected(context: JsonValue) -> list[str] | None:
    if not isinstance(context, list) or not context:
        return None
    values: list[str] = []
    for value in context:
        if not isinstance(value, str) or not value.isdigit() or not value.isascii():
            return None
        values.append(value)
    if len(set(values)) != len(values):
        return None
    return values
