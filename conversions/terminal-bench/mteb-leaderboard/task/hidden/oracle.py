"""Oracle for mteb-leaderboard.

Upstream asserts that /app/result.txt exists, that `open(...).readlines()`
returns exactly one line, and that this line, after `strip()`, equals the
model name. The artifact check reads the file with the `text` parser (strict
UTF-8 without a byte-order mark, at most 1 MiB). `judge` repeats what text-mode
`open` does to line endings (universal newlines: `\\r\\n` and a lone `\\r`
become `\\n`), counts lines as `readlines` does, and applies the same `strip()`
and equality. The work is a few passes over at most 1 MiB of text.
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
PATH = "/app/result.txt"
SHOWN = 256


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if not isinstance(expected, dict) or not _name(expected.get("model")):
        raise Rejected("hidden/expected.json must hold a non-empty stripped one-line model name")
    return Plan(artifact_contexts={CHECK: expected["model"]}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected check"})
    if not isinstance(context, str) or not _name(context):
        return Judgment(False, {"reason": "malformed context"})
    if len(evidence.files) != 1 or evidence.files[0].path != PATH or evidence.listings:
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"{PATH} is {found.status.value}"})
    if not isinstance(found.value, Text):
        return Judgment(False, {"reason": "unexpected evidence"})
    text = found.value.text.replace("\r\n", "\n").replace("\r", "\n")
    # `readlines` ends a line after each `\n`; a final line without one counts.
    count = text.count("\n") + (0 if text.endswith("\n") or text == "" else 1)
    if count != 1:
        return Judgment(False, {"reason": "result.txt must hold exactly one line", "lines": count})
    got = text.strip()
    if got != context:
        return Judgment(False, {"reason": "wrong model", "got": got[:SHOWN]})
    return Judgment(True, None)


def _name(value: JsonValue) -> bool:
    return isinstance(value, str) and value != "" and value == value.strip() and "\n" not in value and "\r" not in value
