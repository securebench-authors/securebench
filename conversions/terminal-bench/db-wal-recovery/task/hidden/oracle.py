"""Oracle for terminal-bench/db-wal-recovery.

Each function below transliterates one test of upstream `tests/test_outputs.py`,
in upstream order, and returns None when the test would pass or a short reason
when it would fail. Upstream rewards the task only when every test passes, so
the first failure decides the verdict. Every later function may rely on the
shape the earlier ones established (a non-empty list of objects with an integer
`id`, a string `name` and an integer `value`), which keeps each one equal to its
upstream test whenever the earlier tests pass.

The checks use Python's own semantics on purpose, as upstream's do: a JSON
boolean satisfies `isinstance(..., int)` and `true == 1`, exactly as in the
native verifier. The expected literals live in `hidden/expected.json`.
"""

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, FileStatus, HiddenResources, Judgment, Plan
from securebench.core.jsondata import JsonValue

CHECK_ID = "recovered-json"


def plan(resources: HiddenResources, seed: int) -> Plan:
    return Plan(artifact_contexts={CHECK_ID: resources.read_json("expected.json")}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK_ID or not isinstance(evidence, ArtifactEvidence) or len(evidence.files) != 1:
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed context"})
    found = evidence.files[0]
    # test_recovered_json_exists and the json.load of every later test.
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"test": "test_recovered_json_exists", "reason": f"recovered.json is {found.status.value}"})
    data = found.value
    tests = (
        ("test_recovered_json_is_valid", lambda: _json_is_valid(data)),
        ("test_recovered_data_structure", lambda: _data_structure(data)),
        ("test_recovered_data_sorted", lambda: _data_sorted(data)),
        ("test_recovered_data_completeness", lambda: _data_completeness(data, context["completeness"])),
        ("test_no_duplicate_ids", lambda: _no_duplicate_ids(data)),
        ("test_wal_was_decrypted", lambda: _wal_was_decrypted(data, context["wal_was_decrypted"])),
    )
    for name, test in tests:
        try:
            reason = test()
        except Exception:  # noqa: BLE001 - fail closed on anything unexpected
            return Judgment(False, {"test": name, "reason": "judging raised an exception"})
        if reason is not None:
            return Judgment(False, {"test": name, "reason": reason})
    return Judgment(True, None)


def _json_is_valid(data: JsonValue) -> str | None:
    if not isinstance(data, list):
        return "JSON should be a list"
    if not len(data) > 0:
        return "JSON should not be empty"
    return None


def _data_structure(data: list[JsonValue]) -> str | None:
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            return f"item {index} should be a dictionary"
        if not {"id", "name", "value"}.issubset(item.keys()):
            return f"item {index} is missing a required field"
        if not isinstance(item["id"], int):
            return f"item {index}: id should be an integer"
        if not isinstance(item["name"], str):
            return f"item {index}: name should be a string"
        if not isinstance(item["value"], int):
            return f"item {index}: value should be an integer"
    return None


def _ids(data: list[dict[str, JsonValue]]) -> list[int]:
    return [item["id"] for item in data]


def _by_id(data: list[dict[str, JsonValue]]) -> dict[int, dict[str, JsonValue]]:
    # Later items overwrite earlier ones with an equal id, as upstream's dict comprehension does.
    return {item["id"]: item for item in data}


def _data_sorted(data: list[dict[str, JsonValue]]) -> str | None:
    ids = _ids(data)
    if ids != sorted(ids):
        return "Data should be sorted by id"
    return None


def _data_completeness(data: list[dict[str, JsonValue]], expected: dict[str, JsonValue]) -> str | None:
    if len(data) != expected["count"]:
        return f"expected {expected['count']} records, got {len(data)}"
    if _ids(data) != expected["ids"]:
        return "ids are not the expected ids"
    by_id = _by_id(data)
    for record_id, value in expected["values"]:
        if record_id not in by_id or by_id[record_id]["value"] != value:
            return f"record {record_id} does not have the value recovered from the WAL"
    for record_id, name in expected["names"]:
        if record_id not in by_id or by_id[record_id]["name"] != name:
            return f"record {record_id} does not have the expected name"
    return None


def _no_duplicate_ids(data: list[dict[str, JsonValue]]) -> str | None:
    ids = _ids(data)
    if len(ids) != len(set(ids)):
        return "There should be no duplicate IDs"
    return None


def _wal_was_decrypted(data: list[dict[str, JsonValue]], expected: dict[str, JsonValue]) -> str | None:
    if not len(data) > expected["more_than"]:
        return "Only base data recovered - WAL decryption failed"
    by_id = _by_id(data)
    # Upstream checks these only when the id is present at all.
    for record_id, value in expected["values_if_present"]:
        if record_id in by_id and by_id[record_id]["value"] != value:
            return f"WAL update for id={record_id} not applied"
    for record_id, name in expected["names_if_present"]:
        if record_id in by_id and by_id[record_id]["name"] != name:
            return f"WAL insert for id={record_id} not found"
    return None
