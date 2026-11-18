"""Oracle for model-extraction-relu-logits.

Upstream's single test overwrites forward.py with a network of 30 hidden
neurons built from np.random.seed(5), runs `python3 /app/steal.py`, loads
/app/stolen_A1.npy as b, and requires every row a of the expected A1 to have an
entry s of b (iterating over b's first axis) with

    np.all(np.abs(s / a - np.mean(s / a)) < 1e-4)

Check `steal` has that one case, from hidden/cases.json (derived by
hidden/derive.py). The judge applies the same condition to the same entries,
with numpy's broadcasting and numpy's own arithmetic reproduced, so that it
decides exactly as upstream's test does on the same array (CONVERSION.md,
"Oracle arithmetic").
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

COLUMNS = 10
TOLERANCE = 1e-4
MAX_VALUES = 40960
FIELDS = {
    "ending",
    "exit_status",
    "stderr_tail",
    "file",
    "error",
    "dtype",
    "kind",
    "shape",
    "re",
    "im",
    "nonfinite",
    "ratio_strides",
}
NUMERIC_KINDS = ("b", "i", "u", "f", "c")
# numpy reduces a contiguous float64 or complex128 array in buffers of this
# many elements, summing each pairwise and the buffers in order.
BUFFER = 8192
PAIRWISE_BLOCK = 128
# Veltkamp's splitting constant for float64, 2**27 + 1.
SPLITTER = 134217729.0

type Entry = tuple[list[float], list[float] | None]
# An entry's values, the length of its last axis, and the order in which numpy
# sums its ratios: positions in the C order of `entry / row`, in memory order.
type Stolen = tuple[Entry, int, list[int]]


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    if not isinstance(cases, list) or not cases:
        raise ValueError("hidden/cases.json must be a non-empty array")
    steal = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"name", "seed", "hidden", "a1"}:
            raise ValueError("every case has exactly name, seed, hidden and a1")
        name, network_seed, hidden, a1 = case["name"], case["seed"], case["hidden"], case["a1"]
        if not isinstance(network_seed, int) or not isinstance(hidden, int) or not isinstance(a1, list):
            raise ValueError(f"case {name}: malformed")
        if len(a1) != hidden or not all(_is_row(row) for row in a1):
            raise ValueError(f"case {name}: a1 holds {hidden} rows of {COLUMNS} non-zero numbers")
        steal.append(Case({"seed": network_seed, "hidden": hidden}, {"name": name, "a1": a1}))
    return Plan(artifact_contexts={}, cases={"steal": tuple(steal)})


def _is_row(row: JsonValue) -> bool:
    return (
        isinstance(row, list)
        and len(row) == COLUMNS
        and all(isinstance(value, float) and math.isfinite(value) and value != 0.0 for value in row)
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "steal" or not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": f"unexpected evidence for check {check_id}"})
    name = context["name"]
    outcome = evidence.outcome
    if isinstance(outcome, Unable):
        return Judgment(False, {"case": name, "reason": "unable", "code": outcome.code})
    if not isinstance(outcome, Observed) or not isinstance(outcome.value, dict):
        return Judgment(False, {"case": name, "reason": "no observation"})
    observed = outcome.value
    if set(observed) != FIELDS:
        return Judgment(False, {"case": name, "reason": "observation fields differ from the schema"})
    expected = context["a1"]
    if not isinstance(expected, list) or not expected or not all(_is_row(row) for row in expected):
        return Judgment(False, {"case": name, "reason": "malformed context"})
    stolen = _stolen(observed)
    if isinstance(stolen, str):
        return Judgment(
            False,
            {
                "case": name,
                "reason": stolen,
                "ending": observed["ending"],
                "file": observed["file"],
                "error": observed["error"],
                "dtype": observed["dtype"],
                "shape": observed["shape"],
                "stderr_tail": observed["stderr_tail"],
            },
        )
    if stolen.empty:
        return Judgment(True, None)
    unmatched: list[JsonValue] = []
    for index, row in enumerate(expected):
        original = [float(value) for value in row] if isinstance(row, list) else []
        if not any(_matches(entry, original) for entry in stolen.entries):
            unmatched.append(index)
    if unmatched:
        return Judgment(False, {"case": name, "reason": "rows of A1 with no matching stolen entry", "rows": unmatched})
    return Judgment(True, None)


class _Stolen:
    """The entries of b's first axis that can match, each broadcast against a row of A1."""

    def __init__(self, entries: list[Stolen], empty: bool) -> None:
        self.entries = entries
        # Every entry has no elements, so each matches every row of A1.
        self.empty = empty


