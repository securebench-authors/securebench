"""Oracle for financial-document-processor.

Upstream identifies every document by the hash of its content, because the
image gives the documents random names. The listings here carry the SHA-256 of
each file, and hidden/expected.json holds the SHA-256 of every shipped
document, with every other value upstream's tests compare (hidden/derive.py
reads them all from upstream's tests/test_outputs.py).

One artifact check per upstream concern:

- `invoices`: test_directories_created (for /app/invoices) and
  test_invoices_moved_correctly.
- `other`: test_directories_created (for /app/other) and
  test_other_documents_moved_correctly.
- `summary`: test_summary_csv_exists, test_summary_csv_structure and
  test_summary_csv_content.
- `documents`: test_original_documents_dir_empty.

Every check lists the three folders. Upstream's tests go through the
filesystem, which follows symlinks and resolves `..`; `_Tree.resolve` does the
same over the listings, so a candidate that uses symlinks between the folders
or writes a summary filename such as `./name` gets the verdict upstream gives
it. A path that leads anywhere else fails: nothing outside /app is captured,
the scope drops everything more than two levels below /app, and the framework
lists no other directory of /app (it cannot list a scope root), nor a folder
that is itself a symlink.

The summary is read the way upstream reads it twice: the header and the row
count as `csv.DictReader` gives them (test_summary_csv_structure), the values
as `pd.read_csv` gives them (test_summary_csv_content): pandas' NA strings,
a field cut at its first NUL character, a first column taken as the index when
the first row is longer than the header, and a column read as numbers or as
booleans when all its values are.

The work is bounded: one pass over at most 1 MiB of CSV text, and at most
STEP_BOUND path components resolved per judgment.
"""

from securebench.core.errors import Rejected
from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    EntryKind,
    FileStatus,
    HiddenResources,
    Judgment,
    ListingEntry,
    ListingEvidence,
    ListingStatus,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

APP = "/app"
FOLDERS = ("invoices", "other", "documents")
INVOICES = "/app/invoices"
OTHER = "/app/other"
DOCUMENTS = "/app/documents"
SUMMARY = "/app/invoices/summary.csv"
# test_invoices_moved_correctly skips names ending in ".json".
SKIPPED_SUFFIX = ".json"
# Upstream's tolerance: abs(actual - expected) < 0.01.
TOLERANCE = 0.01
SHOWN = 128
# pandas 2.3.2's default NA strings (pandas._libs.parsers.STR_NA_VALUES).
# upstream reads the CSV with pd.read_csv, which turns these into NaN.
NA_STRINGS = frozenset(
    {
        "",
        "#N/A",
        "#N/A N/A",
        "#NA",
        "-1.#IND",
        "-1.#QNAN",
        "-NaN",
        "-nan",
        "1.#IND",
        "1.#QNAN",
        "<NA>",
        "N/A",
        "NA",
        "NULL",
        "NaN",
        "None",
        "n/a",
        "nan",
        "null",
    }
)
# pandas' C parser: its boolean values and the words it reads as infinity
# (both compared ignoring case), the spaces its number parsers skip, and the
# range of its integer types: an integer outside int64 and uint64 leaves the
# column as text. The range is compared digit by digit, because int() refuses
# texts of more than 4,300 digits, which pandas reads.
TRUE_WORD = "true"
FALSE_WORD = "false"
INT64_MIN_MAGNITUDE = str(2**63)
UINT64_MAX_DIGITS = str(2**64 - 1)
INFINITY_WORDS = frozenset({"inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"})
ASCII_SPACES = " \t\n\v\f\r"
DIGITS = frozenset("0123456789")
# Linux: a path walk follows at most 40 symlinks (ELOOP after that), and a path
# of PATH_MAX bytes or more, or a component of more than NAME_MAX bytes, fails
# with ENAMETOOLONG. Python's is_file() returns False on ELOOP, ENOENT and
# ENOTDIR but raises on ENAMETOOLONG.
MAX_LINKS = 40
PATH_MAX = 4096
NAME_MAX = 255
STEP_BOUND = 1_000_000
# How a path resolves.
FILE = "file"
DIRECTORY = "directory"
MISSING = "missing"
TOO_LONG = "too long"
UNKNOWN = "unknown"
# States of CPython's csv reader (Modules/_csv.c) that the excel dialect
# reaches.
START_RECORD = 0
START_FIELD = 1
IN_FIELD = 2
IN_QUOTED_FIELD = 3
QUOTE_IN_QUOTED_FIELD = 4
EAT_CRNL = 5
# The reader's end-of-line marker, sent after the characters of each line.
EOL = ""
LINE_ENDS = ("\n", "\r", EOL)


