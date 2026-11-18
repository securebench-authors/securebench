"""Removal waits out a slow daemon but still surfaces real failures."""

import subprocess

import pytest

from securebench.core.errors import HostError
from securebench.isolation import docker


class Clock:
    """A fake monotonic clock that advances only when the code sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(docker.time, "monotonic", fake.monotonic)
    monkeypatch.setattr(docker.time, "sleep", fake.sleep)
    return fake


def script(monkeypatch: pytest.MonkeyPatch, outcomes: list[Exception | None]) -> list[list[str]]:
    """Make each `cli` call take the next outcome: raise it, or succeed on None."""
    calls: list[list[str]] = []

    def fake(arguments: list[str], *_: object, **__: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(arguments)
        outcome = outcomes.pop(0)
        if outcome is not None:
            raise outcome
        return subprocess.CompletedProcess(arguments, 0, b"", b"")

    monkeypatch.setattr(docker, "cli", fake)
    return calls


def timeout() -> HostError:
    return docker._CliTimeout("docker rm did not finish within 60 s")  # pyright: ignore[reportPrivateUsage]


def test_a_removal_that_times_out_then_finishes_succeeds(
    monkeypatch: pytest.MonkeyPatch, clock: Clock
) -> None:
    calls = script(
        monkeypatch, [timeout(), HostError("removal of container x is already in progress"), None]
    )
    docker._remove(["rm", "--force", "x"], "container")  # pyright: ignore[reportPrivateUsage]
    assert len(calls) == 3
    assert clock.sleeps == [0.1, 0.2]


def test_a_timeout_after_which_the_container_is_gone_counts_as_removed(
    monkeypatch: pytest.MonkeyPatch, clock: Clock
) -> None:
    script(monkeypatch, [timeout(), HostError("Error response from daemon: No such container: x")])
    docker._remove(["rm", "--force", "x"], "container")  # pyright: ignore[reportPrivateUsage]
    assert clock.sleeps == [0.1]


def test_a_removal_that_never_finishes_is_a_host_error_after_the_deadline(
    monkeypatch: pytest.MonkeyPatch, clock: Clock
) -> None:
    script(monkeypatch, [timeout() for _ in range(1000)])
    with pytest.raises(HostError, match=r"did not finish within 600 s: docker rm did not finish"):
        docker._remove(["rm", "--force", "x"], "container")  # pyright: ignore[reportPrivateUsage]
    assert clock.now >= docker.REMOVE_DEADLINE_SECONDS
    assert max(clock.sleeps) == 5.0


def test_any_other_removal_error_is_surfaced_at_once(
    monkeypatch: pytest.MonkeyPatch, clock: Clock
) -> None:
    calls = script(monkeypatch, [HostError("docker rm failed: permission denied")])
    with pytest.raises(HostError, match="removing container: docker rm failed: permission denied"):
        docker._remove(["rm", "--force", "x"], "container")  # pyright: ignore[reportPrivateUsage]
    assert len(calls) == 1
    assert clock.sleeps == []


def test_a_timeout_in_cli_is_a_host_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def expire(*_: object, **__: object) -> None:
        raise subprocess.TimeoutExpired("docker", 60)

    monkeypatch.setattr(docker.subprocess, "run", expire)
    with pytest.raises(HostError, match="docker rm did not finish within 60 s") as raised:
        docker.cli(["rm", "x"])
    assert isinstance(raised.value, docker._CliTimeout)  # pyright: ignore[reportPrivateUsage]
