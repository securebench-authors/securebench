"""Oracle for adaptive-rejection-sampler.

Upstream's tests/test_outputs.py makes nine tests in one container. Here:

- `ars-file` (artifact check, /app/ars.R): test_ars_function_exists,
  test_implementation_is_modular and test_implementation_handles_errors, the
  same searches written by hand (the judge applies no regular expressions).
- `generate`: test_can_generate_standard_distribution_samples, upstream's
  one call. Mean and standard deviation are computed as R's mean() and sd()
  compute them, in 80-bit long double where R uses it.
- `test-function`: test_has_test_function over every /app/*.R.
- `formal-testing`: test_formal_testing_with_known_truth on the output of
  upstream's run_test.R, then test_sample_files_generated on the files left
  after it, parsed as numpy.loadtxt parses them and summed as numpy sums.
- `validation`: test_input_validation_functionality, upstream's two calls.
- `log-concavity`: test_log_concavity_functionality, upstream's case, which
  passes whenever the call of ars finishes (CONVERSION.md says why).

Each check has upstream's one case. The cases are in hidden/cases.json. The
R test scripts that make upstream's calls are in hidden/tests/, and plan sends
each case its script in the challenge, so evaluation/ holds no test input.
The bounds `generate` applies to upstream's call are in that case's context.
The thresholds below are the ones upstream's tests use.

Every run must end within upstream's timeout, with output that is valid
UTF-8, because upstream decodes it strictly. Claims in the candidate's output
("PASS") count only where upstream's test reads its format (formal-testing).
"""

import math

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

MAX_SAMPLES = 100_000
SHOWN = 16384
ERROR_PATTERNS = ("stop(", "stopifnot(", "trycatch", "if", "warning(")

type Exact = tuple[int, int]
"""An exact binary value m * 2**e."""


# Exact arithmetic for R's long double (x87, 64-bit significand) and double sums.


def _exact(value: float) -> Exact:
    numerator, denominator = value.as_integer_ratio()
    return numerator, 1 - denominator.bit_length()


def _add(a: Exact, b: Exact) -> Exact:
    if a[0] == 0:
        return b
    if b[0] == 0:
        return a
    low = min(a[1], b[1])
    return (a[0] << (a[1] - low)) + (b[0] << (b[1] - low)), low


def _negate(a: Exact) -> Exact:
    return -a[0], a[1]


def _round(a: Exact, bits: int, lowest: int | None = None) -> Exact:
    """Round to `bits` significant bits, ties to even, no bit below 2**lowest."""
    mantissa, exponent = a
    if mantissa == 0:
        return 0, 0
    size = abs(mantissa)
    shift = size.bit_length() - bits
    if lowest is not None and exponent + shift < lowest:
        shift = lowest - exponent
    if shift <= 0:
        return a
    kept = size >> shift
    rest = size - (kept << shift)
    half = 1 << (shift - 1)
    if rest > half or (rest == half and kept & 1):
        kept += 1
    return (kept if mantissa > 0 else -kept), exponent + shift


def _long(a: Exact) -> Exact:
    """Round to x87 long double; R's sums never approach its exponent range."""
    return _round(a, 64)


def _double(a: Exact) -> float:
    mantissa, exponent = _round(a, 53, -1074)
    try:
        return math.ldexp(mantissa, exponent)
    except OverflowError:
        return math.copysign(math.inf, mantissa)


def _long_divide(a: Exact, n: int) -> Exact:
    """a / n in long double; a remainder becomes a sticky bit below the rounding point."""
    mantissa, exponent = a
    if mantissa == 0:
        return 0, 0
    size = abs(mantissa)
    extra = max(0, 68 + n.bit_length() - size.bit_length())
    quotient, remainder = divmod(size << extra, n)
    quotient = (quotient << 1) | (1 if remainder else 0)
    return _long(((quotient if mantissa > 0 else -quotient), exponent - extra - 1))


def _long_mean(values: list[Exact]) -> Exact:
    """R's two-pass long double mean (summary.c rmean, cov.c MEAN), before rounding."""
    n = len(values)
    total: Exact = (0, 0)
    for value in values:
        total = _long(_add(total, value))
    mean = _long_divide(total, n)
    if math.isfinite(_double(mean)):
        correction: Exact = (0, 0)
        for value in values:
            correction = _long(_add(correction, _long(_add(value, _negate(mean)))))
        mean = _long(_add(mean, _long_divide(correction, n)))
    return mean


def r_mean(values: list[float]) -> float:
    """mean(x) in R 4.3.3 for a double vector of finite values."""
    return _double(_long_mean([_exact(value) for value in values]))


