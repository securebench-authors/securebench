"""End-to-end runs of the fixture tasks F1 to F5 (docs/testing.md).

Every candidate goes through the real runner: pack validation, the Agent run
with a scripted harness, capture, the Oracle's plan and the evaluation.
"""

import subprocess
import time
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from securebench.core import paths
from securebench.core.errors import HostError
from securebench.core.limits import Limits, Settings
from securebench.isolation.backend import Environment, EnvironmentSpec, Ran
from securebench.isolation.configuration import Configuration
from securebench.isolation.docker import DockerBackend
from tests.fixtures.conftest import FIXTURES, Outcome, run_candidate

pytestmark = pytest.mark.integration

F1 = FIXTURES / "f1-answer-file"
F2 = FIXTURES / "f2-repository-build"
F3 = FIXTURES / "f3-generated-file"
F4 = FIXTURES / "f4-allowed-domain"
F5 = FIXTURES / "f5-error-attribution"


def _run(
    backend: DockerBackend, stock_image: str, pack: Path, script: Path, tmp_path: Path, **kw: object
) -> Outcome:
    return run_candidate(backend, stock_image, pack, script, tmp_path / "run", **kw)  # type: ignore[arg-type]


def _manifest_paths(outcome: Outcome) -> set[str]:
    candidate = outcome.record["candidate"]
    assert isinstance(candidate, str)
    return {entry.path for entry in outcome.store.get_manifest(candidate).entries}


@pytest.mark.parametrize(
    ("candidate", "status", "failure_class"),
    [
        ("correct", "passed", None),
        ("wrong", "failed", "oracle"),
        ("malicious-symlink", "failed", "capture"),
        ("malicious-oversized", "failed", "capture"),
        ("malicious-fifo", "failed", "capture"),
        ("malicious-duplicate-keys", "failed", "oracle"),
        ("malicious-nonfinite", "failed", "oracle"),
    ],
)
def test_f1_answer_file(
    backend: DockerBackend,
    stock_image: str,
    tmp_path: Path,
    candidate: str,
    status: str,
    failure_class: str | None,
) -> None:
    outcome = _run(
        backend, stock_image, F1 / "task", F1 / "candidates" / f"{candidate}.sh", tmp_path
    )
    assert outcome.verdict == (status, failure_class), outcome.record["diagnostics"]


@pytest.mark.parametrize(
    ("candidate", "status", "failure_class"),
    [
        ("correct", "passed", None),
        ("wrong", "failed", "oracle"),
        ("build-failure", "failed", "setup"),
        ("malicious-edit-tests", "passed", None),
        ("malicious-hardcode", "failed", "oracle"),
        ("malicious-hidden-access", "failed", "oracle"),
        ("malicious-git-hooks", "passed", None),
    ],
)
def test_f2_repository_build(
    backend: DockerBackend,
    stock_image: str,
    f2_pack: Path,
    tmp_path: Path,
    candidate: str,
    status: str,
    failure_class: str | None,
) -> None:
    outcome = _run(backend, stock_image, f2_pack, F2 / "candidates" / f"{candidate}.sh", tmp_path)
    assert outcome.verdict == (status, failure_class), outcome.record["diagnostics"]
    if candidate.startswith("malicious-"):
        captured = _manifest_paths(outcome)
        assert not any(paths.is_within(path, "/app/tests") for path in captured)
        assert not any("/.git" in path for path in captured)


def test_f2_cases_run_in_parallel_from_one_setup_snapshot(
    backend: DockerBackend, stock_image: str, f2_pack: Path, tmp_path: Path
) -> None:
    outcome = _run(backend, stock_image, f2_pack, F2 / "candidates" / "correct.sh", tmp_path)
    judged = outcome.record["judged"]
    assert isinstance(judged, list)
    assert sorted(entry["case"] for entry in judged if isinstance(entry, dict)) == [0, 1, 2, 3]  # type: ignore[misc]