def _stolen(observed: dict[str, JsonValue]) -> "_Stolen | str":
    """The array's entries, or why upstream's test fails on it."""
    if observed["ending"] != "exited":
        return "steal.py did not finish in time"
    if observed["file"] != "loaded":
        return "no loadable /app/stolen_A1.npy"
    kind, shape, real, imaginary, nonfinite = (
        observed["kind"],
        observed["shape"],
        observed["re"],
        observed["im"],
        observed["nonfinite"],
    )
    # Upstream's division raises on strings, dates and times; void and object
    # arrays do not load without allow_pickle.
    if kind not in NUMERIC_KINDS:
        return "the array does not hold numbers"
    if not isinstance(shape, list) or not all(isinstance(n, int) and not isinstance(n, bool) for n in shape):
        return "malformed shape"
    # Iterating over a 0-d array raises TypeError.
    if not shape:
        return "the array has no first axis to iterate over"
    entries = shape[0]
    inner = shape[1:]
    if entries == 0:
        return "the array has no entries"
    # Broadcasting an entry against a row of 10 needs a last axis of 1 or 10;
    # anything else raises ValueError on the first comparison.
    if inner and inner[-1] not in (1, COLUMNS):
        return f"entries of shape {tuple(inner)} do not broadcast against a row of {COLUMNS}"
    # A zero anywhere makes every entry empty, however long the other axes are.
    size = 0 if 0 in inner else 1
    for n in inner if size else ():
        size *= n
        if size > MAX_VALUES:
            return "malformed shape"
    complex_values = kind == "c"
    if not isinstance(real, list) or not isinstance(imaginary, list) or not isinstance(nonfinite, list):
        return "malformed values"
    if size == 0:
        # An entry with no elements gives np.all over nothing, which is True, so
        # it matches every row of A1 (np.mean warns and returns NaN, unused).
        if real or imaginary or nonfinite:
            return "values present for an array with no elements"
        return _Stolen([], empty=True)
    if entries * size > MAX_VALUES:
        return "malformed shape"
    if len(real) != entries * size or len(imaginary) != (entries * size if complex_values else 0):
        return "value counts differ from the shape"
    skip: set[int] = set()
    for index in nonfinite:
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < entries or index in skip:
            return "malformed values"
        skip.add(index)
    numbers_real = _numbers(real)
    numbers_imaginary = _numbers(imaginary)
    if numbers_real is None or numbers_imaginary is None:
        return "malformed values"
    last = inner[-1] if inner else 1
    order = _memory_order([*inner[:-1], COLUMNS], observed["ratio_strides"])
    if order is None:
        return "malformed ratio layout"
    kept: list[Stolen] = []
    for index in range(entries):
        # An entry holding inf or NaN gives a non-finite mean or ratio, and no
        # comparison with NaN or inf is below the tolerance.
        if index in skip:
            continue
        start = index * size
        parts = (
            numbers_real[start : start + size],
            numbers_imaginary[start : start + size] if complex_values else None,
        )
        kept.append((parts, last, order))
    return _Stolen(kept, empty=False)


def _memory_order(shape: list[int], strides: JsonValue) -> list[int] | None:
    """C-order positions of an array of this shape, sorted by the offsets these element strides give.

    None unless the strides lay the array out contiguously, one element per
    offset, as a freshly allocated ufunc result always is.
    """
    if not isinstance(strides, list) or len(strides) != len(shape):
        return None
    if not all(isinstance(n, int) and not isinstance(n, bool) for n in strides):
        return None
    offsets = [0]
    for length, stride in zip(shape, strides, strict=True):
        offsets = [offset + index * stride for offset in offsets for index in range(length)]
    count = len(offsets)
    position = [-1] * count
    for c_index, offset in enumerate(offsets):
        if not 0 <= offset < count or position[offset] != -1:
            return None
        position[offset] = c_index
    return position


def _numbers(values: list[JsonValue]) -> list[float] | None:
    numbers = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        numbers.append(float(value))
    return numbers


def _broadcast(values: list[float], last: int) -> list[int]:
    """Indices into one entry's values, in the C order of `entry / row`, whose shape ends in 10."""
    if last == COLUMNS:
        return list(range(len(values)))
    return [position for position in range(len(values)) for _ in range(COLUMNS)]