class _CsvError(Exception):
    """What `csv.Error` would be raised for."""


class _Bound(Exception):
    """Path resolution went past STEP_BOUND."""


class _Malformed(Exception):
    """The evidence breaks the framework's own rules."""


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if not isinstance(expected, dict) or set(expected) != {"invoices", "other", "summary"}:
        raise Rejected("hidden/expected.json must hold invoices, other and summary")
    invoices = expected["invoices"]
    other = expected["other"]
    summary = expected["summary"]
    if (
        not isinstance(invoices, dict)
        or set(invoices) != {"documents", "names"}
        or not _strings(invoices["documents"])
        or not _strings(invoices["names"])
    ):
        raise Rejected("hidden/expected.json invoices is malformed")
    if not _strings(other):
        raise Rejected("hidden/expected.json other is malformed")
    if (
        not isinstance(summary, dict)
        or set(summary) != {"header", "rows", "total_row", "columns", "amounts"}
        or not _strings(summary["header"])
        or not _strings(summary["columns"])
        or not isinstance(summary["rows"], int)
        or isinstance(summary["rows"], bool)
        or not isinstance(summary["total_row"], str)
        or not isinstance(summary["amounts"], dict)
        or not all(_amounts(v) for v in summary["amounts"].values())
    ):
        raise Rejected("hidden/expected.json summary is malformed")
    columns = summary["columns"]
    header = summary["header"]
    if not isinstance(columns, list) or not isinstance(header, list) or len(columns) != 3:
        raise Rejected("hidden/expected.json summary columns are malformed")
    if not all(column in header for column in columns):
        raise Rejected("hidden/expected.json summary columns are not in the header")
    return Plan(
        artifact_contexts={
            "invoices": invoices,
            "other": other,
            "summary": summary,
            "documents": None,
        },
        cases={},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, ArtifactEvidence):
        return _fail("unexpected evidence")
    files = (SUMMARY,) if check_id == "summary" else ()
    if check_id not in ("invoices", "other", "summary", "documents") or not _shape(
        evidence, files, tuple(f"{APP}/{folder}" for folder in FOLDERS)
    ):
        return _fail("unexpected evidence")
    tree = _Tree(evidence.listings)
    try:
        if check_id == "invoices":
            return _invoices(context, tree)
        if check_id == "other":
            return _other(context, tree)
        if check_id == "summary":
            return _summary(context, evidence, tree)
        return _documents(tree)
    except _Bound:
        return _fail(f"resolving paths took more than {STEP_BOUND} steps")
    except _Malformed:
        return _fail("unexpected evidence")


def _invoices(context: JsonValue, tree: "_Tree") -> Judgment:
    if not isinstance(context, dict):
        return _fail("malformed context")
    documents = context.get("documents")
    names = context.get("names")
    if not isinstance(documents, list) or not isinstance(names, list):
        return _fail("malformed context")
    files = _folder(tree, INVOICES)
    if isinstance(files, str):
        return _fail(files)
    # Upstream counts the regular files not ending in .json, by hash, except
    # summary.csv, which it counts by name.
    by_name = {str(name) for name in names}
    found = {
        name: name if name in by_name else digest
        for name, digest in files.items()
        if not name.endswith(SKIPPED_SUFFIX)
    }
    return _same_set(found, {*(str(d) for d in documents), *by_name})


