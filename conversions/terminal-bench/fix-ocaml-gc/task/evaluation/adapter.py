"""Runs upstream's basic testsuite, then repeats every command ocamltest runs for it and reports what each produced.

The challenge carries the plan: the testsuite command upstream's test.sh runs, then
the steps ocamltest performs for each test of testsuite/tests/basic (taken from a
traced native run, see CONVERSION.md). This adapter only executes them and reports
exit statuses, file contents and bytecode section tables. It holds no expected
value and decides nothing; the Oracle compares.
"""

import base64
import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

SOURCE_DIR = "/app/ocaml/testsuite/tests/basic"
OCAMLTEST_DIR = "/app/ocaml/testsuite/tests/basic/_ocamltest"
FILE_CAP = 10240  # bytes reported per output; every expected output is shorter
SUMMARY_CAP = 65536
STEP_TIMEOUT = 600  # ocamltest's own per-command timeout in this testsuite (timeout=600)
SUMMARY_TIMEOUT = 1800
MAX_SECTIONS = 64
MAX_PROGRAM_BYTES = 64 * 1024 * 1024
PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# The variables ocamltest's commands saw in the traced native run that can affect
# them; make's own bookkeeping variables are left out.
PROGRAM_ENV = {"PATH": PATH, "HOME": "/root", "TERM": "dumb", "OCAMLRUNPARAM": ""}
COMPILER_ENV = dict(PROGRAM_ENV, OCAML_COLOR="auto", OCAML_ERROR_STYLE="contextual")
ENVS = {"program": PROGRAM_ENV, "compiler": COMPILER_ENV}


def run(argv, cwd, env, stdout, stderr, timeout):
    """Run argv in its own process group; return (returncode or None, timed_out)."""
    try:
        process = subprocess.Popen(
            argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            start_new_session=True,
        )
    except OSError:
        return None, False
    try:
        return process.wait(timeout=timeout), False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        process.wait()
        return process.returncode, True
    finally:
        # Children left behind by the candidate must not outlive their step.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass


def file_value(fd, cap, tail=False):
    """At most cap bytes of the file, and its size capped at cap + 1 (so a longer file shows as cap + 1)."""
    size = os.fstat(fd).st_size
    start = max(0, size - cap) if tail else 0
    data = b""
    while len(data) <= cap:
        chunk = os.pread(fd, cap + 1 - len(data), start + len(data))
        if not chunk:
            break
        data += chunk
    if tail and start > 0:
        return {"size": cap + 1, "content_b64": base64.b64encode(data[-cap:]).decode("ascii")}
    return {"size": len(data), "content_b64": base64.b64encode(data[:cap]).decode("ascii")}


def open_regular(path):
    """Open path for reading only if it is a regular file (never block on a FIFO)."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return None
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        return None
    return fd


def bytecode_toc(path):
    """The section table of a bytecode executable, as tools/cmpbyt reads it (Bytesections.read_toc)."""
    fd = open_regular(path)
    if fd is None:
        return None
    try:
        size = os.fstat(fd).st_size
        if size < 16 or size > MAX_PROGRAM_BYTES:
            return None
        trailer = os.pread(fd, 16, size - 16)
        count = int.from_bytes(trailer[:4], "big", signed=True)
        magic = trailer[4:]
        if count < 0 or count > MAX_SECTIONS:
            return None
        toc_pos = size - 16 - 8 * count
        if toc_pos < 0:
            return None
        table = os.pread(fd, 8 * count, toc_pos)
        entries = [(table[8 * i: 8 * i + 4], int.from_bytes(table[8 * i + 4: 8 * i + 8], "big", signed=True))
                   for i in range(count)]
        sections = []
        position = toc_pos
        for name, length in reversed(entries):
            position -= length
            if length < 0 or position < 0:
                return None
            content = os.pread(fd, length, position)
            if len(content) != length:
                return None
            sections.append({"name_hex": name.hex(), "length": length, "sha256": hashlib.sha256(content).hexdigest()})
        sections.reverse()
        return {"magic_hex": magic.hex(), "sections": sections}
    finally:
        os.close(fd)


def link(step):
    os.makedirs(step["dir"], exist_ok=True)
    for name in step["names"]:
        target = os.path.join(step["dir"], name)
        if not os.path.lexists(target):
            os.symlink(os.path.join(SOURCE_DIR, name), target)


def execute(step):
    result = {"id": step["id"]}
    output = step.get("output")
    if output is None:
        returncode, timed_out = run(step["argv"], step["dir"], ENVS[step["env"]],
                                    subprocess.DEVNULL, subprocess.DEVNULL, STEP_TIMEOUT)
    else:
        # ocamltest sends stdout and stderr to the same file; we read it back
        # through our own descriptor, so a renamed or replaced path changes nothing.
        try:
            fd = os.open(output, os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
        except OSError:
            fd = None
        if fd is None:
            returncode, timed_out = None, False
        else:
            returncode, timed_out = run(step["argv"], step["dir"], ENVS[step["env"]], fd, fd, STEP_TIMEOUT)
            result["file"] = file_value(fd, FILE_CAP)
            os.close(fd)
    if returncode is not None:
        result["returncode"] = returncode
    result["timed_out"] = timed_out
    return result


def read(step):
    result = {"id": step["id"]}
    fd = open_regular(step["path"])
    if fd is not None:
        result["file"] = file_value(fd, FILE_CAP)
        os.close(fd)
    return result


def summary(spec):
    """Upstream's own command, make -C testsuite one DIR=tests/basic, keeping the end of its standard output.

    The end is kept because that is where the testsuite prints its summary."""
    stdout = tempfile.TemporaryFile()
    fd = stdout.fileno()
    returncode, timed_out = run(spec["argv"], spec["dir"], {"PATH": PATH, "HOME": "/root"},
                                fd, subprocess.DEVNULL, SUMMARY_TIMEOUT)
    value = {"timed_out": timed_out, "stdout": file_value(fd, SUMMARY_CAP, tail=True)}
    stdout.close()
    if returncode is not None:
        value["returncode"] = returncode
    return value


def main():
    challenge = json.load(sys.stdin)
    observation = {"summary": summary(challenge["summary"])}
    # The testsuite run above leaves its build directories where the steps below
    # recreate them; start the steps from an empty directory, as ocamltest does.
    if os.path.islink(OCAMLTEST_DIR) or os.path.isfile(OCAMLTEST_DIR):
        os.unlink(OCAMLTEST_DIR)
    elif os.path.isdir(OCAMLTEST_DIR):
        shutil.rmtree(OCAMLTEST_DIR, ignore_errors=True)
    results = []
    for step in challenge["steps"]:
        op = step["op"]
        if op == "link":
            try:
                link(step)
            except OSError:
                pass  # a missing source shows up as a failed compilation in the next step
        elif op == "exec":
            results.append(execute(step))
        elif op == "read":
            results.append(read(step))
        elif op == "toc":
            value = {"id": step["id"]}
            toc = bytecode_toc(step["path"])
            if toc is not None:
                value["toc"] = toc
            results.append(value)
    observation["results"] = results
    sys.stdout.write(json.dumps({"observation": observation}))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
