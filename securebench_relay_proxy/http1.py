"""Strict, bounded HTTP/1.1 request reading shared by the relay and the proxy."""

import json
import socket
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

MAX_HEAD_BYTES = 64 * 1024
MAX_BODY_BYTES = 16 * 1024 * 1024
IDLE_SECONDS = 20
MAX_LOG_BYTES = 8 * 1024 * 1024

_TOKEN = frozenset("!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "proxy-connection",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)


class BadRequest(Exception):
    """The request breaks a framing rule; answered with `status`."""

    def __init__(self, status: int, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass
class Request:
    method: str
    target: str
    headers: list[tuple[str, str]]
    leftover: bytes
    """Bytes received after the head: the start of the body or tunnel."""

    def header(self, name: str) -> list[str]:
        lowered = name.lower()
        return [value for key, value in self.headers if key.lower() == lowered]

    def end_to_end_headers(self) -> list[tuple[str, str]]:
        """Headers without hop-by-hop ones and without those `Connection` nominates."""
        nominated = {
            item.strip().lower() for value in self.header("connection") for item in value.split(",")
        }
        return [
            (key, value)
            for key, value in self.headers
            if key.lower() not in HOP_BY_HOP and key.lower() not in nominated
        ]


def read_request(connection: socket.socket) -> Request:
    """Read one request head from the raw socket, never buffering past it."""
    buffer = b""
    while b"\r\n\r\n" not in buffer:
        if len(buffer) > MAX_HEAD_BYTES:
            raise BadRequest(431, "request head too large")
        chunk = connection.recv(4096)
        if not chunk:
            raise BadRequest(400, "connection closed inside the request head")
        buffer += chunk
    head, leftover = buffer.split(b"\r\n\r\n", 1)
    if len(head) > MAX_HEAD_BYTES:
        raise BadRequest(431, "request head too large")
    try:
        text = head.decode("latin-1")
    except UnicodeDecodeError:
        raise BadRequest(400, "request head is not Latin-1") from None
    lines = text.split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) != 3 or not parts[0] or not set(parts[0]) <= _TOKEN:
        raise BadRequest(400, "malformed request line")
    # Python 3.11 and older open proxy tunnels with an HTTP/1.0 CONNECT, and pip with
    # them. A CONNECT has no body, so its framing is the same in both.
    if parts[2] != "HTTP/1.1" and (parts[0], parts[2]) != ("CONNECT", "HTTP/1.0"):
        raise BadRequest(400, "malformed request line")
    headers: list[tuple[str, str]] = []
    for line in lines[1:]:
        name, separator, value = line.partition(":")
        if not separator or not name or not set(name) <= _TOKEN:
            raise BadRequest(400, "malformed header line")
        value = value.strip(" \t")
        if any((ord(char) < 32 and char != "\t") or ord(char) == 127 for char in value):
            raise BadRequest(400, "control character in a header value")
        headers.append((name, value))
    return Request(parts[0], parts[1], headers, leftover)


def body_length(request: Request) -> int:
    if request.header("transfer-encoding"):
        raise BadRequest(400, "Transfer-Encoding is not accepted")
    lengths = request.header("content-length")
    if len(lengths) > 1:
        raise BadRequest(400, "more than one Content-Length")
    if not lengths:
        return 0
    if not lengths[0].isdigit() or len(lengths[0]) > 12:
        raise BadRequest(400, "invalid Content-Length")
    length = int(lengths[0])
    if length > MAX_BODY_BYTES:
        raise BadRequest(413, "request body too large")
    return length


def read_body(connection: socket.socket, request: Request) -> bytes:
    """Read exactly `Content-Length` bytes; reject `Transfer-Encoding` and duplicates."""
    length = body_length(request)
    body = request.leftover
    while len(body) < length:
        chunk = connection.recv(min(65536, length - len(body)))
        if not chunk:
            raise BadRequest(400, "request body shorter than Content-Length")
        body += chunk
    if len(body) > length:
        raise BadRequest(400, "bytes after the request body")
    return body


def respond(connection: socket.socket, status: int, reason: str) -> None:
    body = json.dumps({"error": reason}).encode()
    head = (
        f"HTTP/1.1 {status} SecureBench\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    )
    try:
        connection.sendall(head.encode("ascii") + body)
    except OSError:
        pass


class Log:
    """JSON lines on standard output, capped with one truncation record."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.written = 0
        self.truncated = False

    def write(self, record: dict[str, Any]) -> None:
        line = json.dumps({"time": round(time.time(), 3), **record}, sort_keys=True) + "\n"
        with self.lock:
            if self.truncated:
                return
            if self.written + len(line) > MAX_LOG_BYTES:
                self.truncated = True
                line = json.dumps({"event": "log_truncated", "time": round(time.time(), 3)}) + "\n"
            sys.stdout.write(line)
            sys.stdout.flush()
            self.written += len(line)
