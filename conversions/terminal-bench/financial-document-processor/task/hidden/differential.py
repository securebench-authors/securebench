"""Differential test of the Oracle against upstream's tests.

Not used by the Oracle. It documents how CONVERSION.md's tables were made.
Upstream's verifier runs Python 3.13 with pandas 2.3.2 and pytest 8.4.1; we
install those into a scratch directory once (with network) and then run every
comparison with no network:

    docker run --rm --memory 2g -v <lib>:/pylib python:3.13-slim \\
      pip install --target /pylib pandas==2.3.2 pytest==8.4.1
    docker run --rm --network none --memory 2g -e PYTHONPATH=/pylib \\
      -v <lib>:/pylib:ro -v "$PWD":/repo:ro \\
      -v "$PWD"/conversions/upstream/terminal-bench/financial-document-processor:/up:ro \\
      python:3.13-slim python3 -B \\
      /repo/conversions/terminal-bench/financial-document-processor/task/hidden/differential.py \\
      <mode>

from the repository root, with <mode> one of:

    layouts   For every case below, builds the case's /app (the shipped
              documents placed in /app/invoices, /app/other and /app/documents,
              and a summary.csv), runs upstream's seven test functions verbatim
              (/up/tests/test_outputs.py), and judges the same tree with the
              Oracle: the three listings built as the framework builds them
              for this pack (direct children only, because the scope drops
              */*/*; a folder that is a symlink is `not_directory`), the
              summary through the framework's `text` parser binding, and
              `plan` and `judge` of hidden/oracle.py loaded as the Oracle
              worker loads it. Prints one line per case: name, upstream
              verdict, Oracle verdict.
    values    Compares, for numbers near each expected value, upstream's
              `abs(float(x) - expected) < 0.01` on the value pandas.read_csv
              parses from a numeric column with the Oracle's float() of the
              same text. Prints the number of values tried and every value
              where the two differ.
    numeric   Compares the Oracle's model of the column types pandas infers
              (numbers, booleans or text) with the dtype pd.read_csv gives a
              one-row column, on every string of up to 4 characters over the
              characters that matter to pandas' number parsers, and on a list
              of words. For strings pandas reads as numbers, also checks that
              Python's float() accepts them, as the Oracle needs. Prints the
              number of strings and every string where the two differ.
    rows      Compares the Oracle's CSV reader with `csv.reader` over a file
              opened in text mode (universal newlines), as upstream's
              DictReader reads it, on 300,000 random texts over the characters
              that matter to the excel dialect. Prints the number of texts and
              every text where the rows or the error differ.
    ours      Prints the Oracle's verdict for every layout case only. Run it
              also on the host's Python (`uv run python -B ... ours`, with the
              upstream task at /up replaced by the UP environment variable) to
              compare the two Pythons.
"""

import hashlib
import itertools
import json
import os
import random
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))

from securebench.core import jsondata  # noqa: E402
from securebench.core.evidence import (  # noqa: E402
    ArtifactEvidence,
    EntryKind,
    FileRead,
    FileStatus,
    FoundFile,
    ListingEntry,
    ListingEvidence,
    ListingStatus,
)
from securebench.core.task import FileSpec, Parser  # noqa: E402
from securebench.evidence.binding import file_evidence  # noqa: E402
from securebench.oracle.worker import load  # noqa: E402

HIDDEN = Path(__file__).resolve().parent
UP = Path(os.environ.get("UP", "/up"))
DOCS = UP / "environment" / "documents"
MIB = 1024 * 1024
EXPECTED = json.loads((HIDDEN / "expected.json").read_text())


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


# The shipped documents, by upstream file name, split as upstream's lists split them.
NAMES = sorted(p.name for p in DOCS.iterdir())
DIGEST = {name: sha256((DOCS / name).read_bytes()) for name in NAMES}
AMOUNTS = EXPECTED["summary"]["amounts"]
INVOICES = [name for name in NAMES if DIGEST[name] in EXPECTED["invoices"]["documents"]]
OTHERS = [name for name in NAMES if DIGEST[name] in EXPECTED["other"]]


def value(number: float | str) -> str:
    return "" if number == "" else repr(float(number))