def _long_multiply(a: Exact, b: Exact) -> Exact:
    return _long((a[0] * b[0], a[1] + b[1]))


def r_sd(values: list[float]) -> float:
    """sd(x) in R 4.3.3: sqrt of cov.c's variance, whose centre, differences, products and sums are long double."""
    exact = [_exact(value) for value in values]
    centre = _double(_long_mean(exact))
    if not math.isfinite(centre):
        return math.nan
    negative_centre = _negate(_exact(centre))
    total: Exact = (0, 0)
    for value in exact:
        difference = _long(_add(value, negative_centre))
        total = _long(_add(total, _long_multiply(difference, difference)))
    return math.sqrt(_double(_long_divide(total, len(values) - 1)))


# numpy 2.3.3: loadtxt with default arguments, and float64 pairwise sums.


def _pairwise(values: list[float], start: int, n: int) -> float:
    """numpy's pairwise_sum_DOUBLE over values[start:start + n]."""
    if n < 8:
        total = 0.0
        for i in range(start, start + n):
            total += values[i]
        return total
    if n <= 128:
        r = values[start : start + 8]
        i = 8
        while i < n - n % 8:
            for j in range(8):
                r[j] += values[start + i + j]
            i += 8
        total = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]))
        while i < n:
            total += values[start + i]
            i += 1
        return total
    half = n // 2
    half -= half % 8
    return _pairwise(values, start, half) + _pairwise(values, start + half, n - half)


def np_sum(values: list[float]) -> float:
    """np.add.reduce of a contiguous float64 array: the identity plus one pairwise sum."""
    return 0.0 + _pairwise(values, 0, len(values))


def np_mean(values: list[float]) -> float:
    return np_sum(values) / len(values)


def np_std(values: list[float]) -> float:
    mean = np_mean(values)
    squares = [(value - mean) * (value - mean) for value in values]
    return math.sqrt(np_sum(squares) / len(values))


def _lines(text: str) -> list[str]:
    """Universal newlines, as numpy's text-mode read splits them."""
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _float(token: str) -> float | None:
    """numpy's float64 conversion: ASCII decimal, inf or nan, no underscores."""
    if not token.isascii() or "_" in token:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def loadtxt(text: str) -> tuple[list[list[float]], str | None]:
    """np.loadtxt(path) with defaults: '#' comments, any whitespace between columns."""
    rows: list[list[float]] = []
    for number, line in enumerate(_lines(text), 1):
        tokens = line.split("#", 1)[0].split()
        if not tokens:
            continue
        if rows and len(tokens) != len(rows[0]):
            return rows, f"line {number}: the number of columns changed"
        row: list[float] = []
        for token in tokens:
            value = _float(token)
            if value is None:
                return rows, f"line {number}: {token[:40]!r} is not a number"
            row.append(value)
        rows.append(row)
    return rows, None


def _sample_file(evidence: FileEvidence, name: str) -> str | None:
    """Upstream's checks on one existing sample file; the reason it fails, or None."""
    if evidence.status is not FileStatus.PRESENT or not isinstance(evidence.value, Text):
        return f"{name} is {evidence.status.value}"
    rows, error = loadtxt(evidence.value.text)
    if error is not None:
        return f"{name}: {error}"
    flat = [value for row in rows for value in row]
    if len(rows) == 1 and len(rows[0]) == 1:
        return f"{name} holds a single value, a 0-d array without a length"
    length = len(rows[0]) if len(rows) == 1 else len(rows)
    if length < 100:
        return f"{name} holds {length} samples, fewer than 100"
    if name == "normal_samples.txt":
        mean, std = np_mean(flat), np_std(flat)
        if not (abs(mean) < 0.5 and 0.5 < std < 1.5):
            return f"{name}: mean {mean!r}, std {std!r} outside upstream's ranges"
        return None
    if len(rows) > 1 and len(rows[0]) > 1:
        return f"{name} has several columns, whose truth value upstream's all() cannot take"
    if not all(value >= 0 for value in flat):
        return f"{name} holds a negative or NaN sample"
    return None


# The searches upstream makes with regular expressions, written by hand.


