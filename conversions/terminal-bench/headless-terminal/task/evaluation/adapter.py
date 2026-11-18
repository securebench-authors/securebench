"""Runs driver.py under the system Python and returns what it recorded.

The driver imports the candidate's code, so it runs in its own process under
/usr/local/bin/python3, the interpreter the candidate installed its
dependencies into. Its standard input is /dev/null and its standard output
and error are unlinked temporary files, as under pytest's default output
capture; the recorded values come back through a result file. The adapter
returns them unchanged and decides nothing.
"""

import json
import os
import subprocess
import sys
import tempfile

PYTHON = "/usr/local/bin/python3"
DRIVER = "/.securebench/evaluation/driver.py"
TAIL_BYTES = 2000


def _unable(code, message):
    json.dump({"unable": {"code": code, "message": message[:4000]}}, sys.stdout)


def _tail(stream):
    stream.seek(0, os.SEEK_END)
    stream.seek(max(0, stream.tell() - TAIL_BYTES))
    return stream.read().decode("utf-8", "replace")


def main():
    tests = json.load(sys.stdin)["tests"]
    result_path = os.path.join(tempfile.mkdtemp(prefix="headless-terminal-"), "result.json")
    with open(os.devnull, "rb") as stdin, tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            status = subprocess.run(
                [PYTHON, "-I", DRIVER, json.dumps(tests), result_path],
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                cwd="/app",
            ).returncode
        except OSError as error:
            _unable("driver-start", f"{PYTHON}: {error}")
            return
        if status != 0:
            # test.sh rewards on pytest's exit status, so a test process that
            # does not exit cleanly fails the task there too.
            _unable("driver-exit", f"driver exited with status {status}; stderr ends: {_tail(stderr)}")
            return
    try:
        with open(result_path, "rb") as stream:
            results = json.loads(stream.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        _unable("driver-result", f"unreadable result file: {error}")
        return
    json.dump({"observation": results}, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