def _other(context: JsonValue, tree: "_Tree") -> Judgment:
    if not isinstance(context, list):
        return _fail("malformed context")
    files = _folder(tree, OTHER)
    if isinstance(files, str):
        return _fail(files)
    return _same_set(files, {str(item) for item in context})


def _documents(tree: "_Tree") -> Judgment:
    files = _folder(tree, DOCUMENTS)
    if isinstance(files, str):
        return _fail(files)
    if files:
        remaining: list[JsonValue] = [_short(name) for name in sorted(files)[:16]]
        return _fail("files remain in /app/documents", remaining)
    return Judgment(True, None)


def _summary(context: JsonValue, evidence: ArtifactEvidence, tree: "_Tree") -> Judgment:
    if not isinstance(context, dict):
        return _fail("malformed context")
    header = context.get("header")
    count = context.get("rows")
    total_row = context.get("total_row")
    columns = context.get("columns")
    amounts = context.get("amounts")
    if (
        not isinstance(header, list)
        or not isinstance(count, int)
        or not isinstance(total_row, str)
        or not isinstance(columns, list)
        or not isinstance(amounts, dict)
    ):
        return _fail("malformed context")
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        # Absent: test_summary_csv_exists fails. Not UTF-8, or with a
        # byte-order mark: upstream's header differs or decoding raises. A
        # symlink: the framework reads files only at their own path.
        return _fail(f"{SUMMARY} is {found.status.value}")
    # Text mode with universal newlines turns \r\n and lone \r into \n.
    text = found.value.text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        rows, open_quote = _csv_rows(text)
    except _CsvError as error:
        return _fail(f"csv reader error: {error}")
    if open_quote:
        # csv.reader keeps the open field, but pd.read_csv raises "EOF inside
        # string", so upstream's content test fails.
        return _fail("the text ends inside a quoted field")
    # test_summary_csv_structure. csv.DictReader takes the first row, even an
    # empty one, as the header and skips empty rows after it.
    if not rows or rows[0] != header:
        return _fail("wrong header", [_short(field) for field in rows[0][:8]] if rows else None)
    data = [row for row in rows[1:] if row]
    if len(data) != count:
        return _fail(f"expected {count} rows", len(data))
    # test_summary_csv_content.
    table = _pandas_table(len(header), data)
    if isinstance(table, str):
        return _fail(table)
    if len(table) != len(amounts):
        return _fail(f"expected {len(amounts)} rows", len(table))
    filename_at, total_at, vat_at = (header.index(column) for column in columns)
    if _column_kind([row[filename_at] for row in table]) != "text":
        # Path / <number or bool> raises TypeError.
        return _fail("pandas reads the filename column as numbers or booleans")
    totals = _numbers([row[total_at] for row in table])
    vats = _numbers([row[vat_at] for row in table])
    for index, row in enumerate(table):
        verdict = _row(row[filename_at], totals[index], vats[index], tree, total_row, amounts)
        if verdict is not None:
            return _fail(verdict, {"row": index + 1, "fields": [_short(str(f)) for f in row[:4]]})
    return Judgment(True, None)


def _row(
    filename: str | None,
    got_total: float | str | None,
    got_vat: float | str | None,
    tree: "_Tree",
    total_row: str,
    amounts: dict[str, JsonValue],
) -> str | None:
    """Why one row fails upstream's loop body, or None."""
    if filename is None:
        return "missing filename"
    if filename == total_row:
        identity = filename
    else:
        kind, digest = tree.resolve(_join(INVOICES, filename))
        if kind == UNKNOWN:
            return "filename leads to a path SecureBench does not see"
        if kind != FILE or not isinstance(digest, str):
            return "filename names no regular file"
        identity = digest
    expected = amounts.get(identity)
    if not isinstance(expected, dict):
        return "filename names a file that is not an invoice"
    expected_total = expected.get("total_amount")
    expected_vat = expected.get("vat_amount")
    # Upstream: an empty expected VAT, or a NaN or empty actual one, counts as 0.
    if expected_vat == "":
        expected_vat = 0
    if (
        not isinstance(expected_total, (int, float))
        or isinstance(expected_total, bool)
        or not isinstance(expected_vat, (int, float))
        or isinstance(expected_vat, bool)
    ):
        return "malformed context"
    if got_total is None:
        return "missing total_amount"
    if isinstance(got_total, str):
        return f"total_amount is not a number: {got_total}"
    if isinstance(got_vat, str):
        return f"vat_amount is not a number: {got_vat}"
    if not abs(got_total - expected_total) < TOLERANCE:
        return "wrong total_amount"
    if not abs((0.0 if got_vat is None else got_vat) - expected_vat) < TOLERANCE:
        return "wrong vat_amount"
    return None


