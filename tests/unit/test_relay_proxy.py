"""The relay and the proxy, run in-process against local sockets."""

import http.server
import json
import socket
import ssl
import threading
from collections.abc import Iterator
from typing import ClassVar

import pytest

from securebench_relay_proxy import proxy, relay
from securebench_relay_proxy.http1 import BadRequest


def _client_hello(server_name: str | None) -> bytes:
    context = ssl.create_default_context()
    context.check_hostname = server_name is not None
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    connection = context.wrap_bio(incoming, outgoing, server_hostname=server_name)
    with pytest.raises(ssl.SSLWantReadError):
        connection.do_handshake()
    return outgoing.read()


def _handshake(records: bytes) -> bytes:
    return records[5:]


def test_server_name_is_read_from_a_real_client_hello() -> None:
    assert proxy.server_name(_handshake(_client_hello("Files.Example.com"))) == "files.example.com"


def test_a_client_hello_without_server_name_is_rejected() -> None:
    hello = _client_hello(None)
    with pytest.raises(BadRequest):
        proxy.server_name(_handshake(hello))


def test_client_hello_reassembly_across_records_and_trailing_bytes() -> None:
    records = _client_hello("a.example.com")
    body = records[5:]
    split = body[:50], body[50:]
    fragmented = b"".join(
        bytes([22]) + records[1:3] + len(part).to_bytes(2, "big") + part for part in split
    )
    left, right = socket.socketpair()
    with left, right:
        left.sendall(fragmented[10:])
        raw, hello = proxy.read_client_hello(right, fragmented[:10])
        assert raw == fragmented and proxy.server_name(hello) == "a.example.com"
        left.sendall(records + b"\x17\x03\x03\x00\x01x")
        with pytest.raises(BadRequest):
            proxy.read_client_hello(right, b"")


@pytest.mark.parametrize(
    ("host", "expected"),
    [("example.com", True), ("a.example.com", True), ("evilexample.com", False), ("com", False)],
)
def test_domain_matching_uses_a_dot_boundary(host: str, expected: bool) -> None:
    assert proxy.allowed(("example.com",), host) is expected


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "0.0.0.0",
        "192.0.2.1",
        "224.0.0.1",
        "::1",
        "fc00::1",
        "fec0::1",
        "::",
        "::ffff:127.0.0.1",
        "fe80::1%eth0",
        "not-an-address",
    ],
)
def test_non_global_addresses_are_rejected(address: str) -> None:
    assert not proxy.global_address(address)


def test_global_addresses_are_accepted() -> None:
    assert proxy.global_address("1.1.1.1")
    assert proxy.global_address("2606:4700:4700::1111")
    assert proxy.global_address("192.0.0.9")


@pytest.mark.parametrize("authority", ["a.com:443@evil", "[::1]:443", "a.com:99999", "a.com:x", ""])
def test_authorities_are_parsed_strictly(authority: str) -> None:
    with pytest.raises(BadRequest):
        proxy.split_authority(authority, 443)


