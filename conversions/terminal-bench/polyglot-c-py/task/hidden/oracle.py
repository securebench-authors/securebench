"""Oracle for polyglot-c-py.

Upstream checks that /app/polyglot holds only main.py.c, then that Python and
the gcc build both exit 0 and print f(n) for n = 42, 10 and 0, compared after
`strip()`. Those three cases and their expected values are upstream's literals,
in hidden/cases.json. Both the `python` and the `c` check run all three.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    EntryKind,
    HiddenResources,
    Judgment,
    ListingStatus,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

SHOWN = 1024


def plan(resources: HiddenResources, seed: int) -> Plan:
    rows = resources.read_json("cases.json")
    if not isinstance(rows, list) or not rows:
        raise ValueError("hidden/cases.json must be a non-empty list")
    cases = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"n", "expected"}:
            raise ValueError("each case needs exactly n and expected")
        if not isinstance(row["n"], int) or not isinstance(row["expected"], str):
            raise ValueError("n is an integer and expected a string")
        cases.append(Case({"n": row["n"]}, {"expected": row["expected"]}))
    return Plan(artifact_contexts={"single-file": None}, cases={"python": tuple(cases), "c": tuple(cases)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if isinstance(evidence, ArtifactEvidence):
        return _single_file(evidence)
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    run = evidence.outcome.value
    if not isinstance(run, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    stripped = run.get("stripped")
    size = run.get("stripped_bytes")
    expected = context.get("expected")
    if not isinstance(stripped, str) or not isinstance(size, int) or not isinstance(expected, str):
        return Judgment(False, {"reason": "malformed"})
    # Upstream's check=True: the run must end normally with exit status 0.
    if run.get("ending") != "exited" or run.get("exit_status") != 0:
        return Judgment(False, {"reason": "did not exit 0", "ending": run.get("ending"), "exit_status": run.get("exit_status")})
    # Upstream's text=True decodes strictly, so invalid UTF-8 fails its test.
    if run.get("utf8") is not True:
        return Judgment(False, {"reason": "output is not valid UTF-8"})
    # Upstream compares all of the stripped output, so it must be shown in full.
    if size > SHOWN or size != len(stripped.encode("utf-8")):
        return Judgment(False, {"reason": "output not shown in full", "stripped_bytes": size})
    if stripped != expected:
        return Judgment(False, {"expected": expected, "got": stripped[:256]})
    return Judgment(True, None)


def _single_file(evidence: ArtifactEvidence) -> Judgment:
    listing = evidence.listings[0]
    if listing.status is not ListingStatus.PRESENT:
        return Judgment(False, {"reason": f"/app/polyglot is {listing.status.value}"})
    entries = [(entry.path, entry.kind.value) for entry in listing.entries]
    if entries != [("main.py.c", EntryKind.FILE.value)]:
        found: list[JsonValue] = [path for path, _ in entries]
        return Judgment(False, {"reason": "expected only main.py.c", "found": found})
    return Judgment(True, None)
