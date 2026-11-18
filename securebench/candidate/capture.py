"""Capture of the candidate and collection of Output Artifacts (architecture Sections 5.3, 7.1)."""

from securebench.candidate import stream
from securebench.candidate.state import BaselineIndex, FileNode, check_tree, compute_delta
from securebench.candidate.store import Store
from securebench.candidate.utility import (
    TARGET_MOUNT,
    WALK_DEADLINE_SECONDS,
    output_bound,
    run_on_snapshot,
)
from securebench.core import hashing
from securebench.core.candidate import Manifest, WriteEntry
from securebench.core.errors import Rejected
from securebench.core.evidence import FileRead, FileStatus
from securebench.core.jsondata import JsonValue
from securebench.core.task import Task
from securebench.core.verdict import AttemptFailed, FailureClass
from securebench.isolation.backend import Snapshot
from securebench.isolation.docker import DockerBackend

MAX_COLLECT_OVERHEAD = 1 << 20


def capture(
    backend: DockerBackend,
    stock_image: str,
    task: Task,
    index: BaselineIndex,
    agent: Snapshot,
    store: Store,
) -> Manifest:
    """Capture and store the candidate from the stopped Agent's snapshot.

    Raises `AttemptFailed` with class `capture` for anything the candidate
    caused, and `HostError` for failures of the host or mechanism.
    """
    scope = task.scope
    known: dict[str, JsonValue] = {
        path: [hashing.hex_part(node.sha256), node.executable]
        for path, node in index.nodes.items()
        if isinstance(node, FileNode)
    }
    request: JsonValue = {
        "op": "walk",
        "target": TARGET_MOUNT,
        "scope": scope.to_json(),
        "known": known,
        "blob_paths": [],
        "deadline_seconds": WALK_DEADLINE_SECONDS,
    }
    try:
        data = run_on_snapshot(
            backend,
            stock_image,
            agent.image,
            request,
            output_bound(scope.max_entries, scope.max_bytes),
        )
        walk = stream.parse_walk(scope, stream.records(data), store.put_blob)
        check_tree(scope, walk.state)
        entries = compute_delta(scope, index, walk.state)
        for entry in entries:
            if isinstance(entry, WriteEntry) and walk.blobs.get(entry.path) != entry.sha256:
                raise Rejected(f"the utility did not send the content of {entry.path!r}")
    except Rejected as error:
        raise AttemptFailed(FailureClass.CAPTURE, error.reason) from None
    manifest = Manifest(index.image, scope.to_json(), entries)
    store.put_manifest(manifest)
    return manifest


def collect(
    backend: DockerBackend,
    stock_image: str,
    files: tuple[tuple[str, int], ...],
    evaluation: Snapshot,
) -> dict[str, FileRead]:
    """Collect declared files from a stopped Evaluation's snapshot (architecture Section 7.1).

    Raises `Rejected` when a file cannot be read or the collector misbehaves;
    the caller fails the case with class `case_error`.
    """
    listed: list[JsonValue] = [[path, size] for path, size in files]
    request: JsonValue = {"op": "collect", "target": TARGET_MOUNT, "files": listed}
    bound = sum(size for _, size in files) + MAX_COLLECT_OVERHEAD
    data = run_on_snapshot(backend, stock_image, evaluation.image, request, bound)
    collected = stream.parse_collected(files, stream.records(data))
    result: dict[str, FileRead] = {}
    for path, value in collected.items():
        if value == "unreadable":
            raise Rejected(f"Output Artifact {path} cannot be read")
        elif value == "directory":
            result[path] = FileStatus.NOT_REGULAR
        elif isinstance(value, FileStatus):
            result[path] = value
        else:
            assert not isinstance(value, str)
            result[path] = value
    return result