def _pandas_table(width: int, data: list[list[str]]) -> list[list[str | None]] | str:
    """The cells `pd.read_csv` gives for the data rows, None for NaN, or why it raises.

    When the first row has more fields than the header, pandas takes the extra
    leading fields as the index; a later row longer than the first raises, and
    a shorter row is filled with NaN. pandas' tokenizer ends a field at its
    first NUL character.
    """
    longest = max(width, len(data[0])) if data else width
    index_fields = longest - width
    table: list[list[str | None]] = []
    for row in data:
        if len(row) > longest:
            return f"a row has {len(row)} fields, more than the {longest} pandas expects"
        cells: list[str | None] = []
        for field in row[index_fields:]:
            cell = field.partition("\x00")[0]
            cells.append(None if cell in NA_STRINGS else cell)
        cells.extend([None] * (width - len(cells)))
        table.append(cells)
    return table


def _column_kind(values: list[str | None]) -> str:
    """The type pandas infers for a column: numbers, booleans or text."""
    present = [value for value in values if value is not None]
    if all(_pandas_number(value) for value in present):
        # An empty or all-NaN column is float64 too.
        return "number"
    if all(value.lower() in (TRUE_WORD, FALSE_WORD) for value in present):
        return "bool"
    return "text"


def _numbers(values: list[str | None]) -> list[float | str | None]:
    """Each cell as upstream's float() of it sees it: None for NaN, the text when
    float() raises."""
    if _column_kind(values) == "bool":
        return [None if value is None else float(value.lower() == TRUE_WORD) for value in values]
    result: list[float | str | None] = []
    for value in values:
        if value is None:
            result.append(None)
            continue
        try:
            result.append(float(value))
        except ValueError:
            result.append(_short(value))
    return result


def _pandas_number(text: str) -> bool:
    """Whether pandas' C parser reads `text` as a number (int64, uint64 or
    precise_xstrtod, then its words for infinity)."""
    if text.lower() in INFINITY_WORDS:
        return True
    stripped = text.strip(ASCII_SPACES)
    body = stripped[1:] if stripped[:1] in ("+", "-") else stripped
    if body and set(body) <= DIGITS:
        digits = body.lstrip("0") or "0"
        bound = INT64_MIN_MAGNITUDE if stripped[0] == "-" else UINT64_MAX_DIGITS
        return len(digits) < len(bound) or (len(digits) == len(bound) and digits <= bound)
    exponent = ""
    for marker in ("e", "E"):
        if marker in body:
            body, _, exponent = body.partition(marker)
            if exponent[:1] in ("+", "-"):
                exponent = exponent[1:]
            if not exponent or not set(exponent) <= DIGITS:
                return False
            break
    whole, _, fraction = body.partition(".")
    if not set(whole) <= DIGITS or not set(fraction) <= DIGITS or not (whole or fraction):
        return False
    # A number too large for a double makes precise_xstrtod report ERANGE.
    return abs(float(stripped)) != float("inf")


