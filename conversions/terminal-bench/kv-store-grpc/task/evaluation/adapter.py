"""Start the candidate's server, run the upstream tests' client side, report what it saw.

Upstream's tests talk to a server the agent left running. No process survives
capture, so this adapter starts it the way the instructions describe and the
upstream solution does: `python server.py` in /app, in the background. It
waits for the port to accept connections, since upstream's verifier only
starts long after the agent launched its server, then runs driver.py under the
baseline's Python and returns the driver's record unchanged. It decides
nothing.
"""

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time

PYTHON = "/usr/local/bin/python3"
DRIVER = "/.securebench/evaluation/driver.py"
STARTUP_SECONDS = 60
DRIVER_SECONDS = 480


def unable(code, message):
    print(json.dumps({"unable": {"code": code, "message": message[:4000]}}))
    sys.exit(0)


def port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def main():
    challenge = json.loads(sys.stdin.buffer.read())
    work = tempfile.mkdtemp(prefix="kv-store-grpc-")
    challenge_path = os.path.join(work, "challenge.json")
    result_path = os.path.join(work, "result.json")
    with open(challenge_path, "w", encoding="utf-8") as file:
        json.dump(challenge, file)

    server = subprocess.Popen(
        [PYTHON, "server.py"],
        cwd="/app",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + STARTUP_SECONDS
        while time.monotonic() < deadline and not port_open(challenge["host"], challenge["port"]):
            time.sleep(0.5)
        # Whether or not the port opened, the driver runs: upstream's port test
        # records the failure, and the Oracle judges it.
        try:
            subprocess.run(
                [PYTHON, DRIVER, challenge_path, result_path],
                cwd="/app",
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=DRIVER_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            unable("driver-timeout", f"the test client did not finish in {DRIVER_SECONDS} s")
    finally:
        try:
            os.killpg(server.pid, signal.SIGKILL)
        except OSError:
            pass

    try:
        with open(result_path, "rb") as file:
            result = json.loads(file.read(1 << 20))
    except (OSError, ValueError) as error:
        unable("no-record", f"the test client wrote no readable record: {error}")
    print(json.dumps({"observation": result}))


main()