def _serve_proxy(domains: tuple[str, ...]) -> tuple[proxy.Server, int]:
    proxy.Handler.domains = domains
    server = proxy.Server(("127.0.0.1", 0), proxy.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def _ask(port: int, data: bytes) -> bytes:
    """Connect without `socket.getaddrinfo`, which some tests replace."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(("127.0.0.1", port))
        connection.sendall(data)
        return connection.recv(65536)


def test_disallowed_destinations_are_refused_before_any_dns_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_dns(*_: object, **__: object) -> None:
        raise AssertionError("DNS was consulted")

    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    server, port = _serve_proxy(("example.com",))
    try:
        for request in (
            b"CONNECT other.com:443 HTTP/1.1\r\nHost: other.com\r\n\r\n",
            b"CONNECT example.com:22 HTTP/1.1\r\n\r\n",
            b"GET http://example.com:8080/ HTTP/1.1\r\n\r\n",
            b"GET /relative HTTP/1.1\r\n\r\n",
            b"CONNECT other.com:443 HTTP/1.0\r\n\r\n",
            b"CONNECT example.com:22 HTTP/1.0\r\n\r\n",
        ):
            assert _ask(port, request).startswith(b"HTTP/1.1 403")
    finally:
        server.shutdown()


def test_an_allowed_name_resolving_to_a_private_address_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def loopback(*_: object, **__: object) -> list[tuple[object, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", loopback)
    server, port = _serve_proxy(("localhost.example",))
    try:
        answer = _ask(port, b"CONNECT localhost.example:443 HTTP/1.1\r\n\r\n")
    finally:
        server.shutdown()
    assert answer.startswith(b"HTTP/1.1 403")


def test_an_allowed_http_1_0_connect_opens_the_tunnel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Python 3.11's `http.client`, and so pip, sends CONNECT as HTTP/1.0."""

    def resolved(host: str, port: int) -> list[tuple[object, ...]]:
        return []

    monkeypatch.setattr(proxy, "resolve", resolved)
    server, port = _serve_proxy(("example.com",))
    try:
        answer = _ask(port, b"CONNECT example.com:443 HTTP/1.0\r\nHost: example.com:443\r\n\r\n")
    finally:
        server.shutdown()
    assert answer.startswith(b"HTTP/1.1 200")


@pytest.mark.parametrize(
    "request_bytes",
    [
        b"GET http://example.com/ HTTP/1.1\r\nX: a\x01b\r\n\r\n",
        b"GET http://example.com/ HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n",
        b"GET http://example.com/ HTTP/1.1\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\n",
        b"GET http://example.com/ HTTP/1.0\r\n\r\n",
        b"CONNECT example.com:443 HTTP/1.2\r\n\r\n",
        b"POST http://example.com/ HTTP/1.0\r\nContent-Length: 0\r\n\r\n",
        b"G\x01T http://example.com/ HTTP/1.1\r\n\r\n",
    ],
)
def test_smuggling_and_injection_are_rejected_before_connecting(
    monkeypatch: pytest.MonkeyPatch, request_bytes: bytes
) -> None:
    def refuse(host: str, port: int) -> socket.socket:
        raise AssertionError(f"connected upstream to {host}:{port}")

    monkeypatch.setattr(proxy, "connect", refuse)
    server, port = _serve_proxy(("example.com",))
    try:
        assert _ask(port, request_bytes).startswith(b"HTTP/1.1 4")
    finally:
        server.shutdown()


TOOL_CASES: list[tuple[str, list[object], list[str]]] = [
    ("anthropic", [{"name": "bash", "input_schema": {}}], []),
    (
        "anthropic",
        [{"type": "web_search_20250305", "name": "web_search"}],
        ["web_search_20250305"],
    ),
    ("openai-responses", [{"type": "function", "name": "f"}], []),
    ("openai-responses", [{"type": "web_search"}], ["web_search"]),
    ("openai-responses", [{"type": "mcp"}], ["mcp"]),
    ("openai-responses", [{"type": "namespace", "tools": [{"type": "function"}]}], []),
    (
        "openai-responses",
        [{"type": "namespace", "tools": [{"type": "function"}, {"type": "web_search"}]}],
        ["namespace:web_search"],
    ),
    (
        "openai-responses",
        [{"type": "namespace", "tools": [{"type": "namespace", "tools": []}]}],
        ["namespace:namespace"],
    ),
    ("openai-chat", [{"type": "namespace", "tools": [{"type": "function"}]}], ["namespace"]),
    ("openai-chat", [{"type": "function"}], []),
    ("openai-chat", [{"type": "code_interpreter"}], ["code_interpreter"]),
]


@pytest.mark.parametrize(("api", "tools", "blocked"), TOOL_CASES)
def test_tool_classification(api: str, tools: list[object], blocked: list[str]) -> None:
    assert relay.blocked_tools(api, json.dumps({"tools": tools}).encode()) == blocked


@pytest.mark.parametrize(
    "body",
    [
        b'{"tools": [], "tools": [{"type": "web_search"}]}',
        b'{"x": NaN}',
        b'{"x": 1e999}',
        b"[1]",
        b'{"tools": {}}',
        b'{"tools": [{"name": "x"}]}',
        b"\xff",
    ],
)
def test_uninspectable_requests_fail_closed(body: bytes) -> None:
    with pytest.raises(relay.Uninspectable):
        relay.blocked_tools("anthropic", body)


@pytest.mark.parametrize(
    ("body", "model"),
    [
        (b'{"model": "gpt-6.1-sol", "tools": []}', "gpt-6.1-sol"),
        (b'{"tools": []}', None),
        (b'{"model": ["gpt-6.1-sol"]}', None),
        (json.dumps({"model": "m" * 1000}).encode(), "m" * 128),
    ],
)
def test_the_requested_model_is_logged_bounded(body: bytes, model: str | None) -> None:
    assert relay.requested_model(body) == model


def test_anthropic_server_side_fields_are_blocked() -> None:
    assert relay.blocked_tools("anthropic", b'{"mcp_servers": []}') == ["field:mcp_servers"]


@pytest.mark.parametrize(
    "path",
    ["/v1/messages-evil", "/v1/files", "/v1/%2e%2e/files", "/v1//messages", "/v1/./messages", ""],
)
def test_relay_paths_are_exact(path: str) -> None:
    with pytest.raises(BadRequest):
        relay.check_path(path, ["/v1/messages"])


class _Provider(http.server.BaseHTTPRequestHandler):
    seen: ClassVar[list[dict[str, str]]] = []

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        self.rfile.read(length)
        type(self).seen.append(dict(self.headers.items()))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for index in range(3):
            self.wfile.write(f"data: {index}\n\n".encode())
            self.wfile.flush()

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def relay_port(monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    provider = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Provider)
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    monkeypatch.setenv("SB_TEST_KEY", "real-secret")
    relay.CONFIG.clear()
    relay.CONFIG.update(
        {
            "provider_hosted_tools": False,
            "providers": {
                "anthropic": {
                    "api": "anthropic",
                    "upstream": f"http://127.0.0.1:{provider.server_address[1]}",
                    "paths": ["/v1/messages"],
                    "credential_env": "SB_TEST_KEY",
                    "credential_header": "x-api-key",
                },
                "anthropic-oauth": {
                    "api": "anthropic",
                    "upstream": f"http://127.0.0.1:{provider.server_address[1]}",
                    "paths": ["/v1/messages"],
                    "credential_env": "SB_TEST_KEY",
                    "credential_header": "authorization",
                },
            },
        }
    )
    server = relay.Server(("127.0.0.1", 0), relay.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()
    provider.shutdown()


def _post(port: int, path: str, body: bytes, extra: str = "") -> bytes:
    head = (
        f"POST {path} HTTP/1.1\r\nHost: relay\r\nx-api-key: dummy\r\n{extra}"
        f"Content-Length: {len(body)}\r\n\r\n"
    )
    with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
        connection.sendall(head.encode() + body)
        chunks = b""
        while chunk := connection.recv(65536):
            chunks += chunk
        return chunks


def test_relay_injects_the_credential_and_streams_the_answer(relay_port: int) -> None:
    _Provider.seen.clear()
    answer = _post(relay_port, "/anthropic/v1/messages?beta=true", b'{"tools": []}')
    assert answer.startswith(b"HTTP/1.1 200")
    assert answer.endswith(b"data: 0\n\ndata: 1\n\ndata: 2\n\n")
    assert _Provider.seen[-1]["x-api-key"] == "real-secret"


def test_relay_replaces_the_client_bearer_token(relay_port: int) -> None:
    _Provider.seen.clear()
    extra = "Authorization: Bearer placeholder\r\n"
    answer = _post(relay_port, "/anthropic-oauth/v1/messages", b'{"tools": []}', extra)
    assert answer.startswith(b"HTTP/1.1 200")
    headers = {key.lower(): value for key, value in _Provider.seen[-1].items()}
    assert headers["authorization"] == "Bearer real-secret"
    assert "x-api-key" not in headers


def test_relay_refuses_hosted_tools_paths_and_methods(relay_port: int) -> None:
    hosted = json.dumps({"tools": [{"type": "web_search_20250305", "name": "w"}]}).encode()
    assert _post(relay_port, "/anthropic/v1/messages", hosted).startswith(b"HTTP/1.1 403")
    assert _post(relay_port, "/anthropic/v1/files", b"{}").startswith(b"HTTP/1.1 403")
    assert _post(relay_port, "/openai/v1/responses", b"{}").startswith(b"HTTP/1.1 403")
    assert _post(relay_port, "http://evil/anthropic/v1/messages", b"{}").startswith(b"HTTP/1.1 403")
    gzip = "Content-Encoding: gzip\r\n"
    assert _post(relay_port, "/anthropic/v1/messages", b"{}", gzip).startswith(b"HTTP/1.1 403")
    with socket.create_connection(("127.0.0.1", relay_port), timeout=10) as connection:
        connection.sendall(b"GET /anthropic/v1/messages HTTP/1.1\r\n\r\n")
        assert connection.recv(100).startswith(b"HTTP/1.1 405")


@pytest.mark.parametrize(
    "tools",
    [
        [{"type": "namespace"}],
        [{"type": "namespace", "tools": []}],
        [{"type": "namespace", "tools": [1]}],
    ],
)
def test_malformed_namespaces_fail_closed(tools: list[object]) -> None:
    with pytest.raises(relay.Uninspectable):
        relay.blocked_tools("openai-responses", json.dumps({"tools": tools}).encode())


# Gap tests: routes the tests above did not cover.


@pytest.mark.parametrize("name", ["evil.com", "other.example.com", "example.com.evil.com"])
def test_a_tls_server_name_other_than_the_connect_host_is_refused(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """An allowed CONNECT host cannot carry a TLS session for another name."""

    def resolved(host: str, port: int) -> list[tuple[object, ...]]:
        return []

    def refuse(host: str, port: int) -> socket.socket:
        raise AssertionError(f"connected upstream to {host}:{port}")

    monkeypatch.setattr(proxy, "resolve", resolved)
    monkeypatch.setattr(proxy, "connect", refuse)
    server, port = _serve_proxy(("example.com",))
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
            connection.sendall(b"CONNECT example.com:443 HTTP/1.1\r\n\r\n" + _client_hello(name))
            answer = b""
            while chunk := connection.recv(65536):
                answer += chunk
    finally:
        server.shutdown()
    assert answer.startswith(b"HTTP/1.1 200")
    assert b"HTTP/1.1 403" in answer


@pytest.mark.parametrize(
    ("authority", "allowed"),
    [
        ("example.com.:443", True),
        ("EXAMPLE.com:443", True),
        ("example.com..:443", False),
        ("example.com.evil.:443", False),
        (".example.com:443", True),
    ],
)
def test_trailing_dots_and_case_cannot_widen_a_domain(authority: str, allowed: bool) -> None:
    host, _ = proxy.split_authority(authority, 443)
    assert proxy.allowed(("example.com",), host) is allowed


@pytest.mark.parametrize("host", ["127.1", "2130706433", "0x7f000001", "0177.0.0.1", "0x7f.1"])
def test_alternate_ipv4_spellings_are_resolved_and_refused(host: str) -> None:
    """The C resolver reads these as 127.0.0.1; the address check sees the result."""
    with pytest.raises(BadRequest) as error:
        proxy.resolve(host, 443)
    assert error.value.status == 403


@pytest.mark.parametrize(
    "address",
    ["64:ff9b::7f00:1", "64:ff9b::a9fe:a9fe", "64:ff9b::a00:1", "::7f00:1", "::a9fe:a9fe"],
)
def test_ipv6_forms_embedding_a_non_global_ipv4_address_are_refused(address: str) -> None:
    """NAT64 (64:ff9b::/96) and IPv4-compatible (::/96) addresses carry an IPv4 address."""
    assert not proxy.global_address(address)


def test_an_answer_that_changes_after_the_check_is_checked_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DNS rebinding: the proxy connects only to addresses it has just checked."""
    target = socket.socket()
    target.bind(("127.0.0.1", 0))
    target.listen()
    target.settimeout(0.5)
    answers = [("1.1.1.1", 443), ("127.0.0.1", target.getsockname()[1])]

    def rebinding(*_: object, **__: object) -> list[tuple[object, ...]]:
        address = answers.pop(0) if len(answers) > 1 else answers[0]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", address)]

    monkeypatch.setattr(socket, "getaddrinfo", rebinding)
    server, port = _serve_proxy(("example.com",))
    try:
        # Not `create_connection`, which would consult the replaced resolver itself.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(10)
            connection.connect(("127.0.0.1", port))
            request = b"CONNECT example.com:443 HTTP/1.1\r\n\r\n" + _client_hello("example.com")
            connection.sendall(request)
            answer = b""
            while chunk := connection.recv(65536):
                answer += chunk
        with pytest.raises(TimeoutError):
            target.accept()
    finally:
        server.shutdown()
        target.close()
    assert b"HTTP/1.1 403" in answer


@pytest.mark.parametrize(
    "path",
    [
        "/V1/messages",
        "/v1/Messages",
        "/v1/messages/",
        "/v1%2Fmessages",
        "/v1/messages%2F",
        "/v1/messages;files",
        "/v1/messages#",
    ],
)
def test_relay_paths_differing_in_case_or_encoding_are_refused(path: str) -> None:
    with pytest.raises(BadRequest):
        relay.check_path(path, ["/v1/messages"])


@pytest.mark.parametrize(
    "target",
    [
        "/Anthropic/v1/messages",
        "/anthropic/../anthropic/v1/messages",
        "/anthropic/v1/messages?next=/v1/files",
        "/anthropic/v1/messages?x=%2e%2e",
        "//anthropic/v1/messages",
    ],
)
def test_relay_targets_cannot_reach_another_path(relay_port: int, target: str) -> None:
    _Provider.seen.clear()
    assert _post(relay_port, target, b'{"tools": []}').startswith(b"HTTP/1.1 403")
    assert _Provider.seen == []


def test_relay_strips_method_override_headers(relay_port: int) -> None:
    """Only POST reaches the provider, also for servers that honour an override header."""
    _Provider.seen.clear()
    extra = "X-HTTP-Method-Override: GET\r\nX-HTTP-Method: DELETE\r\nX-Method-Override: PUT\r\n"
    answer = _post(relay_port, "/anthropic/v1/messages", b'{"tools": []}', extra)
    assert answer.startswith(b"HTTP/1.1 200")
    forwarded = {key.lower() for key in _Provider.seen[-1]}
    assert not forwarded & {"x-http-method-override", "x-http-method", "x-method-override"}


def _raw(port: int, data: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
        connection.sendall(data)
        answer = b""
        while chunk := connection.recv(65536):
            answer += chunk
        return answer


@pytest.mark.parametrize(
    "request_bytes",
    [
        b"POST /anthropic/v1/messages HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n"
        b'd\r\n{"tools": []}\r\n0\r\n\r\n',
        b"POST /anthropic/v1/messages HTTP/1.1\r\nContent-Length: 13\r\nContent-Length: 2\r\n\r\n"
        b'{"tools": []}',
        b"POST /anthropic/v1/messages HTTP/1.1\r\nContent-Length: 13\r\n\r\n"
        b'{"tools": []}POST /anthropic/v1/files HTTP/1.1\r\nContent-Length: 2\r\n\r\n{}',
        b"POST /anthropic/v1/messages HTTP/1.1\r\nContent-Length: 13\r\n x: folded\r\n\r\n"
        b'{"tools": []}',
        b'POST /anthropic/v1/messages HTTP/1.1\r\nContent-Length: +13\r\n\r\n{"tools": []}',
        b'POST /anthropic/v1/messages HTTP/1.0\r\nContent-Length: 13\r\n\r\n{"tools": []}',
    ],
)
def test_relay_rejects_smuggling_before_forwarding(relay_port: int, request_bytes: bytes) -> None:
    _Provider.seen.clear()
    assert _raw(relay_port, request_bytes).startswith(b"HTTP/1.1 4")
    assert _Provider.seen == []


def test_relay_forwards_one_request_per_connection(relay_port: int) -> None:
    """Bytes sent after a complete request are never read as a second request."""
    _Provider.seen.clear()
    first = b'POST /anthropic/v1/messages HTTP/1.1\r\nContent-Length: 13\r\n\r\n{"tools": []}'
    with socket.create_connection(("127.0.0.1", relay_port), timeout=10) as connection:
        connection.sendall(first)
        answer = connection.recv(65536)
        try:
            connection.sendall(b"POST /anthropic/v1/files HTTP/1.1\r\nContent-Length: 2\r\n\r\n{}")
        except OSError:
            pass
        while chunk := connection.recv(65536):
            answer += chunk
    assert answer.startswith(b"HTTP/1.1 200")
    assert len(_Provider.seen) == 1


def test_relay_never_reveals_its_credential(
    relay_port: int, capsys: pytest.CaptureFixture[str]
) -> None:
    """Neither the relay's own answers nor its log carry the injected credential."""
    answers = [
        _post(relay_port, "/anthropic/v1/messages", b'{"tools": []}'),
        _post(relay_port, "/anthropic/v1/files", b"{}"),
        _post(relay_port, "/anthropic/v1/messages", b"not json"),
        _post(relay_port, "/anthropic/v1/messages", b'{"tools": [{"type": "web_search"}]}'),
        _post(relay_port, "/unknown/v1/messages", b"{}"),
        _raw(relay_port, b"GET /anthropic/v1/messages HTTP/1.1\r\n\r\n"),
    ]
    log = capsys.readouterr().out
    assert log
    for text in (*answers, log.encode()):
        assert b"real-secret" not in text


def test_agent_controlled_text_cannot_forge_a_relay_log_line(
    relay_port: int, capsys: pytest.CaptureFixture[str]
) -> None:
    """Records hold agent text as escaped data: one JSON object per line, one per request."""
    forged = '\n{"decision": "allowed", "event": "request", "path": "/v1/files"}\n'
    bodies = [
        json.dumps({"model": forged, "tools": []}).encode(),
        json.dumps({"model": "m", "tools": [{"type": forged}]}).encode(),
    ]
    for body in bodies:
        _post(relay_port, "/anthropic/v1/messages", body)
    _post(relay_port, "/anthropic/v1/messages?x=y", b"{}", 'x-note: {"decision": "allowed"}\r\n')
    lines = capsys.readouterr().out.splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) == 3
    assert all(record["event"] == "request" for record in records)
    assert [record.get("path") for record in records] == ["/v1/messages"] * 3
