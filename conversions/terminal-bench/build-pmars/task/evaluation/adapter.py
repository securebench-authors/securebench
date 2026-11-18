"""Runs the operations of one upstream test and reports what they produced.

The upstream tests (tests/test_outputs.py) check three kinds of thing: that a
path exists, what a shell command prints, and which files a glob under /app
finds. Each case's challenge lists the operations of one upstream test; this
adapter performs them as the test does and returns the raw results. It judges
nothing: the Oracle applies the test's assertions.
"""

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

# The baseline image's PATH, so that `pmars` resolves as it does natively.
ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
}
# Upstream's pytest runs in the image's WORKDIR.
WORKDIR = "/app"


def run_command(command: str) -> dict:
    # subprocess.check_output(cmd, shell=True) runs /bin/sh -c; pytest's fd
    # capture leaves standard input at /dev/null, and only stdout is captured.
    completed = subprocess.run(
        ["/bin/sh", "-c", command],
        cwd=WORKDIR,
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return {
        "exit_status": completed.returncode,
        "stdout_base64": base64.b64encode(completed.stdout).decode("ascii"),
    }


def display_name(path: Path) -> str:
    # A file name need not be UTF-8; JSON strings must be.
    return os.fsencode(path.name).decode("utf-8", "backslashreplace")


def source_glob(operation: dict) -> dict:
    matches = []
    for match in Path(operation["directory"]).glob(operation["pattern"]):
        matches.append(
            {
                "name": display_name(match),
                "exists": [(match / sub).exists() for sub in operation["exists"]],
                "glob_counts": [
                    len(list((match / glob["directory"]).glob(glob["pattern"])))
                    for glob in operation["globs"]
                ],
            }
        )
    return {"matches": matches}


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    observation = {
        "exists": [Path(path).exists() for path in challenge["exists"]],
        "commands": [run_command(command) for command in challenge["commands"]],
        "source_globs": [source_glob(operation) for operation in challenge["source_globs"]],
    }
    sys.stdout.write(json.dumps({"observation": observation}))


if __name__ == "__main__":
    main()
