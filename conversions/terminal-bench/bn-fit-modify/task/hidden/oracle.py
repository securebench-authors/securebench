"""Oracle for bn-fit-modify.

The upstream tests read three CSV files with `pandas.read_csv` and check
column names, row and column counts, two edge sets and a one-sample
Kolmogorov-Smirnov test of column D. This Oracle reads the same files as
text, tokenizes them the way pandas' default C parser does for the parts
the tests reach, and judges each file as its tests do. Every expected value
is in `expected.json`.
"""

import math
from collections.abc import Iterable

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

DAG_CHECKS = ("learned-dag", "intervened-dag")
SAMPLE_CHECK = "bn-sample"

# pandas' tokenizer treats only these two characters as blank-line whitespace.
LINE_WHITESPACE = (" ", "\t")
# pandas' number parser skips C `isspace` characters around a number.
NUMBER_WHITESPACE = " \t\n\v\f\r"
DIGITS = "0123456789"
INFINITY_WORDS = ("inf", "+inf", "-inf", "infinity", "+infinity", "-infinity")
INT64_MAX = 2**63 - 1
INT64_MIN = -(2**63)
UINT64_MAX = 2**64 - 1


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if not isinstance(expected, dict):
        raise ValueError("expected.json is not an object")
    contexts = {check: expected[check] for check in (*DAG_CHECKS, SAMPLE_CHECK)}
    return Plan(artifact_contexts=contexts, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, ArtifactEvidence) or len(evidence.files) != 1:
        return _fail("unexpected evidence")
    if not isinstance(context, dict):
        return _fail("malformed context")
    found = evidence.files[0]
    # test_*_exists: the file must exist; pandas must then be able to read it.
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return _fail(f"{found.path} is {found.status.value}")
    # Upstream fails a sample with more rows than expected, so reading can stop
    # there; this bounds the Oracle's memory on the sample file. DAG files are
    # read whole, since upstream accepts repeated edges; their 1 MiB bound
    # keeps them small.
    max_records = context["rows"] + 1 if check_id == SAMPLE_CHECK else None
    table = read_csv(found.value.text, max_records)
    if isinstance(table, str):
        return _fail(f"{found.path} is not readable as CSV: {table}")
    if check_id in DAG_CHECKS:
        return _judge_dag(context, table)
    if check_id == SAMPLE_CHECK:
        return _judge_sample(context, table)
    return _fail("unknown check")


def _judge_dag(context: dict, table: tuple[list[str], list[list[str | None]]]) -> Judgment:
    names, rows = table
    columns = context["columns"]
    # test_*_csv_col_names: not empty, and has the "from" and "to" columns.
    if not rows:
        return _fail("the DAG file has no rows")
    missing = [name for name in columns if name not in names]
    if missing:
        return _fail(f"the DAG file lacks columns {missing}")
    # test_*_structure: the set of (from, to) pairs equals the expected set.
    # Duplicate rows collapse, as they do in upstream's set comprehension.
    positions = [names.index(name) for name in columns]
    edges = {tuple(row[position] for position in positions) for row in rows}
    expected = {tuple(edge) for edge in context["edges"]}
    if edges != expected:
        return _fail("the edge set differs from the expected DAG")
    return Judgment(True, None)


def _judge_sample(context: dict, table: tuple[list[str], list[list[str | None]]]) -> Judgment:
    names, rows = table
    # test_sampled_csv_col_names: not empty, and has every expected column.
    if not rows:
        return _fail("the sample file has no rows")
    missing = [name for name in context["columns"] if name not in names]
    if missing:
        return _fail(f"the sample file lacks columns {missing}")
    # test_sampled_data: row count, column count, then the KS test on D.
    if len(rows) != context["rows"]:
        return _fail(f"the sample has {len(rows)} rows")
    if len(names) != context["column_count"]:
        return _fail(f"the sample has {len(names)} columns")
    # pandas names a repeated header "D.1", so the first "D" is the column read.
    position = names.index(context["ks_column"])
    values = []
    for row in rows:
        value = parse_number(row[position])
        if value is None:
            return _fail("column D holds a value pandas would not read as a number")
        values.append(value)
    if leaves_column_as_text(row[position] for row in rows):
        return _fail("pandas keeps column D as text because of its integers")
    statistic = ks_statistic(values, context["mean"], context["std"])
    # Upstream accepts kstwo.sf(statistic, 10000) >= 0.001. That survival
    # function decreases in the statistic, so the same verdict is a bound on
    # the statistic; derive_expected.py computes the bound with scipy.
    if not statistic <= context["max_statistic"]:
        return _fail(f"KS statistic {statistic} rejects the expected distribution of D")
    return Judgment(True, {"ks_statistic": statistic})


