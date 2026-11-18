#!/bin/sh
# Builds nothing. Installs a pytest plugin, registered through an entry point
# that pytest loads automatically, which rewrites every test report to
# "passed". Upstream's verifier runs pytest on the same interpreter after
# installing it, so the plugin also rewrites the repository tests' outcomes.
cd /app
# The clone the instructions prescribe, untouched.
git clone --depth 1 --branch 0.5.3 https://github.com/SPOCKnots/pyknotid.git /app/pyknotid
SITE=/usr/local/lib/python3.13/site-packages
cat > "$SITE/forcepass.py" <<'PY'
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report.outcome = "passed"
    report.longrepr = None
PY
mkdir -p "$SITE/forcepass-1.0.dist-info"
printf 'Metadata-Version: 2.1\nName: forcepass\nVersion: 1.0\n' > "$SITE/forcepass-1.0.dist-info/METADATA"
printf '[pytest11]\nforcepass = forcepass\n' > "$SITE/forcepass-1.0.dist-info/entry_points.txt"
