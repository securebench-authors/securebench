"""F3 adapter: run the candidate's program on the challenge and report its exit status.

Assertion-free: it compares nothing, and the Oracle reads /srv/out.json itself.
"""

import json
import os
import subprocess
import sys

challenge = sys.stdin.buffer.read()
if not os.path.isfile("/srv/solve.py"):
    print(
        json.dumps({"unable": {"code": "missing_program", "message": "/srv/solve.py is missing"}})
    )
    sys.exit(0)
try:
    status = subprocess.run(
        [sys.executable, "/srv/solve.py"], input=challenge, timeout=15, capture_output=True
    ).returncode
except subprocess.TimeoutExpired:
    print(json.dumps({"unable": {"code": "timeout", "message": "solve.py ran for 15 s"}}))
    sys.exit(0)
print(json.dumps({"observation": {"exit_status": max(-255, min(255, status))}}))