def rows() -> list[list[str]]:
    """The summary the reference writes: one row per invoice, then the total row."""
    out = [list(EXPECTED["summary"]["header"])]
    for name in INVOICES:
        amounts = AMOUNTS[DIGEST[name]]
        out.append([name, value(amounts["total_amount"]), value(amounts["vat_amount"])])
    total = AMOUNTS["total"]
    out.append(["total", value(total["total_amount"]), value(total["vat_amount"])])
    return out


def text(table: list[list[str]], end: str = "\n") -> bytes:
    return "".join(",".join(row) + end for row in table).encode()


def with_cell(row: int, column: int, cell: str) -> bytes:
    table = rows()
    table[row][column] = cell
    return text(table)


EMPTY_VAT_ROW = next(i for i, r in enumerate(rows()) if i and r[2] == "")
VAT_ROW = next(i for i, r in enumerate(rows()) if i and r[2] not in ("", "0"))
TOTAL_ROW = len(rows()) - 1


def place(app: Path, summary: bytes | None) -> None:
    for folder in ("invoices", "other", "documents"):
        (app / folder).mkdir()
    for name in INVOICES:
        shutil.copy(DOCS / name, app / "invoices" / name)
    for name in OTHERS:
        shutil.copy(DOCS / name, app / "other" / name)
    if summary is not None:
        (app / "invoices" / "summary.csv").write_bytes(summary)


def csv_case(summary: bytes | None) -> Callable[[Path], None]:
    return lambda app: place(app, summary)


def layout(change: Callable[[Path], None]) -> Callable[[Path], None]:
    def build(app: Path) -> None:
        place(app, text(rows()))
        change(app)

    return build


def first_invoice(app: Path) -> Path:
    return app / "invoices" / INVOICES[0]


def relink(app: Path, folder: str, real: str) -> None:
    """Moves a folder to `real` and leaves a relative symlink in its place."""
    (app / folder).rename(app / real)
    os.symlink(real, app / folder)


def table_with(edit: Callable[[list[list[str]]], None], end: str = "\n") -> bytes:
    table = rows()
    edit(table)
    return text(table, end)


def summary_with(edit: Callable[[list[list[str]]], None]) -> Callable[[Path], None]:
    def build(app: Path) -> None:
        place(app, table_with(edit))

    return build


def chain(app: Path, links: int) -> None:
    """`links` symlinks in /app/invoices, link-1 -> link-2 -> ... -> the first
    invoice, and the summary's first row names link-1."""
    for index in range(links, 0, -1):
        target = INVOICES[0] if index == links else f"link-{index + 1}"
        os.symlink(target, app / "invoices" / f"link-{index}")
    (app / "invoices" / "summary.csv").write_bytes(with_cell(1, 0, "link-1"))


def numbered(app: Path, with_total: bool) -> None:
    """Invoices renamed 1 to 10; the summary names them by number, repeating the
    first in place of the total row unless `with_total`."""
    place(app, None)
    table = rows()
    for index, name in enumerate(INVOICES, start=1):
        (app / "invoices" / name).rename(app / "invoices" / str(index))
        table[index][0] = str(index)
    if not with_total:
        table[-1] = table[1]
    (app / "invoices" / "summary.csv").write_bytes(text(table))


def vat_free_rows(*vats: str) -> bytes:
    """Eleven rows that each name an invoice without VAT, and no total row; the
    VAT cells take the values `vats` in turn."""
    free = itertools.cycle([r for r in rows()[1:-1] if r[2] == ""])
    cells = itertools.cycle(vats)
    body = [[r[0], r[1], next(cells)] for r in itertools.islice(free, len(rows()) - 1)]
    return text([rows()[0], *body])


def store_outside_folders(app: Path) -> None:
    """The invoices kept in /app/store, with a symlink to each in /app/invoices."""
    (app / "store").mkdir()
    for name in INVOICES:
        (app / "invoices" / name).rename(app / "store" / name)
        os.symlink(f"../store/{name}", app / "invoices" / name)


