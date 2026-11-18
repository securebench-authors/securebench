"""The harness preflight in a real task image, and the Agent command's sudo setup."""

import json
from pathlib import Path

import pytest

from securebench.agent.harness import claude_code
from securebench.agent.network import Services
from securebench.agent.run import (
    _keep_proxy_through_sudo,  # pyright: ignore[reportPrivateUsage]
    preflight,
)
from securebench.core.errors import HostError
from securebench.core.limits import Limits
from securebench.isolation.backend import AGENT_CAPABILITIES, EnvironmentSpec, Resources, Service
from securebench.isolation.docker import DockerBackend
from securebench.taskspec.load import load

pytestmark = pytest.mark.integration

F1 = Path(__file__).parents[2] / "fixtures" / "f1-answer-file" / "task"
LIMITS = Limits(256 << 20, 1_000_000_000, 64, 1 << 30, 60)


def _overlay(tmp_path: Path, printed: str) -> Path:
    """A stand-in overlay whose `bin/node` prints a version, so no download is needed."""
    root = tmp_path / "overlay"
    (root / "bin").mkdir(parents=True)
    node = root / "bin" / "node"
    node.write_text(f"#!/bin/sh\necho '{printed}'\n")
    node.chmod(0o755)
    metadata = root / "node_modules" / "@anthropic-ai" / "claude-code" / "package.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({"version": "2.1.289", "bin": {"claude": "cli.js"}}))
    (metadata.parent / "cli.js").write_text("#!/usr/bin/env node\n")
    return root


def test_preflight_accepts_the_pinned_version(backend: DockerBackend, tmp_path: Path) -> None:
    task = load(F1)
    harness = claude_code(_overlay(tmp_path, "2.1.289 (Claude Code)"), "2.1.289", "m")
    image = backend.resolve_image(task.public.baseline.image)
    preflight(backend, task.public, image, harness, LIMITS)


def test_preflight_rejects_another_version(backend: DockerBackend, tmp_path: Path) -> None:
    task = load(F1)
    harness = claude_code(_overlay(tmp_path, "9.9.9"), "2.1.289", "m")
    image = backend.resolve_image(task.public.baseline.image)
    with pytest.raises(HostError, match="preflight"):
        preflight(backend, task.public, image, harness, LIMITS)


def test_root_agent_lets_sudo_keep_the_proxy_variables(
    backend: DockerBackend, stock_image: str
) -> None:
    services = Services(
        None, None, Service("proxy"), (("http_proxy", "http://proxy:3128"), ("NO_PROXY", "relay"))
    )
    drop_in = "/etc/sudoers.d/securebench-proxy"
    check = f'cat {drop_in}; stat -c "%a %u" {drop_in}; echo "$@"; exit 3'
    command = _keep_proxy_through_sudo(services, ("sh", "-c", check, "sh", "kept argument"))
    resources = Resources(256 << 20, 1_000_000_000, 64, 1 << 30)
    spec = EnvironmentSpec(stock_image, (), None, "/", None, (), resources, AGENT_CAPABILITIES)
    environment, ran = backend.run(spec, command, b"", 60, 1 << 16)
    backend.destroy(environment)
    assert ran.facts.exit_status == 3, ran.stderr
    assert ran.stdout.decode().splitlines() == [
        'Defaults env_keep += "http_proxy NO_PROXY"',
        "440 0",
        "kept argument",
    ]
