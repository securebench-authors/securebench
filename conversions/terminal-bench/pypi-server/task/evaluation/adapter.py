"""pypi-server adapter: install vectorops==0.1.0 from port 8080 as upstream's test does, and report what happened.

No process the agent started survives replay, so the candidate's server is
gone. The candidate's distribution files are not: this adapter looks for every
file in the scope that pip could install as vectorops (a name starting with
`vectorops-` and an archive extension pip accepts), serves them on
http://localhost:8080/simple as a PEP 503 index, and then repeats upstream's
test:

- `python -I -m pip install --index-url http://localhost:8080/simple vectorops==0.1.0`,
  in a fresh virtual environment on the baseline's Python 3.13 with its bundled
  pip 25.2, as upstream's `uvx -p 3.13 -w pip==25.2` does;
- `python -I -m pip show vectorops`;
- `import vectorops` and one `dotproduct(a, b)` call per pair of the challenge,
  in runner.py, a separate process on that environment's Python.

It records exit statuses, the name and version pip shows, whether the import
worked and each value dotproduct returned. It compares nothing: the Oracle
holds the expected values. The adapter runs on the stock interpreter, which
the candidate's files cannot replace. The baseline's Python is outside the
scope, so its files are the image's own until the candidate's code runs, in
pip's build of a source distribution or in the runner.
"""

import hashlib
import html
import http.server
import json
import math
import os
import select
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
from typing import Any

# The scope roots of task.toml. Changes under `bin` and `__pycache__` are not
# captured, so nothing of the candidate's is there.
ROOTS = ("/app", "/home", "/media", "/mnt", "/opt", "/srv", "/var/local", "/var/opt")
SKIPPED_DIRECTORIES = ("bin", "__pycache__")
# pip's archive extensions (pip/_internal/utils/filetypes.py): wheels and the
# source distribution formats it unpacks.
EXTENSIONS = (
    ".whl",
    ".zip",
    ".tar.gz",
    ".tgz",
    ".tar",
    ".tar.bz2",
    ".tbz",
    ".tar.xz",
    ".txz",
    ".tlz",
    ".tar.lz",
    ".tar.lzma",
)
PROJECT = "vectorops"
MAX_WALKED = 200_000
MAX_DISTRIBUTIONS = 64
MAX_FILE_BYTES = 32 * 1024 * 1024
WORK = "/tmp/securebench-pypi-server"
SYSTEM_PYTHON = "/usr/local/bin/python3"
RUNNER = "/.securebench/evaluation/runner.py"
INDEX = "http://localhost:8080/simple"
PORT = 8080
# Upstream's verifier has 900 s for everything.
TIMEOUT_SECONDS = 840
REPLY_BOUND = 256 * 1024
OUTPUT_BOUND = 4096


