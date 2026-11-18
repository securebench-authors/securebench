"""pypi-server runner: import the installed vectorops and call dotproduct, as upstream's test does.

The adapter starts this file on the Python of the virtual environment it just
installed vectorops into, with -I, so that neither the working directory nor
this file's directory is on sys.path: `import vectorops` finds only the
installed distribution, as in upstream's pytest process.

Standard input holds a JSON list of [a, b] pairs. The reply pipe, whose file
descriptor is the only argument, receives one JSON line for the import and
then one per pair, in order:

    {"imported": true, "error": ""}    or    {"imported": false, "error": "<exception>"}
    {"raised": "", "type": T, "numeric": true, "value": V}
    {"raised": "", "type": T, "numeric": false, "value": 0}
    {"raised": "<exception>", "type": "", "numeric": false, "value": 0}

The runner compares nothing. The candidate's code runs in this process and can
rewrite what it reports; the Oracle checks the values against expectations
the Evaluation never sees.
"""

import decimal
import json
import math
import numbers
import operator
import os
import sys
from fractions import Fraction

LIMIT = 2**63


def exact(result: object) -> int | float | None:
    """The exact value of a returned number, if an int or a float can hold it.

    Upstream asserts `dotproduct(a, b) == expected`, where every expected value
    is an int or a float. For the number types of Python and NumPy that
    equality compares exact values. So a result is reported as the int or
    float with exactly its value: integers (bool and NumPy integers included)
    through operator.index, other real numbers and Decimal through
    as_integer_ratio, complex numbers with a zero imaginary part through their
    real part, and an array of one element through that element. A value no
    int or float holds exactly (NaN, an infinity, 1/3, an integer beyond 64
    bits) cannot equal any expected value, and neither can a result that is
    not a number; both give None.
    """
    try:
        if isinstance(result, numbers.Integral):
            whole = operator.index(result)
            return whole if -LIMIT < whole < LIMIT else None
        if isinstance(result, numbers.Complex) and not isinstance(result, numbers.Real):
            number = complex(result)
            return exact(number.real) if number.imag == 0 else None
        if isinstance(result, (numbers.Real, decimal.Decimal)):
            top, bottom = result.as_integer_ratio()  # type: ignore[union-attr]
            ratio = Fraction(operator.index(top), operator.index(bottom))
            real = ratio.numerator / ratio.denominator
            if math.isfinite(real) and Fraction(real) == ratio:
                return real
            return None
        # An array of one element, such as NumPy's: upstream's `==` compares
        # that element, and the assertion takes the truth of the result.
        size = getattr(result, "size", None)
        if isinstance(size, int) and size == 1 and callable(getattr(result, "item", None)):
            return exact(result.item())  # type: ignore[attr-defined]
    except Exception:  # a conversion the candidate's type breaks gives no number
        pass
    return None


def text(raised: BaseException) -> str:
    try:
        return f"{type(raised).__name__}: {raised}"[:512]
    except Exception:  # an exception whose str() raises
        return type(raised).__name__[:512]


def main() -> None:
    reply_fd = int(sys.argv[1])
    # Processes the candidate starts must not hold the adapter's pipe.
    os.set_inheritable(reply_fd, False)
    pairs = json.loads(sys.stdin.read())
    with open(reply_fd, "wb", buffering=0) as replies:

        def send(message: dict[str, object]) -> None:
            replies.write(json.dumps(message).encode() + b"\n")

        try:
            import vectorops as v
        except BaseException as raised:  # any exception fails upstream's import
            send({"imported": False, "error": text(raised)})
            return
        send({"imported": True, "error": ""})
        for a, b in pairs:
            try:
                result = v.dotproduct(a, b)
            except BaseException as raised:  # any exception fails upstream's assert
                send({"raised": text(raised), "type": "", "numeric": False, "value": 0})
                continue
            value = exact(result)
            kind = type(result).__qualname__[:128]
            if value is None:
                send({"raised": "", "type": kind, "numeric": False, "value": 0})
            else:
                send({"raised": "", "type": kind, "numeric": True, "value": value})


if __name__ == "__main__":
    main()