def _skip_space(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def has_assignment(text: str, name: str) -> bool:
    """re.search(rf"{name}\\s*<-|{name}\\s*=\\s*function", text) is not None."""
    i = text.find(name)
    while i >= 0:
        j = _skip_space(text, i + len(name))
        if text.startswith("<-", j):
            return True
        if text.startswith("=", j) and text.startswith("function", _skip_space(text, j + 1)):
            return True
        i = text.find(name, i + 1)
    return False


def count_functions(text: str) -> int:
    """len(re.findall(r"<-\\s*function", text)) + len(re.findall(r"=\\s*function", text))."""
    count = 0
    for operator in ("<-", "="):
        i = text.find(operator)
        while i >= 0:
            if text.startswith("function", _skip_space(text, i + len(operator))):
                count += 1
            i = text.find(operator, i + len(operator))
    return count


def _segments(stream: JsonValue) -> list[str]:
    if not isinstance(stream, dict):
        return [""]
    head, tail = stream["head"], stream["tail"]
    if not isinstance(head, str) or not isinstance(tail, str):
        return [""]
    return [head] if tail == "" else [head, tail]


def output_contains(run: dict[str, JsonValue], needle: str, lower: bool) -> bool:
    """Whether `needle` is in stdout + stderr, as far as the adapter showed them."""
    out, err = _segments(run["stdout"]), _segments(run["stderr"])
    # The end of stdout and the start of stderr are adjacent in upstream's output.
    pieces = [*out, *err, out[-1] + err[0]]
    return any(needle in (piece.lower() if lower else piece) for piece in pieces)


def run_problem(run: JsonValue) -> str | None:
    """Upstream fails a run that times out or whose output is not strict UTF-8."""
    if not isinstance(run, dict):
        return "malformed run"
    if run["ending"] != "exited":
        return "the R run timed out (upstream's subprocess timeout)"
    for name in ("stdout", "stderr"):
        stream = run[name]
        if not isinstance(stream, dict) or stream["utf8"] is not True:
            return f"the R run's {name} is not valid UTF-8"
    return None


# Plan.


def plan(resources: HiddenResources, seed: int) -> Plan:
    """The cases in hidden/cases.json. Upstream's tests draw no random values, so the seed is unused.

    A case that names a `script` gets that R test script from hidden/tests/ in
    its challenge, where the adapter runs it: the script holds upstream's
    calls and inputs, which must not sit in evaluation/.
    """
    data = resources.read_json("cases.json")
    if not isinstance(data, dict):
        raise ValueError("cases.json is not an object")
    artifact_contexts, checks = data["artifact_contexts"], data["cases"]
    if not isinstance(artifact_contexts, dict) or not isinstance(checks, dict):
        raise ValueError("cases.json is malformed")
    cases: dict[str, tuple[Case, ...]] = {}
    for check_id, entries in checks.items():
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"cases.json: no cases for {check_id}")
        built = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"cases.json: malformed case of {check_id}")
            challenge = entry["challenge"]
            if not isinstance(challenge, dict):
                raise ValueError(f"cases.json: malformed challenge of {check_id}")
            if "script" in entry:
                script = entry["script"]
                if not isinstance(script, str):
                    raise ValueError(f"cases.json: malformed script of {check_id}")
                challenge = {**challenge, "script": resources.read(script).decode("utf-8")}
            built.append(Case(challenge, entry["context"]))
        cases[check_id] = tuple(built)
    return Plan(artifact_contexts=dict(artifact_contexts), cases=cases)


# Judge.


def _number(value: JsonValue) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _fail(reason: str, **details: JsonValue) -> Judgment:
    return Judgment(False, {"reason": reason, **details})


def _ars_file(evidence: ArtifactEvidence) -> Judgment:
    ars = evidence.files[0]
    if ars.status is not FileStatus.PRESENT or not isinstance(ars.value, Text):
        return _fail(f"/app/ars.R is {ars.status.value}", detail=ars.reason)
    text = ars.value.text
    if not has_assignment(text, "ars"):
        return _fail("no 'ars' assignment in ars.R (test_ars_function_exists)")
    lower = text.lower()
    functions = count_functions(lower)
    if functions < 3:
        return _fail("fewer than 3 function definitions (test_implementation_is_modular)", found=functions)
    patterns = sum(1 for pattern in ERROR_PATTERNS if pattern in lower)
    if patterns < 2:
        return _fail("fewer than 2 error-handling patterns (test_implementation_handles_errors)", found=patterns)
    return Judgment(True, {"functions": functions, "patterns": patterns})


