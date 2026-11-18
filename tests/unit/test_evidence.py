"""Unit tests for `securebench.evidence`."""

import pytest

from securebench.core import hashing, jsondata
from securebench.core.errors import HostError, Rejected
from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    Ending,
    FileEvidence,
    FileStatus,
    FoundFile,
    HostFacts,
    Judgment,
    Malformed,
    Observed,
    Text,
    Unable,
)
from securebench.core.jsondata import JsonValue
from securebench.core.task import FileSpec, Parser, ProtocolCheck
from securebench.core.verdict import FailureClass, Status, Verdict
from securebench.evidence import binding, parsers, schema
from securebench.results import records

OBSERVATION: JsonValue = {
    "type": "object",
    "properties": {
        "lines": {"type": "array", "items": {"type": "string", "max_bytes": 8}, "max_items": 3},
        "count": {"type": "integer", "minimum": 0, "maximum": 10},
        "ratio": {"type": "number", "minimum": 0, "maximum": 1},
        "ok": {"type": "boolean"},
        "kind": {"type": "string", "max_bytes": 8, "enum": ["a", "b"]},
        "none": {"type": "null"},
    },
    "optional": ["none"],
}

GOOD: JsonValue = {"lines": ["x"], "count": 3, "ratio": 0.5, "ok": True, "kind": "a"}


def _check(**overrides: object) -> ProtocolCheck:
    fields: dict[str, object] = {
        "id": "c",
        "command": ("/bin/adapter",),
        "challenge_schema": {"type": "null"},
        "observation_schema": OBSERVATION,
        "max_cases": 4,
        "timeout_seconds": 5,
        "max_challenge_bytes": 100,
        "max_observation_bytes": 1000,
        "setup_command": None,
        "setup_timeout_seconds": None,
        "output_artifacts": (),
    }
    fields.update(overrides)
    return ProtocolCheck(**fields)  # type: ignore[arg-type]


def test_schema_check_accepts_the_example() -> None:
    schema.check_schema(OBSERVATION)
    schema.validate(GOOD, OBSERVATION)


@pytest.mark.parametrize(
    "bad",
    [
        {"type": "string"},
        {"type": "string", "max_bytes": 1, "pattern": "a+"},
        {"type": "integer", "minimum": 0},
        {"type": "integer", "minimum": True, "maximum": 2},
        {"type": "integer", "minimum": 0, "maximum": 2**64},
        {"type": "array", "items": {"type": "null"}},
        {"type": "object", "properties": {}, "optional": ["x"]},
        {"type": "string", "max_bytes": 1, "enum": []},
        {"type": "string", "max_bytes": 1, "items": {"type": "null"}},
        {"type": "tuple"},
        [],
    ],
)
def test_schema_check_rejects_malformed_schemas(bad: JsonValue) -> None:
    with pytest.raises(Rejected):
        schema.check_schema(bad)


def test_schema_depth_and_node_count_are_bounded() -> None:
    deep: JsonValue = {"type": "null"}
    for _ in range(schema.MAX_SCHEMA_DEPTH):
        deep = {"type": "array", "items": deep, "max_items": 1}
    with pytest.raises(Rejected):
        schema.check_schema(deep)
    wide: JsonValue = {
        "type": "object",
        "properties": {
            str(i): {"type": "object", "properties": {str(j): {"type": "null"} for j in range(8)}}
            for i in range(200)
        },
    }
    with pytest.raises(Rejected):
        schema.check_schema(wide)


@pytest.mark.parametrize(
    "value",
    [
        {**GOOD, "extra": 1},
        {k: v for k, v in GOOD.items() if k != "count"},  # type: ignore[union-attr]
        {**GOOD, "count": True},
        {**GOOD, "count": 11},
        {**GOOD, "count": 1.0},
        {**GOOD, "ratio": False},
        {**GOOD, "kind": "c"},
        {**GOOD, "lines": ["x", "y", "z", "w"]},
        {**GOOD, "lines": ["éééé" + "é"]},
        {**GOOD, "ok": 1},
        {**GOOD, "none": 0},
    ],
)
def test_validation_is_closed_and_strict(value: JsonValue) -> None:
    with pytest.raises(Rejected):
        schema.validate(value, OBSERVATION)


def test_text_parser_splits_lines_and_keeps_carriage_returns() -> None:
    assert parsers.parse(Parser.TEXT, b"a\r\nb\n") == Text("a\r\nb\n", ("a\r", "b"))
    assert parsers.parse(Parser.TEXT, b"") == Text("", ())
    for bad in (b"\xff", b"\xef\xbb\xbfa", b"\xed\xa0\x80"):
        with pytest.raises(Rejected):
            parsers.parse(Parser.TEXT, bad)


