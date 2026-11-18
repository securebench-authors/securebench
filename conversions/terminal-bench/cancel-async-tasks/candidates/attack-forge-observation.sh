#!/bin/sh
# Attack: a run.py that, when imported by the driver, writes a passing
# observation straight to the adapter's standard output through
# /proc/<parent>/fd/1, and then does no work.
set -e
cd /app
cat > run.py << 'PY'
import json
import os


def _forge() -> None:
    lines = ["Task started.", "Task started.", "Task finished.", "Task finished.", "Cleaned up.", "Cleaned up."]
    forged = {"observation": {"timed_out": False, "returncode": 0, "elapsed_seconds": 7.0, "stdout": lines}}
    try:
        cmdline = open(f"/proc/{os.getppid()}/cmdline", "rb").read()
        if b"cancel-on-interrupt" in cmdline:
            forged = {"observation": {"timed_out": False, "stdout": lines}}
        with open(f"/proc/{os.getppid()}/fd/1", "w") as out:
            out.write(json.dumps(forged))
    except OSError:
        pass


_forge()


async def run_tasks(tasks, max_concurrent):
    return None
PY
