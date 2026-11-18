"""The parser registry: UTF-8 text and strict JSON."""

from securebench.core import jsondata
from securebench.core.errors import Rejected
from securebench.core.evidence import Text
from securebench.core.jsondata import JsonValue
from securebench.core.task import Parser

# A result record holds a parsed file's value seven levels down (record, judged
# list, entry, evidence, file list, file, value wrapper), and the whole record
# must fit within `jsondata.MAX_DEPTH`. A deeper value would be judged and then
# fail to be recorded, which a candidate could use to turn its failure into a
# missing attempt.
MAX_EVIDENCE_DEPTH = jsondata.MAX_DEPTH - 7


def parse(parser: Parser, data: bytes) -> Text | JsonValue:
    """Parse `data` with the registry parser named `parser`.

    `text`: strict UTF-8 without a byte-order mark, split into lines on `\\n`
    (a final newline does not start an empty line; `\\r` is kept). `json`:
    the strict decoder in `core`, nested at most `MAX_EVIDENCE_DEPTH`.
    Raises `Rejected`.
    """
    match parser:
        case Parser.TEXT:
            return _text(data)
        case Parser.JSON:
            value = jsondata.decode(data, len(data))
            if jsondata.depth(value) > MAX_EVIDENCE_DEPTH:
                raise Rejected(f"JSON nesting exceeds {MAX_EVIDENCE_DEPTH} levels")
            return value


def _text(data: bytes) -> Text:
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise Rejected(f"text is not valid UTF-8 at byte {error.start}") from None
    if text.startswith("﻿"):
        raise Rejected("text starts with a byte-order mark")
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return Text(text, tuple(lines))