@pytest.mark.parametrize(
    ("candidate", "status", "failure_class"),
    [
        ("correct", "passed", None),
        ("wrong", "failed", "oracle"),
        ("malicious-symlink", "failed", "oracle"),
        ("malicious-oversized", "failed", "oracle"),
        ("malicious-forged-observation", "failed", "oracle"),
    ],
)
def test_f3_generated_file(
    backend: DockerBackend,
    stock_image: str,
    tmp_path: Path,
    candidate: str,
    status: str,
    failure_class: str | None,
) -> None:
    outcome = _run(
        backend, stock_image, F3 / "task", F3 / "candidates" / f"{candidate}.sh", tmp_path
    )
    assert outcome.verdict == (status, failure_class), outcome.record["diagnostics"]


_SERVER = """
import http.server, threading
class Files(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"payload from an allowed domain\\n" if self.path == "/data.txt" else b"other"
        self.send_response(200); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
class Provider(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        ok = self.headers.get("x-api-key") == "stub-secret"
        body = b'{"type": "message"}' if ok else b'{"error": "bad key"}'
        self.send_response(200 if ok else 401); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
threading.Thread(target=http.server.ThreadingHTTPServer(("", 8000), Provider).serve_forever).start()
server = http.server.ThreadingHTTPServer(("", 80), Files)
print("serving", flush=True)
server.serve_forever()
"""


