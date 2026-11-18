"""Oracle for distribution-search.

Upstream's four tests load /app/dist.npy and require:

- `P.ndim == 1` and `P.size` equal to the expected vocabulary;
- every element finite, `P.min() > 0`, `P.max() <= 1.0`, and
  `abs(P.sum() - 1.0) < 1e-5`;
- after `P = P / P.sum()`, KL(P||U) and KL(U||P) within the tolerance of their
  targets, with KL(P||U) = sum(P * log P) + log V and
  KL(U||P) = -log V - (1/V) sum(log P).

Every literal of those assertions (shape, bounds, targets, tolerances) is in
hidden/cases.json, which `plan` turns into the one case's context. The judge
applies the conditions to the values the adapter reports. It repeats numpy's
float64 arithmetic: np.sum is numpy's pairwise summation, reproduced below (in
buffers of 8,192 elements for a big-endian array, which numpy byte-swaps buffer
by buffer), and every other step is one IEEE operation or a natural logarithm.
float32 and long double files are judged the same way on their values as
float64, where upstream computes in their own precision. CONVERSION.md records
the differential test against numpy 2.3.0, the version upstream's verifier
installs (hidden/differential.py).
"""

import math

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Unable,
)
from securebench.core.jsondata import JsonValue

# The adapter reports the values in rows of this many elements.
ROW = 1_000
# What np.save writes for float64, float32 and x86-64 long double arrays, in
# either byte order. The judge reimplements only real floating-point
# arithmetic; CONVERSION.md says what this means for other dtypes.
FLOATING = frozenset({"<f8", ">f8", "<f4", ">f4", "<f16", ">f16"})
FIELDS = frozenset({"dtype", "shape", "nonfinite", "values"})
BOUNDS = (
    "minimum_exclusive",
    "maximum",
    "sum",
    "sum_tolerance",
    "forward_kl",
    "backward_kl",
    "kl_tolerance",
)
EXPECTED = frozenset({"shape", *BOUNDS})
# numpy's PW_BLOCKSIZE and unroll factor for pairwise summation, and its
# default ufunc buffer size.
BLOCK = 128
UNROLL = 8
BUFFER = 8192
# A float64 array that numpy must byte-swap before summing.
SWAPPED = ">f8"


