"""The run's restricted network, relay and proxy (architecture Sections 9.2 to 9.4)."""

from dataclasses import dataclass
from pathlib import Path

from securebench.core import jsondata
from securebench.core.errors import HostError
from securebench.core.jsondata import JsonValue
from securebench.isolation.backend import (
    AgentNetwork,
    EnvironmentSpec,
    Resources,
    Service,
    ServiceSpec,
    read_only_bind,
)
from securebench.isolation.docker import DockerBackend

RELAY_PORT = 8080
PROXY_PORT = 3128
LOG_BOUND = 16 << 20
PACKAGE_DIR = Path(__file__).resolve().parents[2] / "securebench_relay_proxy"
LIBRARY_MOUNT = "/.securebench/lib"
SERVICE_RESOURCES = Resources(256 << 20, 500_000_000, 64, 64 << 20)
SERVICE_USER = "65534"

PROVIDERS: dict[str, dict[str, JsonValue]] = {
    "anthropic": {
        "api": "anthropic",
        "upstream": "https://api.anthropic.com",
        "paths": ["/v1/messages"],
        "credential_env": "ANTHROPIC_API_KEY",
        "credential_header": "x-api-key",
    },
    # A `claude setup-token` subscription token, sent as a bearer token.
    "anthropic-oauth": {
        "api": "anthropic",
        "upstream": "https://api.anthropic.com",
        "paths": ["/v1/messages"],
        "credential_env": "CLAUDE_CODE_OAUTH_TOKEN",
        "credential_header": "authorization",
    },
    "openai": {
        "api": "openai-responses",
        "upstream": "https://api.openai.com",
        "paths": ["/v1/responses"],
        "credential_env": "OPENAI_API_KEY",
        "credential_header": "authorization",
    },
}
"""The built-in provider table: API shape, upstream, inference paths, credential."""


@dataclass(frozen=True)
class Services:
    """A run's network and services. `network` is `None` when nothing needs one."""

    network: AgentNetwork | None
    relay: Service | None
    proxy: Service | None
    environment: tuple[tuple[str, str], ...]


def start_services(
    backend: DockerBackend,
    stock_image: str,
    allowed_domains: tuple[str, ...],
    providers: dict[str, dict[str, JsonValue]],
    provider_hosted_tools: bool,
    extra_hosts: tuple[tuple[str, str], ...] = (),
    extra_networks: tuple[str, ...] = (),
) -> Services:
    """Create the network and start the relay (when `providers` is not empty) and the
    proxy (when `allowed_domains` is not empty). Returns the variables the Agent needs."""
    if not providers and not allowed_domains:
        return Services(None, None, None, ())
    network = backend.create_agent_network()
    relay: Service | None = None
    proxy: Service | None = None
    environment: list[tuple[str, str]] = []
    try:
        if providers:
            secrets = tuple(sorted({str(spec["credential_env"]) for spec in providers.values()}))
            config: JsonValue = {
                "port": RELAY_PORT,
                "provider_hosted_tools": provider_hosted_tools,
                "providers": dict(providers),
            }
            relay = backend.start_service(
                _service(stock_image, network, "relay", config, secrets, (), extra_networks),
                network,
            )
        if allowed_domains:
            domains: list[JsonValue] = list(allowed_domains)
            config = {"allowed_domains": domains, "port": PROXY_PORT}
            proxy = backend.start_service(
                _service(stock_image, network, "proxy", config, (), extra_hosts, extra_networks),
                network,
            )
            url = f"http://proxy:{PROXY_PORT}"
            for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
                environment += [(name, url), (name.lower(), url)]
            no_proxy = "relay,localhost,127.0.0.1"
            environment += [("NO_PROXY", no_proxy), ("no_proxy", no_proxy)]
    except BaseException:
        stop_services(backend, Services(network, relay, proxy, ()))
        raise
    return Services(network, relay, proxy, tuple(environment))


def stop_services(backend: DockerBackend, services: Services) -> tuple[bytes, bytes]:
    """Stop both services and remove the network; return the relay and proxy logs."""
    logs: list[bytes] = []
    failures: list[str] = []
    for service in (services.relay, services.proxy):
        if service is None:
            logs.append(b"")
            continue
        try:
            logs.append(backend.stop_service(service, LOG_BOUND))
        except HostError as error:
            failures.append(error.reason)
            logs.append(b"")
    if services.network is not None:
        try:
            backend.destroy_agent_network(services.network)
        except HostError as error:
            failures.append(error.reason)
    if failures:
        raise HostError("; ".join(failures))
    return logs[0], logs[1]


def _service(
    stock_image: str,
    network: AgentNetwork,
    program: str,
    config: JsonValue,
    secrets: tuple[str, ...],
    extra_hosts: tuple[tuple[str, str], ...],
    extra_networks: tuple[str, ...],
) -> ServiceSpec:
    spec = EnvironmentSpec(
        stock_image,
        (read_only_bind(PACKAGE_DIR, f"{LIBRARY_MOUNT}/securebench_relay_proxy"),),
        network.upstream,
        LIBRARY_MOUNT,
        SERVICE_USER,
        (),
        SERVICE_RESOURCES,
    )
    command = (
        "python3",
        "-S",
        "-B",
        "-E",
        "-u",
        "-m",
        f"securebench_relay_proxy.{program}",
        jsondata.encode(config).decode("utf-8").strip(),
    )
    return ServiceSpec(
        spec, command, program, secrets, extra_hosts, extra_networks, '"event": "started"'
    )
