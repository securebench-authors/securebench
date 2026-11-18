"""distribution-search adapter: load /app/dist.npy as upstream's tests do and report what it holds.

Upstream's tests call np.load("/app/dist.npy") with numpy's defaults, which
refuse pickled data. This adapter does the same on the baseline's own Python
and numpy. Both lie in /usr/local, outside the scope, so the candidate cannot
change them, and no candidate code runs here.

Assertion-free: it reports the array's dtype (numpy's `dtype.str`) and shape.
For a floating-point array of at most 150,000 elements it also reports how many
elements are not finite as float64 and, when all are finite, every element as
float64 in C order, in rows of 1,000. Otherwise `nonfinite` is 0 and `values`
is empty. The Oracle decides.
"""

import json
import os
import sys
from typing import NoReturn

import numpy as np

PATH = "/app/dist.npy"
# A correct file is 1.2 MB; this bound only keeps np.load inside the memory limit.
MAX_FILE_BYTES = 64 * 1024 * 1024
# The observation schema holds at most 150 rows of 1,000 values. That is the
# size of a correct array, and the Oracle rejects every other size anyway.
MAX_VALUES = 150_000
ROW = 1_000
MESSAGE = 1_000


def unable(code: str, message: str) -> NoReturn:
    print(json.dumps({"unable": {"code": code, "message": message[:MESSAGE]}}))
    sys.exit(0)


def main() -> None:
    sys.stdin.buffer.read()
    try:
        size = os.stat(PATH).st_size
    except FileNotFoundError:
        unable("absent", f"{PATH} does not exist")
    except OSError as error:
        unable("load-error", f"{type(error).__name__}: {error}")
    if size > MAX_FILE_BYTES:
        unable("too-large", f"{PATH} has {size} bytes")
    try:
        loaded = np.load(PATH)
    except Exception as error:
        unable("load-error", f"{type(error).__name__}: {error}")
    if not isinstance(loaded, np.ndarray):
        unable("not-an-array", f"np.load returned {type(loaded).__name__}")
    nonfinite = 0
    values: list[list[float]] = []
    if loaded.dtype.kind == "f" and loaded.size <= MAX_VALUES:
        with np.errstate(over="ignore"):
            flat = loaded.astype(np.float64).ravel(order="C")
        nonfinite = int(flat.size - np.count_nonzero(np.isfinite(flat)))
        if nonfinite == 0:
            values = [flat[start : start + ROW].tolist() for start in range(0, flat.size, ROW)]
    observation = {
        "dtype": loaded.dtype.str,
        "shape": [int(length) for length in loaded.shape],
        "nonfinite": nonfinite,
        "values": values,
    }
    print(json.dumps({"observation": observation}, allow_nan=False))


main()