class Unable(Exception):
    """The adapter could not exercise the candidate."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def cut(text: str, limit: int, keep_end: bool = False) -> str:
    """The text as valid UTF-8 of at most `limit` bytes, keeping its start or its end."""
    raw = text.encode("utf-8", "replace")
    return (raw[-limit:] if keep_end else raw[:limit]).decode("utf-8", "ignore")


def decoded(data: bytes, limit: int, keep_end: bool = False) -> str:
    """Output bytes decoded with invalid UTF-8 replaced, cut to at most `limit` bytes."""
    return cut(data.decode("utf-8", "replace"), limit, keep_end)


def find_distributions() -> list[tuple[str, str, bytes]]:
    """Every distinct (path, file name, content) pip could install as vectorops, in walk order (roots and names sorted)."""
    found: list[tuple[str, str, bytes]] = []
    seen: set[tuple[str, str]] = set()
    walked = 0
    for root in ROOTS:
        for directory, subdirectories, files in os.walk(root):
            walked += len(subdirectories) + len(files)
            if walked > MAX_WALKED:
                raise Unable("scope-too-large", f"more than {MAX_WALKED} entries under the roots")
            subdirectories[:] = sorted(d for d in subdirectories if d not in SKIPPED_DIRECTORIES)
            for name in sorted(files):
                if not name.isprintable() or not name.isascii():
                    continue  # not a name of a distribution pip accepts
                lowered = name.lower()
                if not lowered.startswith(PROJECT + "-") or not lowered.endswith(EXTENSIONS):
                    continue
                path = os.path.join(directory, name)
                try:
                    if not stat.S_ISREG(os.stat(path).st_mode):
                        continue
                    with open(path, "rb") as file:
                        content = file.read(MAX_FILE_BYTES + 1)
                except OSError:
                    continue
                if len(content) > MAX_FILE_BYTES:
                    raise Unable("distribution-too-large", f"{path} is over {MAX_FILE_BYTES} bytes")
                key = (name, hashlib.sha256(content).hexdigest())
                if key in seen:
                    continue
                seen.add(key)
                found.append((path, name, content))
                if len(found) > MAX_DISTRIBUTIONS:
                    raise Unable("too-many-distributions", f"more than {MAX_DISTRIBUTIONS} files")
    return found


def serve(distributions: list[tuple[str, str, bytes]]) -> http.server.ThreadingHTTPServer:
    """A PEP 503 simple index on port 8080 that lists the distributions under /simple/vectorops/."""
    links = "".join(
        f'<a href="/files/{number}/{urllib.parse.quote(name)}'
        f'#sha256={hashlib.sha256(content).hexdigest()}">{html.escape(name)}</a><br>\n'
        for number, (_, name, content) in enumerate(distributions)
    )
    pages = {
        "/simple/": f'<!DOCTYPE html><html><body><a href="{PROJECT}/">{PROJECT}</a></body></html>',
        f"/simple/{PROJECT}/": f"<!DOCTYPE html><html><body>\n{links}</body></html>",
    }
    files = {
        f"/files/{number}/{urllib.parse.quote(name)}": content
        for number, (_, name, content) in enumerate(distributions)
    }

    class Index(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/simple", f"/simple/{PROJECT}"):
                self.send_response(301)
                self.send_header("Location", path + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if path in pages:
                self._reply(pages[path].encode(), "text/html; charset=utf-8")
            elif path in files:
                self._reply(files[path], "application/octet-stream")
            else:
                self.send_error(404)

        def _reply(self, body: bytes, kind: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            pass

    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Index)
    except OSError as error:
        raise Unable("port", f"cannot serve on port {PORT}: {error}") from None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def remaining(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise Unable("timeout", f"the test ran past {TIMEOUT_SECONDS} s")
    return left


def run(command: list[str], environment: dict[str, str], deadline: float) -> tuple[int, bytes]:
    """Run a command in /app with output captured; a timeout ends the case."""
    try:
        ran = subprocess.run(
            command,
            cwd="/app",
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=remaining(deadline),
            start_new_session=True,
        )
    except subprocess.TimeoutExpired:
        raise Unable("timeout", f"{command[1:4]} ran past {TIMEOUT_SECONDS} s") from None
    return max(-255, min(255, ran.returncode)), ran.stdout


def call(
    python: str, environment: dict[str, str], pairs: list[Any], deadline: float
) -> tuple[list[dict[str, Any]], str]:
    """Run runner.py and parse its replies: the import line, then one line per pair."""
    reply_read, reply_write = os.pipe()
    try:
        runner = subprocess.Popen(
            [python, "-I", RUNNER, str(reply_write)],
            cwd="/app",
            env=environment,
            pass_fds=(reply_write,),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        os.close(reply_read)
        os.close(reply_write)
        return [], "not started"
    os.close(reply_write)
    assert runner.stdin is not None
    try:
        runner.stdin.write(json.dumps(pairs).encode())
        runner.stdin.close()
    except OSError:
        pass  # the runner ended before reading: its replies say how far it got
    received = b""
    lines: list[bytes] = []
    status = "complete"
    # One import line and one line per pair; a candidate process holding the
    # pipe open after the last of them does not delay the case.
    while len(lines) < len(pairs) + 1:
        try:
            left = remaining(deadline)
        except Unable:
            status = "timed out"
            break
        ready, _, _ = select.select([reply_read], [], [], min(left, 1.0))
        if not ready:
            continue
        chunk = os.read(reply_read, 65536)
        if not chunk:
            status = "ended early"
            break
        received += chunk
        if len(received) > REPLY_BOUND:
            status = "reply too large"
            break
        *complete, received = received.split(b"\n")
        lines += complete
        if lines and lines[0] and _imported(lines[0]) is False:
            break
    os.close(reply_read)
    try:
        os.killpg(runner.pid, signal.SIGKILL)
    except OSError:
        pass
    runner.wait()
    return [_reply(line) for line in lines[: len(pairs) + 1]], status


def _imported(line: bytes) -> bool | None:
    try:
        message = json.loads(line)
    except ValueError:
        return None
    return message.get("imported") if isinstance(message, dict) else None


def _reply(line: bytes) -> dict[str, Any]:
    """One runner reply, or {} when it is not a JSON object."""
    try:
        message = json.loads(line)
    except ValueError:
        return {}
    return message if isinstance(message, dict) else {}


def observe(pairs: list[Any]) -> dict[str, Any]:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    distributions = find_distributions()
    serve(distributions)
    shutil.rmtree(WORK, ignore_errors=True)
    environment_dir = f"{WORK}/env"
    # Every interpreter runs with -I. With `-m`, Python otherwise puts the
    # working directory, /app, first on sys.path, and a candidate's /app/pip
    # or /app/venv package would run in place of pip or venv.
    created, output = run(
        [SYSTEM_PYTHON, "-I", "-m", "venv", environment_dir], dict(os.environ), deadline
    )
    if created != 0:
        raise Unable("venv", decoded(output, OUTPUT_BOUND, keep_end=True))
    python = f"{environment_dir}/bin/python"
    environment = {
        **os.environ,
        "PATH": f"{environment_dir}/bin:{os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')}",
        "VIRTUAL_ENV": environment_dir,
    }
    install_exit, install_output = run(
        [python, "-I", "-m", "pip", "install", "--index-url", INDEX, f"{PROJECT}==0.1.0"],
        environment,
        deadline,
    )
    show_exit, show_output = run(
        [python, "-I", "-m", "pip", "show", PROJECT], environment, deadline
    )
    fields = {"Name": "", "Version": ""}
    for line in show_output.splitlines():
        key, _, value = line.partition(b": ")
        name = key.decode("ascii", "replace")
        if name in fields and not fields[name]:
            fields[name] = decoded(value.strip(), 256)
    replies, runner_status = call(python, environment, pairs, deadline)
    imported = False
    import_error = "no reply"
    results: list[dict[str, Any]] = []
    if replies:
        first = replies[0]
        imported = first.get("imported") is True
        import_error = (
            first.get("error") if isinstance(first.get("error"), str) else "malformed reply"
        )
        for reply in replies[1:]:
            result = _result(reply)
            if result is None:
                runner_status = "malformed reply"
                break
            results.append(result)
    return {
        "distributions": [
            {"path": cut(path, 4096), "bytes": len(content)} for path, _, content in distributions
        ],
        "install_exit": install_exit,
        "install_output": decoded(install_output, OUTPUT_BOUND, keep_end=True),
        "show_exit": show_exit,
        "show_name": fields["Name"],
        "show_version": fields["Version"],
        "imported": imported,
        "import_error": cut(import_error, 512),
        "runner": runner_status,
        "results": results,
    }


def _result(reply: dict[str, Any]) -> dict[str, Any] | None:
    """A well-formed result reply, bounded to the observation schema, or None."""
    if set(reply) != {"raised", "type", "numeric", "value"}:
        return None
    raised, kind, numeric, value = reply["raised"], reply["type"], reply["numeric"], reply["value"]
    if not isinstance(raised, str) or not isinstance(kind, str) or not isinstance(numeric, bool):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, int) and not -(2**63) < value < 2**63:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return {"raised": cut(raised, 512), "type": cut(kind, 128), "numeric": numeric, "value": value}


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    pairs = [[pair["a"], pair["b"]] for pair in challenge["pairs"]]
    try:
        response = {"observation": observe(pairs)}
    except Unable as unable:
        response = {"unable": {"code": unable.code, "message": cut(str(unable), 4096)}}
    sys.stdout.write(json.dumps(response))
    sys.stdout.flush()
    # The index server's thread and anything the candidate started must not
    # keep the case open.
    os._exit(0)


if __name__ == "__main__":
    main()
