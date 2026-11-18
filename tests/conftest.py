"""Shared test configuration: integration tests are skipped when no Docker daemon answers."""

import subprocess

import pytest

from securebench.isolation.backend import STOCK_IMAGE
from securebench.isolation.configuration import Configuration, check_configuration
from securebench.isolation.docker import DockerBackend


def _docker_available() -> bool:
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if any(item.get_closest_marker("integration") for item in items) and not _docker_available():
        skip = pytest.mark.skip(reason="no Docker daemon is available")
        for item in items:
            if item.get_closest_marker("integration"):
                item.add_marker(skip)


@pytest.fixture(scope="session")
def stock_image() -> str:
    return DockerBackend(disk_quota=False).resolve_image(STOCK_IMAGE)


@pytest.fixture(scope="session")
def configuration(stock_image: str) -> Configuration:
    return check_configuration(stock_image)


@pytest.fixture(scope="session")
def backend(configuration: Configuration) -> DockerBackend:
    return DockerBackend(disk_quota=configuration.disk_quota)
