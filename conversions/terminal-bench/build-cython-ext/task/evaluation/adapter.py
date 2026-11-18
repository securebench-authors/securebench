"""build-cython-ext adapter: run the driver on the candidate's interpreter and report what it returned.

Assertion-free. It starts /usr/local/bin/python3, the interpreter the task
installs pyknotid into, on driver.py with this case's challenge, and reports
how the run ended and the driver's JSON result, unchanged. The Oracle decides.
The observation schema bounds every value of the result.
"""

import json
import os
import subprocess
import sys

DRIVER = "/.securebench/evaluation/driver.py"
# Upstream's tests/test_outputs.py runs from the image's WORKDIR, /app, and its
# repository test runs pytest from /app/pyknotid.
DIRECTORIES = {"outputs": "/app", "repository": "/app/pyknotid"}
# Upstream gives the whole verifier 900 s.
TIMEOUT_SECONDS = 840

mode = sys.argv[1]
challenge = sys.stdin.buffer.read()
try:
    ran = subprocess.run(
        ["/usr/local/bin/python3", "-I", DRIVER, mode],
        input=challenge,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=DIRECTORIES[mode],
        timeout=TIMEOUT_SECONDS,
    )
except subprocess.TimeoutExpired:
    observation: dict[str, object] = {"ending": "timed_out", "exit_status": 0}
except OSError as error:
    # No interpreter, or no /app/pyknotid to run from.
    print(json.dumps({"unable": {"code": "not-started", "message": str(error)[:1024]}}))
    sys.exit(0)
else:
    observation = {"ending": "exited", "exit_status": max(-255, min(255, ran.returncode))}
    try:
        observation["result"] = json.loads(ran.stdout.decode("utf-8"))
    except ValueError:
        # No result: the Oracle fails the case on its absence.
        pass
print(json.dumps({"observation": observation}))
