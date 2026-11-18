"""Replay: building the replayed candidate image (architecture Section 5.4)."""

from securebench.candidate import stream
from securebench.candidate.state import BaselineIndex, apply_delta, check_manifest
from securebench.candidate.store import Store
from securebench.candidate.utility import WALK_DEADLINE_SECONDS, output_bound, run_replay
from securebench.core import hashing, jsondata
from securebench.core.candidate import Manifest, WriteEntry
from securebench.core.errors import HostError, Rejected
from securebench.core.jsondata import JsonValue
from securebench.core.task import Task
from securebench.core.verdict import AttemptFailed, FailureClass
from securebench.isolation.backend import Snapshot
from securebench.isolation.docker import DockerBackend


def replay(
    backend: DockerBackend,
    stock_image: str,
    task: Task,
    index: BaselineIndex,
    manifest: Manifest,
    store: Store,
) -> Snapshot:
    """Apply the candidate to a fresh baseline container and snapshot it.

    The task's current scope rules are re-applied first. The replay program
    walks the scope before and after applying; both walks must match what the
    host expects, or the replay is a host error. A delta the program cannot
    apply fails the attempt with class `capture`.
    """
    try:
        check_manifest(task.scope, index, manifest)
    except Rejected as error:
        raise AttemptFailed(FailureClass.CAPTURE, error.reason) from None
    blobs: dict[str, int] = {}
    for entry in manifest.entries:
        if isinstance(entry, WriteEntry):
            blobs[entry.sha256] = entry.size
    listed: list[JsonValue] = [[hashing.hex_part(digest), size] for digest, size in blobs.items()]
    manifest_json = manifest.to_json()
    assert isinstance(manifest_json, dict)
    header: JsonValue = {
        "op": "replay",
        "scope": task.scope.to_json(),
        "entries": manifest_json["entries"],
        "blobs": listed,
        "deadline_seconds": WALK_DEADLINE_SECONDS,
    }
    request = jsondata.encode(header) + b"".join(
        store.get_blob(digest, size) for digest, size in blobs.items()
    )
    bound = 2 * output_bound(task.scope.max_entries, 0)
    environment, data = run_replay(backend, stock_image, index.image, request, bound)
    try:
        try:
            records = stream.records(data)
            first, _ = next(records)
            if first != {"t": "phase", "name": "before"}:
                raise Rejected("replay output does not start with the before phase")
            before = stream.parse_walk(task.scope, records, _no_blobs, stop_at_phase=True)
            if before.state != index.nodes:
                raise HostError("the replay baseline differs from the baseline index")
            after = stream.parse_walk(task.scope, records, _no_blobs)
        except Rejected as error:
            raise AttemptFailed(FailureClass.CAPTURE, f"replay: {error.reason}") from None
        if after.state != apply_delta(index, manifest):
            raise HostError("the replayed filesystem differs from the candidate")
        return backend.snapshot(environment)
    finally:
        backend.destroy(environment)


def _no_blobs(data: bytes) -> str:
    raise Rejected("a replay walk sent file content")
