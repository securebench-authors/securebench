"""Oracle for terminal-bench/regex-chess.

Upstream's tests/test_outputs.py has four tests. test_not_long becomes two
artifact checks on /app/re.json, one per assertion. Each of the three game
tests becomes one case of the protocol check "legal-moves": the adapter
applies the candidate's regexes to every position the test walks through, and
judge repeats verify_legal_moves on the strings it reports. The expected
positions, computed with python-chess 1.11.2 by hidden/derive.py, are in
hidden/cases.json.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

# test_not_long: len(open("/app/re.json").read()) < 10e6
MAX_CHARACTERS_EXCLUSIVE = 10_000_000
# test_not_long: len(json.loads(open("/app/re.json").read())) < 1e5
MAX_PAIRS_EXCLUSIVE = 100_000


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    cases = []
    for case in data["cases"]:
        cases.append(
            Case(
                challenge={"fens": case["fens"]},
                context={"test": case["test"], "fens": case["fens"], "expected": case["expected"]},
            )
        )
    return Plan(
        artifact_contexts={"not-long-characters": None, "not-long-pairs": None},
        cases={"legal-moves": tuple(cases)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == "not-long-characters" and isinstance(evidence, ArtifactEvidence):
        return _judge_characters(evidence)
    if check_id == "not-long-pairs" and isinstance(evidence, ArtifactEvidence):
        return _judge_pairs(evidence)
    if check_id == "legal-moves" and isinstance(evidence, CaseEvidence):
        return _judge_game(context, evidence)
    return Judgment(False, {"reason": "unexpected check or evidence"})


def _judge_characters(evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "expected exactly one file"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return Judgment(False, {"reason": f"/app/re.json is {found.status.value}", "detail": found.reason})
    text = found.value.text
    # Upstream reads the file in text mode, whose universal newlines turn each
    # "\r\n" into one character; SecureBench's text parser keeps the "\r".
    characters = len(text) - text.count("\r\n")
    if characters >= MAX_CHARACTERS_EXCLUSIVE:
        return Judgment(False, {"reason": "re.json is too long", "characters": characters})
    return Judgment(True, {"characters": characters})


def _judge_pairs(evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "expected exactly one file"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return Judgment(False, {"reason": f"/app/re.json is {found.status.value}", "detail": found.reason})
    length = _json_length(found.value.text)
    if length is None:
        return Judgment(False, {"reason": "re.json is not JSON whose top-level value has a length"})
    if length >= MAX_PAIRS_EXCLUSIVE:
        return Judgment(False, {"reason": "re.json has too many pairs", "pairs": length})
    return Judgment(True, {"pairs": length})


# Upstream takes len(json.loads(text)) with Python's json module, which
# accepts more than SecureBench's strict JSON parser (lone surrogates, NaN,
# duplicate keys, deep nesting). So the Oracle reads the file as text and
# computes that length itself: the number of elements of a top-level array,
# the number of distinct keys of a top-level object, or the number of code
# points of a top-level string, decoded as Python's json does. Any other
# top-level value has no len() upstream. The scan validates only what it needs;
# a file Python's json rejects also fails every game case, where the adapter's
# json.load raises, so the overall verdict is upstream's. The text is at most
# 16 MiB, and the scan takes time linear in it: every loop advances the index,
# and each str.find resumes after the previous hit instead of rescanning.

_JSON_WHITESPACE = " \t\n\r"
_SIMPLE_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
_HEX_DIGITS = "0123456789abcdefABCDEF"
_MAX_DEPTH = 10_000


def _skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index] in _JSON_WHITESPACE:
        index += 1
    return index


def _hex4(text: str, index: int) -> int | None:
    digits = text[index : index + 4]
    if len(digits) != 4 or any(c not in _HEX_DIGITS for c in digits):
        return None
    return int(digits, 16)


def _next(text: str, needle: str, index: int, cache: dict[str, int]) -> int:
    """The position of the next `needle` at or after `index`, or len(text).

    The last position found is kept in `cache` and reused while it is still
    ahead of `index`. Indexes only grow during a scan, so the searches for one
    needle cover the text once in total.
    """
    found = cache.get(needle, -1)
    if found < index:
        found = text.find(needle, index)
        if found < 0:
            found = len(text)
        cache[needle] = found
    return found


def _decode_string(text: str, index: int, cache: dict[str, int]) -> tuple[str, int] | None:
    """Decode the JSON string whose opening quote is at index - 1, as Python's
    json.scanstring does in strict mode; return it and the index after the
    closing quote."""
    parts: list[str] = []
    while True:
        quote = _next(text, '"', index, cache)
        backslash = _next(text, "\\", index, cache)
        if quote == len(text):
            return None
        stop = min(quote, backslash)
        chunk = text[index:stop]
        if any(ord(c) < 0x20 for c in chunk):
            return None
        parts.append(chunk)
        if stop == quote:
            return "".join(parts), quote + 1
        escape = text[stop + 1 : stop + 2]
        if escape in _SIMPLE_ESCAPES:
            parts.append(_SIMPLE_ESCAPES[escape])
            index = stop + 2
            continue
        if escape != "u":
            return None
        unit = _hex4(text, stop + 2)
        if unit is None:
            return None
        index = stop + 6
        if 0xD800 <= unit <= 0xDBFF and text[index : index + 2] == "\\u":
            low = _hex4(text, index + 2)
            if low is not None and 0xDC00 <= low <= 0xDFFF:
                unit = 0x10000 + (((unit - 0xD800) << 10) | (low - 0xDC00))
                index += 6
        parts.append(chr(unit))


def _json_length(text: str) -> int | None:
    start = _skip_whitespace(text, 0)
    if start >= len(text):
        return None
    opening = text[start]
    if opening == '"':
        decoded = _decode_string(text, start + 1, {})
        if decoded is None or _skip_whitespace(text, decoded[1]) != len(text):
            return None
        return len(decoded[0])
    if opening not in "[{":
        return None
    closers = {"[": "]", "{": "}"}
    stack = [closers[opening]]
    elements = 0
    keys: set[str] = set()
    expect_key = opening == "{"
    cache: dict[str, int] = {}
    index = _skip_whitespace(text, start + 1)
    empty = index < len(text) and text[index] == stack[0]
    while index < len(text) and stack:
        c = text[index]
        if c == '"':
            decoded = _decode_string(text, index + 1, cache)
            if decoded is None:
                return None
            if len(stack) == 1 and expect_key:
                keys.add(decoded[0])
                expect_key = False
            index = decoded[1]
            continue
        if c in closers:
            # Python's json raises RecursionError well before this depth.
            if len(stack) + 1 >= _MAX_DEPTH:
                return None
            stack.append(closers[c])
        elif c in "]}":
            if c != stack[-1]:
                return None
            stack.pop()
        elif c == "," and len(stack) == 1:
            elements += 1
            expect_key = opening == "{"
        index += 1
    if stack or _skip_whitespace(text, index) != len(text):
        return None
    if opening == "{":
        return len(keys)
    return 0 if empty else elements + 1


def _judge_game(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or set(observation) != {"outputs"}:
        return Judgment(False, {"reason": "observation is not {outputs}"})
    outputs = observation["outputs"]
    fens = context["fens"]
    expected = context["expected"]
    if not isinstance(outputs, list) or len(outputs) != len(fens):
        return Judgment(False, {"reason": "expected one output per position", "positions": len(fens)})
    for index, (fen, output, legal) in enumerate(zip(fens, outputs, expected, strict=True)):
        if not isinstance(output, str):
            return Judgment(False, {"reason": "output is not a string", "position": index})
        failure = _verify_legal_moves(output, frozenset(legal))
        if failure is not None:
            failure["position"] = index
            failure["fen"] = fen
            failure["test"] = context["test"]
            return Judgment(False, failure)
    return Judgment(True, {"test": context["test"], "positions": len(fens)})


def _verify_legal_moves(output: str, python_chess_moves: frozenset[str]) -> dict[str, JsonValue] | None:
    # run_solution's post-processing and verify_legal_moves' two assertions,
    # in upstream's order. Upstream counts lines, not distinct lines, so a
    # repeated line is not deduplicated here either.
    our_moves = [" ".join(x.split(" ")[:-2]) for x in output.split("\n")]
    for x in our_moves:
        # The second form accepts an en-passant square that python-chess,
        # which prints one only when an en-passant capture is legal, omits.
        if not (x in python_chess_moves or x.rpartition(" ")[0] + " -" in python_chess_moves):
            return {"reason": "move not found in python-chess moves", "move": x[:256]}
    if len(our_moves) != len(python_chess_moves):
        return {"reason": "wrong number of moves", "ours": len(our_moves), "python_chess": len(python_chess_moves)}
    return None