@pytest.fixture(scope="module")
def f4_network(stock_image: str) -> Iterator[str]:
    """A test network on 192.0.0.8/29, which Python classifies as global."""
    name = f"securebench-f4-{int(time.time())}"
    docker = ["docker"]
    subprocess.run(
        [
            *docker,
            "network",
            "create",
            "--label",
            "securebench.owned=1",
            "--subnet",
            "192.0.0.8/29",
            name,
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    server = (
        subprocess.run(
            [
                *docker,
                "run",
                "--detach",
                "--label",
                "securebench.fixture=f4",
                "--network",
                name,
                "--ip",
                "192.0.0.10",
                "--entrypoint",
                "",
                stock_image,
                "python3",
                "-c",
                _SERVER,
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        .stdout.decode()
        .strip()
    )
    try:
        for _ in range(50):
            logs = subprocess.run([*docker, "logs", server], capture_output=True, timeout=30)
            if b"serving" in logs.stdout:
                break
            time.sleep(0.2)
        yield name
    finally:
        subprocess.run([*docker, "rm", "--force", server], capture_output=True, timeout=60)
        subprocess.run([*docker, "network", "rm", name], capture_output=True, timeout=60)


def _f4(
    backend: DockerBackend,
    stock_image: str,
    network: str,
    candidate: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Outcome:
    monkeypatch.setenv("SB_STUB_KEY", "stub-secret")
    stub = {
        "api": "anthropic",
        "upstream": "http://192.0.0.10:8000",
        "paths": ["/v1/messages"],
        "credential_env": "SB_STUB_KEY",
        "credential_header": "x-api-key",
    }
    return _run(
        backend,
        stock_image,
        F4 / "task",
        F4 / "candidates" / f"{candidate}.sh",
        tmp_path,
        providers={"stub": stub},
        extra_hosts=(("files.securebench.test", "192.0.0.10"),),
        extra_networks=(network,),
    )


def _log(tmp_path: Path, name: str) -> str:
    return (tmp_path / "run" / "attempts" / "f4-allowed-domain" / f"1.{name}").read_text()


@pytest.mark.parametrize(
    ("candidate", "status", "failure_class"),
    [("correct", "passed", None), ("wrong", "failed", "oracle")],
)
def test_f4_allowed_domain(
    backend: DockerBackend,
    stock_image: str,
    f4_network: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate: str,
    status: str,
    failure_class: str | None,
) -> None:
    outcome = _f4(backend, stock_image, f4_network, candidate, tmp_path, monkeypatch)
    assert outcome.verdict == (status, failure_class), outcome.record["diagnostics"]


def test_f4_forbidden_routes_fail_and_are_logged(
    backend: DockerBackend,
    stock_image: str,
    f4_network: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome = _f4(backend, stock_image, f4_network, "malicious-forbidden", tmp_path, monkeypatch)
    assert outcome.verdict == ("passed", None), outcome.record["diagnostics"]
    transcript = _log(tmp_path, "transcript")
    for attempt in (
        "other domain failed",
        "private address failed",
        "non-standard port failed",
        "direct connection failed",
        "direct to file server failed",
        "external DNS failed",
        "relay stored state failed",
        "relay hosted tool failed",
        "relay inference SUCCEEDED",
    ):
        assert attempt in transcript, transcript
    proxy = _log(tmp_path, "proxy")
    assert '"host": "example.com"' in proxy and '"decision": "denied"' in proxy
    assert '"host": "files.securebench.test"' in proxy and '"decision": "allowed"' in proxy
    relay = _log(tmp_path, "relay")
    assert '"path": "/v1/files"' in relay
    assert '"blocked_tools": ["web_search_20250305"]' in relay
    assert '"status": 200' in relay
    assert "stub-secret" not in relay and "stub-secret" not in transcript


@pytest.mark.parametrize("candidate", ["crash-adapter", "timeout", "memory", "processes", "disk"])
def test_f5_evaluation_errors_are_case_errors(
    backend: DockerBackend,
    stock_image: str,
    configuration: Configuration,
    tmp_path: Path,
    candidate: str,
) -> None:
    if candidate == "disk" and not configuration.disk_quota:
        pytest.skip("the backend does not enforce disk quotas on this worker")
    outcome = _run(
        backend, stock_image, F3 / "task", F5 / "candidates" / f"{candidate}.sh", tmp_path
    )
    assert outcome.verdict == ("failed", "case_error"), outcome.record["diagnostics"]
    leftovers = subprocess.run(
        [
            "docker",
            "ps",
            "--quiet",
            "--filter",
            "label=securebench.owned=1",
            "--filter",
            "status=running",
        ],
        capture_output=True,
        timeout=60,
        check=True,
    ).stdout
    assert leftovers.strip() == b"", "a container survived the attempt"


class FlakyBackend(DockerBackend):
    """The real backend, failing on purpose for the commands it is told to fail."""

    def __init__(self, disk_quota: bool, fail_on: str) -> None:
        super().__init__(disk_quota)
        self.fail_on = fail_on
        self.failures = 0

    def run(
        self,
        spec: EnvironmentSpec,
        command: Sequence[str],
        stdin: bytes,
        timeout_seconds: float,
        output_bound: int,
        cancel: object = None,
    ) -> tuple[Environment, Ran]:
        if any(self.fail_on in part for part in command):
            self.failures += 1
            raise HostError("simulated host failure")
        return super().run(spec, command, stdin, timeout_seconds, output_bound, cancel)  # type: ignore[arg-type]


def test_f5_host_failures_during_cases_are_retried_then_invalid(
    configuration: Configuration, stock_image: str, tmp_path: Path
) -> None:
    flaky = FlakyBackend(configuration.disk_quota, "/.securebench/evaluation/adapter.py")
    outcome = _run(flaky, stock_image, F3 / "task", F3 / "candidates" / "correct.sh", tmp_path)
    assert outcome.verdict == ("invalid", None)
    assert flaky.failures >= 3
    host_errors = outcome.record["host_errors"]
    assert isinstance(host_errors, list) and len(host_errors) >= 3


def test_f5_host_failure_during_the_agent_phase_is_invalid_at_once(
    configuration: Configuration, stock_image: str, tmp_path: Path
) -> None:
    flaky = FlakyBackend(configuration.disk_quota, "/.securebench/harness/")
    outcome = _run(flaky, stock_image, F3 / "task", F3 / "candidates" / "correct.sh", tmp_path)
    assert outcome.verdict == ("invalid", None)
    assert flaky.failures == 1


def test_expired_agent_time_limit_is_captured_and_evaluated(
    backend: DockerBackend, stock_image: str, tmp_path: Path
) -> None:
    # The overlay is the script's directory: keep the run directory out of it, and make it
    # readable by the capability-free Agent, since pytest creates tmp_path with mode 0700.
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    overlay.chmod(0o755)
    script = overlay / "slow.sh"
    script.write_text((F3 / "candidates" / "correct.sh").read_text() + "sleep 600\n")
    settings = Settings(False, 2, Limits(512 << 20, 1_000_000_000, 256, 2 << 30, 5))
    outcome = _run(backend, stock_image, F3 / "task", script, tmp_path, settings=settings)
    assert outcome.verdict == ("passed", None)
    agent = outcome.record["agent"]
    assert isinstance(agent, dict) and agent["time_limit_expired"] is True