def _generate(context: JsonValue, value: dict[str, JsonValue]) -> Judgment:
    """Upstream's conditions on its call, with its bounds from the case's context
    (hidden/cases.json): at least `min_samples` samples, |mean| below
    `mean_abs_below`, and sd strictly between `sd_above` and `sd_below`."""
    if not isinstance(context, dict):
        return _fail("malformed context")
    problem = run_problem(value["run"])
    if problem is not None:
        return _fail(problem)
    if value["outcome"] != "returned":
        return _fail(f"ars did not return numeric samples: {value['outcome']}")
    count, non_finite, values = value["count"], value["non_finite"], value["values"]
    if not isinstance(count, int) or not isinstance(non_finite, int) or not isinstance(values, list):
        return _fail("malformed observation")
    if count > MAX_SAMPLES:
        return _fail(f"ars returned {count} samples, more than the {MAX_SAMPLES} the adapter reports")
    samples = [number for number in map(_number, values) if number is not None]
    if len(samples) + non_finite != count:
        return _fail("the reported samples do not add up to their count")
    # Upstream's mean() or sd() of a non-finite sample is Inf or NaN, and its
    # comparisons then fail or raise inside its tryCatch.
    if non_finite:
        return _fail(f"{non_finite} samples are not finite")
    if count < context["min_samples"]:
        return _fail(f"ars returned {count} samples, fewer than {context['min_samples']}")
    mean, sd = r_mean(samples), r_sd(samples)
    if not (abs(mean) < context["mean_abs_below"] and sd > context["sd_above"] and sd < context["sd_below"]):
        return _fail("mean or sd outside upstream's ranges", mean=mean, sd=sd)
    return Judgment(True, {"mean": mean, "sd": sd})


def _test_function(value: dict[str, JsonValue]) -> Judgment:
    files = value["files"]
    if not isinstance(files, list):
        return _fail("malformed observation")
    for entry in files:
        if not isinstance(entry, dict):
            return _fail("malformed observation")
        text = entry["text"]
        if entry["kind"] == "file" and entry["utf8"] is True and isinstance(text, str):
            if has_assignment(text, "test"):
                return Judgment(True, {"file": entry["name"]})
    return _fail("no 'test' assignment in the /app/*.R files (test_has_test_function)", count=value["count"])


def _formal_testing(value: dict[str, JsonValue], artifacts: tuple[FileEvidence, ...]) -> Judgment:
    run = value["run"]
    problem = run_problem(run)
    if problem is not None or not isinstance(run, dict):
        return _fail(problem or "malformed run")
    if not (output_contains(run, ": PASS", False) or output_contains(run, ": FAIL", False)):
        return _fail("test() printed no 'TEST_NAME: PASS' or 'TEST_NAME: FAIL'")
    if not output_contains(run, "mean", True):
        return _fail("test() printed no mean statistics")
    files = {evidence.path.rsplit("/", 1)[1]: evidence for evidence in artifacts}
    present = [name for name, evidence in files.items() if evidence.status is not FileStatus.ABSENT]
    if not present:
        return _fail("neither normal_samples.txt nor exponential_samples.txt exists")
    for name in sorted(present, key=lambda name: name != "normal_samples.txt"):
        reason = _sample_file(files[name], name)
        if reason is not None:
            return _fail(reason)
    return Judgment(True, {"sample_files": sorted(present)})


def _validation(value: dict[str, JsonValue]) -> Judgment:
    problem = run_problem(value["run"])
    if problem is not None:
        return _fail(problem)
    outcomes = value["outcomes"]
    if not isinstance(outcomes, list):
        return _fail("malformed observation")
    if "error" not in outcomes:
        return _fail("ars rejected neither invalid call", outcomes=outcomes)
    return Judgment(True, {"outcomes": outcomes})


def _log_concavity(value: dict[str, JsonValue]) -> Judgment:
    """Upstream prints a line containing "PASS" or "concave" whichever way ars ends,
    so it passes whenever the call finishes; the candidate's own mention of
    concavity also passes it. A "PASS" the candidate prints is ignored."""
    run = value["run"]
    problem = run_problem(run)
    if problem is not None or not isinstance(run, dict):
        return _fail(problem or "malformed run")
    if value["outcome"] in ("error", "returned"):
        return Judgment(True, {"outcome": value["outcome"]})
    if output_contains(run, "concave", True):
        return Judgment(True, {"outcome": value["outcome"], "output": "mentions concavity"})
    return _fail("the call of ars did not finish", outcome=value["outcome"])


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if isinstance(evidence, ArtifactEvidence):
        return _ars_file(evidence)
    if not isinstance(evidence.outcome, Observed):
        return _fail("no observation", outcome=str(evidence.outcome)[:500])
    value = evidence.outcome.value
    if not isinstance(value, dict):
        return _fail("malformed observation")
    if check_id == "generate":
        return _generate(context, value)
    if check_id == "test-function":
        return _test_function(value)
    if check_id == "formal-testing":
        return _formal_testing(value, evidence.output_artifacts)
    if check_id == "validation":
        return _validation(value)
    return _log_concavity(value)
