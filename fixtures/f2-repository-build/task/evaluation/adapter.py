"""F2 adapter: feed the challenge's lines to `/app/lines -r` and return what it printed.

Assertion-free: it reports the program's output and compares nothing.
"""

import json
import os
import subprocess
import sys

challenge = json.loads(sys.stdin.buffer.read())
if not os.access("/app/lines", os.X_OK):
    print(json.dumps({"unable": {"code": "not_built", "message": "/app/lines is missing"}}))
    sys.exit(0)
data = "".join(line + "\n" for line in challenge["lines"]).encode()
try:
    run = subprocess.run(["/app/lines", "-r"], input=data, capture_output=True, timeout=10)
except subprocess.TimeoutExpired:
    print(json.dumps({"unable": {"code": "timeout", "message": "lines ran for 10 s"}}))
    sys.exit(0)
if run.returncode != 0:
    message = f"lines exited with status {run.returncode}"
    print(json.dumps({"unable": {"code": "exit_status", "message": message}}))
    sys.exit(0)
output = run.stdout.decode("utf-8", "replace").split("\n")
if output and output[-1] == "":
    output.pop()
print(json.dumps({"observation": {"lines": [line[:256] for line in output[:64]]}}))
