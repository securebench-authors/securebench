"""Validation the Docker backend performs before it calls Docker."""

from dataclasses import replace
from pathlib import Path

import pytest

from securebench.core.errors import HostError
from securebench.isolation.backend import (
    AGENT_CAPABILITIES,
    EnvironmentSpec,
    Mount,
    MountKind,
    Resources,
)
from securebench.isolation.docker import DockerBackend

IMAGE = "sha256:" + "a" * 64
RESOURCES = Resources(1 << 28, 1_000_000_000, 64, 1 << 30)


def _spec(*mounts: Mount, environment: tuple[tuple[str, str], ...] = ()) -> EnvironmentSpec:
    return EnvironmentSpec(IMAGE, mounts, None, "/srv", None, environment, RESOURCES)


def test_arguments_carry_the_hardening_flags() -> None:
    arguments = DockerBackend(disk_quota=True)._container_arguments(_spec(), ["true"])  # pyright: ignore[reportPrivateUsage]
    joined = " ".join(arguments)
    for flag in (
        "--cap-drop ALL",
        "--security-opt no-new-privileges",
        "--network none",
        "--entrypoint ",
        "--storage-opt size=1073741824",
        "--pids-limit 64",
    ):
        assert flag in joined
    assert arguments[-2:] == [IMAGE, "true"]


def test_no_capability_is_kept_by_default() -> None:
    arguments = DockerBackend(disk_quota=True)._container_arguments(_spec(), ["true"])  # pyright: ignore[reportPrivateUsage]
    assert "--cap-add" not in arguments


def test_the_agent_keeps_exactly_its_capabilities() -> None:
    spec = replace(_spec(), capabilities=AGENT_CAPABILITIES)
    arguments = DockerBackend(disk_quota=True)._container_arguments(spec, ["true"])  # pyright: ignore[reportPrivateUsage]
    added = [arguments[i + 1] for i, flag in enumerate(arguments) if flag == "--cap-add"]
    assert added == ["CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"]
    assert arguments.index("--cap-drop") < arguments.index("--cap-add")


@pytest.mark.parametrize("capability", ["SYS_ADMIN", "NET_RAW", "ALL", "chown"])
def test_capabilities_outside_the_agent_set_are_rejected(capability: str) -> None:
    spec = replace(_spec(), capabilities=AGENT_CAPABILITIES | {capability})
    with pytest.raises(HostError, match="B7"):
        DockerBackend(disk_quota=True)._container_arguments(spec, ["true"])  # pyright: ignore[reportPrivateUsage]


def test_disk_quota_flag_is_omitted_when_not_enforced() -> None:
    arguments = DockerBackend(disk_quota=False)._container_arguments(_spec(), ["true"])  # pyright: ignore[reportPrivateUsage]
    assert "--storage-opt" not in arguments


@pytest.mark.parametrize(
    ("mounts", "reason"),
    [
        ((Mount(MountKind.BIND, "relative/dir", "/a"),), "not an absolute real path"),
        ((Mount(MountKind.BIND, "/nonexistent-securebench", "/a"),), "does not exist"),
        ((Mount(MountKind.BIND, "/", "/a,readonly=false"),), "separator"),
        ((Mount(MountKind.BIND, "/", "/a"), Mount(MountKind.BIND, "/", "/A/b")), "overlaps"),
        ((Mount(MountKind.IMAGE, "python:3.12", "/a"),), "not an image ID"),
        ((Mount(MountKind.BIND, "/", "/a/../b"),), "not canonical"),
    ],
)
def test_invalid_mount_plans_are_rejected(mounts: tuple[Mount, ...], reason: str) -> None:
    with pytest.raises(HostError, match=reason):
        DockerBackend(disk_quota=False)._container_arguments(_spec(*mounts), ["true"])  # pyright: ignore[reportPrivateUsage]


def test_symlinked_bind_source_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "link").symlink_to(tmp_path)
    with pytest.raises(HostError):
        DockerBackend(disk_quota=False)._container_arguments(  # pyright: ignore[reportPrivateUsage]
            _spec(Mount(MountKind.BIND, str(tmp_path / "link"), "/a")), ["true"]
        )


@pytest.mark.parametrize(
    "environment", [(("", "x"),), (("A=B", "x"),), (("A", "x\x00y"),), (("-e", "x"),)]
)
def test_invalid_environment_variables_are_rejected(
    environment: tuple[tuple[str, str], ...],
) -> None:
    with pytest.raises(HostError):
        DockerBackend(disk_quota=False)._container_arguments(  # pyright: ignore[reportPrivateUsage]
            _spec(environment=environment), ["true"]
        )


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), True, 10**400])
def test_unrepresentable_timeouts_are_rejected_before_starting(timeout: float) -> None:
    with pytest.raises(HostError, match="timeout"):
        DockerBackend(disk_quota=False).run(_spec(), ["true"], b"", timeout, 10)


@pytest.mark.parametrize(
    "reference", ["python:3.12", "python", "-x@sha256:" + "a" * 64, "sha256:A"]
)
def test_unpinned_images_are_rejected(reference: str) -> None:
    with pytest.raises(HostError):
        DockerBackend(disk_quota=False).resolve_image(reference)
