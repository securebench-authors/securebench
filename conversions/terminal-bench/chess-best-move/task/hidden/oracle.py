"""Oracle for chess-best-move.

Upstream asserts that `sorted(Path("/app/move.txt").read_text().strip().split())`
equals `sorted(["g2g4", "e2e4"])`. The artifact check reads the file with the
`text` parser (strict UTF-8, at most 1 MiB), and `judge` applies the same
`str.split()` and compares the moves as a multiset, as the sorted lists do:
order and line breaks do not matter, a repeated or extra move fails. The
`strip()` before `split()` changes nothing, because `split()` drops leading
and trailing whitespace itself. The work is one pass over at most 1 MiB of
text; the sort runs only when the count already matches.
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

CHECK = "moves"
PATH = "/app/move.txt"
SHOWN = 16
SHOWN_CHARS = 16


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if not isinstance(expected, dict) or not _moves(expected.get("moves")):
        raise Rejected("hidden/expected.json must hold a non-empty list of moves")
    return Plan(artifact_contexts={CHECK: expected["moves"]}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected check"})
    if not isinstance(context, list) or not _moves(context):
        return Judgment(False, {"reason": "malformed context"})
    if len(evidence.files) != 1 or evidence.files[0].path != PATH or evidence.listings:
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"{PATH} is {found.status.value}"})
    if not isinstance(found.value, Text):
        return Judgment(False, {"reason": "unexpected evidence"})
    got = found.value.text.split()
    if len(got) != len(context) or sorted(got) != sorted(str(move) for move in context):
        shown: list[JsonValue] = [move[:SHOWN_CHARS] for move in got[:SHOWN]]
        return Judgment(False, {"reason": "wrong moves", "count": len(got), "got": shown})
    return Judgment(True, None)


def _moves(value: JsonValue) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(move, str) and move != "" and move.split() == [move] for move in value)
