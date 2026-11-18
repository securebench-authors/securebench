"""Derive hidden/expected.json from the upstream task.

Run from anywhere, with the upstream task directory as the argument:

    python3 -I derive.py <upstream>/financial-document-processor

The Oracle does not run this script; it only reads expected.json.

Every value comes from upstream tests/test_outputs.py, read with `ast`, so
nothing is copied by hand:

- `invoices`: `expected_original_documents` of test_invoices_moved_correctly.
  Its document hashes go to `documents`, and the entry upstream counts by name
  ("summary.csv") goes to `names`.
- `other`: `expected_original_others` of test_other_documents_moved_correctly.
- `summary.header`: `expected_headers` of test_summary_csv_structure.
- `summary.rows`: the constant in its `len(rows) == 11`, which must equal
  `len(expected_data)`, the count test_summary_csv_content asserts.
- `summary.total_row`: the constant in `filename == "total"` of
  test_summary_csv_content, which must be the one key of `expected_data` that
  names no document.
- `summary.columns`: the columns test_summary_csv_content reads as the
  filename (`filename = row[...]`), the total (`float(row[...])` in the total
  assertion) and the VAT (`row[...]` in `actual_vat = ...`), in that order.
- `summary.amounts`: `expected_data`, keyed by document hash and by the total
  row's name.

Upstream identifies documents by the SHA-512 of their content. A SecureBench
listing gives the SHA-256 of each file, so the script maps every SHA-512 to the
SHA-256 of the same document in environment/documents/, written
`sha256:<hex>` as listings give it. Those are the files the baseline image
copies into /app/documents/ under random names. It fails unless every listed
SHA-512 is the hash of exactly one shipped document, every shipped document is
listed exactly once, as an invoice or as another document, and no two
documents share a SHA-256.
"""

import ast
import hashlib
import json
import sys
from pathlib import Path


def function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise SystemExit(f"{name} not found")


def literal(test: ast.FunctionDef, name: str) -> object:
    for statement in ast.walk(test):
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id == name
        ):
            return ast.literal_eval(statement.value)
    raise SystemExit(f"{test.name}.{name} not found")


def compared_constant(test: ast.FunctionDef, left: str) -> object:
    """The constant in the one comparison `<left> == <constant>` of the test."""
    found = [
        node.comparators[0].value
        for node in ast.walk(test)
        if isinstance(node, ast.Compare)
        and ast.unparse(node.left) == left
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and isinstance(node.comparators[0], ast.Constant)
    ]
    if len(found) != 1:
        raise SystemExit(f"{test.name}: expected one comparison {left} == <constant>")
    return found[0]


def row_column(node: ast.AST) -> str:
    """The first `row["<column>"]` inside `node`."""
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Subscript)
            and isinstance(sub.value, ast.Name)
            and sub.value.id == "row"
            and isinstance(sub.slice, ast.Constant)
            and isinstance(sub.slice.value, str)
        ):
            return sub.slice.value
    raise SystemExit("no row[...] found")


def assigned(test: ast.FunctionDef, name: str) -> ast.AST:
    for node in ast.walk(test):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            return node.value
    raise SystemExit(f"{test.name}: {name} is never assigned")


def total_column(test: ast.FunctionDef) -> str:
    """The column in `float(row[...])` of the assertion on total_amount."""
    for node in ast.walk(test):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "float"
            and node.args
            and isinstance(node.args[0], ast.Subscript)
        ):
            return row_column(node.args[0])
    raise SystemExit(f"{test.name}: no float(row[...])")


def main(upstream: Path) -> None:
    tree = ast.parse((upstream / "tests" / "test_outputs.py").read_text())
    moved = function(tree, "test_invoices_moved_correctly")
    others_test = function(tree, "test_other_documents_moved_correctly")
    structure = function(tree, "test_summary_csv_structure")
    content = function(tree, "test_summary_csv_content")

    invoices_set = literal(moved, "expected_original_documents")
    others = literal(others_test, "expected_original_others")
    headers = literal(structure, "expected_headers")
    data = literal(content, "expected_data")
    rows = compared_constant(structure, "len(rows)")
    total_row = compared_constant(content, "filename")
    assert isinstance(invoices_set, set) and isinstance(others, set)
    assert isinstance(headers, list) and isinstance(data, dict)
    assert isinstance(rows, int) and rows == len(data), "the two row counts differ"

    sha256_of: dict[str, str] = {}
    for document in sorted((upstream / "environment" / "documents").iterdir()):
        content_bytes = document.read_bytes()
        sha512 = hashlib.sha512(content_bytes).hexdigest()
        assert sha512 not in sha256_of, f"duplicate document {document.name}"
        sha256_of[sha512] = "sha256:" + hashlib.sha256(content_bytes).hexdigest()

    invoices = {item for item in invoices_set if item in sha256_of}
    names = sorted(invoices_set - invoices)
    assert set(sha256_of) == invoices | others, "documents and upstream lists differ"
    assert not invoices & others
    assert len(set(sha256_of.values())) == len(sha256_of), "two documents share a SHA-256"
    assert set(data) == invoices | {total_row}, "expected_data must cover the invoices and total"

    columns = [
        row_column(assigned(content, "filename")),
        total_column(content),
        row_column(assigned(content, "actual_vat")),
    ]
    assert sorted(columns) == sorted(headers), "the content test reads other columns"

    def amounts(key: str) -> dict[str, object]:
        return {
            "total_amount": data[key]["total_amount"],
            "vat_amount": data[key]["vat_amount"],
        }

    expected = {
        "invoices": {
            "documents": sorted(sha256_of[sha512] for sha512 in invoices),
            "names": names,
        },
        "other": sorted(sha256_of[sha512] for sha512 in others),
        "summary": {
            "header": headers,
            "rows": rows,
            "total_row": total_row,
            "columns": columns,
            "amounts": {
                **{sha256_of[sha512]: amounts(sha512) for sha512 in sorted(invoices)},
                total_row: amounts(total_row),
            },
        },
    }
    out = Path(__file__).resolve().parent / "expected.json"
    out.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