CASES: dict[str, Callable[[Path], None]] = {
    "reference": csv_case(text(rows())),
    "crlf": csv_case(text(rows(), "\r\n")),
    "lone-cr": csv_case(text(rows(), "\r")),
    "no-final-newline": csv_case(text(rows()).rstrip(b"\n")),
    "quoted-all": csv_case("".join(",".join(f'"{c}"' for c in r) + "\n" for r in rows()).encode()),
    "rows-reversed": csv_case(text([rows()[0], *reversed(rows()[1:])])),
    "blank-line-between-rows": csv_case(text(rows()).replace(b"\n", b"\n\n", 3)),
    "blank-lines-at-end": csv_case(text(rows()) + b"\n\n\n"),
    "blank-line-first": csv_case(b"\n" + text(rows())),
    "whitespace-only-line": csv_case(text(rows()).replace(b"\n", b"\n \n", 2)),
    "padded-to-1-mib": csv_case(text(rows()) + b"\n" * (MIB - len(text(rows())))),
    "padded-past-1-mib": csv_case(text(rows()) + b"\n" * (MIB - len(text(rows())) + 1)),
    "header-capitalized": csv_case(with_cell(0, 0, "Filename")),
    "header-space": csv_case(with_cell(0, 1, " total_amount")),
    "header-extra-column": csv_case(table_with(lambda t: [r.append("x") for r in t])),
    "byte-order-mark": csv_case(b"\xef\xbb\xbf" + text(rows())),
    "invalid-utf8": csv_case(text(rows()) + b"\xff\n"),
    "empty-file": csv_case(b""),
    "header-only": csv_case(text(rows()[:1])),
    "absent": csv_case(None),
    "trailing-comma-every-row": csv_case(text([rows()[0], *[[*r, ""] for r in rows()[1:]]])),
    "trailing-comma-one-row": csv_case(table_with(lambda t: t[2].append(""))),
    "short-row-empty-vat": csv_case(table_with(lambda t: t[EMPTY_VAT_ROW].pop())),
    "short-row-vat": csv_case(table_with(lambda t: t[VAT_ROW].pop())),
    "no-total-row": csv_case(text(rows()[:-1])),
    "total-row-twice-no-invoice": csv_case(text([rows()[0], *rows()[2:], rows()[-1]])),
    "invoice-row-twice": csv_case(text([rows()[0], rows()[2], *rows()[2:]])),
    "invoice-row-twice-no-total-row": csv_case(text([rows()[0], *rows()[1:-1], rows()[1]])),
    "numbered-invoices-with-total-row": lambda a: numbered(a, with_total=True),
    "numbered-invoices-no-total-row": lambda a: numbered(a, with_total=False),
    "vat-free-rows-vat-False": csv_case(vat_free_rows("False")),
    "vat-free-rows-vat-false-lowercase": csv_case(vat_free_rows("false")),
    "vat-free-rows-vat-0": csv_case(vat_free_rows("0")),
    "vat-free-rows-vat-True": csv_case(vat_free_rows("True")),
    "vat-free-rows-vat-False-and-empty": csv_case(vat_free_rows("False", "")),
    "absolute-filename": csv_case(with_cell(1, 0, "/app/invoices/" + INVOICES[0])),
    "dot-slash-filename": csv_case(with_cell(1, 0, "./" + INVOICES[0])),
    "dot-dot-filename": csv_case(with_cell(1, 0, "../invoices/" + INVOICES[0])),
    "dot-component-after-filename": csv_case(with_cell(1, 0, INVOICES[0] + "/.")),
    "trailing-slash-filename": csv_case(with_cell(1, 0, INVOICES[0] + "/")),
    "double-slash-absolute-filename": csv_case(with_cell(1, 0, "/app//invoices/" + INVOICES[0])),
    "root-dot-dot-filename": csv_case(with_cell(1, 0, "/../app/invoices/" + INVOICES[0])),
    "filename-through-documents": csv_case(
        with_cell(1, 0, "../documents/../invoices/" + INVOICES[0])
    ),
    "filename-through-missing-directory": csv_case(
        with_cell(1, 0, "../missing/../invoices/" + INVOICES[0])
    ),
    "filename-relative-to-app": csv_case(with_cell(1, 0, "invoices/" + INVOICES[0])),
    "filename-dot-dot-after-file": csv_case(with_cell(1, 0, INVOICES[1] + "/../" + INVOICES[0])),
    "filename-outside-app": csv_case(with_cell(1, 0, "/etc/hostname")),
    "filename-other-document": csv_case(with_cell(1, 0, "../other/" + OTHERS[0])),
    "filename-summary": csv_case(with_cell(1, 0, "summary.csv")),
    "filename-space": csv_case(with_cell(1, 0, INVOICES[0] + " ")),
    "filename-na": csv_case(with_cell(1, 0, "NA")),
    "total-space": csv_case(with_cell(TOTAL_ROW, 0, " total")),
    "total-uppercase": csv_case(with_cell(TOTAL_ROW, 0, "Total")),
    "vat-empty-as-0": csv_case(with_cell(EMPTY_VAT_ROW, 2, "0")),
    "vat-empty-as-0.00": csv_case(with_cell(EMPTY_VAT_ROW, 2, "0.00")),
    "vat-empty-as-NA": csv_case(with_cell(EMPTY_VAT_ROW, 2, "NA")),
    "vat-empty-as-N/A": csv_case(with_cell(EMPTY_VAT_ROW, 2, "N/A")),
    "vat-empty-as-nan": csv_case(with_cell(EMPTY_VAT_ROW, 2, "nan")),
    "vat-empty-as-NAN": csv_case(with_cell(EMPTY_VAT_ROW, 2, "NAN")),
    "vat-empty-as-None": csv_case(with_cell(EMPTY_VAT_ROW, 2, "None")),
    "vat-empty-as-null": csv_case(with_cell(EMPTY_VAT_ROW, 2, "null")),
    "vat-empty-as-quoted-empty": csv_case(with_cell(EMPTY_VAT_ROW, 2, '""')),
    "vat-empty-as-dash": csv_case(with_cell(EMPTY_VAT_ROW, 2, "-")),
    "vat-empty-as-space": csv_case(with_cell(EMPTY_VAT_ROW, 2, " ")),
    "vat-empty-as-0.0099": csv_case(with_cell(EMPTY_VAT_ROW, 2, "0.0099")),
    "vat-empty-as-0.01": csv_case(with_cell(EMPTY_VAT_ROW, 2, "0.01")),
    "vat-empty-as-minus-0.0099": csv_case(with_cell(EMPTY_VAT_ROW, 2, "-0.0099")),
    "vat-missing": csv_case(with_cell(VAT_ROW, 2, "")),
    "vat-NA": csv_case(with_cell(VAT_ROW, 2, "NA")),
    "total-NA": csv_case(with_cell(1, 1, "NA")),
    "total-empty": csv_case(with_cell(1, 1, "")),
    "total-nan-text": csv_case(with_cell(1, 1, "NAN")),
    "total-inf": csv_case(with_cell(1, 1, "inf")),
    "total-dollar": csv_case(with_cell(VAT_ROW, 1, "$" + rows()[VAT_ROW][1])),
    "total-quoted-thousands": csv_case(
        with_cell(VAT_ROW, 1, '"' + f"{float(rows()[VAT_ROW][1]):,.2f}" + '"')
    ),
    "total-decimal-comma": csv_case(
        with_cell(VAT_ROW, 1, '"' + rows()[VAT_ROW][1].replace(".", ",") + '"')
    ),
    "total-underscore": csv_case(
        with_cell(VAT_ROW, 1, rows()[VAT_ROW][1][:1] + "_" + rows()[VAT_ROW][1][1:])
    ),
    "total-plus": csv_case(with_cell(VAT_ROW, 1, "+" + rows()[VAT_ROW][1])),
    "total-exponent": csv_case(with_cell(VAT_ROW, 1, f"{float(rows()[VAT_ROW][1]):.6e}")),
    "total-spaces-around": csv_case(with_cell(VAT_ROW, 1, " " + rows()[VAT_ROW][1] + " ")),
    "total-fullwidth-digits": csv_case(
        with_cell(
            VAT_ROW,
            1,
            "".join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in rows()[VAT_ROW][1]),
        )
    ),
    "total-row-plus-0.0099": csv_case(
        with_cell(TOTAL_ROW, 1, repr(AMOUNTS["total"]["total_amount"] + 0.0099))
    ),
    "total-row-plus-0.01": csv_case(
        with_cell(TOTAL_ROW, 1, repr(round(AMOUNTS["total"]["total_amount"] + 0.01, 2)))
    ),
    "total-row-minus-0.01": csv_case(
        with_cell(TOTAL_ROW, 1, repr(round(AMOUNTS["total"]["total_amount"] - 0.01, 2)))
    ),
    "total-row-two-decimals": csv_case(with_cell(TOTAL_ROW, 1, "81315.20")),
    "net-instead-of-gross": csv_case(
        with_cell(
            VAT_ROW,
            1,
            repr(round(float(rows()[VAT_ROW][1]) - float(rows()[VAT_ROW][2]), 2)),
        )
    ),
    "embedded-quote-filename": csv_case(with_cell(1, 0, '"' + INVOICES[0] + '"x')),
    "newline-in-quoted-filename": csv_case(with_cell(1, 0, '"' + INVOICES[0] + '\n"')),
    "claim-column-values": csv_case(text(rows()) + b"verdict,passed,\n"),
    "extra-json-in-invoices": layout(lambda a: (a / "invoices" / "x.json").write_text("{}")),
    "extra-txt-in-invoices": layout(lambda a: (a / "invoices" / "x.txt").write_text("x")),
    "subdirectory-in-invoices": layout(lambda a: (a / "invoices" / "ocr").mkdir()),
    "subdirectory-in-documents": layout(lambda a: (a / "documents" / "done").mkdir()),
    "subdirectory-in-other": layout(lambda a: (a / "other" / "x").mkdir()),
    "invoice-copied-twice": layout(
        lambda a: shutil.copy(first_invoice(a), a / "invoices" / ("copy-" + INVOICES[0]))
    ),
    "invoice-also-in-other": layout(
        lambda a: shutil.copy(first_invoice(a), a / "other" / INVOICES[0])
    ),
    "invoice-left-in-documents": layout(
        lambda a: shutil.copy(first_invoice(a), a / "documents" / INVOICES[0])
    ),
    "other-in-invoices": layout(
        lambda a: shutil.move(a / "other" / OTHERS[0], a / "invoices" / OTHERS[0])
    ),
    "documents-removed": layout(lambda a: (a / "documents").rmdir()),
    "other-missing": layout(lambda a: shutil.rmtree(a / "other")),
    "symlink-to-invoice-in-invoices": layout(
        lambda a: os.symlink(INVOICES[0], a / "invoices" / ("link-" + INVOICES[0]))
    ),
    "symlink-to-directory-in-documents": layout(
        lambda a: os.symlink("../other", a / "documents" / "other")
    ),
    "symlink-dangling-in-documents": layout(lambda a: os.symlink("gone", a / "documents" / "x")),
    "symlink-loop-in-documents": layout(
        lambda a: (os.symlink("b", a / "documents" / "a"), os.symlink("a", a / "documents" / "b"))
    ),
    "symlink-to-invoice-in-documents": layout(
        lambda a: os.symlink("../invoices/" + INVOICES[0], a / "documents" / "x")
    ),
    "symlink-to-other-in-other-from-invoices": layout(
        lambda a: os.symlink("../other/" + OTHERS[0], a / "invoices" / "x")
    ),
    "invoice-moved-to-other-symlinked-back": layout(
        lambda a: (
            first_invoice(a).rename(a / "other" / INVOICES[0]),
            os.symlink("../other/" + INVOICES[0], first_invoice(a)),
        )
    ),
    "summary-row-names-symlink": layout(
        lambda a: (
            os.symlink(INVOICES[0], a / "invoices" / "alias"),
            (a / "invoices" / "summary.csv").write_bytes(with_cell(1, 0, "alias")),
        )
    ),
    "invoices-link-component-255": layout(lambda a: os.symlink("a" * 255, a / "invoices" / "junk")),
    "invoices-link-component-256": layout(lambda a: os.symlink("a" * 256, a / "invoices" / "junk")),
    "other-link-component-255": layout(lambda a: os.symlink("a" * 255, a / "other" / "junk")),
    "other-link-component-256": layout(lambda a: os.symlink("a" * 256, a / "other" / "junk")),
    "documents-link-component-255": layout(
        lambda a: os.symlink("a" * 255, a / "documents" / "junk")
    ),
    "documents-link-component-256": layout(
        lambda a: os.symlink("a" * 256, a / "documents" / "junk")
    ),
    "documents-link-long-component-dir": layout(
        lambda a: os.symlink("a" * 256 + "/..", a / "documents" / "junk")
    ),
    "filename-long-component": csv_case(with_cell(1, 0, "a" * 256 + "/../" + INVOICES[0])),
    "filename-component-255-missing": csv_case(with_cell(1, 0, "a" * 255 + "/../" + INVOICES[0])),
    "symlink-chain-40": layout(lambda a: chain(a, 40)),
    "symlink-chain-41": layout(lambda a: chain(a, 41)),
    "invoices-in-store-symlinked": layout(store_outside_folders),
    "summary-symlink-to-app": layout(
        lambda a: (
            (a / "invoices" / "summary.csv").rename(a / "summary-real.csv"),
            os.symlink("../summary-real.csv", a / "invoices" / "summary.csv"),
        )
    ),
    "unterminated-quote-last-field-newline": csv_case(
        with_cell(TOTAL_ROW, 2, '"' + rows()[TOTAL_ROW][2])
    ),
    "unterminated-quote-last-field-no-newline": csv_case(
        with_cell(TOTAL_ROW, 2, '"' + rows()[TOTAL_ROW][2]).rstrip(b"\n")
    ),
    "unterminated-quote-own-last-line": csv_case(text(rows()) + b'"\n'),
    "leading-extra-column-data-rows": csv_case(text([rows()[0], *[["x", *r] for r in rows()[1:]]])),
    "two-leading-extra-columns": csv_case(text([rows()[0], *[["x", "y", *r] for r in rows()[1:]]])),
    "leading-extra-column-first-row-only": csv_case(
        text([rows()[0], ["x", *rows()[1]], *rows()[2:]])
    ),
    "leading-extra-column-later-row-longer": csv_case(
        text([rows()[0], *[["x", *r] for r in rows()[1:-1]], ["x", "y", *rows()[-1]]])
    ),
    "leading-extra-column-short-last-row": csv_case(
        text([rows()[0], *[["x", *r] for r in rows()[1:-1]], rows()[-1]])
    ),
    "nul-in-filename": csv_case(with_cell(1, 0, INVOICES[0] + "\x00")),
    "nul-alone-vat-empty": csv_case(with_cell(EMPTY_VAT_ROW, 2, "\x00")),
    "nul-in-vat": csv_case(with_cell(VAT_ROW, 2, rows()[VAT_ROW][2] + "\x00")),
    "vat-zero-4300-digits": csv_case(with_cell(EMPTY_VAT_ROW, 2, "0" * 4300)),
    "vat-zero-4301-digits": csv_case(with_cell(EMPTY_VAT_ROW, 2, "0" * 4301)),
    "total-int-padded-4400": csv_case(
        with_cell(EMPTY_VAT_ROW, 1, "0" * 4400 + str(int(float(rows()[EMPTY_VAT_ROW][1]))))
    ),
    "nul-before-filename": csv_case(with_cell(1, 0, "\x00" + INVOICES[0])),
    "nul-in-total-quoted": csv_case(with_cell(1, 1, '"' + rows()[1][1] + '\x00junk"')),
    "nul-after-total-keyword": csv_case(with_cell(TOTAL_ROW, 0, "total\x00x")),
    "invoices-dir-symlink": layout(lambda a: relink(a, "invoices", "invoices-real")),
    "other-dir-symlink": layout(lambda a: relink(a, "other", "other-real")),
    "documents-dir-symlink-empty": layout(lambda a: relink(a, "documents", "empty")),
}