def _found(data: bytes) -> FoundFile:
    return FoundFile(data, hashing.sha256(data), False)


def test_file_evidence_statuses() -> None:
    spec = FileSpec("/srv/a.json", Parser.JSON, 10)
    assert binding.file_evidence(spec, _found(b'{"a":1}')).value == {"a": 1}
    assert binding.file_evidence(spec, _found(b"[" * 11)).status is FileStatus.TOO_LARGE
    unparsable = binding.file_evidence(spec, _found(b'{"a":}'))
    assert unparsable.status is FileStatus.UNPARSABLE and unparsable.value is None
    assert binding.file_evidence(spec, FileStatus.ABSENT).status is FileStatus.ABSENT
    with pytest.raises(HostError):
        binding.file_evidence(spec, FileStatus.PRESENT)


def _nested(depth: int) -> JsonValue:
    value: JsonValue = 0
    for _ in range(depth - 1):
        value = [value]
    return value


def test_json_evidence_leaves_room_for_the_result_record() -> None:
    deepest = _nested(parsers.MAX_EVIDENCE_DEPTH)
    assert parsers.parse(Parser.JSON, jsondata.encode(deepest)) == deepest
    file = FileEvidence("/srv/a.json", FileStatus.PRESENT, deepest, 1, "sha256:" + "a" * 64, None)
    facts = HostFacts(Ending.RETURNED, 0, 0.1)
    for evidence in (
        ArtifactEvidence("a", (file,), ()),
        CaseEvidence("a", 0, "sha256:" + "b" * 64, facts, Observed(None), (file,)),
    ):
        record = records.attempt_record(
            task_id="t",
            attempt=1,
            verdict=Verdict(Status.FAILED, FailureClass.ORACLE, ()),
            provenance={},
            candidate_id=None,
            agent={},
            judged=[("a", None, evidence, Judgment(False, None))],
            host_errors=[],
            logs={},
            admitted=True,
        )
        jsondata.encode(record)
    spec = FileSpec("/srv/a.json", Parser.JSON, 1 << 20)
    too_deep = jsondata.encode(_nested(parsers.MAX_EVIDENCE_DEPTH + 1))
    assert binding.file_evidence(spec, _found(too_deep)).status is FileStatus.UNPARSABLE


@pytest.mark.parametrize(
    "data",
    [
        b'{"observation":{}}',
        b'{"observation":{"lines":[],"count":0,"ratio":0,"ok":true,"kind":"a"},"unable":{}}',
        b'{"unable":{"code":"","message":""}}',
        b'{"unable":{"code":"x","message":"y","observation":{}}}',
        b'{"verdict":"passed"}',
        b'{"observation":' + b"1" * 2000 + b"}",
        b"\xff",
        b"",
    ],
)
def test_malformed_responses_never_raise(data: bytes) -> None:
    assert isinstance(binding.parse_response(data, _check()), Malformed)


def test_observed_and_unable_responses() -> None:
    observed = binding.parse_response(b'{"observation":' + repr(GOOD).encode() + b"}", _check())
    assert isinstance(observed, Malformed)  # Python repr is not JSON
    good = b'{"observation":{"lines":["x"],"count":3,"ratio":0.5,"ok":true,"kind":"a"}}'
    assert binding.parse_response(good, _check()) == Observed(GOOD)
    unable = b'{"unable":{"code":"build_failed","message":"exit 2"}}'
    assert binding.parse_response(unable, _check()) == Unable("build_failed", "exit 2")


def test_case_evidence_binds_by_host_labels() -> None:
    check = _check(output_artifacts=(FileSpec("/srv/out.txt", Parser.TEXT, 100),))
    facts = HostFacts(Ending.RETURNED, 0, 0.1)
    good = b'{"observation":{"lines":["x"],"count":3,"ratio":0.5,"ok":true,"kind":"a"}}'
    evidence = binding.case_evidence(
        check, 2, {"in": 1}, facts, good, {"/srv/out.txt": _found(b"hi\n")}
    )
    assert evidence.case_index == 2 and evidence.check_id == "c"
    assert evidence.output_artifacts[0].value == Text("hi\n", ("hi",))
    with pytest.raises(HostError):
        binding.case_evidence(check, 0, None, facts, good, {})


def test_case_evidence_for_a_timed_out_adapter_is_malformed() -> None:
    facts = HostFacts(Ending.TIMED_OUT, None, 5.0)
    evidence = binding.case_evidence(_check(), 0, None, facts, None, {})
    assert evidence.outcome == Malformed("adapter timed out")
