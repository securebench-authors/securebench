"""The Agent command's sudo setup when a proxy runs."""

from securebench.agent.network import Services
from securebench.agent.run import _keep_proxy_through_sudo  # pyright: ignore[reportPrivateUsage]


def test_without_a_proxy_the_harness_command_runs_unchanged() -> None:
    services = Services(None, None, None, ())
    assert _keep_proxy_through_sudo(services, ("sh", "/x/run.sh")) == ("sh", "/x/run.sh")
