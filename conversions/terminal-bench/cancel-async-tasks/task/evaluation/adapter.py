"""Adapter for cancel-async-tasks.

Runs upstream's driver, test.py, against the candidate's /app/run.py the way
upstream's tests/test_outputs.py does, and reports what the driver process did:
whether it ended within the timeout, its exit status, the elapsed time and the
lines it printed. The Oracle compares these with upstream's assertions.

Usage: adapter.py run-to-completion | cancel-on-interrupt, with the challenge on
standard input.
"""

import json
import shutil
import signal
import subprocess
import sys
import time

DRIVER = "/.securebench/evaluation/test.py"
# Upstream runs "python" from inside its uvx environment, which is the
# baseline's /usr/local/bin/python 3.13 with a separate site-packages.
PYTHON = "/usr/local/bin/python"
WORKDIR = "/app"


def lines(stdout: bytes) -> list[str] | None:
    # Upstream decodes strictly; a stdout that is not UTF-8 fails its test.
    try:
        text = stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text.split("\n")


def driver_argv(challenge: dict) -> list[str]:
    return [
        PYTHON,
        "test.py",
        "--n-tasks",
        str(challenge["n_tasks"]),
        "--max-concurrent",
        str(challenge["max_concurrent"]),
    ]


def run_to_completion(challenge: dict) -> dict:
    # test_tasks_run_concurrently / test_tasks_obey_max_concurrent:
    # subprocess.run(..., timeout=..., check=True, capture_output=True)
    start = time.monotonic()
    try:
        result = subprocess.run(
            driver_argv(challenge),
            cwd=WORKDIR,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=challenge["timeout_seconds"],
        )
    except subprocess.TimeoutExpired:
        return {"timed_out": True, "elapsed_seconds": time.monotonic() - start}
    elapsed = time.monotonic() - start
    observation = {"timed_out": False, "returncode": result.returncode, "elapsed_seconds": elapsed}
    stdout = lines(result.stdout)
    if stdout is not None:
        observation["stdout"] = stdout
    return observation


def cancel_on_interrupt(challenge: dict) -> dict:
    # test_tasks_cancel_*_max_concurrent: Popen, sleep, SIGINT, communicate(timeout=...)
    proc = subprocess.Popen(
        driver_argv(challenge),
        cwd=WORKDIR,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(challenge["interrupt_after_seconds"])
    proc.send_signal(signal.SIGINT)
    try:
        stdout, _ = proc.communicate(timeout=challenge["timeout_seconds"])
    except subprocess.TimeoutExpired:
        return {"timed_out": True}
    finally:
        proc.kill()
    observation = {"timed_out": False}
    decoded = lines(stdout)
    if decoded is not None:
        observation["stdout"] = decoded
    return observation


def main() -> None:
    check = sys.argv[1]
    challenge = json.load(sys.stdin)

    # Upstream's tests/test.sh: cp /tests/test.py /app/test.py
    shutil.copyfile(DRIVER, WORKDIR + "/test.py")

    # An ignored or blocked SIGINT survives exec, and Python then never raises
    # KeyboardInterrupt in the driver; upstream's runner leaves SIGINT at its
    # default, so we make sure the driver starts the same way.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT})

    # A fresh Evaluation reads the interpreter and the standard library cold,
    # and with sibling cases starting at the same time the driver could still
    # be importing asyncio when the SIGINT arrives 0.5 s later. Natively the
    # cancel tests run after two earlier tests have loaded the same files in
    # the same container. Load them once here, without the candidate's code
    # (-I keeps /app off sys.path).
    subprocess.run(
        [PYTHON, "-I", "-c", "import argparse, asyncio"],
        cwd="/",
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=30,
    )

    if check == "run-to-completion":
        observation = run_to_completion(challenge)
    elif check == "cancel-on-interrupt":
        observation = cancel_on_interrupt(challenge)
    else:
        json.dump({"unable": {"code": "unknown-check", "message": check}}, sys.stdout)
        return
    json.dump({"observation": observation}, sys.stdout)


if __name__ == "__main__":
    main()