def _matches(entry: Stolen, original: list[float]) -> bool:
    """Upstream's condition for one entry of b against one row of A1."""
    (real, imaginary), last, memory = entry
    order = _broadcast(real, last)
    if len(memory) != len(order):
        return False
    columns = [original[k % COLUMNS] for k in range(len(order))]
    if imaginary is None:
        ratios = [real[i] / a for i, a in zip(order, columns, strict=True)]
        mean = _sum([ratios[k] for k in memory]) / len(ratios)
        return all(abs(r - mean) < TOLERANCE for r in ratios)
    pairs = [_complex_divide(real[i], imaginary[i], a) for i, a in zip(order, columns, strict=True)]
    total = _complex_sum([pairs[k] for k in memory])
    mean = _complex_divide(total[0], total[1], float(len(pairs)))
    return all(_complex_abs(r - mean[0], i - mean[1]) < TOLERANCE for r, i in pairs)


# numpy's arithmetic for upstream's expression, reproduced so that the decision
# matches numpy 2.2.5 and 2.3.1 bit for bit (CONVERSION.md, "Oracle arithmetic").


def _sum(values: list[float]) -> float:
    """np.add.reduce over a contiguous float64 array, in memory order: pairwise within each buffer, buffers in order."""
    total = 0.0
    for start in range(0, len(values), BUFFER):
        total = total + _pairwise(values[start : start + BUFFER])
    return total


def _pairwise(v: list[float]) -> float:
    """numpy's DOUBLE_pairwise_sum: eight running sums per block of 128, halves above that."""
    n = len(v)
    if n < 8:
        result = -0.0
        for value in v:
            result = result + value
        return result
    if n <= PAIRWISE_BLOCK:
        r = v[:8]
        i = 8
        while i < n - n % 8:
            for j in range(8):
                r[j] = r[j] + v[i + j]
            i += 8
        result = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]))
        while i < n:
            result = result + v[i]
            i += 1
        return result
    half = n // 2
    half -= half % 8
    return _pairwise(v[:half]) + _pairwise(v[half:])


def _complex_sum(pairs: list[tuple[float, float]]) -> tuple[float, float]:
    """np.add.reduce over a contiguous complex128 array, buffered as for float64."""
    real, imaginary = 0.0, 0.0
    for start in range(0, len(pairs), BUFFER):
        chunk = pairs[start : start + BUFFER]
        flat = [part for pair in chunk for part in pair]
        r, i = _complex_pairwise(flat)
        real, imaginary = real + r, imaginary + i
    return real, imaginary


def _complex_pairwise(flat: list[float]) -> tuple[float, float]:
    """numpy's CDOUBLE_pairwise_sum over interleaved real and imaginary parts (n counts both)."""
    n = len(flat)
    if n < 8:
        real, imaginary = -0.0, -0.0
        for i in range(0, n, 2):
            real, imaginary = real + flat[i], imaginary + flat[i + 1]
        return real, imaginary
    if n <= PAIRWISE_BLOCK:
        r = flat[:8]
        i = 8
        while i < n - n % 8:
            for j in range(8):
                r[j] = r[j] + flat[i + j]
            i += 8
        real = (r[0] + r[2]) + (r[4] + r[6])
        imaginary = (r[1] + r[3]) + (r[5] + r[7])
        while i < n:
            real, imaginary = real + flat[i], imaginary + flat[i + 1]
            i += 2
        return real, imaginary
    half = n // 2
    half -= half % 8
    first, second = _complex_pairwise(flat[:half]), _complex_pairwise(flat[half:])
    return first[0] + second[0], first[1] + second[1]


def _complex_divide(real: float, imaginary: float, divisor: float) -> tuple[float, float]:
    """numpy's complex division by (divisor + 0j), which multiplies by a reciprocal."""
    ratio = 0.0 / divisor
    scale = 1.0 / (divisor + 0.0 * ratio)
    return (real + imaginary * ratio) * scale, (imaginary - real * ratio) * scale


def _complex_abs(real: float, imaginary: float) -> float:
    """numpy's vectorized complex absolute value: larger * sqrt(fma(ratio, ratio, 1))."""
    if not (math.isfinite(real) and math.isfinite(imaginary)):
        return math.inf
    larger, smaller = max(abs(real), abs(imaginary)), min(abs(real), abs(imaginary))
    if larger == 0.0:
        return 0.0
    ratio = smaller / larger
    return math.sqrt(_square_plus_one(ratio)) * larger


def _square_plus_one(x: float) -> float:
    """x * x + 1 rounded once, as a fused multiply-add gives it (Dekker's exact product, then fsum)."""
    product = x * x
    split = SPLITTER * x
    high = split - (split - x)
    low = x - high
    error = ((high * high - product) + 2.0 * high * low) + low * low
    return math.fsum((product, error, 1.0))
