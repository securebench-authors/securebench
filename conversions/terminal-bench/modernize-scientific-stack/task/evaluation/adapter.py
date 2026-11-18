"""Runs the candidate's modernized script the way upstream's test does and reports what happened.

Upstream's test_modernized_code_runs checks that the script and the CSV exist,
runs `python /app/analyze_climate_modern.py` with a 30-second timeout and
`text=True`, and asserts on its stdout. test_dependency_file_exists then checks
for a dependency file in the same container, after the script has run. This
adapter repeats those steps in the same order and returns the raw facts; the
Oracle decides.
"""

import codecs
import json
import os
import subprocess
import sys
import threading
import time

# The observation is bounded at 4 MiB; a larger stdout could not be reported.
STDOUT_LIMIT = 4 * 1024 * 1024


class Drain:
    """Reads one pipe to its end, decoding UTF-8 strictly as `text=True` does natively."""

    def __init__(self, fd: int, keep: bool) -> None:
        self.fd = fd
        self.keep = keep
        self.decoder = codecs.getincrementaldecoder("utf-8")("strict")
        self.parts: list[str] = []
        self.size = 0
        self.decodable = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self) -> None:
        while True:
            chunk = os.read(self.fd, 65536)
            if not chunk:
                break
            self.size += len(chunk)
            self.feed(chunk, False)
        self.feed(b"", True)

    def feed(self, chunk: bytes, final: bool) -> None:
        if not self.decodable:
            return
        try:
            text = self.decoder.decode(chunk, final)
        except UnicodeDecodeError:
            self.decodable = False
            self.parts = []
            return
        if self.keep and self.size <= STDOUT_LIMIT:
            self.parts.append(text)


def run_script(interpreter: str, script: str, timeout: int) -> dict[str, object] | None:
    start = time.monotonic()
    process = subprocess.Popen(
        [interpreter, script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None and process.stderr is not None
    out = Drain(process.stdout.fileno(), keep=True)
    err = Drain(process.stderr.fileno(), keep=False)
    timed_out = False
    try:
        # Natively the timeout covers both the process and reading its pipes to the end.
        process.wait(timeout=max(0.0, start + timeout - time.monotonic()))
        for drain in (out, err):
            drain.thread.join(timeout=max(0.0, start + timeout - time.monotonic()))
            if drain.thread.is_alive():
                timed_out = True
    except subprocess.TimeoutExpired:
        timed_out = True
    if timed_out:
        process.kill()
        returncode = process.wait()
        return {
            "timed_out": True,
            "returncode": returncode,
            "stderr_decodable": err.decodable,
        }
    if out.size > STDOUT_LIMIT:
        return None
    result: dict[str, object] = {
        "timed_out": False,
        "returncode": process.returncode,
        "stderr_decodable": err.decodable,
    }
    if out.decodable:
        # subprocess translates newlines this way when text=True.
        text = "".join(out.parts).replace("\r\n", "\n").replace("\r", "\n")
        result["stdout_lines"] = text.split("\n")
    return result


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    observation: dict[str, object] = {
        "script_exists": os.path.exists(challenge["script"]),
        "csv_exists": os.path.exists(challenge["csv"]),
    }
    # Upstream asserts both files exist before it runs the script.
    if observation["script_exists"] and observation["csv_exists"]:
        run = run_script(challenge["interpreter"], challenge["script"], challenge["timeout_seconds"])
        if run is None:
            print(json.dumps({"unable": {"code": "stdout-too-large", "message": f"stdout exceeds {STDOUT_LIMIT} bytes"}}))
            return
        observation["run"] = run
    observation["dependency_files"] = [
        {"path": path, "exists": os.path.exists(path)} for path in challenge["dependency_files"]
    ]
    sys.stdout.write(json.dumps({"observation": observation}, ensure_ascii=False))


main()
