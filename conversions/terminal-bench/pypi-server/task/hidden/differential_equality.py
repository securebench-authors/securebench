"""Differential test of runner.exact against upstream's `dotproduct(a, b) == expected`.

Upstream asserts with Python's `==` inside the candidate's process. The runner
instead reports the exact int or float value of what dotproduct returned, and
the Oracle compares that with `==` on the host. This script checks, for many
return values and each of upstream's expected values (hidden/cases.json), that
the two decisions agree, and prints every disagreement.

Run it on the baseline's Python with NumPy installed, from the pack root:

    docker run --rm --memory 1g -v <pack>:/pack:ro \
      alexgshaw/pypi-server@sha256:d18bb30f47c7dcaa3acdbc31ac7413c98eadca2ea16540bbd380f2f063b95276 \
      sh -c 'pip install -q numpy==2.3.4 && python3 -B -I /pack/hidden/differential_equality.py'
"""

import importlib.util
import math
import sys
from decimal import Decimal
from fractions import Fraction

import numpy as np

spec = importlib.util.spec_from_file_location("runner", "/pack/evaluation/runner.py")
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

# Upstream's expected values: 1, 2, 1 and 0.
EXPECTED: list[int | float] = [0, 1, 2]


class AlwaysEqual:
    def __eq__(self, other: object) -> bool:
        return True


class EqualInt(int):
    def __eq__(self, other: object) -> bool:
        return True

    __hash__ = int.__hash__


def returns(expected: int | float) -> list[object]:
    """Return values near `expected`: the same value in every numeric type, and its neighbours."""
    up = math.nextafter(float(expected), math.inf)
    down = math.nextafter(float(expected), -math.inf)
    values: list[object] = [
        expected,
        float(expected),
        up,
        down,
        Fraction(expected),
        Fraction(expected) + Fraction(1, 10**30),
        Decimal(expected),
        Decimal(expected) + Decimal("1e-25"),
        Decimal(repr(float(expected))),
        complex(expected),
        complex(expected, 1e-300),
        np.float64(expected),
        np.float32(expected),
        np.float32(expected) + np.float32(2) ** -10,
        np.float16(expected),
        np.longdouble(expected),
        np.longdouble(expected) + np.longdouble(2) ** -60,
        np.complex128(expected),
        np.array(expected),
        np.array([expected]),
        str(expected),
        [expected],
        (expected,),
        None,
        math.nan,
        math.inf,
        -math.inf,
        Decimal("NaN"),
        Decimal("Infinity"),
        2**70,
        AlwaysEqual(),
        EqualInt(int(expected) + 1),
    ]
    if float(expected).is_integer():
        whole = int(expected)
        values += [
            whole,
            True if whole == 1 else whole,
            np.int64(whole),
            np.int8(whole) if -128 <= whole < 128 else whole,
            np.uint64(abs(whole)),
            whole + 1,
            whole - 1,
        ]
    return values


def upstream(value: object, expected: int | float) -> bool:
    try:
        return bool(value == expected)
    except Exception:
        return False


def ours(value: object, expected: int | float) -> bool:
    reported = runner.exact(value)
    return reported is not None and reported == expected


# Deliberate differences: an object whose __eq__ claims equality with
# anything is not a number, and an int subclass is judged by its int value.
# NumPy 2 compares a float16 scalar with a Python float in float16 (NEP 50),
# so upstream accepts a float16 that equals the expected value only after the
# expected value is rounded to 11 bits; the runner reports its exact value.
DELIBERATE = (AlwaysEqual, EqualInt, np.float16)

compared = 0
differences = 0
for expected in EXPECTED:
    for value in returns(expected):
        compared += 1
        a, b = upstream(value, expected), ours(value, expected)
        if a != b:
            label = "deliberate" if isinstance(value, DELIBERATE) else "DIFFERENT"
            if label == "DIFFERENT":
                differences += 1
            print(
                f"{label}: expected {expected!r}, returned {type(value).__name__} {value!r}: upstream {a}, ours {b}"
            )
print(
    f"{compared} comparisons, {differences} unexplained differences, numpy {np.__version__}, python {sys.version.split()[0]}"
)
