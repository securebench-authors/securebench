"""The egress proxy (architecture Section 9.3).

`python -S -B -E -m securebench_relay_proxy.proxy '<config JSON>'`, where the
config is `{"allowed_domains": [...], "port": n}`. It permits the allowed
domains and their subdomains on ports 80 (absolute-form HTTP) and 443
(`CONNECT`), resolves names itself, rejects non-global addresses, requires the
TLS server name to equal the `CONNECT` host and never intercepts TLS. Every
decision is one JSON log line on standard output, capped with a truncation
record.
"""

import ipaddress
import json
import select
import socket
import socketserver
import sys
from typing import Any

from securebench_relay_proxy.http1 import (
    IDLE_SECONDS,
    BadRequest,
    Log,
    Request,
    body_length,
    read_body,
    read_request,
    respond,
)

MAX_CLIENT_HELLO = 64 * 1024
LOG = Log()
# IPv6 ranges whose last 32 bits are an IPv4 address that a translator or a tunnel
# would reach: NAT64's well-known prefix and the deprecated IPv4-compatible form.
_EMBEDDED_IPV4 = (ipaddress.IPv6Network("64:ff9b::/96"), ipaddress.IPv6Network("::/96"))


def allowed(domains: tuple[str, ...], host: str) -> bool:
    """Exact match or a subdomain on a dot boundary."""
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def global_address(address: str) -> bool:
    """Global unicast only, with IPv4 addresses embedded in IPv6 unwrapped."""
    try:
        parsed = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        parsed = parsed.ipv4_mapped
    elif isinstance(parsed, ipaddress.IPv6Address) and any(
        parsed in network for network in _EMBEDDED_IPV4
    ):
        parsed = ipaddress.IPv4Address(int(parsed) & 0xFFFFFFFF)
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.is_site_local:
        return False
    return parsed.is_global and not parsed.is_multicast


def resolve(host: str, port: int) -> list[tuple[Any, ...]]:
    """Resolve once; reject the whole answer if any address is not global."""
    try:
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    except socket.gaierror as error:
        raise BadRequest(502, f"cannot resolve {host}: {error}") from None
    addresses: list[tuple[Any, ...]] = []
    for family, kind, _, _, address in answers:
        if family not in (socket.AF_INET, socket.AF_INET6) or kind != socket.SOCK_STREAM:
            raise BadRequest(403, f"{host} resolved to an unexpected address type")
        if not global_address(str(address[0])):
            raise BadRequest(403, f"{host} resolved to a non-global address {address[0]}")
        addresses.append((family, address))
    if not addresses:
        raise BadRequest(502, f"{host} has no addresses")
    return addresses


def connect(host: str, port: int) -> socket.socket:
    last: OSError | None = None
    for family, address in resolve(host, port):
        upstream = socket.socket(family, socket.SOCK_STREAM)
        upstream.settimeout(IDLE_SECONDS)
        try:
            upstream.connect(address)
            return upstream
        except OSError as error:
            upstream.close()
            last = error
    raise BadRequest(502, f"cannot connect to {host}:{port}: {last}")


def split_authority(authority: str, default_port: int) -> tuple[str, int]:
    """Parse `host[:port]` strictly: no userinfo, no IP literals, numeric ports."""
    if "@" in authority or "[" in authority or not authority:
        raise BadRequest(400, "unsupported authority")
    host, separator, port_text = authority.rpartition(":")
    if not separator:
        host, port_text = authority, str(default_port)
    if not port_text.isdigit() or len(port_text) > 5 or not 0 < int(port_text) < 65536:
        raise BadRequest(400, "invalid port")
    host = host.lower()
    if host.endswith("."):
        host = host[:-1]
    return host, int(port_text)


def server_name(hello: bytes) -> str:
    """The single SNI host name of a complete ClientHello handshake message."""
    try:
        if hello[0] != 1:
            raise BadRequest(403, "the first handshake message is not a ClientHello")
        length = int.from_bytes(hello[1:4], "big")
        if length != len(hello) - 4:
            raise BadRequest(403, "trailing bytes after the ClientHello")
        position = 4 + 2 + 32
        position += 1 + hello[position]
        position += 2 + int.from_bytes(hello[position : position + 2], "big")
        position += 1 + hello[position]
        end = position + 2 + int.from_bytes(hello[position : position + 2], "big")
        position += 2
        if end != len(hello):
            raise BadRequest(403, "malformed ClientHello extensions")
        names: list[str] = []
        while position < end:
            kind = int.from_bytes(hello[position : position + 2], "big")
            size = int.from_bytes(hello[position + 2 : position + 4], "big")
            data = hello[position + 4 : position + 4 + size]
            if len(data) != size:
                raise BadRequest(403, "truncated ClientHello extension")
            position += 4 + size
            if kind == 0:
                names.extend(_sni_names(data))
    except IndexError:
        raise BadRequest(403, "truncated ClientHello") from None
    if len(names) != 1:
        raise BadRequest(403, f"the ClientHello carries {len(names)} server names")
    return names[0]