def plan(resources: HiddenResources, seed: int) -> Plan:
    entries = resources.read_json("cases.json")
    if not isinstance(entries, list) or not entries:
        raise ValueError("hidden/cases.json must be a non-empty list")
    cases = []
    for entry in entries:
        if not isinstance(entry, dict) or frozenset(entry) != {"challenge", "expected"}:
            raise ValueError("each case needs exactly a challenge and an expected value")
        if _expected(entry["expected"]) is None:
            raise ValueError("malformed expected value in hidden/cases.json")
        cases.append(Case(entry["challenge"], entry["expected"]))
    return Plan(artifact_contexts={}, cases={"distribution": tuple(cases)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "distribution" or not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": f"unexpected evidence for check {check_id}"})
    expected = _expected(context)
    if expected is None:
        return Judgment(False, {"reason": "malformed context"})
    outcome = evidence.outcome
    if isinstance(outcome, Unable):
        return Judgment(
            False, {"reason": "unable", "code": outcome.code, "message": outcome.message}
        )
    if not isinstance(outcome, Observed) or not isinstance(outcome.value, dict):
        return Judgment(False, {"reason": "no observation"})
    observed = outcome.value
    if frozenset(observed) != FIELDS:
        found: list[JsonValue] = [*sorted(observed)]
        return Judgment(False, {"reason": "observation fields", "found": found})
    dtype, shape, nonfinite, rows = (
        observed["dtype"],
        observed["shape"],
        observed["nonfinite"],
        observed["values"],
    )
    if dtype not in FLOATING:
        return Judgment(
            False, {"reason": "dtype is not float64, float32 or long double", "dtype": dtype}
        )
    if shape != expected["shape"]:
        return Judgment(
            False, {"reason": "shape differs", "shape": shape, "expected": expected["shape"]}
        )
    if nonfinite != 0:
        return Judgment(False, {"reason": "non-finite elements", "count": nonfinite})
    size = expected["shape"][0]
    values = _flatten(rows, size)
    if values is None:
        return Judgment(False, {"reason": f"values are not {size} floats in rows of {ROW}"})
    return _distribution(values, expected, swapped=dtype == SWAPPED)


def _expected(context: JsonValue) -> dict | None:
    """The context as upstream's literals, or None when it is not well formed."""
    if not isinstance(context, dict) or frozenset(context) != EXPECTED:
        return None
    shape = context["shape"]
    if not isinstance(shape, list) or len(shape) != 1 or type(shape[0]) is not int or shape[0] < 1:
        return None
    for name in BOUNDS:
        if type(context[name]) is not float or not math.isfinite(context[name]):
            return None
    return context


def _flatten(rows: JsonValue, size: int) -> list[float] | None:
    """The adapter's rows of ROW values, the last one shorter, as one list of `size` floats."""
    if not isinstance(rows, list) or len(rows) != -(-size // ROW):
        return None
    values: list[float] = []
    for index, row in enumerate(rows):
        length = min(ROW, size - index * ROW)
        if not isinstance(row, list) or len(row) != length:
            return None
        for value in row:
            if type(value) is not float or not math.isfinite(value):
                return None
            values.append(value)
    return values


def _distribution(values: list[float], expected: dict, swapped: bool) -> Judgment:
    smallest, largest = min(values), max(values)
    if not smallest > expected["minimum_exclusive"]:
        return Judgment(False, {"reason": "an element is not above the minimum", "min": smallest})
    if not largest <= expected["maximum"]:
        return Judgment(False, {"reason": "an element exceeds the maximum", "max": largest})
    total = buffered_sum(values) if swapped else pairwise_sum(values)
    if not abs(total - expected["sum"]) < expected["sum_tolerance"]:
        return Judgment(False, {"reason": "sum is outside the tolerance", "sum": total})
    normalized = [value / total for value in values]
    # A subnormal element can round to 0 here. Upstream's np.log then gives
    # -inf, so a divergence is infinite or NaN and its test fails; math.log
    # would raise instead.
    if not min(normalized) > 0.0:
        return Judgment(False, {"reason": "an element is 0 after normalization"})
    logs = [math.log(value) for value in normalized]
    size = len(values)
    log_size = math.log(size)
    forward = (
        pairwise_sum([value * log for value, log in zip(normalized, logs, strict=True)]) + log_size
    )
    backward = -log_size - (1.0 / size) * pairwise_sum(logs)
    measured: JsonValue = {
        "sum": total,
        "min": smallest,
        "max": largest,
        "forward": forward,
        "backward": backward,
    }
    if not abs(forward - expected["forward_kl"]) <= expected["kl_tolerance"]:
        return Judgment(
            False, {"reason": "KL(P||U) is outside the tolerance", "measured": measured}
        )
    if not abs(backward - expected["backward_kl"]) <= expected["kl_tolerance"]:
        return Judgment(
            False, {"reason": "KL(U||P) is outside the tolerance", "measured": measured}
        )
    return Judgment(True, {"measured": measured})


def pairwise_sum(values: list[float]) -> float:
    """np.add.reduce over a contiguous float64 array: numpy's pairwise_sum_DOUBLE."""
    return _pairwise(values, 0, len(values))


def buffered_sum(values: list[float]) -> float:
    """np.add.reduce over a byte-swapped float64 array: each buffer pairwise, then in order."""
    total = 0.0
    for start in range(0, len(values), BUFFER):
        total += _pairwise(values, start, min(BUFFER, len(values) - start))
    return total


def _pairwise(values: list[float], start: int, count: int) -> float:
    if count < UNROLL:
        total = 0.0
        for index in range(start, start + count):
            total += values[index]
        return total
    if count <= BLOCK:
        partial = values[start : start + UNROLL]
        end = start + count - count % UNROLL
        for index in range(start + UNROLL, end, UNROLL):
            for lane in range(UNROLL):
                partial[lane] += values[index + lane]
        total = ((partial[0] + partial[1]) + (partial[2] + partial[3])) + (
            (partial[4] + partial[5]) + (partial[6] + partial[7])
        )
        for index in range(end, start + count):
            total += values[index]
        return total
    half = count // 2
    half -= half % UNROLL
    return _pairwise(values, start, half) + _pairwise(values, start + half, count - half)