def native(app: Path, test_outputs: object) -> bool:
    for name in sorted(dir(test_outputs)):
        if name.startswith("test_"):
            try:
                getattr(test_outputs, name)()
            except Exception:  # pytest counts any exception as a failure
                return False
    return True


def listing(app: Path, folder: str) -> ListingEvidence:
    """A listing as lookup gives it for this pack: entries directly in the folder."""
    path = f"/app/{folder}"
    directory = app / folder
    if not directory.exists() and not directory.is_symlink():
        return ListingEvidence(path, ListingStatus.ABSENT, ())
    if directory.is_symlink() or not directory.is_dir():
        return ListingEvidence(path, ListingStatus.NOT_DIRECTORY, ())
    entries: list[ListingEntry] = []
    for child in sorted(directory.iterdir(), key=lambda p: p.name.encode()):
        if child.is_symlink():
            entries.append(
                ListingEntry(child.name, EntryKind.SYMLINK, None, None, None, os.readlink(child))
            )
        elif child.is_dir():
            entries.append(ListingEntry(child.name, EntryKind.DIR, None, None, None, None))
        else:
            data = child.read_bytes()
            entries.append(
                ListingEntry(child.name, EntryKind.FILE, len(data), sha256(data), False, None)
            )
    return ListingEvidence(path, ListingStatus.PRESENT, tuple(entries))


