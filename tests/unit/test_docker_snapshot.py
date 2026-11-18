"""A snapshot waits out a slow commit in one long call."""

import subprocess

import pytest

from securebench.isolation import docker
from securebench.isolation.backend import Environment


def test_a_snapshot_gives_the_commit_the_long_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], float]] = []

    def fake(
        arguments: list[str], timeout: float = docker.CLI_TIMEOUT_SECONDS
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append((arguments, timeout))
        return subprocess.CompletedProcess(arguments, 0, b"sha256:" + b"a" * 64 + b"\n", b"")

    monkeypatch.setattr(docker, "cli", fake)
    snapshot = docker.DockerBackend(disk_quota=True).snapshot(Environment("securebench-x"))
    assert snapshot.image == "sha256:" + "a" * 64
    assert [(arguments[0], timeout) for arguments, timeout in calls] == [("commit", 600)]
