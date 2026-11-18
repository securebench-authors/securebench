"""Turning collected bytes into bound evidence."""

from collections.abc import Mapping

from securebench.core import jsondata
from securebench.core.errors import HostError, Rejected
from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    Ending,
    FileEvidence,
    FileRead,
    FileStatus,
    FoundFile,
    HostFacts,
    ListingEvidence,
    Malformed,
    Observed,
    Outcome,
    Unable,
)
from securebench.core.jsondata import JsonValue
from securebench.core.task import ArtifactCheck, FileSpec, ProtocolCheck
from securebench.evidence import parsers, schema

UNABLE_CODE_BYTES = 128
UNABLE_MESSAGE_BYTES = 4096


def file_evidence(spec: FileSpec, read: FileRead) -> FileEvidence:
    """Parse one declared file. Oversized or unparsable content becomes a status."""
    if not isinstance(read, FoundFile):
        if read not in (FileStatus.ABSENT, FileStatus.NOT_REGULAR, FileStatus.TOO_LARGE):
            raise HostError(f"lookup returned status {read} for {spec.path}")
        return FileEvidence(spec.path, read, None, None, None, None)
    size = len(read.data)
    if size > spec.max_bytes:
        return FileEvidence(spec.path, FileStatus.TOO_LARGE, None, size, read.sha256, None)
    try:
        value = parsers.parse(spec.parser, read.data)
    except Rejected as error:
        return FileEvidence(spec.path, FileStatus.UNPARSABLE, None, size, read.sha256, error.reason)
    return FileEvidence(spec.path, FileStatus.PRESENT, value, size, read.sha256, None)


def artifact_evidence(
    check: ArtifactCheck,
    files: Mapping[str, FileRead],
    listings: Mapping[str, ListingEvidence],
) -> ArtifactEvidence:
    """Bind an artifact check's reads. The keys must equal the declared paths exactly."""
    _require_keys(set(files), {spec.path for spec in check.files}, check.id, "files")
    _require_keys(set(listings), {spec.path for spec in check.listings}, check.id, "listings")
    return ArtifactEvidence(
        check.id,
        tuple(file_evidence(spec, files[spec.path]) for spec in check.files),
        tuple(listings[spec.path] for spec in check.listings),
    )


def parse_response(data: bytes, check: ProtocolCheck) -> Outcome:
    """Parse an adapter response: bound, strict JSON, one of the two envelopes, schema.

    Returns `Observed`, `Unable` or `Malformed`; never raises for bad input.
    """
    try:
        value = jsondata.decode(data, check.max_observation_bytes)
        if not isinstance(value, dict) or len(value) != 1:
            raise Rejected("response must be an object with exactly one key")
        if "observation" in value:
            schema.validate(value["observation"], check.observation_schema)
            return Observed(value["observation"])
        if "unable" in value:
            return _unable(value["unable"])
        raise Rejected("response envelope must be 'observation' or 'unable'")
    except Rejected as error:
        return Malformed(error.reason)


def case_evidence(
    check: ProtocolCheck,
    case_index: int,
    challenge: JsonValue,
    facts: HostFacts,
    response: bytes | None,
    output_artifacts: Mapping[str, FileRead],
    collection_failure: str | None = None,
) -> CaseEvidence:
    """Bind one case's evidence by the host's own labels.

    `response` is the adapter's standard output when it returned with status
    0, else `None`, in which case the outcome is `Malformed` with the ending
    as reason. `output_artifacts` keys must equal the declared paths when the
    outcome is `Observed`, and be empty otherwise. `collection_failure` says
    why the Output Artifacts could not be collected; the outcome is then
    `Malformed` with that reason.
    """
    if collection_failure is not None:
        outcome: Outcome = Malformed(collection_failure)
        return CaseEvidence(check.id, case_index, jsondata.digest(challenge), facts, outcome, ())
    if response is None:
        if facts.ending is Ending.RETURNED and facts.exit_status == 0:
            raise HostError("a response is required when the adapter returned with status 0")
        outcome = Malformed(_ending_reason(facts))
    else:
        outcome = parse_response(response, check)
    if isinstance(outcome, Observed):
        declared = {spec.path for spec in check.output_artifacts}
        _require_keys(set(output_artifacts), declared, check.id, "output artifacts")
        artifacts = tuple(
            file_evidence(spec, output_artifacts[spec.path]) for spec in check.output_artifacts
        )
    else:
        if output_artifacts:
            raise HostError("output artifacts are collected only after an observation")
        artifacts = ()
    return CaseEvidence(check.id, case_index, jsondata.digest(challenge), facts, outcome, artifacts)


def _unable(report: JsonValue) -> Unable:
    if not isinstance(report, dict) or set(report) != {"code", "message"}:
        raise Rejected("unable report must have exactly 'code' and 'message'")
    code, message = report["code"], report["message"]
    if not isinstance(code, str) or not 1 <= len(code.encode("utf-8")) <= UNABLE_CODE_BYTES:
        raise Rejected(f"unable code must be 1 to {UNABLE_CODE_BYTES} bytes")
    if not isinstance(message, str) or len(message.encode("utf-8")) > UNABLE_MESSAGE_BYTES:
        raise Rejected(f"unable message must be at most {UNABLE_MESSAGE_BYTES} bytes")
    if "\x00" in code or "\x00" in message:
        raise Rejected("unable report contains NUL")
    return Unable(code, message)


def _ending_reason(facts: HostFacts) -> str:
    if facts.ending is Ending.RETURNED:
        return f"adapter exited with status {facts.exit_status}"
    return f"adapter {facts.ending.value.replace('_', ' ')}"


def _require_keys(actual: set[str], declared: set[str], check_id: str, what: str) -> None:
    if actual != declared:
        raise HostError(f"check {check_id}: {what} {sorted(actual)} differ from {sorted(declared)}")
