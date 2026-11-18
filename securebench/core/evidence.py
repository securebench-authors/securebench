"""Evidence, the Oracle's plan and its judgments (architecture Sections 6, 7).

These are the only types the Oracle sees. Every value in them is bounded and
already validated by the framework.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from securebench.core.errors import Rejected
from securebench.core.jsondata import JsonValue


class HiddenResources(Protocol):
    """The task's hidden resources, as `plan` may read them."""

    def read(self, relative_path: str) -> bytes:
        """Return the bytes of `hidden/<relative_path>`. Raises `Rejected` for a bad path."""
        ...

    def read_json(self, relative_path: str) -> JsonValue:
        """Return `hidden/<relative_path>` decoded with the strict JSON decoder."""
        ...


@dataclass(frozen=True)
class Case:
    """One case: the challenge released to its Evaluation, the context kept on the host."""

    challenge: JsonValue
    context: JsonValue


@dataclass(frozen=True)
class Plan:
    """The Oracle's fixed plan.

    `artifact_contexts` has one context per artifact check; `cases` has one
    non-empty case list per protocol check.
    """

    artifact_contexts: dict[str, JsonValue]
    cases: dict[str, tuple[Case, ...]]


@dataclass(frozen=True)
class Judgment:
    passed: bool
    diagnostic: JsonValue


class FileStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    NOT_REGULAR = "not_regular"
    TOO_LARGE = "too_large"
    UNPARSABLE = "unparsable"


@dataclass(frozen=True)
class FoundFile:
    """A regular file read by lookup or collection; `sha256` is of `data`."""

    data: bytes
    sha256: str
    executable: bool


type FileRead = FoundFile | FileStatus
"""What lookup or collection returns for one declared path: the file, or
`ABSENT`, `NOT_REGULAR` or `TOO_LARGE`."""


@dataclass(frozen=True)
class Text:
    """A file parsed as UTF-8 text, also split into lines without their terminators."""

    text: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class FileEvidence:
    """One declared file. `value` is set exactly when `status` is `present`."""

    path: str
    status: FileStatus
    value: Text | JsonValue
    size: int | None
    sha256: str | None
    reason: str | None


class EntryKind(StrEnum):
    FILE = "file"
    DIR = "dir"
    SYMLINK = "symlink"


@dataclass(frozen=True)
class ListingEntry:
    """One entry under a listed directory; `path` is relative to it."""

    path: str
    kind: EntryKind
    size: int | None
    sha256: str | None
    executable: bool | None
    target: str | None


class ListingStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    NOT_DIRECTORY = "not_directory"
    TOO_MANY = "too_many"


@dataclass(frozen=True)
class ListingEvidence:
    path: str
    status: ListingStatus
    entries: tuple[ListingEntry, ...]


@dataclass(frozen=True)
class ArtifactEvidence:
    check_id: str
    files: tuple[FileEvidence, ...]
    listings: tuple[ListingEvidence, ...]


class Ending(StrEnum):
    """How an environment's command ended, as the host measured it."""

    RETURNED = "returned"
    TIMED_OUT = "timed_out"
    MEMORY_KILLED = "memory_killed"
    OUTPUT_EXCEEDED = "output_exceeded"
    CRASHED = "crashed"


@dataclass(frozen=True)
class HostFacts:
    ending: Ending
    exit_status: int | None
    duration_seconds: float


@dataclass(frozen=True)
class Observed:
    value: JsonValue


@dataclass(frozen=True)
class Unable:
    """The adapter reported that it could not exercise the candidate."""

    code: str
    message: str


@dataclass(frozen=True)
class Malformed:
    """The case produced no valid response; `reason` says why."""

    reason: str


type Outcome = Observed | Unable | Malformed


@dataclass(frozen=True)
class CaseEvidence:
    """The bound evidence of one case."""

    check_id: str
    case_index: int
    challenge_digest: str
    facts: HostFacts
    outcome: Outcome
    output_artifacts: tuple[FileEvidence, ...]


type Evidence = ArtifactEvidence | CaseEvidence


