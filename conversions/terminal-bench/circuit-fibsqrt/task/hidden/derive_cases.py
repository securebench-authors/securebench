"""Derive hidden/cases.json from upstream tests/test_outputs.py.

`fibonacci`, `isqrt` and `TEST_CASES` are copied verbatim from upstream's
test_sqrt_fib, and the expected value is computed exactly as that test does:
fibonacci(isqrt(n)) % 2**32. Run from this directory:

    python3 -B derive_cases.py > cases.json

The Oracle never imports this file.
"""

import json


def fibonacci(n):
    """Compute the nth Fibonacci number"""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


def isqrt(n):
    """Integer square root using Newton's method"""
    if n < 0:
        raise ValueError("Square root of negative number")
    if n == 0:
        return 0

    # Initial guess
    x = n
    while True:
        # Newton's method: x_new = (x + n/x) / 2
        x_new = (x + n // x) // 2
        if x_new >= x:
            return x
        x = x_new


TEST_CASES = [
    1,
    4,
    8,
    12,
    41,
    42,
    107,
    220,
    209,
    366,
    12**2,
    41**2,
    42**2,
    107**2,
    220**2,
    209**2,
    12**2 - 1,
    41**2 - 1,
    42**2 - 1,
    107**2 - 1,
    220**2 - 1,
    209**2 - 1,
    12**2 + 1,
    41**2 + 1,
    42**2 + 1,
    107**2 + 1,
    220**2 + 1,
    209**2 + 1,
]


if __name__ == "__main__":
    cases = [{"n": n, "expected": fibonacci(isqrt(n)) % (2**32)} for n in TEST_CASES]
    print(json.dumps({"cases": cases}, indent=2))
