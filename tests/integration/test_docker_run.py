"""Running an environment against the real Docker backend."""

import threading
import time

import pytest

from securebench.isolation import docker
from securebench.isolation.backend import Cancelled, EnvironmentSpec, Resources
from securebench.isolation.docker import DockerBackend

pytestmark = pytest.mark.integration

RESOURCES = Resources(512 << 20, 1_000_000_000, 128, 1 << 30)


def test_a_cancel_before_the_container_starts_still_stops_it(
    backend: DockerBackend, stock_image: str
) -> None:
    # The cancel is seen before `docker run` has started the container, so the
    # first kill finds nothing running. The container must not then run on: a
    # case that hangs would outlast the wait and crash the whole run.
    cancel = threading.Event()
    cancel.set()
    spec = EnvironmentSpec(stock_image, (), None, "/", None, (), RESOURCES)
    started = time.monotonic()
    with pytest.raises(Cancelled):
        backend.run(spec, ["sleep", "300"], b"", 600, 1 << 16, cancel)
    assert time.monotonic() - started < docker.CLI_TIMEOUT_SECONDS
