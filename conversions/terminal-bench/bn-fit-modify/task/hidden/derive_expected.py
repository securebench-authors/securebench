"""Derive hidden/expected.json from upstream tests/test_outputs.py.

Run with the verifier's packages (Python 3.13, scipy 1.16.1, numpy):

    python3 derive_expected.py > expected.json

The edge sets, column names and counts are literals from the upstream tests.
`mean` and `std` are test_sampled_data's `true_mean` and `true_std`, computed
with the same expressions. `max_statistic` turns the test's acceptance rule,
`kstest(...).pvalue >= 0.001` with 10,000 rows, into a bound on the KS
statistic: scipy's p-value is `kstwo.sf(statistic, 10000)`, so the bound is
the largest double whose survival function is still at least 0.001. The
script checks that the survival function is non-increasing around the bound,
so the bound and the p-value give the same verdict for every statistic.
"""

import json

import numpy as np
from scipy.stats import kstwo

ROWS = 10_000
ALPHA = 0.001


def largest_accepted_statistic() -> float:
    low, high = 0.001, 0.1
    assert kstwo.sf(low, ROWS) >= ALPHA > kstwo.sf(high, ROWS)
    while True:
        middle = (low + high) / 2
        if middle in (low, high):
            break
        if kstwo.sf(middle, ROWS) >= ALPHA:
            low = middle
        else:
            high = middle
    assert kstwo.sf(np.nextafter(low, 1.0), ROWS) < ALPHA
    grid = np.linspace(low - 1e-5, low + 1e-5, 2001)
    survival = kstwo.sf(grid, ROWS)
    assert (np.diff(survival) <= 0).all()
    assert ((survival >= ALPHA) == (grid <= low)).all()
    neighbours = [low]
    for _ in range(50):
        neighbours.append(float(np.nextafter(neighbours[-1], 1.0)))
        neighbours.insert(0, float(np.nextafter(neighbours[0], 0.0)))
    for value in neighbours:
        assert (kstwo.sf(value, ROWS) >= ALPHA) == (value <= low)
    return float(low)


def main() -> None:
    dag_columns = ["from", "to"]
    expected = {
        "learned-dag": {
            "columns": dag_columns,
            "edges": [["U", "M"], ["U", "Y"], ["U", "D"], ["U", "R"], ["Y", "D"], ["R", "M"]],
        },
        "intervened-dag": {
            "columns": dag_columns,
            "edges": [["U", "M"], ["U", "D"], ["U", "R"], ["Y", "D"], ["R", "M"]],
        },
        "bn-sample": {
            "columns": ["U", "R", "Y", "M", "D"],
            "rows": ROWS,
            "column_count": 5,
            "ks_column": "D",
            "mean": -12.2965135 + 0.5495886 * 50.47989,
            "std": ((0.5495886**2) * 10.68515**2 + 14.0916**2) ** 0.5,
            "max_statistic": largest_accepted_statistic(),
        },
    }
    print(json.dumps(expected, indent=2))


if __name__ == "__main__":
    main()
