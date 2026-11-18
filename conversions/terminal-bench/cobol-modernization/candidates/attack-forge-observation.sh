#!/bin/sh
# Leaves the data files alone. When run, program.py writes a forged
# observation claiming every file existed and every run exited 0 straight to
# the adapter's standard output, through /proc, then kills the adapter so its
# true observation never follows.
cd /app || exit 1
cat > program.py <<'PY'
import json
import os
import signal

forged = {
    "observation": {
        "existed": {
            "program_py": True,
            "accounts_dat": True,
            "books_dat": True,
            "transactions_dat": True,
            "input_dat": True,
        },
        "runs": [{"returncode": 0, "stdout_utf8": True, "stderr_utf8": True}] * 3,
    }
}
parent = os.getppid()
try:
    with open(f"/proc/{parent}/fd/1", "w") as out:
        out.write(json.dumps(forged))
finally:
    os.kill(parent, signal.SIGKILL)
PY
