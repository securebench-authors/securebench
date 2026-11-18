"""The data the isolation backend works with (architecture Section 8.1).

The operations live on `DockerBackend`. An environment runs
exactly one command as its main process. When that process ends, every other
process in the environment ends with it (B2), and the environment's filesystem
stays available for `snapshot` until `destroy`.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from securebench.core.evidence import HostFacts


class MountKind(StrEnum):
    BIND = "bind"
    IMAGE = "image"


@dataclass(frozen=True)
class Mount:
    """A read-only mount: a host directory or file (`bind`), or an image's filesystem (`image`).

    Every mount is read-only (B1). `source` is an absolute host path for
    `bind`, and a verified image ID for `image`.
    """

    kind: MountKind
    source: str
    target: str


@dataclass(frozen=True)
class Resources:
    """Per-environment caps (B6). `disk_bytes` applies only where the backend enforces quotas."""

    memory_bytes: int
    nano_cpus: int
    pids: int
    disk_bytes: int


@dataclass(frozen=True)
class EnvironmentSpec:
    """Everything an environment is created from.

    `image` is a verified image ID (B8). `network` is `None` for no network
    (B5), or the name of a network this backend created. `user` is `None` for
    the image's default user. `environment` lists variables by exact name and
    value; nothing is inherited from the host.
    """

    image: str
    mounts: tuple[Mount, ...]
    network: str | None
    workdir: str
    user: str | None
    environment: tuple[tuple[str, str], ...]
    resources: Resources
    capabilities: frozenset[str] = frozenset()
    """Capabilities kept after dropping all; a subset of `AGENT_CAPABILITIES` (B7)."""


AGENT_CAPABILITIES: frozenset[str] = frozenset(
    {"CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"}
)
"""What the Agent environment keeps so that package managers work as root.
Every other environment keeps no capability."""


@dataclass(frozen=True)
class Environment:
    """A handle on a created environment."""

    name: str


@dataclass(frozen=True)
class Snapshot:
    """An immutable filesystem image taken from a stopped environment."""

    image: str


@dataclass(frozen=True)
class Ran:
    """How the command ended, with a bounded prefix of its output streams.

    `stdout` holds at most the requested bound; when the command wrote more,
    the ending is `OUTPUT_EXCEEDED`. `stderr` holds at most `STDERR_BOUND`
    bytes and is only ever a diagnostic.
    """

    facts: HostFacts
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class AgentNetwork:
    """A run's two networks: `internal` for the Agent, `upstream` for the relay and proxy."""

    internal: str
    upstream: str


@dataclass(frozen=True)
class ServiceSpec:
    """A long-running trusted container (relay or proxy) on a run's networks.

    `alias` is its name on the internal network. `secrets` are host variable
    names whose values are passed by name only, never on a command line,
    where other processes could read them. `extra_hosts` adds fixed name-to-address entries, and
    `extra_networks` further upstream networks; production runs leave both
    empty. `ready` is a text the service prints once it accepts
    connections; `start_service` waits for it.
    """

    environment: EnvironmentSpec
    command: tuple[str, ...]
    alias: str
    secrets: tuple[str, ...]
    extra_hosts: tuple[tuple[str, str], ...]
    extra_networks: tuple[str, ...]
    ready: str


@dataclass(frozen=True)
class Service:
    name: str


STDERR_BOUND = 64 * 1024

STOCK_IMAGE = "python@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d"
"""The stock `python:3.12-slim` image that utility, relay, proxy and probe code runs in,
pinned by its multi-platform index digest."""


class Cancelled(Exception):
    """`run` stopped because its cancel event was set."""


def read_only_bind(source: Path, target: str) -> Mount:
    """A read-only bind mount of an existing, absolute, non-symlink host path."""
    return Mount(MountKind.BIND, str(source.absolute()), target)