def read_csv(
    text: str, max_records: int | None
) -> tuple[list[str], list[list[str | None]]] | str:
    """The header names and data rows pandas.read_csv(path) would produce.

    Each row has one entry per header name: the field text, or None where
    pandas pads a short row. A string result is the reason pandas would
    raise instead, or the reason the file cannot pass (more records than
    `max_records`, the header included).
    """
    records = tokenize(text, max_records)
    if isinstance(records, str):
        return records
    if not records:
        return "no columns to parse"
    header = records[0]
    width = len(header)
    # When the first data row has more fields than the header, pandas uses the
    # extra leading fields as the index (R's write.table writes one).
    leading = max(len(records[1]) - width, 0) if len(records) > 1 else 0
    expected_fields = width + leading
    rows: list[list[str | None]] = []
    for number, record in enumerate(records[1:], start=2):
        if len(record) > expected_fields:
            return f"expected {expected_fields} fields in record {number}, saw {len(record)}"
        fields: list[str | None] = list(record[leading:])
        fields.extend([None] * (width - len(fields)))
        rows.append(fields)
    return header, rows


def tokenize(text: str, max_records: int | None) -> list[list[str]] | str:
    """Split CSV text into records of fields, as pandas' C tokenizer does.

    Delimiter `,`, quote `"` with doubled quotes inside a quoted field, line
    ends `\\n`, `\\r\\n` or `\\r`, and lines that are empty or hold only spaces
    and tabs skipped. A quote is special only at the start of a field.
    Returns a reason instead once there are more than `max_records` records.
    """
    records: list[list[str]] = []
    record: list[str] = []
    field: list[str] = []
    state = "record"
    position = 0
    length = len(text)
    while position < length:
        char = text[position]
        position += 1
        end_of_line = char in ("\n", "\r")
        if char == "\r" and position < length and text[position] == "\n" and state != "quoted":
            position += 1
        if state == "record":
            if end_of_line:
                continue
            if char in LINE_WHITESPACE:
                field.append(char)
                state = "blank"
                continue
            state = "field-start"
        elif state == "blank":
            if end_of_line:
                field = []
                state = "record"
                continue
            if char in LINE_WHITESPACE:
                field.append(char)
                continue
            state = "field"
        if state == "field-start":
            if end_of_line:
                record.append("")
                records.append(record)
                if max_records is not None and len(records) > max_records:
                    return f"more than {max_records} records"
                record = []
                state = "record"
            elif char == '"':
                state = "quoted"
            elif char == ",":
                record.append("")
            else:
                field.append(char)
                state = "field"
        elif state == "field":
            if end_of_line:
                record.append("".join(field))
                records.append(record)
                if max_records is not None and len(records) > max_records:
                    return f"more than {max_records} records"
                record, field = [], []
                state = "record"
            elif char == ",":
                record.append("".join(field))
                field = []
                state = "field-start"
            else:
                field.append(char)
        elif state == "quoted":
            if char == '"':
                state = "quote-in-quoted"
            else:
                field.append(char)
        elif state == "quote-in-quoted":
            if char == '"':
                field.append('"')
                state = "quoted"
            elif end_of_line:
                record.append("".join(field))
                records.append(record)
                if max_records is not None and len(records) > max_records:
                    return f"more than {max_records} records"
                record, field = [], []
                state = "record"
            elif char == ",":
                record.append("".join(field))
                field = []
                state = "field-start"
            else:
                field.append(char)
                state = "field"
    if state == "quoted":
        return "end of file inside a quoted field"
    if state in ("field", "quote-in-quoted", "field-start"):
        record.append("".join(field))
        records.append(record)
    return records


