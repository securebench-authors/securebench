"""The baseline index and the live baseline checks (architecture Section 5.3)."""

from securebench.candidate import stream
from securebench.candidate.state import BaselineIndex, FileNode, check_tree
from securebench.candidate.store import Store
from securebench.candidate.utility import (
    TARGET_MOUNT,
    UTILITY_RESOURCES,
    WALK_DEADLINE_SECONDS,
    output_bound,
    run_on_snapshot,
)
from securebench.core.errors import PackError, Rejected
from securebench.core.evidence import Ending
from securebench.core.jsondata import JsonValue
from securebench.core.task import Task
from securebench.isolation.backend import EnvironmentSpec
from securebench.isolation.docker import DockerBackend

_GIT_ENVIRONMENT = (
    ("HOME", "/nonexistent"),
    ("GIT_CONFIG_NOSYSTEM", "1"),
    ("GIT_CONFIG_GLOBAL", "/dev/null"),
    ("GIT_TERMINAL_PROMPT", "0"),
    ("GIT_OPTIONAL_LOCKS", "0"),
    ("PATH", "/usr/local/bin:/usr/bin:/bin"),
)


def artifact_paths(task: Task) -> tuple[str, ...]:
    """The baseline files whose content artifact checks may read by lookup."""
    return tuple(spec.path for check in task.artifact_checks for spec in check.files)


def build_index(
    backend: DockerBackend, stock_image: str, task: Task, baseline_image: str, store: Store
) -> BaselineIndex:
    """Index the baseline image. Raises `PackError` for a baseline that breaks the scope rules."""
    scope = task.scope
    blob_paths = artifact_paths(task)
    listed: list[JsonValue] = list(blob_paths)
    request: JsonValue = {
        "op": "walk",
        "target": TARGET_MOUNT,
        "scope": scope.to_json(),
        "known": None,
        "blob_paths": listed,
        "deadline_seconds": WALK_DEADLINE_SECONDS,
    }
    try:
        data = run_on_snapshot(
            backend,
            stock_image,
            baseline_image,
            request,
            output_bound(scope.max_entries, scope.max_bytes),
        )
        walk = stream.parse_walk(scope, stream.records(data), store.put_blob)
        check_tree(scope, walk.state)
        _require_absent(backend, stock_image, baseline_image, "/.securebench")
    except Rejected as error:
        raise PackError(f"the baseline violates the task's scope: {error.reason}") from None
    blobs = frozenset(path for path in blob_paths if isinstance(walk.state.get(path), FileNode))
    index = BaselineIndex(baseline_image, scope.to_json(), walk.state, frozenset(walk.keeps), blobs)
    return index


def _require_absent(backend: DockerBackend, stock_image: str, image: str, path: str) -> None:
    status = _status(backend, stock_image, image, path)
    if status != "absent":
        raise Rejected(f"the baseline must not contain {path} (found {status})")


def _status(backend: DockerBackend, stock_image: str, image: str, path: str) -> str:
    request: JsonValue = {"op": "collect", "target": TARGET_MOUNT, "files": [[path, 0]]}
    data = run_on_snapshot(backend, stock_image, image, request, 4096)
    collected = stream.parse_collected(((path, 0),), stream.records(data))
    value = collected[path]
    return str(value) if isinstance(value, str) else "file"


def check_repository(
    backend: DockerBackend, stock_image: str, task: Task, baseline_image: str
) -> None:
    """Confirm a clean repository at the declared commit.

    Raises `PackError`.
    """
    repository = task.public.baseline.repository
    if repository is None:
        return
    git_dir = f"{repository.path}/.git"
    try:
        status = _status(backend, stock_image, baseline_image, git_dir)
    except Rejected as error:
        raise PackError(f"cannot inspect {git_dir}: {error.reason}") from None
    if status != "directory":
        raise PackError(f"{git_dir} in the baseline is not a real directory ({status})")
    environment = (
        *_GIT_ENVIRONMENT,
        ("GIT_DIR", git_dir),
        ("GIT_WORK_TREE", repository.path),
    )
    spec = EnvironmentSpec(
        baseline_image, (), None, repository.path, "0", environment, UTILITY_RESOURCES
    )
    head = _git(backend, spec, ["rev-parse", "--verify", "HEAD"])
    if head.strip() != repository.commit:
        raise PackError(f"the baseline repository is at {head.strip()!r}, not {repository.commit}")
    dirty = _git(backend, spec, ["status", "--porcelain", "--untracked-files=all"])
    if dirty.strip():
        raise PackError(f"the baseline repository is not clean: {dirty[:500]!r}")


def _git(backend: DockerBackend, spec: EnvironmentSpec, arguments: list[str]) -> str:
    command = [
        "git",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.untrackedCache=false",
        *arguments,
    ]
    environment, ran = backend.run(spec, command, b"", 300, 1 << 20)
    backend.destroy(environment)
    if ran.facts.ending is not Ending.RETURNED or ran.facts.exit_status != 0:
        detail = ran.stderr.decode("utf-8", "replace")[-500:]
        raise PackError(f"git {arguments[0]} failed in the baseline ({ran.facts}): {detail}")
    return ran.stdout.decode("utf-8", "replace")
