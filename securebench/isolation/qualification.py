"""The live qualification suite for B1 to B8 (architecture Section 8.5).

Each probe exercises the real backend with a stock Python image and records
what it saw. Negative network probes are paired with a positive control,
so that "blocked" never only means "nothing was listening".
"""

import socket
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from securebench.core import jsondata
from securebench.core.errors import HostError
from securebench.core.jsondata import JsonValue
from securebench.isolation.backend import (
    AGENT_CAPABILITIES,
    EnvironmentSpec,
    Mount,
    MountKind,
    Resources,
    ServiceSpec,
)
from securebench.isolation.docker import DockerBackend, cli

PROBE_RESOURCES = Resources(256 << 20, 1_000_000_000, 64, 64 << 20)
SERVICE_PORT = 8080


@dataclass(frozen=True)
class Probe:
    guarantee: str
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Qualification:
    """A qualification record: worker facts and one result per probe."""

    facts: JsonValue
    probes: tuple[Probe, ...]

    @property
    def passed(self) -> bool:
        return all(probe.passed for probe in self.probes)

    def to_json(self) -> JsonValue:
        return {
            "facts": self.facts,
            "probes": [
                {
                    "detail": probe.detail,
                    "guarantee": probe.guarantee,
                    "name": probe.name,
                    "passed": probe.passed,
                }
                for probe in self.probes
            ],
        }

    @property
    def id(self) -> str:
        """The digest of the record, referenced from run provenance."""
        return jsondata.digest(self.to_json())


def qualify(backend: DockerBackend, image: str, facts: JsonValue) -> Qualification:
    """Run every probe with `image` (a verified stock image) and return the record."""
    probes: list[Probe] = []
    for guarantee, name, probe in _PROBES:
        try:
            passed, detail = probe(backend, image)
        except HostError as error:
            passed, detail = False, f"host error: {error.reason}"
        probes.append(Probe(guarantee, name, passed, detail[:2000]))
    return Qualification(facts, tuple(probes))


def _spec(
    image: str, mounts: tuple[Mount, ...] = (), network: str | None = None
) -> EnvironmentSpec:
    return EnvironmentSpec(image, mounts, network, "/", "0", (), PROBE_RESOURCES)


def _python(
    backend: DockerBackend, spec: EnvironmentSpec, program: str, timeout: float = 60
) -> tuple[str, int | None]:
    environment, ran = backend.run(spec, ["python3", "-I", "-c", program], b"", timeout, 65536)
    backend.destroy(environment)
    return ran.stdout.decode("utf-8", "replace").strip(), ran.facts.exit_status


def _read_only_mounts(backend: DockerBackend, image: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "input").write_text("x")
        mounts = (
            Mount(MountKind.BIND, directory, "/probe/bind"),
            Mount(MountKind.IMAGE, image, "/probe/image"),
        )
        program = (
            "import os\n"
            "results = []\n"
            "for path in ('/probe/bind/new', '/probe/bind/input', '/probe/image/new'):\n"
            "    try:\n"
            "        open(path, 'w').write('y')\n"
            "        results.append('writable')\n"
            "    except OSError:\n"
            "        results.append('denied')\n"
            "print(','.join(results))\n"
        )
        output, _ = _python(backend, _spec(image, mounts), program)
        host_unchanged = Path(directory, "input").read_text() == "x"
        return output == "denied,denied,denied" and host_unchanged, output


def _no_process_survives(backend: DockerBackend, image: str) -> tuple[bool, str]:
    environment, _ = backend.run(
        _spec(image), ["sh", "-c", "sleep 1000 & sleep 1000 & exit 0"], b"", 30, 1024
    )
    try:
        snapshot = backend.snapshot(environment)
    finally:
        backend.destroy(environment)
    backend.destroy_snapshot(snapshot)
    return True, "main process exited; the environment was stopped and could be snapshotted"