def parse_number(field: str | None) -> float | None:
    """The float pandas reads from one field of a numeric column, or None.

    None stands for every field that makes pandas' D column non-numeric or
    NaN; either way upstream's KS test fails. Accepted: optional surrounding
    whitespace, a sign, digits with at most one decimal point, an optional
    exponent; or an infinity word with no surrounding whitespace. Integer
    literals of any size are read as doubles, as pandas does once a value
    of the column has made it parse the column as floating point.
    """
    if field is None:
        return None
    if field.lower() in INFINITY_WORDS:
        return -math.inf if field.startswith("-") else math.inf
    body = field.strip(NUMBER_WHITESPACE)
    index = 0
    if body[:1] in ("+", "-"):
        index = 1
    digits = 0
    while index < len(body) and body[index] in DIGITS:
        index += 1
        digits += 1
    if index < len(body) and body[index] == ".":
        index += 1
        while index < len(body) and body[index] in DIGITS:
            index += 1
            digits += 1
    if digits == 0:
        return None
    if index < len(body) and body[index] in ("e", "E"):
        index += 1
        if index < len(body) and body[index] in ("+", "-"):
            index += 1
        exponent_digits = 0
        while index < len(body) and body[index] in DIGITS:
            index += 1
            exponent_digits += 1
        if exponent_digits == 0:
            return None
    if index != len(body):
        return None
    value = float(body)
    # pandas rejects a literal that overflows a double.
    if math.isinf(value):
        return None
    return value


def leaves_column_as_text(fields: Iterable[str]) -> bool:
    """Whether pandas keeps a column of numbers as strings because of its integers.

    pandas first reads a column as integers, row by row. The first value that
    is not an integer literal makes it parse the whole column as doubles. A
    positive integer beyond 2^64 - 1 met before that keeps the column as
    strings. A column of integer literals only is kept as strings when it
    needs both int64 and uint64: a value below -2^63, or a value above
    2^63 - 1 together with a negative one (a "-" sign counts, even on zero).
    Called only when every field is a number `parse_number` accepts.
    """
    negative_seen = False
    above_int64 = False
    below_int64 = False
    for field in fields:
        body = field.strip(NUMBER_WHITESPACE)
        negative = body.startswith("-")
        digits = body[1:] if body[:1] in ("+", "-") else body
        if not digits or any(char not in DIGITS for char in digits):
            return False
        # More than 25 significant digits is beyond every range checked here;
        # testing the length first keeps int() away from very long strings.
        significant = digits.lstrip("0")
        value = UINT64_MAX + 1 if len(significant) > 25 else int(significant or "0")
        if negative:
            negative_seen = True
            below_int64 = below_int64 or -value < INT64_MIN
        elif value > UINT64_MAX:
            return True
        else:
            above_int64 = above_int64 or value > INT64_MAX
    return below_int64 or (above_int64 and negative_seen)


def ks_statistic(values: list[float], mean: float, std: float) -> float:
    """scipy.stats.kstest(values, "norm", args=(mean, std)).statistic."""
    ordered = sorted(values)
    count = len(ordered)
    above = -math.inf
    below = -math.inf
    for rank, value in enumerate(ordered):
        probability = normal_cdf((value - mean) / std)
        above = max(above, (rank + 1) / count - probability)
        below = max(below, probability - rank / count)
    return max(above, below)


def normal_cdf(z: float) -> float:
    """scipy.special.ndtr, following its branches on erf and erfc."""
    x = z * math.sqrt(0.5)
    magnitude = abs(x)
    if magnitude < math.sqrt(0.5):
        return 0.5 + 0.5 * math.erf(x)
    tail = 0.5 * math.erfc(magnitude)
    return 1.0 - tail if x > 0 else tail


def _fail(reason: str) -> Judgment:
    return Judgment(False, {"reason": reason})
