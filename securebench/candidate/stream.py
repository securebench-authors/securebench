"""Parsing the record stream the utility program prints (see `securebench_utility.utility`).

The stream is untrusted: a compromised utility environment can print anything.
Every record has an exact key set, every path is canonical and inside the
scope, and every blob is hashed here. Excluded paths are dropped with the
host's own matcher, whatever the utility decided.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from securebench.candidate.state import DirNode, FileNode, LinkNode, State, root_of
from securebench.core import hashing, jsondata, paths, patterns
from securebench.core.errors import Rejected
from securebench.core.evidence import FileRead, FileStatus, FoundFile
from securebench.core.jsondata import JsonValue
from securebench.core.task import Scope

MAX_LINE_BYTES = 64 * 1024
_HEX = frozenset("0123456789abcdef")

type Record = dict[str, JsonValue]


@dataclass
class Walk:
    """One walk: the state, the directories holding excluded entries, and received blob digests."""

    state: State = field(default_factory=lambda: {})
    keeps: set[str] = field(default_factory=lambda: set())
    blobs: dict[str, str] = field(default_factory=lambda: {})


def records(data: bytes) -> Iterator[tuple[Record, bytes]]:
    """Yield each record with its payload; the stream must end with `end` (or `rejected`)."""
    position = 0
    while True:
        newline = data.find(b"\n", position, position + MAX_LINE_BYTES + 1)
        if newline < 0:
            raise Rejected("the utility output ended without an end record")
        value = jsondata.decode(data[position:newline], MAX_LINE_BYTES)
        position = newline + 1
        if not isinstance(value, dict) or not isinstance(value.get("t"), str):
            raise Rejected("a utility record is not an object with a type")
        kind = value["t"]
        if kind == "rejected":
            reason = value.get("reason")
            raise Rejected(f"utility rejected the filesystem: {str(reason)[:4000]}")
        size = _payload_size(value)
        payload = data[position : position + size]
        if len(payload) != size:
            raise Rejected("the utility output is truncated")
        position += size
        if kind == "end":
            if set(value) != {"t"} or position != len(data):
                raise Rejected("the utility output continues after its end record")
            return
        yield value, payload


def _payload_size(record: Record) -> int:
    has_payload = record.get("blob") is True or (
        record.get("t") == "collected" and record.get("status") == "present"
    )
    if not has_payload:
        return 0
    size = record.get("size")
    if type(size) is not int or size < 0:
        raise Rejected("a utility record has an invalid size")
    return size


def parse_walk(
    scope: Scope,
    stream: Iterator[tuple[Record, bytes]],
    put_blob: Callable[[bytes], str],
    stop_at_phase: bool = False,
) -> Walk:
    """Parse walk records until the stream (or, with `stop_at_phase`, the next phase) ends."""
    walk = Walk()
    for record, payload in stream:
        kind = record["t"]
        if kind == "phase":
            if stop_at_phase:
                return walk
            raise Rejected("unexpected phase record")
        if kind == "excluded_in":
            _exact(record, {"t", "p"})
            walk.keeps.add(_path(scope, record["p"], allow_root=True))
            continue
        path = _path(scope, record.get("p"), allow_root=False)
        root = root_of(scope, path)
        assert root is not None
        if path in walk.state:
            raise Rejected(f"the utility listed {path!r} twice")
        excluded = patterns.is_excluded(
            root.exclude, root.git_directories, paths.relative_to(path, root.path)
        )
        match kind:
            case "dir":
                _exact(record, {"t", "p"})
                node: DirNode | FileNode | LinkNode = DirNode()
            case "symlink":
                _exact(record, {"t", "p", "target"})
                target = record["target"]
                if not isinstance(target, str):
                    raise Rejected("a symlink target is not a string")
                node = LinkNode(target)
            case "file":
                node = _file(record, payload)
                if record.get("blob") is True and not excluded:
                    walk.blobs[path] = put_blob(payload)
            case _:
                raise Rejected(f"unexpected utility record type {kind!r}")
        if not excluded:
            walk.state[path] = node
    if stop_at_phase:
        raise Rejected("the utility output ended inside a phase")
    return walk


def parse_collected(
    files: tuple[tuple[str, int], ...], stream: Iterator[tuple[Record, bytes]]
) -> dict[str, FileRead | str]:
    """Parse `collected` records: exactly one per declared path, in order.

    Values are a `FileRead`, or the strings `"directory"` and `"unreadable"`.
    """
    result: dict[str, FileRead | str] = {}
    expected = iter(files)
    for record, payload in stream:
        declared = next(expected, None)
        if record["t"] != "collected" or declared is None or record.get("p") != declared[0]:
            raise Rejected("the utility collected an undeclared file")
        path, max_bytes = declared
        status = record.get("status")
        if status == "present":
            _exact(record, {"t", "p", "status", "size", "x"})
            if len(payload) > max_bytes or not isinstance(record["x"], bool):
                raise Rejected(f"collected file {path!r} is malformed")
            result[path] = FoundFile(payload, hashing.sha256(payload), record["x"])
            continue
        _exact(record, {"t", "p", "status"})
        match status:
            case "absent":
                result[path] = FileStatus.ABSENT
            case "not_regular":
                result[path] = FileStatus.NOT_REGULAR
            case "too_large":
                result[path] = FileStatus.TOO_LARGE
            case "directory" | "unreadable":
                result[path] = status
            case _:
                raise Rejected(f"unknown collection status {status!r}")
    if next(expected, None) is not None:
        raise Rejected("the utility did not collect every declared file")
    return result


def _file(record: Record, payload: bytes) -> FileNode:
    size, executable = record.get("size"), record.get("x")
    if type(size) is not int or size < 0 or type(executable) is not bool:
        raise Rejected("a file record has an invalid size or executable bit")
    if record.get("blob") is True:
        _exact(record, {"t", "p", "size", "x", "blob"})
        return FileNode(hashing.sha256(payload), size, executable)
    _exact(record, {"t", "p", "size", "x", "sha256"})
    digest = record["sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or not set(digest) <= _HEX:
        raise Rejected("a file record has an invalid digest")
    return FileNode(hashing.PREFIX + digest, size, executable)


def _path(scope: Scope, value: JsonValue, allow_root: bool) -> str:
    if not isinstance(value, str):
        raise Rejected("a utility record path is not a string")
    path = paths.check_absolute(value)
    root = root_of(scope, path)
    if root is None or (path == root.path and not allow_root):
        raise Rejected(f"the utility listed {path!r}, which is outside the scope")
    return path


def _exact(record: Record, keys: set[str]) -> None:
    if set(record) != keys:
        raise Rejected(f"utility record has keys {sorted(record)}, expected {sorted(keys)}")