def plan_to_json(plan: Plan) -> JsonValue:
    """The plan as JSON data, for the Oracle worker protocol and the result record."""
    cases: dict[str, JsonValue] = {
        check_id: [{"challenge": case.challenge, "context": case.context} for case in check_cases]
        for check_id, check_cases in plan.cases.items()
    }
    contexts: dict[str, JsonValue] = dict(plan.artifact_contexts)
    return {"artifact_contexts": contexts, "cases": cases}


def plan_from_json(value: JsonValue) -> Plan:
    """Parse plan data with exact key sets. Raises `Rejected`."""
    top = _object(value, {"artifact_contexts", "cases"}, "plan")
    contexts = _object(top["artifact_contexts"], None, "plan artifact_contexts")
    raw_cases = _object(top["cases"], None, "plan cases")
    cases: dict[str, tuple[Case, ...]] = {}
    for check_id, check_cases in raw_cases.items():
        if not isinstance(check_cases, list):
            raise Rejected(f"plan cases for {check_id!r} must be an array")
        parsed: list[Case] = []
        for raw in check_cases:
            case = _object(raw, {"challenge", "context"}, "plan case")
            parsed.append(Case(case["challenge"], case["context"]))
        cases[check_id] = tuple(parsed)
    return Plan(dict(contexts), cases)


def evidence_to_json(evidence: Evidence) -> JsonValue:
    """Evidence as JSON data, as stored in result records and sent to the Oracle worker."""
    match evidence:
        case ArtifactEvidence():
            files: list[JsonValue] = [_file_to_json(item) for item in evidence.files]
            listings: list[JsonValue] = [_listing_to_json(item) for item in evidence.listings]
            return {
                "check_id": evidence.check_id,
                "files": files,
                "kind": "artifact",
                "listings": listings,
            }
        case CaseEvidence():
            artifacts: list[JsonValue] = [_file_to_json(item) for item in evidence.output_artifacts]
            return {
                "case_index": evidence.case_index,
                "challenge_digest": evidence.challenge_digest,
                "check_id": evidence.check_id,
                "facts": {
                    "duration_seconds": evidence.facts.duration_seconds,
                    "ending": evidence.facts.ending.value,
                    "exit_status": evidence.facts.exit_status,
                },
                "kind": "case",
                "outcome": _outcome_to_json(evidence.outcome),
                "output_artifacts": artifacts,
            }


def evidence_from_json(value: JsonValue) -> Evidence:
    """Parse stored evidence with exact key sets. Raises `Rejected`."""
    if not isinstance(value, dict):
        raise Rejected("evidence must be an object")
    if value.get("kind") == "artifact":
        top = _object(value, {"check_id", "files", "kind", "listings"}, "artifact evidence")
        return ArtifactEvidence(
            _str(top["check_id"]),
            tuple(_file_from_json(item) for item in _list(top["files"])),
            tuple(_listing_from_json(item) for item in _list(top["listings"])),
        )
    top = _object(
        value,
        {
            "case_index",
            "challenge_digest",
            "check_id",
            "facts",
            "kind",
            "outcome",
            "output_artifacts",
        },
        "case evidence",
    )
    if top["kind"] != "case":
        raise Rejected("evidence kind must be 'artifact' or 'case'")
    facts = _object(top["facts"], {"duration_seconds", "ending", "exit_status"}, "host facts")
    duration = facts["duration_seconds"]
    if type(duration) not in (int, float):
        raise Rejected("host facts duration must be a number")
    return CaseEvidence(
        _str(top["check_id"]),
        _int(top["case_index"]),
        _str(top["challenge_digest"]),
        HostFacts(
            _enum(Ending, facts["ending"]),
            _optional_int(facts["exit_status"]),
            float(duration),  # pyright: ignore[reportArgumentType]
        ),
        _outcome_from_json(top["outcome"]),
        tuple(_file_from_json(item) for item in _list(top["output_artifacts"])),
    )


def _file_to_json(item: FileEvidence) -> JsonValue:
    value: JsonValue
    if isinstance(item.value, Text):
        lines: list[JsonValue] = list(item.value.lines)
        value = {"lines": lines, "text": item.value.text}
    elif item.status is FileStatus.PRESENT:
        value = {"json": item.value}
    else:
        value = None
    return {
        "path": item.path,
        "reason": item.reason,
        "sha256": item.sha256,
        "size": item.size,
        "status": item.status.value,
        "value": value,
    }