def summary_read(app: Path) -> FileRead:
    summary = app / "invoices" / "summary.csv"
    if (app / "invoices").is_symlink() or not (app / "invoices").is_dir():
        return FileStatus.ABSENT
    if summary.is_symlink() or (summary.exists() and not summary.is_file()):
        return FileStatus.NOT_REGULAR
    if not summary.exists():
        return FileStatus.ABSENT
    data = summary.read_bytes()
    return FoundFile(data, sha256(data), False)


class Resources:
    def read(self, relative_path: str) -> bytes:
        return (HIDDEN / relative_path).read_bytes()

    def read_json(self, relative_path: str) -> jsondata.JsonValue:
        data = self.read(relative_path)
        return jsondata.decode(data, len(data))


def ours(app: Path, oracle: object) -> bool:
    contexts = oracle.plan(Resources(), 0).artifact_contexts  # type: ignore[attr-defined]
    spec = FileSpec("/app/invoices/summary.csv", Parser.TEXT, MIB)
    folders = tuple(listing(app, folder) for folder in ("invoices", "other", "documents"))
    summary = (file_evidence(spec, summary_read(app)),)
    evidence = {
        "invoices": ArtifactEvidence("invoices", (), folders),
        "other": ArtifactEvidence("other", (), folders),
        "summary": ArtifactEvidence("summary", summary, folders),
        "documents": ArtifactEvidence("documents", (), folders),
    }
    return all(
        oracle.judge(check, contexts[check], found).passed  # type: ignore[attr-defined]
        for check, found in evidence.items()
    )