def _folder(tree: "_Tree", path: str) -> dict[str, str] | str:
    """The regular files in the directory at `path` as upstream's iterdir() and
    is_file() find them, name to SHA-256, or why iterdir() would raise."""
    kind, location = tree.resolve(path)
    if kind == UNKNOWN:
        return f"{path} leads to a path SecureBench does not see"
    if kind != DIRECTORY or not isinstance(location, tuple):
        return f"{path} is not a directory"
    names = tree.names(location)
    if names is None:
        return f"{path} leads to a directory SecureBench does not list"
    base = "/" + "/".join(location)
    files: dict[str, str] = {}
    for name in names:
        kind, digest = tree.resolve(f"{base}/{name}")
        if kind == UNKNOWN:
            return f"{path}/{_short(name)} leads to a path SecureBench does not see"
        if kind == TOO_LONG:
            return f"{path}/{_short(name)} leads to a name too long, so is_file() raises"
        if kind == FILE and isinstance(digest, str):
            files[name] = digest
    return files


def _join(directory: str, name: str) -> str:
    """`str(Path(directory) / name)`: an absolute name replaces the directory, and
    empty and "." components are dropped."""
    joined = name if name.startswith("/") else f"{directory}/{name}"
    return "/" + "/".join(part for part in joined.split("/") if part not in ("", "."))


class _Tree:
    """What the listings of the three folders show of the filesystem."""

    def __init__(self, listings: tuple[ListingEvidence, ...]) -> None:
        # Per folder: its listing's status, its entries by path relative to it,
        # and the names in each of its directories ("" for the folder itself).
        self.status: dict[str, ListingStatus] = {}
        self.entries: dict[str, dict[str, ListingEntry]] = {}
        self.children: dict[str, dict[str, list[str]]] = {}
        self.steps = 0
        for folder, listing in zip(FOLDERS, listings, strict=True):
            self.status[folder] = listing.status
            entries: dict[str, ListingEntry] = {}
            children: dict[str, list[str]] = {}
            for entry in listing.entries:
                entries[entry.path] = entry
                parent, _, name = entry.path.rpartition("/")
                children.setdefault(parent, []).append(name)
            self.entries[folder] = entries
            self.children[folder] = children

    def entry(self, location: tuple[str, ...]) -> ListingEntry | str | None:
        """DIRECTORY for /, /app and a listed folder, UNKNOWN for a path no
        listing shows, the listing's entry, or None when the path is absent."""
        if not location or location == ("app",):
            return DIRECTORY
        if location[0] != "app" or location[1] not in FOLDERS:
            return UNKNOWN
        status = self.status[location[1]]
        if status is ListingStatus.ABSENT:
            return None
        if status is not ListingStatus.PRESENT:
            # Not a directory (a file or a symlink, which a listing does not
            # tell apart) or too many entries.
            return UNKNOWN
        if len(location) == 2:
            return DIRECTORY
        return self.entries[location[1]].get("/".join(location[2:]))

    def names(self, location: tuple[str, ...]) -> list[str] | None:
        """The names in a directory inside a listed folder, or None for any other."""
        if len(location) < 2 or location[0] != "app" or location[1] not in FOLDERS:
            return None
        if self.status[location[1]] is not ListingStatus.PRESENT:
            return None
        return self.children[location[1]].get("/".join(location[2:]), [])

    def resolve(self, path: str) -> tuple[str, str | tuple[str, ...] | None]:
        """What `open` or `stat` of an absolute path reaches, following every
        symlink as Linux does: (FILE, sha256), (DIRECTORY, location),
        (MISSING, None) for the errors is_file() ignores, (TOO_LONG, None) for
        ENAMETOOLONG, or (UNKNOWN, None)."""
        if len(_encoded(path)) >= PATH_MAX:
            return TOO_LONG, None
        pending = path.split("/")[::-1]
        location: tuple[str, ...] = ()
        links = 0
        while pending:
            self.steps += 1
            if self.steps > STEP_BOUND:
                raise _Bound
            part = pending.pop()
            if part in ("", "."):
                continue
            if len(_encoded(part)) > NAME_MAX:
                return TOO_LONG, None
            if part == "..":
                location = location[:-1]
                continue
            here = (*location, part)
            found = self.entry(here)
            if found == UNKNOWN:
                return UNKNOWN, None
            if found is None:
                return MISSING, None
            if found == DIRECTORY:
                location = here
                continue
            if not isinstance(found, ListingEntry):
                raise _Malformed
            if found.kind is EntryKind.DIR:
                location = here
            elif found.kind is EntryKind.SYMLINK:
                links += 1
                if links > MAX_LINKS or not found.target:
                    return MISSING, None
                if found.target.startswith("/"):
                    location = ()
                pending.extend(found.target.split("/")[::-1])
            else:
                if pending:
                    # A component after a regular file: ENOTDIR.
                    return MISSING, None
                if found.sha256 is None:
                    raise _Malformed
                return FILE, found.sha256
        return DIRECTORY, location


