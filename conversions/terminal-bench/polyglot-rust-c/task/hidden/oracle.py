"""Oracle for polyglot-rust-c.

The listing check stands for upstream's `os.listdir("/app/polyglot") ==
["main.rs"]`; each case of `fibonacci` stands for one entry of upstream's
`test_cases` list, where both binaries must exit 0 and print the expected
number once stripped.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    HiddenResources,
    Judgment,
    ListingStatus,
    Observed,
    Plan,
    Case,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict):
        raise ValueError("cases.json must be an object")
    listing = data["listing"]
    cases = data["cases"]
    if not isinstance(cases, list):
        raise ValueError("cases.json cases must be a list")
    planned: list[Case] = []
    for entry in cases:
        if not isinstance(entry, dict):
            raise ValueError("each case must be an object")
        planned.append(Case({"n": entry["n"]}, {"expected": entry["expected"]}))
    return Plan(
        artifact_contexts={"polyglot-listing": {"names": listing}},
        cases={"fibonacci-rust": tuple(planned), "fibonacci-cpp": tuple(planned)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    if check_id == "polyglot-listing" and isinstance(evidence, ArtifactEvidence):
        return _judge_listing(context, evidence)
    if check_id in ("fibonacci-rust", "fibonacci-cpp") and isinstance(evidence, CaseEvidence):
        return _judge_case(context, evidence)
    return Judgment(False, {"reason": "unexpected check or evidence"})


def _judge_listing(context: dict[str, JsonValue], evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.listings) != 1:
        return Judgment(False, {"reason": "expected exactly one listing"})
    listing = evidence.listings[0]
    if listing.status is not ListingStatus.PRESENT:
        return Judgment(False, {"reason": f"/app/polyglot is {listing.status.value}"})
    # The listing is recursive; os.listdir sees only the top level.
    names = [entry.path for entry in listing.entries if "/" not in entry.path]
    if names != context["names"]:
        return Judgment(False, {"reason": "/app/polyglot must hold only main.rs", "found": names[:50]})
    return Judgment(True, None)


def _judge_case(context: dict[str, JsonValue], evidence: CaseEvidence) -> Judgment:
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    run = evidence.outcome.value
    if not isinstance(run, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if "launch_error" in run:
        return Judgment(False, {"reason": "binary did not run", "error": run["launch_error"]})
    status = run.get("exit_status")
    if not isinstance(status, int) or isinstance(status, bool) or status != 0:
        return Judgment(False, {"reason": "exit status is not 0", "exit_status": status})
    stripped = run.get("stdout_stripped")
    if not isinstance(stripped, str):
        return Judgment(False, {"reason": "stdout unreadable", "error": run.get("stdout_error")})
    if stripped != context["expected"]:
        return Judgment(False, {"reason": "wrong output", "got": stripped[:200]})
    return Judgment(True, None)