def fresh(app: Path) -> None:
    for child in app.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
        else:
            shutil.rmtree(child)


def verdict(passed: bool) -> str:
    return "pass" if passed else "fail"


def run_layouts(with_native: bool) -> None:
    oracle = load(HIDDEN / "oracle.py")
    test_outputs = None
    if with_native:
        sys.path.insert(0, str(UP / "tests"))
        import test_outputs  # upstream's tests/test_outputs.py, verbatim
    for name, build in CASES.items():
        if with_native:
            app = Path("/app")
            app.mkdir(exist_ok=True)
            fresh(app)
            build(app)
            upstream = verdict(native(app, test_outputs))
            mine = verdict(ours(app, oracle))
            print(name, upstream, mine, "" if upstream == mine else "DIFFERENT")
        else:
            with tempfile.TemporaryDirectory() as scratch:
                app = Path(scratch) / "app"
                app.mkdir()
                build(app)
                print(name, verdict(ours(app, oracle)))


def run_values() -> None:
    import io

    import pandas as pd

    targets = sorted(
        {float(a["total_amount"]) for a in AMOUNTS.values()}
        | {float(a["vat_amount"] or 0) for a in AMOUNTS.values()}
    )
    generator = random.Random(57)
    tried = 0
    differ = 0
    for target in targets:
        texts: list[str] = []
        for cents in (-1, 1):
            for digits in range(2, 18):
                texts.append(f"{target + cents * 0.01:.{digits}f}")
        for _ in range(20000):
            offset = generator.uniform(-0.0105, 0.0105)
            texts.append(f"{target + offset:.{generator.randint(2, 17)}f}")
            texts.append(repr(target + offset))
        for step in range(-40, 41):
            # Neighbouring doubles of target +/- 0.01, written exactly.
            for edge in (target - 0.01, target + 0.01):
                texts.append(repr(edge + step * abs(edge) * 2.0**-52))
        frame = pd.read_csv(io.StringIO("x\n" + "\n".join(texts) + "\n"))
        assert frame["x"].dtype == "float64"
        for raw, parsed in zip(texts, frame["x"], strict=True):
            tried += 1
            upstream = abs(float(parsed) - target) < 0.01
            mine = abs(float(raw) - target) < 0.01
            if upstream != mine:
                differ += 1
                print("DIFFERENT", target, raw, repr(float(parsed)), repr(float(raw)))
    print("values tried", tried, "different", differ)


