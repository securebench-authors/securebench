"""Capture, replay, lookup and collection against the real Docker backend."""

import shutil
from pathlib import Path

import pytest

from securebench.candidate import capture, index, lookup, replay
from securebench.candidate.state import BaselineIndex
from securebench.candidate.store import Store
from securebench.core import hashing
from securebench.core.candidate import DeleteEntry, Manifest, WriteEntry
from securebench.core.errors import PackError
from securebench.core.evidence import FileStatus, FoundFile
from securebench.core.task import Task
from securebench.core.verdict import AttemptFailed, FailureClass
from securebench.isolation.backend import EnvironmentSpec, Resources, Snapshot
from securebench.isolation.docker import DockerBackend
from securebench.taskspec.load import load

pytestmark = pytest.mark.integration

F1 = Path(__file__).parents[2] / "fixtures" / "f1-answer-file" / "task"
RESOURCES = Resources(512 << 20, 1_000_000_000, 128, 1 << 30)


@pytest.fixture
def task(tmp_path: Path) -> Task:
    pack = tmp_path / "pack"
    shutil.copytree(F1, pack)
    toml = pack / "task.toml"
    toml.write_text(
        toml.read_text().replace("symlinks = false", 'symlinks = true\nexclude = ["tests"]')
    )
    return load(pack)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "store")


@pytest.fixture
def baseline(backend: DockerBackend, task: Task) -> str:
    return backend.resolve_image(task.public.baseline.image)


@pytest.fixture
def baseline_index(
    backend: DockerBackend, stock_image: str, task: Task, baseline: str, store: Store
) -> BaselineIndex:
    return index.build_index(backend, stock_image, task, baseline, store)


def _agent(backend: DockerBackend, image: str, script: str) -> Snapshot:
    spec = EnvironmentSpec(image, (), None, "/srv", "0", (), RESOURCES)
    environment, ran = backend.run(spec, ["sh", "-c", script], b"", 60, 1 << 16)
    assert ran.facts.exit_status == 0, ran.stderr
    try:
        return backend.snapshot(environment)
    finally:
        backend.destroy(environment)


def _run(backend: DockerBackend, image: str, script: str) -> str:
    spec = EnvironmentSpec(image, (), None, "/srv", "0", (), RESOURCES)
    environment, ran = backend.run(spec, ["sh", "-c", script], b"", 60, 1 << 16)
    backend.destroy(environment)
    return ran.stdout.decode()


def test_capture_replay_and_lookup_round_trip(
    backend: DockerBackend,
    stock_image: str,
    task: Task,
    baseline: str,
    baseline_index: BaselineIndex,
    store: Store,
) -> None:
    agent = _agent(
        backend,
        baseline,
        "printf '{\"sum\": 1294}' > answer.json && mkdir -p d/e && printf x > d/e/f"
        " && printf '#!/bin/sh\\necho hi\\n' > run.sh && chmod +x run.sh && ln -s d link"
        " && mkdir tests && printf t > tests/ignored.py",
    )
    try:
        manifest = capture.capture(backend, stock_image, task, baseline_index, agent, store)
    finally:
        backend.destroy_snapshot(agent)
    paths = {entry.path for entry in manifest.entries}
    assert paths == {
        "/srv/answer.json",
        "/srv/d",
        "/srv/d/e",
        "/srv/d/e/f",
        "/srv/link",
        "/srv/run.sh",
    }
    assert store.get_manifest(manifest.id) == manifest
    view = lookup.FinalView(task.scope, baseline_index, manifest, store)
    read = lookup.read_file(view, "/srv/answer.json", 4096)
    assert isinstance(read, FoundFile) and read.data == b'{"sum": 1294}'
    assert lookup.read_file(view, "/srv/missing.json", 4096) is FileStatus.ABSENT
    assert lookup.read_file(view, "/srv/link", 4096) is FileStatus.NOT_REGULAR
    assert lookup.read_file(view, "/srv/link/e/f", 4096) is FileStatus.ABSENT
    replayed = replay.replay(backend, stock_image, task, baseline_index, manifest, store)
    try:
        output = _run(
            backend,
            replayed.image,
            "cat answer.json; echo; ./run.sh; readlink link; ls tests 2>&1 | head -1;"
            " stat -c '%a %u' run.sh d/e/f",
        )
    finally:
        backend.destroy_snapshot(replayed)
    lines = output.splitlines()
    assert lines[0] == '{"sum": 1294}'
    assert lines[1:3] == ["hi", "d"]
    assert "No such file" in lines[3]
    assert lines[4:] == ["755 0", "644 0"]


