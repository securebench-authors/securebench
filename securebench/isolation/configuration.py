"""The per-run configuration check (architecture Section 8.5)."""

from dataclasses import dataclass

from securebench.core import jsondata
from securebench.core.errors import HostError, Rejected
from securebench.core.jsondata import JsonValue
from securebench.isolation.docker import DockerBackend, cli
from securebench.isolation.qualification import disk_quota_probe

MINIMUM_SERVER_MAJOR = 28


@dataclass(frozen=True)
class Configuration:
    """What the check found. `failures` is empty when the worker may run admitted attempts."""

    facts: JsonValue
    disk_quota: bool
    failures: tuple[str, ...]


def check_configuration(probe_image: str) -> Configuration:
    """Inspect the daemon and probe disk-quota enforcement live.

    Requires a Linux daemon of version 28 or later (image mounts, isolated
    gateway mode), cgroup v2, seccomp and an enforced disk quota.
    `probe_image` is a verified image ID with Python.
    """
    version = _json(["version", "--format", "{{json .}}"])
    info = _json(["info", "--format", "{{json .}}"])
    server = version.get("Server")
    client = version.get("Client")
    server_version = server.get("Version") if isinstance(server, dict) else None
    facts: dict[str, JsonValue] = {
        "client_version": client.get("Version") if isinstance(client, dict) else None,
        "server_version": server_version,
        "server_os": server.get("Os") if isinstance(server, dict) else None,
        "kernel": info.get("KernelVersion"),
        "operating_system": info.get("OperatingSystem"),
        "storage_driver": info.get("Driver"),
        "cgroup_version": info.get("CgroupVersion"),
        "security_options": info.get("SecurityOptions"),
    }
    failures: list[str] = []
    if facts["server_os"] != "linux":
        failures.append(f"the daemon runs {facts['server_os']}, not linux")
    if not isinstance(server_version, str) or _major(server_version) < MINIMUM_SERVER_MAJOR:
        failures.append(f"Docker {server_version} is older than {MINIMUM_SERVER_MAJOR}")
    if facts["cgroup_version"] != "2":
        failures.append("the daemon does not use cgroup v2")
    options = facts["security_options"]
    if not isinstance(options, list) or not any("seccomp" in str(item) for item in options):
        failures.append("the daemon does not apply seccomp")
    disk_quota = _probe_quota(probe_image)
    facts["disk_quota"] = disk_quota
    if not disk_quota:
        failures.append("the daemon does not enforce per-container disk quotas")
    return Configuration(facts, disk_quota, tuple(failures))


def _probe_quota(probe_image: str) -> bool:
    try:
        passed, _ = disk_quota_probe(DockerBackend(disk_quota=True), probe_image)
    except HostError as error:
        if "storage-opt" in error.reason or "storage opt" in error.reason:
            return False
        raise
    return passed


def _json(arguments: list[str]) -> dict[str, JsonValue]:
    try:
        value = jsondata.decode(cli(arguments).stdout, 1 << 20)
    except Rejected as error:
        raise HostError(f"docker {arguments[0]} returned malformed JSON: {error.reason}") from None
    if not isinstance(value, dict):
        raise HostError(f"docker {arguments[0]} returned malformed JSON")
    return value


def _major(version: str) -> int:
    head = version.split(".", 1)[0]
    return int(head) if head.isdigit() else 0
