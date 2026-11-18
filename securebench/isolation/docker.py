"""The Docker implementation of the backend contract, driven through the `docker` CLI.

Every call uses an argument list and never a shell. Every
container is created with all capabilities dropped, no new privileges, the
default seccomp profile, no devices, an empty entrypoint and the `none` log
driver (B7), and is named `securebench-<32 hex>` before it
is created so that cleanup works even after an ambiguous failure.
"""

import os
import selectors
import subprocess
import tempfile
import threading
import time
import uuid
from collections.abc import Sequence
from typing import IO, cast

from securebench.core import hashing, jsondata, paths
from securebench.core.errors import HostError, Rejected
from securebench.core.evidence import Ending, HostFacts
from securebench.isolation.backend import (
    AGENT_CAPABILITIES,
    STDERR_BOUND,
    AgentNetwork,
    Cancelled,
    Environment,
    EnvironmentSpec,
    MountKind,
    Ran,
    Service,
    ServiceSpec,
    Snapshot,
)

CLI_TIMEOUT_SECONDS = 60
# Removing a container with a large writable layer can outlast one CLI call on a
# loaded host, and Docker keeps removing after the client stops waiting.
REMOVE_DEADLINE_SECONDS = 600
# Committing a large writable layer can outlast one CLI call on a loaded host. A
# retry would race the daemon's unfinished commit, so it gets one long call (0039).
COMMIT_TIMEOUT_SECONDS = 600
PULL_TIMEOUT_SECONDS = 1800
NAME_PREFIX = "securebench-"
LABEL = "securebench.owned=1"
MAX_RUN_SECONDS = 24 * 3600
SERVICE_LOG_MAX = "16m"
SERVICE_READY_SECONDS = 30
UPSTREAM_INTERFACE_PREFIX = "sbu"
_CLI_ENVIRONMENT = ("PATH", "HOME", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG")
_MOUNT_FORBIDDEN = frozenset(',"\n\r')
_POLL_SECONDS = 0.1
_KILL_RETRY_SECONDS = 1.0


class DockerBackend:
    """The operations of architecture Section 8.1, realized with Docker.

    `disk_quota` says whether the daemon enforces `--storage-opt size`.
    """

    def __init__(self, disk_quota: bool) -> None:
        self.disk_quota = disk_quota

    def resolve_image(self, reference: str) -> str:
        """Return the image ID of a digest-pinned reference, pulling it by digest if absent.

        Raises `HostError` when the image cannot be verified (B8).
        """
        _check_pinned(reference)
        found = _inspect_image_id(reference)
        if found is None and not reference.startswith("sha256:"):
            cli(["pull", "--quiet", reference], timeout=PULL_TIMEOUT_SECONDS)
            found = _inspect_image_id(reference)
        if found is None:
            raise HostError(f"image {reference} is not available")
        if reference.startswith("sha256:") and found != reference:
            raise HostError(f"image {reference} resolved to a different ID {found}")
        return found

    def run(
        self,
        spec: EnvironmentSpec,
        command: Sequence[str],
        stdin: bytes,
        timeout_seconds: float,
        output_bound: int,
        cancel: threading.Event | None = None,
    ) -> tuple[Environment, Ran]:
        """Create an environment, run `command` as its main process, and wait for it to end.

        `stdin` is delivered from a file. On timeout or when `output_bound`
        is exceeded, the environment is killed. When `cancel` is set the
        environment is killed and `Cancelled` raised after it is destroyed.
        The returned environment is stopped and must be destroyed by the
        caller. Raises `HostError` for failures of the mechanism.
        """
        _check_timeout(timeout_seconds)
        if output_bound <= 0:
            raise HostError("output bound must be positive")
        arguments = self._container_arguments(spec, command)
        environment = Environment(NAME_PREFIX + uuid.uuid4().hex)
        try:
            ran = self._run(environment, arguments, stdin, timeout_seconds, output_bound, cancel)
        except BaseException:
            self.destroy(environment)
            raise
        return environment, ran

    def _container_arguments(self, spec: EnvironmentSpec, command: Sequence[str]) -> list[str]:
        """Validate the whole spec before any name is assigned."""
        _check_mounts(spec)
        _check_command(command)
        if not spec.capabilities <= AGENT_CAPABILITIES:
            extra = sorted(spec.capabilities - AGENT_CAPABILITIES)
            raise HostError(f"capabilities outside the Agent's set (B7): {extra}")
        if spec.workdir != "/":
            try:
                paths.check_absolute(spec.workdir)
            except Rejected as error:
                raise HostError(f"workdir: {error.reason}") from None
        arguments = [
            "--label",
            LABEL,
            # A minimal init from the host's Docker as PID 1: the command is an
            # ordinary process that signals can reach, and zombies are reaped (0014).
            "--init",
            "--entrypoint",
            "",
            "--cap-drop",
            "ALL",
            *(flag for name in sorted(spec.capabilities) for flag in ("--cap-add", name)),
            "--security-opt",
            "no-new-privileges",
            "--network",
            spec.network or "none",
            "--memory",
            str(spec.resources.memory_bytes),
            "--memory-swap",
            str(spec.resources.memory_bytes),
            "--pids-limit",
            str(spec.resources.pids),
            "--cpus",
            f"{spec.resources.nano_cpus / 1e9:.3f}",
            "--workdir",
            spec.workdir,
            "--hostname",
            "securebench",
        ]
        if self.disk_quota:
            arguments += ["--storage-opt", f"size={spec.resources.disk_bytes}"]
        if spec.user is not None:
            arguments += ["--user", spec.user]
        for name, value in spec.environment:
            _check_variable(name, value)
            arguments += ["--env", f"{name}={value}"]
        for mount in spec.mounts:
            if mount.kind is MountKind.BIND:
                description = f"type=bind,source={mount.source},target={mount.target},readonly"
            else:
                description = f"type=image,source={mount.source},target={mount.target}"
            arguments += ["--mount", description]
        return [*arguments, spec.image, *command]

    def _run(
        self,
        environment: Environment,
        arguments: list[str],
        stdin: bytes,
        timeout_seconds: float,
        output_bound: int,
        cancel: threading.Event | None,
    ) -> Ran:
        with tempfile.TemporaryFile() as stdin_file:
            stdin_file.write(stdin)
            stdin_file.seek(0)
            started = time.monotonic()
            process = subprocess.Popen(
                [
                    "docker",
                    "run",
                    "--interactive",
                    "--log-driver",
                    "none",
                    "--name",
                    environment.name,
                    *arguments,
                ],
                stdin=stdin_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_cli_environment(),
            )
            try:
                stdout, stderr, reason = _supervise(
                    process, started + timeout_seconds, output_bound, cancel
                )
                # Closing our ends first lets a CLI (and the daemon behind it) that is
                # blocked writing to a full pipe give up, so the kill is not stuck.
                cast(IO[bytes], process.stdout).close()
                cast(IO[bytes], process.stderr).close()
                if reason is not None:
                    _stop(process, environment.name)
                process.wait(timeout=CLI_TIMEOUT_SECONDS)
            except BaseException:
                process.kill()
                process.wait()
                raise
            duration = time.monotonic() - started
        if reason == "cancelled":
            raise Cancelled(environment.name)
        state = _container_state(environment.name, stderr)
        if reason == "output":
            ending, exit_status = Ending.OUTPUT_EXCEEDED, None
            stdout = stdout[:output_bound]
        elif reason == "timeout":
            ending, exit_status = Ending.TIMED_OUT, None
        elif state["OOMKilled"] is True:
            ending, exit_status = Ending.MEMORY_KILLED, None
        elif state["started"]:
            code = state["ExitCode"]
            ending, exit_status = Ending.RETURNED, code if isinstance(code, int) else None
        else:
            ending, exit_status = Ending.CRASHED, None
        return Ran(HostFacts(ending, exit_status, round(duration, 3)), stdout, stderr)

    def snapshot(self, environment: Environment) -> Snapshot:
        """Take a filesystem snapshot of a stopped environment (B3: never written in place)."""
        result = cli(
            ["commit", "--change", f"LABEL {LABEL}", environment.name], COMMIT_TIMEOUT_SECONDS
        )
        image = result.stdout.decode("ascii", "replace").strip()
        if not image.startswith("sha256:"):
            raise HostError(f"docker commit returned {image[:100]!r}")
        return Snapshot(image)

    def destroy(self, environment: Environment) -> None:
        """Remove the environment and everything it wrote; confirm it is gone (B4)."""
        _remove(["rm", "--force", "--volumes", environment.name], "container")
        _confirm_absent(["container", "inspect", environment.name])

    def destroy_snapshot(self, snapshot: Snapshot) -> None:
        """Remove a snapshot image; confirm it is gone (B4)."""
        # Without --no-prune Docker also deletes untagged parent images, which
        # would remove a setup snapshot or replayed candidate still in use.
        _remove(["image", "rm", "--force", "--no-prune", snapshot.image], "image")
        _confirm_absent(["image", "inspect", snapshot.image])

    def create_agent_network(self) -> AgentNetwork:
        """Create a run's internal network (no gateway, B5) and its upstream network."""
        suffix = uuid.uuid4().hex
        network = AgentNetwork(f"{NAME_PREFIX}internal-{suffix}", f"{NAME_PREFIX}upstream-{suffix}")
        try:
            cli(
                [
                    "network",
                    "create",
                    "--driver",
                    "bridge",
                    "--internal",
                    "--label",
                    LABEL,
                    "--opt",
                    "com.docker.network.bridge.gateway_mode_ipv4=isolated",
                    "--opt",
                    "com.docker.network.bridge.gateway_mode_ipv6=isolated",
                    network.internal,
                ]
            )
            _check_internal_network(network.internal)
            cli(
                [
                    "network",
                    "create",
                    "--driver",
                    "bridge",
                    "--label",
                    LABEL,
                    # A fixed interface prefix lets one host firewall rule cover every
                    # run's upstream network (docs/operating.md).
                    "--opt",
                    f"com.docker.network.bridge.name={UPSTREAM_INTERFACE_PREFIX}{suffix[:12]}",
                    network.upstream,
                ]
            )
        except BaseException:
            self.destroy_agent_network(network)
            raise
        return network

    def destroy_agent_network(self, network: AgentNetwork) -> None:
        """Remove both networks; confirm they are gone (B4)."""
        failures: list[str] = []
        for name in (network.internal, network.upstream):
            try:
                _remove(["network", "rm", name], "network")
                _confirm_absent(["network", "inspect", name])
            except HostError as error:
                failures.append(error.reason)
        if failures:
            raise HostError("; ".join(failures))

    def start_service(self, spec: ServiceSpec, network: AgentNetwork) -> Service:
        """Start a service on `upstream` and attach it to `internal` under its alias."""
        if spec.environment.network not in (None, network.upstream):
            raise HostError("a service starts on its run's upstream network")
        arguments = self._container_arguments(spec.environment, spec.command)
        options = ["--network", network.upstream, "--read-only", "--tmpfs", "/tmp:size=16m"]
        options += ["--log-driver", "json-file", "--log-opt", f"max-size={SERVICE_LOG_MAX}"]
        options += ["--log-opt", "max-file=1"]
        for secret in spec.secrets:
            _check_variable(secret, "")
            if secret not in os.environ:
                raise HostError(f"secret variable {secret} is not set on the host")
            options += ["--env", secret]
        for host, address in spec.extra_hosts:
            _check_variable(host, address)
            options += ["--add-host", f"{host}:{address}"]
        network_index = arguments.index("--network")
        del arguments[network_index : network_index + 2]
        image_index = arguments.index(spec.environment.image)
        arguments[image_index:image_index] = options
        service = Service(NAME_PREFIX + uuid.uuid4().hex)
        extra = {name: os.environ[name] for name in spec.secrets}
        try:
            cli(["run", "--detach", "--name", service.name, *arguments], extra_env=extra)
            cli(["network", "connect", "--alias", spec.alias, network.internal, service.name])
            for extra in spec.extra_networks:
                cli(["network", "connect", extra, service.name])
            _wait_ready(service.name, spec.ready)
        except BaseException:
            _remove(["rm", "--force", service.name], "container")
            raise
        return service

    def stop_service(self, service: Service, log_bound: int) -> bytes:
        """Stop and remove a service, returning at most `log_bound` bytes of its output."""
        try:
            logs = cli(["logs", service.name], merge_stderr=True).stdout[:log_bound]
        finally:
            _remove(["rm", "--force", service.name], "container")
            _confirm_absent(["container", "inspect", service.name])
        return logs


def remove_leftovers() -> list[str]:
    """Remove every container, network and image labelled as SecureBench-owned.

    For recovery after a crashed run, only when no run is active. Returns
    what was removed.
    """
    removed: list[str] = []
    for listing, removal in (
        (["ps", "--all", "--quiet", "--filter", f"label={LABEL}"], ["rm", "--force"]),
        (["network", "ls", "--quiet", "--filter", f"label={LABEL}"], ["network", "rm"]),
        (
            ["image", "ls", "--all", "--quiet", "--filter", f"label={LABEL}"],
            ["image", "rm", "--force"],
        ),
    ):
        for identifier in cli(listing).stdout.decode("ascii", "replace").split():
            _remove([*removal, identifier], "leftover")
            removed.append(identifier)
    return removed


class _CliTimeout(HostError):
    """A docker call outlived its timeout; the daemon may still be carrying it out."""


def cli(
    arguments: list[str],
    timeout: float = CLI_TIMEOUT_SECONDS,
    extra_env: dict[str, str] | None = None,
    merge_stderr: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    """Run one bounded `docker` call; any failure is a `HostError` with Docker's message."""
    environment = _cli_environment()
    environment.update(extra_env or {})
    try:
        result = subprocess.run(
            ["docker", *arguments],
            stdin=subprocess.DEVNULL,
            capture_output=not merge_stderr,
            stdout=subprocess.PIPE if merge_stderr else None,
            stderr=subprocess.STDOUT if merge_stderr else None,
            timeout=timeout,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise _CliTimeout(f"docker {arguments[0]} did not finish within {timeout} s") from None
    if result.returncode != 0:
        message = (result.stderr or b"").decode("utf-8", "replace").strip()[:2000]
        raise HostError(f"docker {' '.join(arguments[:2])} failed: {message}")
    return result


def _cli_environment() -> dict[str, str]:
    return {name: os.environ[name] for name in _CLI_ENVIRONMENT if name in os.environ}


def _inspect_image_id(reference: str) -> str | None:
    try:
        result = cli(["image", "inspect", "--format", "{{.Id}}", reference])
    except HostError as error:
        if "No such image" in error.reason or "no such image" in error.reason:
            return None
        raise
    return result.stdout.decode("ascii", "replace").strip()


def _supervise(
    process: subprocess.Popen[bytes],
    deadline: float,
    output_bound: int,
    cancel: threading.Event | None,
) -> tuple[bytes, bytes, str | None]:
    """Drain both pipes under one deadline; say why we stopped early, if so."""
    stdout = bytearray()
    stderr = bytearray()
    selector = selectors.DefaultSelector()
    streams = cast(tuple[IO[bytes], IO[bytes]], (process.stdout, process.stderr))
    for stream in streams:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ)
    open_streams = 2
    try:
        while open_streams:
            if cancel is not None and cancel.is_set():
                return bytes(stdout), bytes(stderr), "cancelled"
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return bytes(stdout), bytes(stderr), "timeout"
            for key, _ in selector.select(min(remaining, _POLL_SECONDS)):
                stream = cast(IO[bytes], key.fileobj)
                chunk = os.read(stream.fileno(), 65536)
                if not chunk:
                    selector.unregister(stream)
                    open_streams -= 1
                elif stream is process.stdout:
                    stdout += chunk
                    if len(stdout) > output_bound:
                        return bytes(stdout), bytes(stderr), "output"
                elif len(stderr) < STDERR_BOUND:
                    stderr += chunk[: STDERR_BOUND - len(stderr)]
    finally:
        selector.close()
    return bytes(stdout), bytes(stderr), None


def _stop(process: subprocess.Popen[bytes], name: str) -> None:
    """Kill the container until the `docker run` attached to it exits.

    A container that `docker run` has not yet created or started answers a
    kill with "No such container" or "is not running", and would then start
    and run on. Killing again until the CLI exits stops it whenever it starts.
    """
    deadline = time.monotonic() + CLI_TIMEOUT_SECONDS
    while True:
        _kill(name)
        try:
            process.wait(timeout=_KILL_RETRY_SECONDS)
            return
        except subprocess.TimeoutExpired:
            if time.monotonic() >= deadline:
                raise HostError(
                    f"container {name} did not stop within {CLI_TIMEOUT_SECONDS} s"
                ) from None


def _kill(name: str) -> None:
    try:
        cli(["kill", name])
    except HostError as error:
        if "is not running" not in error.reason and "No such container" not in error.reason:
            raise


def _container_state(name: str, stderr: bytes) -> dict[str, object]:
    try:
        result = cli(["container", "inspect", "--format", "{{json .State}}", name])
    except HostError as error:
        detail = stderr.decode("utf-8", "replace")[-500:]
        raise HostError(f"container {name} vanished: {error.reason}; {detail}") from None
    try:
        state = jsondata.decode(result.stdout, 1 << 16)
    except Rejected as error:
        raise HostError(f"docker returned malformed state: {error.reason}") from None
    if not isinstance(state, dict):
        raise HostError("docker returned malformed state")
    started_at = state.get("StartedAt")
    started = isinstance(started_at, str) and not started_at.startswith("0001-")
    message = state.get("Error")
    if not started and not (isinstance(message, str) and "exec" in message):
        raise HostError(f"container {name} did not start: {message!r}")
    return {**state, "started": started}


def _remove(arguments: list[str], what: str) -> None:
    """Idempotent removal that waits out a slow daemon.

    Docker's concurrent-removal race and a CLI timeout both mean the removal may
    still be under way, so both are retried until `REMOVE_DEADLINE_SECONDS`.
    """
    deadline = time.monotonic() + REMOVE_DEADLINE_SECONDS
    pause = 0.1
    while True:
        try:
            cli(arguments)
            return
        except _CliTimeout as error:
            last = error.reason
        except HostError as error:
            text = error.reason.lower()
            if "no such" in text or "not found" in text:
                return
            if "already in progress" not in text:
                raise HostError(f"removing {what}: {error.reason}") from None
            last = error.reason
        if time.monotonic() >= deadline:
            raise HostError(
                f"removing {what} {arguments[-1]} did not finish within "
                f"{REMOVE_DEADLINE_SECONDS} s: {last}"
            )
        time.sleep(pause)
        pause = min(pause * 2, 5.0)


def _confirm_absent(arguments: list[str]) -> None:
    """Positively confirm removal."""
    try:
        cli(arguments)
    except HostError as error:
        text = error.reason.lower()
        if "no such" in text or "not found" in text:
            return
        raise
    raise HostError(f"{arguments[0]} {arguments[-1]} still exists after removal")


def _check_internal_network(name: str) -> None:
    """Inspect the new network before anything attaches."""
    result = cli(["network", "inspect", "--format", "{{json .}}", name])
    try:
        info = jsondata.decode(result.stdout, 1 << 16)
    except Rejected as error:
        raise HostError(f"network inspect returned malformed data: {error.reason}") from None
    if not isinstance(info, dict):
        raise HostError("network inspect returned malformed data")
    options = info.get("Options")
    ipam = info.get("IPAM")
    configs = ipam.get("Config") if isinstance(ipam, dict) else None
    if (
        info.get("Internal") is not True
        or info.get("Driver") != "bridge"
        or not isinstance(options, dict)
        or options.get("com.docker.network.bridge.gateway_mode_ipv4") != "isolated"
        or options.get("com.docker.network.bridge.gateway_mode_ipv6") != "isolated"
        or not isinstance(ipam, dict)
        or ipam.get("Driver") != "default"
        or not isinstance(configs, list)
        or any(not isinstance(config, dict) or config.get("Gateway") for config in configs)
    ):
        raise HostError(f"network {name} is not an isolated internal network: {info}")


def _wait_ready(name: str, marker: str) -> None:
    """Wait until the service prints `marker`; fail if it exits first."""
    deadline = time.monotonic() + SERVICE_READY_SECONDS
    while time.monotonic() < deadline:
        logs = cli(["logs", name], merge_stderr=True).stdout
        if marker.encode() in logs:
            return
        state = cli(["container", "inspect", "--format", "{{.State.Running}}", name]).stdout
        if state.strip() != b"true":
            raise HostError(f"service {name} exited before it was ready: {logs[-1000:]!r}")
        time.sleep(0.2)
    raise HostError(f"service {name} was not ready within {SERVICE_READY_SECONDS} s")


def _check_pinned(reference: str) -> None:
    repository, separator, digest = reference.rpartition("@")
    if not separator:
        repository, digest = "", reference
    try:
        hashing.check_digest(digest)
    except Rejected:
        raise HostError(f"image reference {reference!r} is not pinned by digest") from None
    if separator and (not repository or repository.startswith("-") or "\x00" in repository):
        raise HostError(f"image reference {reference!r} has an invalid repository")


def _check_timeout(timeout_seconds: float) -> None:
    # The range test also rejects NaN and infinities, without converting huge ints to float.
    if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= MAX_RUN_SECONDS:
        raise HostError(f"timeout {timeout_seconds!r} is not a finite positive number of seconds")


def _check_mounts(spec: EnvironmentSpec) -> None:
    targets: list[str] = []
    for mount in spec.mounts:
        try:
            paths.check_absolute(mount.target)
        except Rejected as error:
            raise HostError(f"mount target: {error.reason}") from None
        if _MOUNT_FORBIDDEN & set(mount.source + mount.target):
            raise HostError(f"mount {mount.source} -> {mount.target} has a separator character")
        if mount.kind is MountKind.BIND:
            if not os.path.isabs(mount.source) or os.path.islink(mount.source):
                raise HostError(f"bind source {mount.source} is not an absolute real path")
            if not os.path.exists(mount.source):
                raise HostError(f"bind source {mount.source} does not exist")
        elif not mount.source.startswith("sha256:"):
            raise HostError(f"image mount source {mount.source} is not an image ID")
        if any(paths.overlaps_folded(mount.target, other) for other in targets):
            raise HostError(f"mount target {mount.target} overlaps another mount")
        targets.append(mount.target)


def _check_command(command: Sequence[str]) -> None:
    if not command or any(not part or "\x00" in part for part in command):
        raise HostError("command parts must be non-empty and free of NUL")


def _check_variable(name: str, value: str) -> None:
    if not name or "=" in name or "\x00" in name or "\x00" in value or name.startswith("-"):
        raise HostError(f"environment variable {name!r} is not valid")