def _sni_names(data: bytes) -> list[str]:
    if int.from_bytes(data[0:2], "big") != len(data) - 2:
        raise BadRequest(403, "malformed server_name extension")
    names: list[str] = []
    position = 2
    while position < len(data):
        kind = data[position]
        size = int.from_bytes(data[position + 1 : position + 3], "big")
        raw = data[position + 3 : position + 3 + size]
        if len(raw) != size:
            raise BadRequest(403, "truncated server name")
        position += 3 + size
        if kind != 0:
            continue
        if not raw.isascii() or b"\x00" in raw:
            raise BadRequest(403, "the server name is not plain ASCII")
        name = raw.decode("ascii").lower()
        names.append(name[:-1] if name.endswith(".") else name)
    return names


def read_client_hello(connection: socket.socket, leftover: bytes) -> tuple[bytes, bytes]:
    """Reassemble the ClientHello across TLS records, bounded.

    Returns the raw records, to forward unchanged, and the handshake message.
    """
    raw = leftover
    handshake = b""
    offset = 0
    while True:
        while len(raw) - offset >= 5:
            if raw[offset] != 22:
                raise BadRequest(403, "a TLS record before the ClientHello is not a handshake")
            size = int.from_bytes(raw[offset + 3 : offset + 5], "big")
            if len(raw) - offset < 5 + size:
                break
            handshake += raw[offset + 5 : offset + 5 + size]
            offset += 5 + size
            if len(handshake) >= 4:
                needed = 4 + int.from_bytes(handshake[1:4], "big")
                if len(handshake) > needed or (len(handshake) == needed and offset != len(raw)):
                    raise BadRequest(403, "bytes after the ClientHello before the server answered")
                if len(handshake) == needed:
                    return raw, handshake
        if len(raw) > MAX_CLIENT_HELLO:
            raise BadRequest(403, "ClientHello too large")
        chunk = connection.recv(4096)
        if not chunk:
            raise BadRequest(403, "connection closed inside the ClientHello")
        raw += chunk


def pipe(client: socket.socket, upstream: socket.socket) -> int:
    """Relay bytes both ways until either side closes or stays idle."""
    total = 0
    sockets = [client, upstream]
    while True:
        ready, _, _ = select.select(sockets, [], [], IDLE_SECONDS)
        if not ready:
            return total
        for source in ready:
            data = source.recv(65536)
            if not data:
                return total
            (upstream if source is client else client).sendall(data)
            total += len(data)


class Handler(socketserver.BaseRequestHandler):
    domains: tuple[str, ...] = ()

    def handle(self) -> None:
        client: socket.socket = self.request
        client.settimeout(IDLE_SECONDS)
        record: dict[str, Any] = {"event": "request"}
        try:
            request = read_request(client)
            record.update(method=request.method, target=request.target[:512])
            if request.method == "CONNECT":
                self._connect(client, request, record)
            else:
                self._http(client, request, record)
        except BadRequest as error:
            record.update(decision="denied" if error.status == 403 else "failed")
            record.update(status=error.status, reason=error.reason)
            respond(client, error.status, error.reason)
        except OSError as error:
            record.update(decision="failed", reason=f"socket error: {error}")
        LOG.write(record)

    def _connect(self, client: socket.socket, request: Request, record: dict[str, Any]) -> None:
        host, port = split_authority(request.target, 443)
        record["host"] = host
        if port != 443 or not allowed(self.domains, host):
            raise BadRequest(403, f"CONNECT to {host}:{port} is not allowed")
        resolve(host, port)
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        hello_records, hello = read_client_hello(client, request.leftover)
        name = server_name(hello)
        if name != host:
            raise BadRequest(403, f"TLS server name {name!r} differs from {host}")
        upstream = connect(host, port)
        with upstream:
            upstream.sendall(hello_records)
            record.update(decision="allowed", bytes=pipe(client, upstream))

    def _http(self, client: socket.socket, request: Request, record: dict[str, Any]) -> None:
        target = request.target
        if not target.startswith("http://"):
            raise BadRequest(403, "only absolute-form http:// requests and CONNECT are proxied")
        authority, _, rest = target[len("http://") :].partition("/")
        host, port = split_authority(authority, 80)
        record["host"] = host
        if port != 80 or not allowed(self.domains, host):
            raise BadRequest(403, f"HTTP to {host}:{port} is not allowed")
        if "#" in rest or any(ord(char) < 33 or ord(char) > 126 for char in rest):
            raise BadRequest(400, "invalid request target")
        body_length(request)
        body = read_body(client, request)
        headers = [
            (key, value)
            for key, value in request.end_to_end_headers()
            if key.lower() not in ("host", "content-length")
        ]
        lines = [f"{request.method} /{rest} HTTP/1.1", f"Host: {host}", "Connection: close"]
        lines += [f"{key}: {value}" for key, value in headers]
        if body:
            lines.append(f"Content-Length: {len(body)}")
        upstream = connect(host, port)
        with upstream:
            upstream.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body)
            record.update(decision="allowed", bytes=pipe(client, upstream))


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> int:
    config = json.loads(sys.argv[1])
    Handler.domains = tuple(str(domain) for domain in config["allowed_domains"])
    with Server(("0.0.0.0", int(config["port"])), Handler) as server:
        LOG.write({"event": "started", "allowed_domains": list(Handler.domains)})
        server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
