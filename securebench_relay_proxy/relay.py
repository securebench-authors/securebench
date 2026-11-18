"""The provider relay (architecture Section 9.2).

`python -S -B -E -m securebench_relay_proxy.relay '<config JSON>'`. It
forwards only each provider's inference endpoints, by exact path and with
`POST` only, injects the provider credential from its own environment, blocks
provider-hosted tools unless enabled, and streams responses back. Every
request is one metadata-only JSON log line on standard output, capped with a
truncation record.

Config: `{"port": n, "provider_hosted_tools": bool, "providers": {name: {"api":
"anthropic" | "openai-responses" | "openai-chat", "upstream": "https://host[:port]",
"paths": ["/v1/messages", ...], "credential_env": NAME, "credential_header":
"x-api-key" | "authorization"}}}`. The agent calls `http://relay:<port>/<name><path>`.
"""

import http.client
import json
import math
import os
import socket
import socketserver
import sys
from typing import Any, cast
from urllib.parse import urlsplit

from securebench_relay_proxy.http1 import (
    IDLE_SECONDS,
    BadRequest,
    Log,
    Request,
    read_body,
    read_request,
    respond,
)

LOG = Log()
UPSTREAM_TIMEOUT_SECONDS = 600
_QUERY_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789=&_.-")
# Credentials, framing, and the method-override headers some servers honour, so that
# only POST reaches the provider.
_STRIPPED = frozenset(
    {
        "authorization",
        "x-api-key",
        "chatgpt-account-id",
        "host",
        "content-length",
        "cookie",
        "x-http-method-override",
        "x-http-method",
        "x-method-override",
    }
)
_CLIENT_TOOL_TYPES: dict[str, frozenset[str]] = {
    "openai-responses": frozenset({"function", "custom", "shell", "apply_patch"}),
    "openai-chat": frozenset({"function"}),
}
_SERVER_SIDE_FIELDS: dict[str, frozenset[str]] = {
    "anthropic": frozenset({"mcp_servers", "container"}),
    "openai-responses": frozenset(),
    "openai-chat": frozenset(),
}


class Uninspectable(Exception):
    """The body cannot be inspected, so it is blocked."""


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Uninspectable(f"duplicate key {key!r}")
        result[key] = value
    return result


def _finite(literal: str) -> float:
    value = float(literal)
    if not math.isfinite(value):
        raise Uninspectable("non-finite number")
    return value


def _constant(name: str) -> None:
    raise Uninspectable(f"constant {name}")


def strict_json(body: bytes) -> Any:
    try:
        text = body.decode("utf-8", "strict")
        if text.startswith("﻿"):
            raise Uninspectable("byte-order mark")
        return json.loads(
            text, object_pairs_hook=_unique, parse_float=_finite, parse_constant=_constant
        )
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise Uninspectable(f"not strict JSON: {type(error).__name__}") from None


def blocked_tools(api: str, body: bytes) -> list[str]:
    """Names of provider-hosted tools or server-side features declared in the request.

    Raises `Uninspectable` when the request cannot be classified.
    """
    payload: object = strict_json(body)
    if not isinstance(payload, dict):
        raise Uninspectable("the request body is not an object")
    fields = cast(dict[str, object], payload)
    blocked = [f"field:{field}" for field in _SERVER_SIDE_FIELDS[api] if field in fields]
    tools = fields.get("tools", [])
    if not isinstance(tools, list):
        raise Uninspectable("'tools' is not an array")
    for raw_tool in cast(list[object], tools):
        if not isinstance(raw_tool, dict):
            raise Uninspectable("a tool declaration is not an object")
        tool = cast(dict[str, object], raw_tool)
        kind = tool.get("type")
        if api == "anthropic":
            if kind not in (None, "custom"):
                blocked.append(str(kind)[:64])
            elif not isinstance(tool.get("name"), str) or not isinstance(
                tool.get("input_schema"), dict
            ):
                raise Uninspectable("an untyped tool lacks a name or input_schema")
        elif kind == "namespace" and api == "openai-responses":
            blocked.extend(_namespace(tool))
        elif kind not in _CLIENT_TOOL_TYPES[api]:
            blocked.append(str(kind)[:64])
    return blocked


def requested_model(body: bytes) -> str | None:
    """The model a request names, bounded; agent-controlled, logged as data.

    Called only on a body `blocked_tools` has accepted, so it parses as an object.
    """
    model = cast(dict[str, object], strict_json(body)).get("model")
    return model[:128] if isinstance(model, str) else None


def _namespace(tool: dict[str, object]) -> list[str]:
    """A namespace groups client tools; every member must be a client tool itself.

    Members may not be namespaces again, so the check stays one level deep.
    """
    members = tool.get("tools")
    if not isinstance(members, list) or not members:
        raise Uninspectable("a namespace tool has no member list")
    blocked: list[str] = []
    for raw in cast(list[object], members):
        if not isinstance(raw, dict):
            raise Uninspectable("a namespace member is not an object")
        kind = cast(dict[str, object], raw).get("type")
        if kind not in _CLIENT_TOOL_TYPES["openai-responses"]:
            blocked.append(f"namespace:{str(kind)[:64]}")
    return blocked