def _no_shared_writable_state(backend: DockerBackend, image: str) -> tuple[bool, str]:
    first, _ = backend.run(_spec(image), ["sh", "-c", "echo base > /srv/state"], b"", 30, 1024)
    try:
        snapshot = backend.snapshot(first)
    finally:
        backend.destroy(first)
    try:
        clone = _spec(snapshot.image)
        writer, _ = backend.run(clone, ["sh", "-c", "echo changed > /srv/state"], b"", 30, 1024)
        backend.destroy(writer)
        reader, ran = backend.run(clone, ["cat", "/srv/state"], b"", 30, 1024)
        backend.destroy(reader)
    finally:
        backend.destroy_snapshot(snapshot)
    seen = ran.stdout.decode("utf-8", "replace").strip()
    return seen == "base", f"a fresh clone read {seen!r}"


def _destroy_is_complete(backend: DockerBackend, image: str) -> tuple[bool, str]:
    environment, _ = backend.run(_spec(image), ["true"], b"", 30, 1024)
    backend.destroy(environment)
    network = backend.create_agent_network()
    backend.destroy_agent_network(network)
    return True, "destroy confirmed the container and both networks absent"


def _no_network_by_default(backend: DockerBackend, image: str) -> tuple[bool, str]:
    program = (
        "import socket\n"
        "routes = len(open('/proc/net/route').read().splitlines()) - 1\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
        "    reach = 'reached'\n"
        "except OSError:\n"
        "    reach = 'blocked'\n"
        "print(f'routes={routes}', reach)\n"
    )
    output, _ = _python(backend, _spec(image), program)
    return output == "routes=0 blocked", output


_SERVER = (
    "import http.server\n"
    "class H(http.server.BaseHTTPRequestHandler):\n"
    "    def do_GET(self):\n"
    "        self.send_response(200); self.end_headers(); self.wfile.write(b'peer')\n"
    f"server = http.server.HTTPServer(('0.0.0.0', {SERVICE_PORT}), H)\n"
    "print('serving', flush=True)\n"
    "server.serve_forever()\n"
)

_REACH = (
    "import socket, sys, urllib.request\n"
    "out = []\n"
    "try:\n"
    f"    url = 'http://peer:{SERVICE_PORT}/'\n"
    "    out.append(urllib.request.urlopen(url, timeout=5).read().decode())\n"
    "except OSError as error:\n"
    "    out.append('peer-unreachable')\n"
    "try:\n"
    "    socket.getaddrinfo('example.com', 80)\n"
    "    out.append('dns-resolved')\n"
    "except OSError:\n"
    "    out.append('blocked')\n"
    "for host, port in [('1.1.1.1', 53), ('169.254.169.254', 80),"
    " ('host.docker.internal', 80), (sys.argv[1], 80), (sys.argv[1], 22)]:\n"
    "    try:\n"
    "        socket.create_connection((host, port), timeout=3)\n"
    "        out.append(f'{host}:{port}=reached')\n"
    "    except OSError:\n"
    "        out.append('blocked')\n"
    "print(' '.join(out))\n"
)


def _restricted_network_reaches_only_peers(backend: DockerBackend, image: str) -> tuple[bool, str]:
    network = backend.create_agent_network()
    try:
        service = backend.start_service(
            ServiceSpec(
                _spec(image), ("python3", "-I", "-u", "-c", _SERVER), "peer", (), (), (), "serving"
            ),
            network,
        )
        try:
            gateway = _upstream_gateway(network.upstream)
            spec = _spec(image, network=network.internal)
            command = ["python3", "-I", "-c", _REACH, gateway]
            output = "peer-unreachable"
            for _ in range(20):
                environment, ran = backend.run(spec, command, b"", 60, 65536)
                backend.destroy(environment)
                output = ran.stdout.decode("utf-8", "replace").strip()
                if not output.startswith("peer-unreachable"):
                    break
        finally:
            backend.stop_service(service, 4096)
    finally:
        backend.destroy_agent_network(network)
    expected = "peer " + " ".join(["blocked"] * 6)
    return output == expected, f"upstream gateway {gateway}: {output}"


def _upstream_gateway(name: str) -> str:
    result = cli(
        ["network", "inspect", "--format", "{{range .IPAM.Config}}{{.Gateway}}{{end}}", name]
    )
    return result.stdout.decode("ascii", "replace").strip() or "0.0.0.0"