def run_numeric() -> None:
    import io

    import pandas as pd

    oracle = load(HIDDEN / "oracle.py")
    alphabet = ["0", "1", ".", "e", "E", "+", "-", " ", "\t", "i", "n", "f", "a"]
    words = [
        "inf",
        "Inf",
        "INF",
        "-inf",
        "+inf",
        "infinity",
        "Infinity",
        "-Infinity",
        "+INFINITY",
        " inf",
        "inf ",
        "infinit",
        "infinityy",
        "NAN",
        "nAn",
        "-nan",
        "+nan",
        "nan ",
        "True",
        "TRUE",
        "true",
        "tRue",
        " True",
        "True ",
        "False",
        "FALSE",
        "false",
        "fAlse",
        "1_0",
        "0x10",
        "\uff11",
        "1e400",
        "-1e400",
        "1e-400",
        "9" * 25,
        "1" * 400,
        "18446744073709551615",
        "18446744073709551616",
        "-9223372036854775809",
        "1.5e+3",
        "1.e3",
        ".e3",
        "1e+",
        "1e-",
        "e3",
        "++1",
        "1 2",
        "9223372036854775807",
        "9223372036854775808",
        "-9223372036854775808",
        "18446744073709551614",
        " 18446744073709551615 ",
        "+18446744073709551615",
        "1.7976931348623157e308",
        "1.7976931348623158e308",
        "1.8e308",
        "1e308",
        "1e309",
        "0.1e309",
        "10e307",
        "-1.8e308",
        "4.9e-324",
        "1e-330",
        "1" * 400 + ".5",
        "1" * 308 + ".0",
        "1" * 309 + ".0",
        "0" * 4301,
        "0" * 5000 + "1",
        "-" + "0" * 4400 + "9223372036854775808",
        "-" + "0" * 4400 + "9223372036854775809",
        "0" * 4400 + "18446744073709551615",
        "+" + "0" * 4400 + "18446744073709551616",
        "1" * 4301,
        "-" + "1" * 4400,
        "TrUe",
        "fALSE",
        " true",
        "false ",
    ]
    strings = [*words]
    for size in range(1, 5):
        strings.extend("".join(chars) for chars in itertools.product(alphabet, repeat=size))
    tried = 0
    differ = 0
    for raw in strings:
        if raw in oracle.NA_STRINGS:  # type: ignore[attr-defined]
            continue
        tried += 1
        frame = pd.read_csv(io.StringIO("x,y\n" + raw + ",1\n"), dtype=None)
        kind = frame["x"].dtype.kind
        upstream = "number" if kind in "iuf" else "bool" if kind == "b" else "text"
        mine = oracle._column_kind([raw])  # type: ignore[attr-defined]
        problem = upstream != mine
        if upstream == "number":
            try:
                float(raw)
            except ValueError:
                problem = True
        if problem:
            differ += 1
            print("DIFFERENT", repr(raw), upstream, mine)
    print("strings tried", tried, "different", differ)


def run_rows() -> None:
    import csv
    import io

    oracle = load(HIDDEN / "oracle.py")
    generator = random.Random(52)
    alphabet = [",", '"', "\n", "\r", "a", "b", " ", "\x00"]
    differ = 0
    tries = 300000
    for _ in range(tries):
        text = "".join(generator.choice(alphabet) for _ in range(generator.randint(0, 14)))
        try:
            expected: object = list(csv.reader(io.StringIO(text, newline=None)))
        except csv.Error:
            expected = "error"
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        try:
            got: object = oracle._csv_rows(normalized)[0]  # type: ignore[attr-defined]
        except Exception:  # the Oracle's _CsvError
            got = "error"
        if got != expected:
            differ += 1
            print("DIFFERENT", repr(text), expected, got)
    print("texts tried", tries, "different", differ)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "layouts":
        run_layouts(with_native=True)
    elif mode == "ours":
        run_layouts(with_native=False)
    elif mode == "values":
        run_values()
    elif mode == "rows":
        run_rows()
    elif mode == "numeric":
        run_numeric()
    else:
        raise SystemExit(f"unknown mode {mode}")