def check_path(path: str, allowed: list[str]) -> None:
    """Exact allowlisted paths only; reject encodings and traversal."""
    if not path.startswith("/") or path not in allowed:
        raise BadRequest(403, "path not allowed")
    if any(char in path for char in "%\\#") or "//" in path:
        raise BadRequest(403, "path not allowed")
    if any(part in (".", "..") for part in path.split("/")):
        raise BadRequest(403, "path not allowed")


CONFIG: dict[str, Any] = {}


class Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        client: socket.socket = self.request
        client.settimeout(IDLE_SECONDS)
        record: dict[str, Any] = {"event": "request"}
        try:
            request = read_request(client)
            self._relay(client, request, record)
        except BadRequest as error:
            record.update(decision="denied", status=error.status, reason=error.reason)
            respond(client, error.status, error.reason)
        except OSError as error:
            record.update(decision="failed", reason=f"socket error: {error}")
        LOG.write(record)

    def _relay(self, client: socket.socket, request: Request, record: dict[str, Any]) -> None:
        if not request.target.startswith("/"):
            raise BadRequest(403, "absolute-form targets are not relayed")
        provider_name, _, rest = request.target[1:].partition("/")
        provider = CONFIG["providers"].get(provider_name)
        record.update(provider=provider_name[:64], method=request.method)
        if provider is None:
            raise BadRequest(403, "unknown provider")
        path, _, query = ("/" + rest).partition("?")
        record["path"] = path[:256]
        if request.method != "POST":
            raise BadRequest(405, "only POST is relayed")
        check_path(path, provider["paths"])
        if query and not set(query) <= _QUERY_CHARS:
            raise BadRequest(403, "query not allowed")
        if request.header("content-encoding"):
            raise BadRequest(403, "compressed requests cannot be inspected")
        body = read_body(client, request)
        record["request_bytes"] = len(body)
        try:
            blocked = blocked_tools(provider["api"], body)
        except Uninspectable as error:
            raise BadRequest(403, f"request cannot be inspected: {error}") from None
        record["model"] = requested_model(body)
        if blocked and not CONFIG["provider_hosted_tools"]:
            record["blocked_tools"] = blocked
            raise BadRequest(403, f"provider-hosted tools are disabled: {blocked}")
        record["status"] = self._forward(client, request, provider, path, query, body, record)
        record["decision"] = "allowed"

    def _forward(
        self,
        client: socket.socket,
        request: Request,
        provider: dict[str, Any],
        path: str,
        query: str,
        body: bytes,
        record: dict[str, Any],
    ) -> int:
        upstream = urlsplit(str(provider["upstream"]))
        connection_class = (
            http.client.HTTPSConnection
            if upstream.scheme == "https"
            else http.client.HTTPConnection
        )
        connection = connection_class(
            upstream.hostname or "", upstream.port, timeout=UPSTREAM_TIMEOUT_SECONDS
        )
        headers = {
            key: value
            for key, value in request.end_to_end_headers()
            if key.lower() not in _STRIPPED
        }
        credential = os.environ.get(provider["credential_env"], "")
        if not credential:
            raise BadRequest(502, "the relay has no credential for this provider")
        if provider["credential_header"] == "authorization":
            headers["Authorization"] = f"Bearer {credential}"
        else:
            headers["x-api-key"] = credential
        try:
            connection.request("POST", path + ("?" + query if query else ""), body, headers)
            response = connection.getresponse()
            head = [f"HTTP/1.1 {response.status} {response.reason}"]
            for key, value in response.getheaders():
                if key.lower() not in ("connection", "transfer-encoding", "keep-alive"):
                    head.append(f"{key}: {value}")
            head.append("Connection: close")
            client.sendall(("\r\n".join(head) + "\r\n\r\n").encode("latin-1"))
            sent = 0
            while chunk := response.read1(65536):
                client.sendall(chunk)
                sent += len(chunk)
            record["response_bytes"] = sent
            return response.status
        except (http.client.HTTPException, OSError) as error:
            raise BadRequest(502, f"upstream error: {type(error).__name__}") from None
        finally:
            connection.close()


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> int:
    config = json.loads(sys.argv[1])
    CONFIG.update(config)
    providers = {
        name: {"api": spec["api"], "paths": spec["paths"]}
        for name, spec in config["providers"].items()
    }
    hosted = config["provider_hosted_tools"]
    with Server(("0.0.0.0", int(config["port"])), Handler) as server:
        LOG.write({"event": "started", "providers": providers, "provider_hosted_tools": hosted})
        server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