_UPSTREAM_REACH = (
    "import socket, sys\n"
    "port = int(sys.argv[1])\n"
    "try:\n"
    "    socket.create_connection(('1.1.1.1', 53), timeout=5).close()\n"
    "    out = ['internet']\n"
    "except OSError:\n"
    "    out = ['no-internet']\n"
    "for host in sys.argv[2:]:\n"
    "    try:\n"
    "        socket.create_connection((host, port), timeout=3).close()\n"
    "        out.append(f'{host}=reached')\n"
    "    except OSError:\n"
    "        out.append('blocked')\n"
    "print(' '.join(out))\n"
)


def _upstream_reaches_only_global(backend: DockerBackend, image: str) -> tuple[bool, str]:
    """B5 for the relay and proxy network, with two positive controls:
    the network reaches the Internet, and the host listener it must not reach is up."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("0.0.0.0", 0))
    listener.listen(16)
    port = listener.getsockname()[1]
    threading.Thread(target=_accept_forever, args=(listener,), daemon=True).start()
    try:
        socket.create_connection(("127.0.0.1", port), timeout=3).close()
        network = backend.create_agent_network()
        try:
            targets = [
                _upstream_gateway(network.upstream),
                "host.docker.internal",
                *_host_addresses(),
            ]
            spec = _spec(image, network=network.upstream)
            command = ["python3", "-I", "-c", _UPSTREAM_REACH, str(port), *targets]
            environment, ran = backend.run(spec, command, b"", 120, 65536)
            backend.destroy(environment)
        finally:
            backend.destroy_agent_network(network)
    finally:
        listener.close()
    output = ran.stdout.decode("utf-8", "replace").strip()
    expected = " ".join(["internet", *["blocked"] * len(targets)])
    return output == expected, f"host listener on port {port}, targets {targets}: {output}"


def _accept_forever(listener: socket.socket) -> None:
    while True:
        try:
            connection, _ = listener.accept()
        except OSError:
            return
        connection.close()


def _host_addresses() -> list[str]:
    """The worker's own non-loopback IPv4 addresses."""
    try:
        answers = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    found = {str(answer[4][0]) for answer in answers}
    return sorted(address for address in found if not address.startswith("127."))


def _limits_are_enforced_and_reported(backend: DockerBackend, image: str) -> tuple[bool, str]:
    spec = _spec(image)
    details: list[str] = []
    environment, ran = backend.run(spec, ["python3", "-I", "-c", "b'x' * (1 << 30)"], b"", 60, 1024)
    backend.destroy(environment)
    details.append(f"memory:{ran.facts.ending.value}")
    environment, ran = backend.run(spec, ["sleep", "60"], b"", 1, 1024)
    backend.destroy(environment)
    details.append(f"time:{ran.facts.ending.value}")
    environment, ran = backend.run(spec, ["yes"], b"", 30, 4096)
    backend.destroy(environment)
    details.append(f"output:{ran.facts.ending.value}")
    fork_program = (
        "import subprocess\n"
        "started = 0\n"
        "try:\n"
        "    for _ in range(500):\n"
        "        subprocess.Popen(['sleep', '30']); started += 1\n"
        "except OSError:\n"
        "    pass\n"
        "print(started)\n"
    )
    output, _ = _python(backend, spec, fork_program)
    details.append(f"pids:{output}")
    passed = (
        details[:3] == ["memory:memory_killed", "time:timed_out", "output:output_exceeded"]
        and output.isdigit()
        and int(output) < PROBE_RESOURCES.pids
    )
    return passed, " ".join(details)


_FILL = (
    "import errno, os\n"
    "try:\n"
    "    with open('/srv/fill', 'wb') as handle:\n"
    "        for _ in range(4):\n"
    f"            handle.write(bytes({PROBE_RESOURCES.disk_bytes}))\n"
    "            handle.flush(); os.fsync(handle.fileno())\n"
    "    print('unlimited')\n"
    "except OSError as error:\n"
    "    print('enospc' if error.errno == errno.ENOSPC else 'error')\n"
)


