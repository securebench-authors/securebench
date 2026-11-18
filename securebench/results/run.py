"""The run directory: append-only attempt records, logs and the run manifest.

Layout:

    run.json                    the run configuration, written once
    lock                        held (flock) while a process works on the run
    manifest.jsonl              one line per record: path and digest, append-only
    digest.json                 the root digest, written when the run ends
    attempts/<task>/<n>.json    one result record per attempt, never overwritten
    attempts/<task>/<n>.<name>  logs and transcripts (untrusted bytes)
    store/                      the candidate store
"""

import fcntl
import os
from pathlib import Path
from types import TracebackType
from typing import IO

from securebench.core import hashing, jsondata
from securebench.core.errors import HostError, Rejected
from securebench.core.jsondata import JsonValue

EXECUTION_CONTRACT = "1"
MAX_RECORD_BYTES = 1 << 30
_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")


class RunDirectory:
    """One run's directory, locked for the lifetime of the object."""

    def __init__(self, root: Path, configuration: JsonValue) -> None:
        """Create the run, or resume it when `configuration` equals the stored one exactly."""
        self.root = root
        self.configuration = configuration
        self._lock: IO[bytes] | None = None

    def __enter__(self) -> "RunDirectory":
        self.root.mkdir(parents=True, exist_ok=True)
        lock = (self.root / "lock").open("ab")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            raise HostError(f"another process is working on {self.root}") from None
        self._lock = lock
        try:
            self._open()
        except BaseException:
            self._release()
            raise
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self._release()

    def _release(self) -> None:
        if self._lock is not None:
            fcntl.flock(self._lock, fcntl.LOCK_UN)
            self._lock.close()
            self._lock = None

    def _open(self) -> None:
        stored = self.root / "run.json"
        encoded = jsondata.encode(self.configuration)
        if stored.exists():
            if _read(stored, MAX_RECORD_BYTES) != encoded:
                raise HostError(
                    f"{self.root} was started with a different configuration; resume refused"
                )
            if (self.root / "digest.json").exists():
                raise HostError(f"{self.root} is finished; start a new run")
            self._verify_manifest()
        else:
            _write_new(stored, encoded)
            (self.root / "manifest.jsonl").touch()
        (self.root / "attempts").mkdir(exist_ok=True)

    @property
    def store_root(self) -> Path:
        return self.root / "store"

    def _manifest(self) -> list[tuple[str, str]]:
        return _manifest_entries(self.root)

    def _verify_manifest(self) -> None:
        """Every listed record is present and unchanged (Section 11, Integrity)."""
        for path, digest in self._manifest():
            _verified(self.root, path, digest)

    def attempts(self, task_id: str) -> list[JsonValue]:
        """Every stored record for a task, in attempt order, re-verified against the manifest."""
        prefix = f"attempts/{_name(task_id)}/"
        return [
            _decode_record(path, _verified(self.root, path, digest))
            for path, digest in self._manifest()
            if path.startswith(prefix) and path.endswith(".json")
        ]

    def next_attempt(self, task_id: str) -> int:
        return len(self.attempts(task_id)) + 1

    def save_log(self, task_id: str, attempt: int, name: str, data: bytes) -> str:
        """Store untrusted bytes next to the record; return their digest."""
        directory = self.root / "attempts" / _name(task_id)
        directory.mkdir(exist_ok=True)
        relative = f"attempts/{_name(task_id)}/{attempt}.{_name(name)}"
        _write_new(self.root / relative, data)
        digest = hashing.sha256(data)
        self._append(relative, digest)
        return digest

    def record(self, task_id: str, attempt: int, record: JsonValue) -> str:
        """Append one result record; never overwrites. Returns its digest."""
        directory = self.root / "attempts" / _name(task_id)
        directory.mkdir(exist_ok=True)
        relative = f"attempts/{_name(task_id)}/{attempt}.json"
        data = jsondata.encode(record)
        _write_new(self.root / relative, data)
        digest = hashing.sha256(data)
        self._append(relative, digest)
        return digest

    def _append(self, relative: str, digest: str) -> None:
        line = jsondata.encode({"digest": digest, "path": relative})
        with (self.root / "manifest.jsonl").open("ab") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def finish(self) -> str:
        """Write the root digest over the manifest and return it."""
        self._verify_manifest()
        root = hashing.sha256(_read(self.root / "manifest.jsonl", MAX_RECORD_BYTES))
        _write_new(
            self.root / "digest.json",
            jsondata.encode({"manifest": root, "records": len(self._manifest())}),
        )
        return root


def _name(text: str) -> str:
    if not text or not set(text) <= _NAME_CHARS or len(text) > 64:
        raise HostError(f"{text!r} cannot name a file in the run directory")
    return text


def _read(path: Path, bound: int) -> bytes:
    with path.open("rb") as handle:
        data = handle.read(bound + 1)
    if len(data) > bound:
        raise HostError(f"{path} is larger than {bound} bytes")
    return data


def _write_new(path: Path, data: bytes) -> None:
    """Create `path` exclusively and durably; an existing file is an integrity error."""
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        raise HostError(f"{path} already exists; records are never overwritten") from None
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def load_records(root: Path) -> list[JsonValue]:
    """Every attempt record of a run, read-only, each verified against the run manifest
    and the manifest against the root digest when the run has finished."""
    finished = root / "digest.json"
    if finished.exists():
        manifest = hashing.sha256(_read(root / "manifest.jsonl", MAX_RECORD_BYTES))
        try:
            stored = jsondata.decode(_read(finished, 1 << 16), 1 << 16)
        except Rejected as error:
            raise HostError(f"the run's root digest is malformed: {error.reason}") from None
        if not isinstance(stored, dict) or stored.get("manifest") != manifest:
            raise HostError("the run manifest does not match the run's root digest")
    records: list[JsonValue] = []
    for path, digest in _manifest_entries(root):
        data = _verified(root, path, digest)
        if path.endswith(".json"):
            records.append(_decode_record(path, data))
    return records


def _manifest_entries(root: Path) -> list[tuple[str, str]]:
    """The run manifest's (path, digest) lines, with exact keys; paths stay inside the run."""
    entries: list[tuple[str, str]] = []
    for line in _read(root / "manifest.jsonl", MAX_RECORD_BYTES).splitlines():
        try:
            value = jsondata.decode(line, 1 << 16)
        except Rejected as error:
            raise HostError(f"the run manifest is corrupted: {error.reason}") from None
        if (
            not isinstance(value, dict)
            or set(value) != {"digest", "path"}
            or not isinstance(value["path"], str)
            or not isinstance(value["digest"], str)
            or not value["path"].startswith("attempts/")
            or ".." in value["path"].split("/")
        ):
            raise HostError("the run manifest is corrupted")
        entries.append((value["path"], value["digest"]))
    return entries


def _verified(root: Path, path: str, digest: str) -> bytes:
    data = _read(root / path, MAX_RECORD_BYTES)
    if hashing.sha256(data) != digest:
        raise HostError(f"{path} changed after it was recorded")
    return data


def _decode_record(path: str, data: bytes) -> JsonValue:
    try:
        return jsondata.decode(data, MAX_RECORD_BYTES)
    except Rejected as error:
        raise HostError(f"{path} is malformed: {error.reason}") from None
