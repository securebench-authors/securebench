"""Real model harnesses solving F1 against stub providers, through the real relay.

Each test needs a prepared overlay (`docs/operating.md`): set
`SECUREBENCH_CLAUDE_CODE_OVERLAY` and `SECUREBENCH_CLAUDE_CODE_VERSION`, or
`SECUREBENCH_CODEX_OVERLAY` and `SECUREBENCH_CODEX_VERSION`; otherwise the test
is skipped.
"""

import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from securebench.agent.harness import claude_code, codex
from securebench.agent.network import PROVIDERS
from securebench.isolation.docker import DockerBackend
from tests.fixtures.conftest import FIXTURES, run_candidate

pytestmark = pytest.mark.integration


@pytest.fixture(params=["stub_anthropic.py", "stub_openai.py"])
def stub_provider(stock_image: str, request: pytest.FixtureRequest) -> Iterator[str]:
    """A stub model API on a globally classified test subnet."""
    stub = Path(__file__).with_name(str(request.param))
    name = f"securebench-stub-{time.time_ns()}"
    subprocess.run(
        ["docker", "network", "create", "--label", "securebench.owned=1",
         "--subnet", "192.0.0.8/29", name],
        check=True, capture_output=True, timeout=60,
    )  # fmt: skip
    server = subprocess.run(
        ["docker", "run", "--detach", "--label", "securebench.fixture=stub", "--network", name,
         "--ip", "192.0.0.10", "--mount", f"type=bind,source={stub},target=/stub.py,readonly",
         "--entrypoint", "", stock_image, "python3", "-u", "/stub.py"],
        check=True, capture_output=True, timeout=60,
    ).stdout.decode().strip()  # fmt: skip
    try:
        for _ in range(50):
            logs = subprocess.run(["docker", "logs", server], capture_output=True, timeout=30)
            if b"serving" in logs.stdout:
                break
            time.sleep(0.2)
        yield f"{name} {server} {request.param}"
    finally:
        subprocess.run(["docker", "rm", "--force", server], capture_output=True, timeout=60)
        subprocess.run(["docker", "network", "rm", name], capture_output=True, timeout=60)


@pytest.mark.parametrize("oauth", [False, True], ids=["api-key", "oauth"])
def test_a_model_harness_solves_f1_through_the_relay(
    backend: DockerBackend,
    stock_image: str,
    stub_provider: str,
    oauth: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    network, server, stub = stub_provider.split()
    if oauth and stub != "stub_anthropic.py":
        pytest.skip("only Claude Code has a subscription token mode")
    preset, provider, variable = (
        ("codex", "openai", "OPENAI_API_KEY")
        if stub != "stub_anthropic.py"
        else ("claude-code", "anthropic-oauth", "CLAUDE_CODE_OAUTH_TOKEN")
        if oauth
        else ("claude-code", "anthropic", "ANTHROPIC_API_KEY")
    )
    prefix = f"SECUREBENCH_{preset.upper().replace('-', '_')}"
    overlay, version = os.environ.get(f"{prefix}_OVERLAY"), os.environ.get(f"{prefix}_VERSION")
    if not overlay or not version:
        pytest.skip(f"no prepared {preset} overlay (see docs/operating.md)")
    monkeypatch.setenv(variable, "stub-secret")
    providers = {provider: {**PROVIDERS[provider], "upstream": "http://192.0.0.10:8000"}}
    outcome = run_candidate(
        backend,
        stock_image,
        FIXTURES / "f1-answer-file" / "task",
        Path("unused"),
        tmp_path / "run",
        providers=providers,
        extra_networks=(network,),
        harness=(
            claude_code(Path(overlay), version, "stub-model", oauth)
            if preset == "claude-code"
            else codex(Path(overlay), version, "stub-model")
        ),
    )
    attempt = tmp_path / "run" / "attempts" / "f1-answer-file"
    relay = (attempt / "1.relay").read_text()
    seen = subprocess.run(["docker", "logs", server], capture_output=True, timeout=30).stdout
    assert outcome.verdict == ("passed", None), (outcome.record["diagnostics"], relay, seen)
    assert b'"key_ok": true' in seen and b'"answered": true' in seen
    assert (
        "stub-secret" not in relay and "stub-secret" not in (attempt / "1.transcript").read_text()
    )