def disk_quota_probe(backend: DockerBackend, image: str) -> tuple[bool, str]:
    """Write four times the quota; pass when the write fails with ENOSPC."""
    output, _ = _python(backend, _spec(image), _FILL, timeout=120)
    return output == "enospc", f"writing four times the quota: {output}"


_PRIVILEGE_PROGRAM = (
    "import os\n"
    "status = dict(line.split(':', 1) for line in open('/proc/self/status'))\n"
    "keys = ('CapEff', 'CapPrm', 'CapBnd', 'NoNewPrivs', 'Seccomp')\n"
    "fields = [status[k].strip() for k in keys]\n"
    "devices = sorted(os.listdir('/dev'))\n"
    "print(' '.join(fields), ','.join(devices))\n"
)
# Bit numbers from linux/capability.h.
_CAPABILITY_BITS = {"CHOWN": 0, "DAC_OVERRIDE": 1, "FOWNER": 3, "SETGID": 6, "SETUID": 7}


def _no_privilege_gain(backend: DockerBackend, image: str) -> tuple[bool, str]:
    return _privileges_are(backend, _spec(image), "0000000000000000")


def _agent_keeps_only_its_capabilities(backend: DockerBackend, image: str) -> tuple[bool, str]:
    """The Agent's five capabilities and nothing more, and they do not open read-only mounts."""
    mask = sum(1 << _CAPABILITY_BITS[name] for name in AGENT_CAPABILITIES)
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "input").write_text("x")
        mounts = (Mount(MountKind.BIND, directory, "/probe/bind"),)
        spec = replace(_spec(image, mounts), capabilities=AGENT_CAPABILITIES)
        passed, detail = _privileges_are(backend, spec, f"{mask:016x}")
        program = (
            "try:\n"
            "    open('/probe/bind/input', 'a').write('y')\n"
            "    print('written')\n"
            "except OSError:\n"
            "    print('denied')\n"
        )
        written, _ = _python(backend, spec, program)
        unchanged = Path(directory, "input").read_text() == "x"
    return passed and written == "denied" and unchanged, f"{detail}; read-only bind: {written}"


def _privileges_are(backend: DockerBackend, spec: EnvironmentSpec, mask: str) -> tuple[bool, str]:
    output, _ = _python(backend, spec, _PRIVILEGE_PROGRAM)
    fields = output.split(" ")
    allowed_devices = {
        "console",
        "core",
        "fd",
        "full",
        "mqueue",
        "null",
        "ptmx",
        "pts",
        "random",
        "shm",
        "stderr",
        "stdin",
        "stdout",
        "tty",
        "urandom",
        "zero",
    }
    devices: set[str] = set(fields[-1].split(",")) if len(fields) == 6 else set()
    passed = (
        len(fields) == 6
        and fields[:3] == [mask] * 3
        and fields[3:5] == ["1", "2"]
        and devices <= allowed_devices
    )
    return passed, output


def _images_by_digest_only(backend: DockerBackend, image: str) -> tuple[bool, str]:
    try:
        backend.resolve_image("python:3.12-slim")
    except HostError:
        rejected = True
    else:
        rejected = False
    resolved = backend.resolve_image(image)
    return rejected and resolved == image, f"tag rejected: {rejected}; digest resolved: {resolved}"


_PROBES: tuple[tuple[str, str, Callable[[DockerBackend, str], tuple[bool, str]]], ...] = (
    ("B1", "read-only mounts stay read-only", _read_only_mounts),
    ("B2", "no process survives the main process", _no_process_survives),
    ("B3", "clones share no writable state", _no_shared_writable_state),
    ("B4", "destroy is complete", _destroy_is_complete),
    ("B5", "no network by default", _no_network_by_default),
    ("B5", "a restricted network reaches only its peers", _restricted_network_reaches_only_peers),
    ("B5", "the upstream network reaches only global addresses", _upstream_reaches_only_global),
    ("B6", "limits are enforced and reported", _limits_are_enforced_and_reported),
    ("B6", "the disk quota is enforced", disk_quota_probe),
    ("B7", "no privilege gain", _no_privilege_gain),
    ("B7", "the Agent keeps only its five capabilities", _agent_keeps_only_its_capabilities),
    ("B8", "images by pinned digest only", _images_by_digest_only),
)
