"""Oracle for rstan-to-pystan.

Upstream's tests/test_outputs.py reads the four result files the agent's
PyStan run left in /app and checks each posterior mean against a fixed range.
One artifact check per file reproduces one upstream test. The files are read
as upstream reads them: strict UTF-8 text with universal newlines (Python's
`open()` in text mode), then `strip()`, `split(",")` and `float()` for alpha
and sigma, and the first field of every non-empty `csv.reader` row for rho and
beta. The csv module is not available to an Oracle, so `_csv_rows` follows
CPython's reader for the default (excel) dialect, including its default
field size limit, past which `csv.reader` raises and upstream's test fails;
CONVERSION.md records the differential test against `csv.reader`.

Upstream's ranges are in hidden/ranges.json, one [low, high] pair per value in
the order of the file's rows. `plan` gives each check its list of ranges as
its context.
"""

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

# The checks, and how upstream reads each file: alpha and sigma as one number,
# rho and beta as csv rows.
CHECKS = ("alpha", "sigma", "rho", "beta")
SCALARS = ("alpha", "sigma")

# States of CPython's csv reader (Modules/_csv.c) that the excel dialect reaches.
START_RECORD = 0
START_FIELD = 1
IN_FIELD = 2
IN_QUOTED_FIELD = 3
QUOTE_IN_QUOTED_FIELD = 4
EAT_CRNL = 5
# The reader's end-of-line marker, sent after the characters of each line.
EOL = ""
LINE_ENDS = ("\n", "\r", EOL)
# csv.field_size_limit()'s default, which upstream's test does not change.
FIELD_LIMIT = 131072


class _CsvError(Exception):
    """What `csv.Error` would be raised for."""


def plan(resources: HiddenResources, seed: int) -> Plan:
    ranges = resources.read_json("ranges.json")
    if not isinstance(ranges, dict) or set(ranges) != set(CHECKS):
        raise ValueError("ranges.json must give ranges for exactly the four checks")
    return Plan(artifact_contexts={check: ranges[check] for check in CHECKS}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, ArtifactEvidence) or check_id not in CHECKS:
        return Judgment(False, {"reason": "unexpected evidence"})
    ranges = _ranges(context)
    if ranges is None:
        return Judgment(False, {"reason": "malformed context"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        # Upstream's open() fails on an absent file, and its strict UTF-8
        # decoding on undecodable text.
        return Judgment(False, {"reason": f"{found.path} is {found.status.value}"})
    # Text mode with universal newlines turns \r\n and lone \r into \n.
    text = found.value.text.replace("\r\n", "\n").replace("\r", "\n")
    if check_id in SCALARS:
        values = _scalar(text)
    else:
        values = _first_fields(text)
    if isinstance(values, str):
        return Judgment(False, {"reason": values})
    if len(values) != len(ranges):
        return Judgment(False, {"reason": f"expected {len(ranges)} values", "got": len(values)})
    for index, (value, (low, high)) in enumerate(zip(values, ranges, strict=True)):
        # NaN fails both comparisons, as it fails upstream's chained comparison.
        if not low <= value <= high:
            return Judgment(
                False, {"reason": "outside range", "index": index, "value": repr(value)}
            )
    return Judgment(True, None)


def _ranges(context: JsonValue) -> list[tuple[float, float]] | None:
    """The context's [low, high] pairs, or None if it is not a non-empty list of them."""
    if not isinstance(context, list) or not context:
        return None
    ranges: list[tuple[float, float]] = []
    for pair in context:
        if not isinstance(pair, list) or len(pair) != 2:
            return None
        low, high = pair
        for bound in (low, high):
            if isinstance(bound, bool) or not isinstance(bound, (int, float)):
                return None
        ranges.append((low, high))
    return ranges


def _scalar(text: str) -> list[float] | str:
    """Upstream: `content = read().strip()`, non-empty, `float(content.split(",")[0].strip())`."""
    content = text.strip()
    if not content:
        return "file is empty"
    try:
        return [float(content.split(",")[0].strip())]
    except ValueError:
        return "first value does not parse as a float"


def _first_fields(text: str) -> list[float] | str:
    """Upstream: `float(row[0].strip())` for every non-empty row of `csv.reader(f)`."""
    try:
        rows = _csv_rows(text)
    except _CsvError as error:
        return f"csv reader error: {error}"
    values: list[float] = []
    for row in rows:
        if row:
            try:
                values.append(float(row[0].strip()))
            except ValueError:
                return "a row does not start with a float"
    return values


def _lines(text: str) -> list[str]:
    """The lines a text-mode file iterates over: each keeps its \\n, the last may lack one."""
    pieces = text.split("\n")
    lines = [piece + "\n" for piece in pieces[:-1]]
    if pieces[-1]:
        lines.append(pieces[-1])
    return lines


def _csv_rows(text: str) -> list[list[str]]:
    """The rows `csv.reader` yields over the lines of `text` (excel dialect, not strict)."""
    rows: list[list[str]] = []
    lines = _lines(text)
    index = 0
    while True:
        fields: list[str] = []
        field: list[str] = []
        state = START_RECORD
        while True:
            if index == len(lines):
                # End of input: a pending field ends the record; otherwise iteration stops.
                if field or state == IN_QUOTED_FIELD:
                    fields.append("".join(field))
                    rows.append(fields)
                return rows
            for character in lines[index]:
                state = _step(state, character, fields, field)
            index += 1
            state = _step(state, EOL, fields, field)
            if state == START_RECORD:
                break
        rows.append(fields)


def _save(fields: list[str], field: list[str]) -> None:
    fields.append("".join(field))
    field.clear()


def _add(field: list[str], character: str) -> None:
    """CPython's `parse_add_char`: a field may not grow past the field size limit."""
    if len(field) >= FIELD_LIMIT:
        raise _CsvError(f"field larger than field limit ({FIELD_LIMIT})")
    field.append(character)


def _step(state: int, character: str, fields: list[str], field: list[str]) -> int:
    """One call of CPython's `parse_process_char` for the excel dialect, not strict."""
    if state == START_RECORD:
        if character == EOL:
            return START_RECORD
        if character in ("\n", "\r"):
            return EAT_CRNL
        state = START_FIELD
    if state == START_FIELD:
        if character in LINE_ENDS:
            _save(fields, field)
            return START_RECORD if character == EOL else EAT_CRNL
        if character == '"':
            return IN_QUOTED_FIELD
        if character == ",":
            _save(fields, field)
            return START_FIELD
        _add(field, character)
        return IN_FIELD
    if state == IN_FIELD:
        if character in LINE_ENDS:
            _save(fields, field)
            return START_RECORD if character == EOL else EAT_CRNL
        if character == ",":
            _save(fields, field)
            return START_FIELD
        _add(field, character)
        return IN_FIELD
    if state == IN_QUOTED_FIELD:
        if character == EOL:
            return IN_QUOTED_FIELD
        if character == '"':
            return QUOTE_IN_QUOTED_FIELD
        _add(field, character)
        return IN_QUOTED_FIELD
    if state == QUOTE_IN_QUOTED_FIELD:
        if character == '"':
            _add(field, character)
            return IN_QUOTED_FIELD
        if character == ",":
            _save(fields, field)
            return START_FIELD
        if character in LINE_ENDS:
            _save(fields, field)
            return START_RECORD if character == EOL else EAT_CRNL
        _add(field, character)
        return IN_FIELD
    # EAT_CRNL
    if character in ("\n", "\r"):
        return EAT_CRNL
    if character == EOL:
        return START_RECORD
    raise _CsvError("new-line character seen in unquoted field")