def test_deletion_and_type_change_replay(
    backend: DockerBackend, stock_image: str, task: Task, baseline: str, store: Store
) -> None:
    prepared = _agent(
        backend, baseline, "mkdir -p old/sub && printf a > old/sub/a && printf k > keep"
    )
    try:
        new_index = index.build_index(backend, stock_image, task, prepared.image, store)
        agent = _agent(backend, prepared.image, "rm -rf old && printf z > keep && printf f > old")
        try:
            manifest = capture.capture(backend, stock_image, task, new_index, agent, store)
        finally:
            backend.destroy_snapshot(agent)
        kinds = {entry.path: type(entry) for entry in manifest.entries}
        assert kinds == {
            "/srv/keep": WriteEntry,
            "/srv/old": WriteEntry,
            "/srv/old/sub": DeleteEntry,
            "/srv/old/sub/a": DeleteEntry,
        }
        replayed = replay.replay(backend, stock_image, task, new_index, manifest, store)
        try:
            assert _run(backend, replayed.image, "cat old keep") == "fz"
        finally:
            backend.destroy_snapshot(replayed)
    finally:
        backend.destroy_snapshot(prepared)


@pytest.mark.parametrize(
    ("script", "reason"),
    [
        ("mkfifo pipe", "named pipe"),
        ("ln -s ../etc/shadow escape", "escapes"),
        ("ln -s /etc/shadow absolute", "absolute"),
        ("printf s > secret && chmod 000 secret", "cannot be read"),
        ("head -c 70000 /dev/zero > big", "bytes"),
        ("for i in $(seq 1 70); do touch f$i; done", "entries"),
        ("mkdir locked && touch locked/x && chmod 000 locked", "cannot be read"),
    ],
)
def test_candidate_faults_fail_capture(
    backend: DockerBackend,
    stock_image: str,
    task: Task,
    baseline: str,
    baseline_index: BaselineIndex,
    store: Store,
    script: str,
    reason: str,
) -> None:
    agent = _agent(backend, baseline, script)
    try:
        with pytest.raises(AttemptFailed) as caught:
            capture.capture(backend, stock_image, task, baseline_index, agent, store)
    finally:
        backend.destroy_snapshot(agent)
    assert caught.value.failure_class is FailureClass.CAPTURE
    assert reason in caught.value.reason


def test_empty_candidate_is_valid_and_replayable(
    backend: DockerBackend,
    stock_image: str,
    task: Task,
    baseline: str,
    baseline_index: BaselineIndex,
    store: Store,
) -> None:
    agent = _agent(backend, baseline, "true")
    try:
        manifest = capture.capture(backend, stock_image, task, baseline_index, agent, store)
    finally:
        backend.destroy_snapshot(agent)
    assert manifest.entries == ()
    replayed = replay.replay(backend, stock_image, task, baseline_index, manifest, store)
    backend.destroy_snapshot(replayed)


def test_replay_refuses_a_candidate_from_another_baseline(
    backend: DockerBackend,
    stock_image: str,
    task: Task,
    baseline_index: BaselineIndex,
    store: Store,
) -> None:
    other = BaselineIndex(
        "other@sha256:" + "b" * 64,
        baseline_index.scope,
        baseline_index.nodes,
        baseline_index.keeps,
        baseline_index.blobs,
    )
    manifest = Manifest(baseline_index.image, task.scope.to_json(), ())
    with pytest.raises(AttemptFailed) as caught:
        replay.replay(backend, stock_image, task, other, manifest, store)
    assert caught.value.failure_class is FailureClass.CAPTURE
    assert "different baseline" in caught.value.reason


def test_collect_reads_only_regular_files_without_following_links(
    backend: DockerBackend, stock_image: str, baseline: str
) -> None:
    evaluation = _agent(
        backend,
        baseline,
        "printf out > out.json && ln -s out.json link.json && mkdir d && ln -s d dl"
        " && printf in > d/in.json && head -c 100 /dev/zero > big.json",
    )
    try:
        files = (
            ("/srv/out.json", 100),
            ("/srv/link.json", 100),
            ("/srv/dl/in.json", 100),
            ("/srv/missing.json", 100),
            ("/srv/d", 100),
            ("/srv/big.json", 10),
        )
        collected = capture.collect(backend, stock_image, files, evaluation)
    finally:
        backend.destroy_snapshot(evaluation)
    assert collected["/srv/out.json"] == FoundFile(b"out", hashing.sha256(b"out"), False)
    assert collected["/srv/link.json"] is FileStatus.NOT_REGULAR
    assert collected["/srv/dl/in.json"] is FileStatus.NOT_REGULAR
    assert collected["/srv/missing.json"] is FileStatus.ABSENT
    assert collected["/srv/d"] is FileStatus.NOT_REGULAR
    assert collected["/srv/big.json"] is FileStatus.TOO_LARGE


def test_index_rejects_a_baseline_with_framework_paths(
    backend: DockerBackend, stock_image: str, task: Task, baseline: str, store: Store
) -> None:
    polluted = _agent(backend, baseline, "mkdir -p /.securebench/x")
    try:
        with pytest.raises(PackError, match="securebench"):
            index.build_index(backend, stock_image, task, polluted.image, store)
    finally:
        backend.destroy_snapshot(polluted)
