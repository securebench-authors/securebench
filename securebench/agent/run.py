"""The Agent run: from a fresh baseline container to a stopped snapshot (Section 9.1)."""

from dataclasses import dataclass

from securebench.agent.harness import HARNESS_MOUNT, Harness
from securebench.agent.network import Services
from securebench.core.errors import HostError
from securebench.core.evidence import Ending, HostFacts
from securebench.core.limits import Limits
from securebench.core.task import INSTRUCTIONS_MOUNT, PublicTask
from securebench.isolation.backend import (
    AGENT_CAPABILITIES,
    EnvironmentSpec,
    Resources,
    Snapshot,
    read_only_bind,
)
from securebench.isolation.docker import DockerBackend

TRANSCRIPT_BOUND = 32 << 20
_SUDOERS_DROP_IN = "/etc/sudoers.d/securebench-proxy"


@dataclass(frozen=True)
class AgentRun:
    """The stopped Agent's snapshot and what the host recorded about the run.

    `transcript` is the harness's standard output: untrusted, kept as data.
    """

    snapshot: Snapshot
    facts: HostFacts
    transcript: bytes
    stderr: bytes


def resources(limits: Limits) -> Resources:
    return Resources(limits.memory_bytes, limits.nano_cpus, limits.pids, limits.disk_bytes)


def preflight(
    backend: DockerBackend, task: PublicTask, baseline_image: str, harness: Harness, limits: Limits
) -> None:
    """Run the harness's version command in the task image, networkless.

    Raises `HostError` when it fails or prints another version: an incompatible
    overlay is the host's problem, never a zero-score attempt.
    """
    if harness.version_command is None:
        return
    spec = EnvironmentSpec(
        baseline_image,
        (read_only_bind(harness.overlay, HARNESS_MOUNT),),
        None,
        task.workdir,
        None,
        harness.environment,
        resources(limits),
    )
    environment, ran = backend.run(spec, harness.version_command, b"", 120, 1 << 16)
    backend.destroy(environment)
    printed = ran.stdout.decode("utf-8", "replace")
    if ran.facts.ending is not Ending.RETURNED or ran.facts.exit_status != 0:
        detail = ran.stderr.decode("utf-8", "replace")[-1000:]
        raise HostError(f"{harness.name} preflight failed ({ran.facts}): {detail}")
    if harness.version not in printed:
        raise HostError(
            f"{harness.name} preflight printed {printed[:200]!r}, not {harness.version}"
        )


def run_agent(
    backend: DockerBackend,
    task: PublicTask,
    baseline_image: str,
    harness: Harness,
    services: Services,
    limits: Limits,
) -> AgentRun:
    """Run the harness until it exits or the time limit expires, then snapshot.

    An expired time limit or transcript bound is not an error: the candidate is
    captured normally (architecture Section 9.1). A harness that cannot start
    is a `HostError`.
    """
    mounts = (
        read_only_bind(task.instructions, INSTRUCTIONS_MOUNT),
        read_only_bind(harness.overlay, HARNESS_MOUNT),
        *(read_only_bind(asset.source, asset.target) for asset in task.public_assets),
    )
    spec = EnvironmentSpec(
        baseline_image,
        mounts,
        services.network.internal if services.network else None,
        task.workdir,
        None,
        (*harness.environment, *services.environment),
        resources(limits),
        AGENT_CAPABILITIES,
    )
    instructions = task.instructions.read_bytes()
    command = _keep_proxy_through_sudo(services, harness.command)
    environment, ran = backend.run(
        spec, command, instructions, limits.agent_timeout_seconds, TRANSCRIPT_BOUND
    )
    try:
        if ran.facts.ending is Ending.CRASHED:
            detail = ran.stderr.decode("utf-8", "replace")[-1000:]
            raise HostError(f"the {harness.name} harness could not start: {detail}")
        snapshot = backend.snapshot(environment)
    finally:
        backend.destroy(environment)
    return AgentRun(snapshot, ran.facts, ran.stdout, ran.stderr)


def _keep_proxy_through_sudo(services: Services, command: tuple[str, ...]) -> tuple[str, ...]:
    """Prefix `command` so that, when the Agent runs as root, `sudo` keeps the proxy variables.

    sudo's `env_reset` drops them, which leaves `sudo apt-get` with no egress
    although the domain is allowed. `/etc/sudoers.d` is
    framework-protected, so the drop-in never enters a capture.
    """
    if services.proxy is None:
        return command
    names = " ".join(name for name, _ in services.environment)
    script = (
        "if [ -w /etc ]; then mkdir -p /etc/sudoers.d"
        f" && echo 'Defaults env_keep += \"{names}\"' > {_SUDOERS_DROP_IN}"
        f' && chmod 0440 {_SUDOERS_DROP_IN}; fi; exec "$@"'
    )
    return ("sh", "-c", script, "sh", *command)
