"""The B1 to B8 qualification suite, run live against the local Docker daemon."""

import pytest

from securebench.isolation.configuration import Configuration
from securebench.isolation.docker import DockerBackend
from securebench.isolation.qualification import qualify

pytestmark = pytest.mark.integration


def test_qualification_probes_pass(
    backend: DockerBackend, stock_image: str, configuration: Configuration
) -> None:
    record = qualify(backend, stock_image, configuration.facts)
    unmet: list[str] = []
    for probe in record.probes:
        if probe.name in WORKER_SETUP and not probe.passed:
            unmet.append(f"{probe.name}: {probe.detail}")
            continue
        assert probe.passed, f"{probe.guarantee} {probe.name}: {probe.detail}"
    if unmet:
        pytest.skip(f"this worker lacks setup outside SecureBench: {unmet}")


WORKER_SETUP = {"the disk quota is enforced", "the upstream network reaches only global addresses"}
"""Probes that depend on how the worker is set up (docs/operating.md), not on SecureBench's code.
They still decide whether a worker is qualified."""