def _file_from_json(raw: JsonValue) -> FileEvidence:
    item = _object(raw, {"path", "reason", "sha256", "size", "status", "value"}, "file evidence")
    status = _enum(FileStatus, item["status"])
    stored = item["value"]
    value: Text | JsonValue = None
    if status is FileStatus.PRESENT:
        if isinstance(stored, dict) and set(stored) == {"lines", "text"}:
            value = Text(_str(stored["text"]), tuple(_str(line) for line in _list(stored["lines"])))
        else:
            value = _object(stored, {"json"}, "file evidence value")["json"]
    elif stored is not None:
        raise Rejected("file evidence carries a value although it is not present")
    return FileEvidence(
        _str(item["path"]),
        status,
        value,
        _optional_int(item["size"]),
        _optional_str(item["sha256"]),
        _optional_str(item["reason"]),
    )


def _listing_to_json(item: ListingEvidence) -> JsonValue:
    entries: list[JsonValue] = [
        {
            "executable": entry.executable,
            "kind": entry.kind.value,
            "path": entry.path,
            "sha256": entry.sha256,
            "size": entry.size,
            "target": entry.target,
        }
        for entry in item.entries
    ]
    return {"entries": entries, "path": item.path, "status": item.status.value}


def _listing_from_json(raw: JsonValue) -> ListingEvidence:
    item = _object(raw, {"entries", "path", "status"}, "listing evidence")
    entries: list[ListingEntry] = []
    for raw_entry in _list(item["entries"]):
        entry = _object(
            raw_entry, {"executable", "kind", "path", "sha256", "size", "target"}, "listing entry"
        )
        executable = entry["executable"]
        if executable is not None and type(executable) is not bool:
            raise Rejected("listing entry executable must be a boolean or null")
        entries.append(
            ListingEntry(
                _str(entry["path"]),
                _enum(EntryKind, entry["kind"]),
                _optional_int(entry["size"]),
                _optional_str(entry["sha256"]),
                executable,
                _optional_str(entry["target"]),
            )
        )
    return ListingEvidence(_str(item["path"]), _enum(ListingStatus, item["status"]), tuple(entries))


def _outcome_to_json(outcome: Outcome) -> JsonValue:
    match outcome:
        case Observed():
            return {"observed": outcome.value}
        case Unable():
            return {"unable": {"code": outcome.code, "message": outcome.message}}
        case Malformed():
            return {"malformed": outcome.reason}


def _outcome_from_json(raw: JsonValue) -> Outcome:
    if not isinstance(raw, dict) or len(raw) != 1:
        raise Rejected("outcome must be an object with one key")
    if "observed" in raw:
        return Observed(raw["observed"])
    if "unable" in raw:
        report = _object(raw["unable"], {"code", "message"}, "unable report")
        return Unable(_str(report["code"]), _str(report["message"]))
    if "malformed" in raw:
        return Malformed(_str(raw["malformed"]))
    raise Rejected("outcome kind is unknown")


def _enum[E: StrEnum](kind: type[E], value: JsonValue) -> E:
    try:
        return kind(_str(value))
    except ValueError:
        raise Rejected(f"{value!r} is not a valid {kind.__name__}") from None


def _object(value: JsonValue, keys: set[str] | None, what: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise Rejected(f"{what} must be an object")
    if keys is not None and set(value) != keys:
        raise Rejected(f"{what} has keys {sorted(value)}, expected {sorted(keys)}")
    return value


def _list(value: JsonValue) -> list[JsonValue]:
    if not isinstance(value, list):
        raise Rejected("expected an array")
    return value


def _str(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise Rejected("expected a string")
    return value


def _int(value: JsonValue) -> int:
    if type(value) is not int:
        raise Rejected("expected an integer")
    return value


def _optional_int(value: JsonValue) -> int | None:
    return None if value is None else _int(value)


def _optional_str(value: JsonValue) -> str | None:
    return None if value is None else _str(value)
