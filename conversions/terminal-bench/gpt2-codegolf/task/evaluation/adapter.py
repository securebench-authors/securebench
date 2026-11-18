"""Compile the candidate's /app/gpt2.c and run it, as upstream's test does.

The adapter reports what happened: exit statuses, whether each output stream
decodes as UTF-8, and the program's standard output. It holds no expected
value; the Oracle decides whether the output is right.

Upstream's test runs both commands with `subprocess.run(..., text=True)`,
which decodes stdout and stderr as strict UTF-8 and fails the test when either
does not decode, so the adapter reports decodability of every stream it reads.
Streams are read in chunks and only a bounded prefix is kept, so a program that
prints without end cannot exhaust the adapter's memory.
"""

import codecs
import json
import subprocess
import sys
import threading
import time

CHUNK = 65536
STDOUT_KEEP = 512 * 1024
STDERR_KEEP = 16 * 1024


class Collector:
    def __init__(self, stream, keep):
        self.stream = stream
        self.keep = keep
        self.head = bytearray()
        self.total = 0
        self.utf8 = True
        self.decoder = codecs.getincrementaldecoder("utf-8")("strict")
        self.done = threading.Event()

    def run(self):
        try:
            while True:
                chunk = self.stream.read1(CHUNK)
                if not chunk:
                    break
                self.total += len(chunk)
                if len(self.head) < self.keep:
                    self.head += chunk[: self.keep - len(self.head)]
                if self.utf8:
                    try:
                        self.decoder.decode(chunk)
                    except UnicodeDecodeError:
                        self.utf8 = False
            if self.utf8:
                try:
                    self.decoder.decode(b"", final=True)
                except UnicodeDecodeError:
                    self.utf8 = False
        finally:
            self.done.set()

    def text(self):
        # Only a diagnostic or a prefix to search: a cut through a multi-byte
        # character at the end of the prefix must not hide the rest.
        return bytes(self.head).decode("utf-8", errors="replace")


def execute(argv, timeout):
    """Run argv with piped output; the timeout covers exit and end of output, like subprocess.run."""
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = Collector(proc.stdout, STDOUT_KEEP)
    err = Collector(proc.stderr, STDERR_KEEP)
    for collector in (out, err):
        threading.Thread(target=collector.run, daemon=True).start()
    deadline = None if timeout is None else time.monotonic() + timeout
    timed_out = False
    try:
        proc.wait(timeout=None if deadline is None else max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        proc.wait()
    for collector in (out, err):
        remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
        if not collector.done.wait(remaining):
            timed_out = True
    return proc.returncode, timed_out, out, err


def main():
    challenge = json.loads(sys.stdin.read())
    try:
        status, _, out, err = execute(challenge["compile_argv"], None)
    except OSError as error:
        return {"unable": {"code": "compiler_not_started", "message": str(error)[:4000]}}
    observation = {
        "compile": {
            "exit_status": status,
            "stdout_utf8": out.utf8,
            "stderr_utf8": err.utf8,
            "stderr": err.text(),
        }
    }
    # Upstream's test stops at a failed compilation and never runs the program.
    if status != 0:
        return {"observation": observation}
    try:
        status, timed_out, out, err = execute(challenge["run_argv"], challenge["run_timeout_seconds"])
    except OSError as error:
        return {"unable": {"code": "program_not_started", "message": str(error)[:4000]}}
    observation["run"] = {
        "timed_out": timed_out,
        "exit_status": status,
        "stdout_bytes": out.total,
        "stdout_truncated": out.total > len(out.head),
        "stdout_utf8": out.utf8,
        "stdout": out.text(),
        "stderr_utf8": err.utf8,
        "stderr": err.text(),
    }
    return {"observation": observation}


if __name__ == "__main__":
    response = main()
    sys.stdout.write(json.dumps(response, allow_nan=False))
    sys.stdout.flush()