def _same_set(found: dict[str, str], expected: set[str]) -> Judgment:
    """Upstream compares sets: `found` maps each counted name to its digest
    (or to its name), and its values must be exactly `expected`."""
    if set(found.values()) == expected:
        return Judgment(True, None)
    unexpected: list[JsonValue] = [
        _short(name) for name, token in sorted(found.items()) if token not in expected
    ]
    return _fail(
        "wrong documents",
        {
            "missing": len(expected - set(found.values())),
            "unexpected": unexpected[:16],
        },
    )


def _shape(evidence: ArtifactEvidence, files: tuple[str, ...], listings: tuple[str, ...]) -> bool:
    return (
        tuple(found.path for found in evidence.files) == files
        and tuple(listing.path for listing in evidence.listings) == listings
    )


def _strings(value: JsonValue) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _number_value(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _amounts(value: JsonValue) -> bool:
    if not isinstance(value, dict) or set(value) != {"total_amount", "vat_amount"}:
        return False
    vat = value["vat_amount"]
    return _number_value(value["total_amount"]) and (vat == "" or _number_value(vat))


def _encoded(text: str) -> bytes:
    """The bytes the kernel sees for a name or path."""
    return text.encode("utf-8", "surrogateescape")


def _short(text: str) -> str:
    return text if len(text) <= SHOWN else text[:SHOWN] + "..."


def _fail(reason: str, detail: JsonValue = None) -> Judgment:
    return Judgment(False, {"reason": reason, "detail": detail})


def _lines(text: str) -> list[str]:
    """The lines a text-mode file iterates over: each keeps its \\n, the last may lack one."""
    pieces = text.split("\n")
    lines = [piece + "\n" for piece in pieces[:-1]]
    if pieces[-1]:
        lines.append(pieces[-1])
    return lines


def _csv_rows(text: str) -> tuple[list[list[str]], bool]:
    """The rows `csv.reader` yields over the lines of `text` (excel dialect, not
    strict), and whether the text ends inside a quoted field."""
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
                return rows, state == IN_QUOTED_FIELD
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
        field.append(character)
        return IN_FIELD
    if state == IN_FIELD:
        if character in LINE_ENDS:
            _save(fields, field)
            return START_RECORD if character == EOL else EAT_CRNL
        if character == ",":
            _save(fields, field)
            return START_FIELD
        field.append(character)
        return IN_FIELD
    if state == IN_QUOTED_FIELD:
        if character == EOL:
            return IN_QUOTED_FIELD
        if character == '"':
            return QUOTE_IN_QUOTED_FIELD
        field.append(character)
        return IN_QUOTED_FIELD
    if state == QUOTE_IN_QUOTED_FIELD:
        if character == '"':
            field.append(character)
            return IN_QUOTED_FIELD
        if character == ",":
            _save(fields, field)
            return START_FIELD
        if character in LINE_ENDS:
            _save(fields, field)
            return START_RECORD if character == EOL else EAT_CRNL
        field.append(character)
        return IN_FIELD
    # EAT_CRNL
    if character in ("\n", "\r"):
        return EAT_CRNL
    if character == EOL:
        return START_RECORD
    raise _CsvError("new-line character seen in unquoted field")
