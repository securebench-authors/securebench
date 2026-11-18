"""Rebuild hidden/cases.json from the upstream test.

Usage: python3 -B derive_cases.py <upstream>/regex-log/tests/test_outputs.py > cases.json

The upstream test holds its inputs and its expected answer as two list literals,
`sample_logs` and `expected_dates`, and joins the logs with "\\n". We read both
literals from the test's syntax tree instead of retyping them, so the case
cannot drift from upstream by a typo.
"""

import ast
import json
import sys


def literal(tree: ast.AST, name: str) -> list[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            value = ast.literal_eval(node.value)
            assert isinstance(value, list) and all(isinstance(item, str) for item in value)
            return value
    raise SystemExit(f"{name} not found")


def main() -> None:
    tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
    sample_logs = literal(tree, "sample_logs")
    expected_dates = literal(tree, "expected_dates")
    cases = [{"challenge": {"log_text": "\n".join(sample_logs)}, "expected_matches": expected_dates}]
    json.dump({"cases": cases}, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
