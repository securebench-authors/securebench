"""Oracle for kv-store-grpc: upstream's seven tests, judged from captured files and one case.

Expected substrings, the challenge and the expected values live in
hidden/cases.json. This file only says how upstream's assertions compare.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Case,
    Text,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    assert isinstance(cases, dict)
    grpc_server = cases["grpc-server"]
    assert isinstance(grpc_server, dict)
    return Plan(
        artifact_contexts={
            "proto-file": cases["proto-file"],
            "server-file": cases["server-file"],
            "generated-files": None,
        },
        cases={"grpc-server": (Case(grpc_server["challenge"], grpc_server["context"]),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id in ("proto-file", "server-file") and isinstance(evidence, ArtifactEvidence):
        return _contains_all(context, evidence)
    if check_id == "generated-files" and isinstance(evidence, ArtifactEvidence):
        return _all_exist(evidence)
    if check_id == "grpc-server" and isinstance(evidence, CaseEvidence):
        return _grpc_server(context, evidence)
    return Judgment(False, {"reason": "unexpected check or evidence"})


def _contains_all(context: JsonValue, evidence: ArtifactEvidence) -> Judgment:
    # Upstream: the file exists, and each required string is `in` its text.
    if not isinstance(context, dict) or len(evidence.files) != 1:
        return Judgment(False, {"reason": "unexpected context or evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return Judgment(False, {"reason": f"{found.path} is {found.status.value}"})
    substrings = context["substrings"]
    if not isinstance(substrings, list):
        return Judgment(False, {"reason": "unexpected context"})
    missing = [s for s in substrings if not isinstance(s, str) or s not in found.value.text]
    if missing:
        return Judgment(False, {"reason": f"{found.path} lacks required text", "missing": missing})
    return Judgment(True, None)


def _all_exist(evidence: ArtifactEvidence) -> Judgment:
    # Upstream only asks Path.exists(): any file type and any content will do.
    if len(evidence.files) != 2:
        return Judgment(False, {"reason": "unexpected evidence"})
    absent = [f.path for f in evidence.files if f.status is FileStatus.ABSENT]
    if absent:
        return Judgment(False, {"reason": "generated files do not exist", "absent": absent})
    return Judgment(True, None)


def _equals(record: JsonValue, expected: JsonValue) -> bool:
    """Python's `response.val == expected` for an integer `expected`."""
    if not isinstance(record, dict) or isinstance(expected, bool) or not isinstance(expected, int):
        return False
    kind = record.get("kind")
    if kind == "integer":
        value = record.get("integer")
        return isinstance(value, int) and not isinstance(value, bool) and value == expected
    if kind == "float":
        value = record.get("float")
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value == expected
    return False


def _grpc_server(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    observed = evidence.outcome.value
    if not isinstance(context, dict) or not isinstance(observed, dict):
        return Judgment(False, {"reason": "unexpected context or observation"})

    # test_grpc_tools_installation: `import grpc` raised nothing.
    grpc_import = observed.get("grpc_import")
    if not isinstance(grpc_import, dict) or grpc_import.get("imported") is not True:
        return Judgment(False, {"reason": "test_grpc_tools_installation: import grpc failed"})

    # test_real_grpc_server_running: connect_ex(...) == 0.
    result = observed.get("port_connect_result")
    expected_result = context["port_connect_result"]
    if not isinstance(result, int) or isinstance(result, bool) or result != expected_result:
        return Judgment(False, {"reason": "test_real_grpc_server_running: port not listening"})

    # test_grpc_protocol_handshake: either any grpc.RpcError, or a response
    # that has `val` equal to the value set.
    handshake = observed.get("handshake")
    if not isinstance(handshake, dict) or handshake.get("channel_closed") is not True:
        return Judgment(False, {"reason": "test_grpc_protocol_handshake: setup or close failed"})
    stage = handshake.get("stage")
    if stage == "response":
        if handshake.get("has_val") is not True:
            return Judgment(False, {"reason": "test_grpc_protocol_handshake: response has no val"})
        if not _equals(handshake.get("val"), context["handshake_val"]):
            return Judgment(False, {"reason": "test_grpc_protocol_handshake: wrong val"})
    elif stage != "rpc_error":
        return Judgment(False, {"reason": f"test_grpc_protocol_handshake: {stage}"})

    # test_grpc_server_functionality: every call returns, and each val equals
    # the value upstream asserts, in order.
    functionality = observed.get("functionality")
    if (
        not isinstance(functionality, dict)
        or functionality.get("setup_error") != ""
        or functionality.get("channel_closed") is not True
    ):
        return Judgment(False, {"reason": "test_grpc_server_functionality: setup or close failed"})
    steps = functionality.get("steps")
    expected_vals = context["functionality_vals"]
    if not isinstance(steps, list) or not isinstance(expected_vals, list):
        return Judgment(False, {"reason": "unexpected observation or context"})
    if len(steps) != len(expected_vals):
        return Judgment(
            False,
            {"reason": "test_grpc_server_functionality: a call failed", "completed": len(steps)},
        )
    for index, (step, expected) in enumerate(zip(steps, expected_vals)):
        if not isinstance(step, dict) or "error" in step or not _equals(step.get("val"), expected):
            return Judgment(
                False, {"reason": "test_grpc_server_functionality: wrong val", "call": index}
            )
    return Judgment(True, None)
